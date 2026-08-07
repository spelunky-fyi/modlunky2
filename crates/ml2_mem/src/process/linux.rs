//! Linux backend: attach to Spel2.exe running under Wine/Proton, read
//! through `/proc/<pid>/mem`, enumerate mappings from `/proc/<pid>/maps`,
//! scan for the feedcode marker.
//!
//! Wine doesn't emulate: the PE is loaded into an ordinary Linux process and
//! Win32 virtual addresses are that process's virtual addresses. So every
//! `#[offset]` in `ml2_trackers` applies unchanged and only the mechanism for
//! fetching bytes differs from `win.rs`.
//!
//! Two mechanisms exist for that: `process_vm_readv(2)` and pread on
//! `/proc/<pid>/mem`. They share a permission model (both gated on
//! `PTRACE_MODE_ATTACH`) and perform comparably for the one-region-at-a-time
//! reads we do, so this uses the file, which needs no `libc` dependency.
//!
//! Permissions are the one real difference from Windows. Reading another
//! process requires passing the ptrace access check, and distributions
//! commonly ship `kernel.yama.ptrace_scope=1`, which narrows that to
//! descendants of the caller.
//!
//! In practice that turns out not to bite, for a reason worth writing down
//! because it is not obvious. Modern Proton runs games inside a
//! pressure-vessel container, which puts them in a user namespace owned by
//! the invoking user. Yama also allows the read when the caller has
//! `CAP_SYS_PTRACE` in the target's user namespace, and per
//! `user_namespaces(7)` a process has every capability in a namespace whose
//! owner UID matches its own. So a Proton-launched game is readable by the
//! same user whatever its ancestry, and it makes no difference whether Steam
//! or modlunky2 started it. Measured, not assumed: an ordinary detached
//! process in the root-owned init namespace is refused under the same
//! setting, while the game is not.
//!
//! `AccessDenied` therefore covers the configurations where that doesn't
//! hold: `ptrace_scope` of 2 or 3, or a game run outside a container by a
//! bare wine via `command_prefix`. Being a descendant still always works,
//! which is why it stays the suggested fix.

use std::fs::File;
use std::io::ErrorKind;
use std::os::unix::fs::FileExt;
use std::sync::OnceLock;

use super::{FEEDCODE_MARKER, SPEL2_EXE_NAME};
use crate::error::{MemError, Result};
use crate::process::ReadProcess;

/// Matches `win.rs`. State lives well above this on both platforms: under
/// Proton the marker turns up around 0x79xx_xxxx_xxxx, so the same floor
/// skips the low mappings without risking a miss.
const SCAN_MIN_ADDR: u64 = 0x400_0000_0000;

/// Bytes per pread while scanning. Larger than the Windows backend's 4 KiB
/// because a pread costs one syscall regardless of size and `maps` regions
/// are megabytes, not pages.
const SCAN_CHUNK: usize = 64 * 1024;

/// Attached game process. Holds the open `/proc/<pid>/mem` handle; dropping
/// it closes the fd.
pub struct Spel2Process {
    pid: u32,
    mem: File,
    /// Cached feedcode address so subsequent state reads don't re-scan.
    feedcode: OnceLock<u64>,
}

impl Spel2Process {
    /// Opens `/proc/<pid>/mem`. The open itself is what triggers the ptrace
    /// access check, so a process we're not allowed to read fails here rather
    /// than on the first read.
    pub fn from_pid(pid: u32) -> Result<Self> {
        let path = format!("/proc/{pid}/mem");
        let mem = File::open(&path).map_err(|e| match e.kind() {
            // `msg` is shown to the user as-is, so it says what to do rather
            // than what failed. The pid and the /proc path are noise there;
            // they come back via the `Display` impl, which is what gets
            // logged.
            //
            // Deliberately does not suggest `sysctl kernel.yama.ptrace_scope=0`,
            // which is the fix most search results give. That turns off a
            // hardening measure for the whole machine, letting any process
            // read any other of the same user's, permanently, to fix one app.
            //
            // Says "unusual" because it is: the normal Proton path is readable
            // whatever started the game (see the module docs). Reaching here
            // means an unusual setup, so the text avoids asserting a cause it
            // can't know and offers the one fix that always works.
            ErrorKind::PermissionDenied => MemError::AccessDenied {
                pid,
                msg: format!(
                    "Spelunky 2 is running, but Linux won't let modlunky2 read \
                     its memory (kernel.yama.ptrace_scope={}), so the trackers \
                     are stuck waiting. This is unusual. Launching the game \
                     from modlunky2 should fix it, since the trackers can \
                     always read a game modlunky2 started itself.",
                    ptrace_scope().unwrap_or_else(|| "?".into())
                ),
            },
            ErrorKind::NotFound => MemError::NotAttached,
            _ => MemError::Read {
                addr: 0,
                msg: format!("open {path}: {e}"),
            },
        })?;
        Ok(Self {
            pid,
            mem,
            feedcode: OnceLock::new(),
        })
    }

    /// Convenience: find Spel2.exe, open it. Returns `NotAttached` when the
    /// game isn't running.
    pub fn attach() -> Result<Self> {
        let Some(pid) = find_spelunky2_pid() else {
            return Err(MemError::NotAttached);
        };
        Self::from_pid(pid)
    }

    /// Scans candidate mappings for the feedcode marker, caching the result
    /// so subsequent calls are O(1). Returns `FeedcodeMissing` when the game
    /// is still loading and hasn't written the marker yet, which is normal
    /// for the first several seconds after launch.
    pub fn get_feedcode(&self) -> Result<u64> {
        if let Some(addr) = self.feedcode.get() {
            return Ok(*addr);
        }
        let mut buf = vec![0u8; SCAN_CHUNK];
        for region in self.scan_candidates()? {
            if let Some(addr) = self.find_in_region(&region, FEEDCODE_MARKER, &mut buf) {
                let _ = self.feedcode.set(addr);
                return Ok(addr);
            }
        }
        Err(MemError::FeedcodeMissing)
    }

    /// The mappings worth scanning: the Linux spelling of the Windows
    /// backend's MEM_COMMIT + MEM_PRIVATE + not-PAGE_NOACCESS filter.
    /// `rw-p` covers committed and writable and not a shared mapping, and an
    /// empty pathname is the anonymous (not file-backed) part, which is where
    /// a Wine `VirtualAlloc` lands.
    ///
    /// Narrowing this way matters: with the address floor it is roughly 400 MB
    /// to scan instead of 1 GB, and the marker has been observed inside it.
    fn scan_candidates(&self) -> Result<Vec<Region>> {
        let path = format!("/proc/{}/maps", self.pid);
        let maps = std::fs::read_to_string(&path).map_err(|e| MemError::Read {
            addr: 0,
            msg: format!("read {path}: {e}"),
        })?;
        let mut out = Vec::new();
        // Line format: `start-end perms offset dev inode [pathname]`
        for line in maps.lines() {
            let fields: Vec<&str> = line.split_whitespace().collect();
            let [range, perms, _offset, _dev, _inode, pathname @ ..] = fields.as_slice() else {
                continue;
            };
            if *perms != "rw-p" || !pathname.is_empty() {
                continue;
            }
            let Some((start, end)) = range.split_once('-') else {
                continue;
            };
            let (Ok(start), Ok(end)) =
                (u64::from_str_radix(start, 16), u64::from_str_radix(end, 16))
            else {
                continue;
            };
            if end > SCAN_MIN_ADDR {
                out.push(Region {
                    start: start.max(SCAN_MIN_ADDR),
                    end,
                });
            }
        }
        Ok(out)
    }

    /// Scans one region chunk-by-chunk, overlapping by `needle.len() - 1` so
    /// a marker straddling a chunk boundary is still found.
    fn find_in_region(&self, region: &Region, needle: &[u8], buf: &mut [u8]) -> Option<u64> {
        if needle.is_empty() {
            return None;
        }
        let overlap = needle.len() - 1;
        let mut cursor = region.start;
        while cursor < region.end {
            let want = ((region.end - cursor) as usize)
                .min(buf.len())
                .max(needle.len());
            let slice = &mut buf[..want];
            // A mapping can be listed and still refuse a read: it may have
            // been unmapped since we read `maps`, or hold a guard page. Skip
            // the rest of the region rather than failing the whole scan.
            if self.mem.read_exact_at(slice, cursor).is_err() {
                return None;
            }
            if let Some(pos) = slice.windows(needle.len()).position(|w| w == needle) {
                return Some(cursor + pos as u64);
            }
            if want <= overlap {
                return None;
            }
            cursor += (want - overlap) as u64;
        }
        None
    }
}

impl ReadProcess for Spel2Process {
    fn read_bytes(&self, addr: u64, dst: &mut [u8]) -> Result<()> {
        self.mem
            .read_exact_at(dst, addr)
            .map_err(|e| MemError::Read {
                addr,
                msg: e.to_string(),
            })
    }
}

struct Region {
    start: u64,
    end: u64,
}

/// Enumerates `/proc/*/comm` and returns the PID of the first Spel2.exe.
/// `comm` is truncated to 15 characters, which the 9-character name survives.
/// Returns None when the game isn't running.
pub fn find_spelunky2_pid() -> Option<u32> {
    let mut found: Option<u32> = None;
    for entry in std::fs::read_dir("/proc").ok()?.flatten() {
        let Some(pid) = entry
            .file_name()
            .to_str()
            .and_then(|s| s.parse::<u32>().ok())
        else {
            continue;
        };
        let Ok(comm) = std::fs::read_to_string(entry.path().join("comm")) else {
            continue;
        };
        if comm.trim_end_matches('\n') == SPEL2_EXE_NAME {
            // Lowest pid wins, so repeated calls pick the same process when
            // several somehow exist.
            found = Some(found.map_or(pid, |f: u32| f.min(pid)));
        }
    }
    found
}

/// Current `kernel.yama.ptrace_scope`, for the `AccessDenied` message.
/// None when the kernel has no Yama LSM, in which case restriction isn't the
/// explanation.
fn ptrace_scope() -> Option<String> {
    std::fs::read_to_string("/proc/sys/kernel/yama/ptrace_scope")
        .ok()
        .map(|s| s.trim().to_string())
}
