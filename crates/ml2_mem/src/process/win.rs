//! Windows backend: attach to Spel2.exe, ReadProcessMemory, enumerate
//! committed pages, scan for the feedcode marker.

use std::ffi::c_void;

use windows::Win32::Foundation::{CloseHandle, HANDLE};
use windows::Win32::System::Diagnostics::Debug::ReadProcessMemory;
use windows::Win32::System::Diagnostics::ToolHelp::{
    CreateToolhelp32Snapshot, PROCESSENTRY32, Process32First, Process32Next, TH32CS_SNAPPROCESS,
};
use windows::Win32::System::Memory::{
    MEM_COMMIT, MEM_PRIVATE, MEMORY_BASIC_INFORMATION, PAGE_NOACCESS, VirtualQueryEx,
};
use windows::Win32::System::Threading::{OpenProcess, PROCESS_QUERY_INFORMATION, PROCESS_VM_READ};

use crate::error::{MemError, Result};
use crate::process::ReadProcess;

/// Bytes marking the sentinel value the game plants near `State`. The
/// exact byte sequence must be `\x00\xde\xc0\xed\xfe` so tooling that
/// already knows this address recognises the scan.
pub const FEEDCODE_MARKER: &[u8] = &[0x00, 0xde, 0xc0, 0xed, 0xfe];

/// Exe file name to look for during process enumeration. Kept public so
/// the tauri app can surface a "not running" toast that matches.
pub const SPEL2_EXE_NAME: &str = "Spel2.exe";

/// Cheapest useful memory-page scan window. State lives well above
/// `0x40000000000` on target systems; a lower floor would waste minutes
/// on unrelated ranges.
const SCAN_MIN_ADDR: u64 = 0x400_0000_0000;
const SCAN_MAX_ADDR: u64 = 0x0000_7FFF_FFFE_FFFF;

/// Buffer size used when scanning a page for the marker. Larger reads
/// mean fewer syscalls but larger discarded buffers on a hit.
const PAGE_READ_CHUNK: usize = 4096;

/// Attached game process. Owns a Win32 HANDLE and closes it on Drop so a
/// dropped Spel2Process doesn't leak handles even mid-attach.
pub struct Spel2Process {
    handle: HANDLE,
    /// Cached feedcode address so subsequent state reads don't re-scan
    /// the entire heap.
    feedcode: std::cell::Cell<Option<u64>>,
}

impl Spel2Process {
    /// Opens the process by PID with PROCESS_VM_READ +
    /// PROCESS_QUERY_INFORMATION rights.
    pub fn from_pid(pid: u32) -> Result<Self> {
        let handle = unsafe {
            OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, false, pid).map_err(|e| {
                MemError::Read {
                    addr: 0,
                    msg: format!("OpenProcess({pid}) failed: {e}"),
                }
            })?
        };
        if handle.is_invalid() {
            return Err(MemError::NotAttached);
        }
        Ok(Self {
            handle,
            feedcode: std::cell::Cell::new(None),
        })
    }

    /// Convenience: enumerate processes, find Spel2.exe, open it.
    /// Returns `NotAttached` when the game isn't running.
    pub fn attach() -> Result<Self> {
        let Some(pid) = find_spelunky2_pid() else {
            return Err(MemError::NotAttached);
        };
        Self::from_pid(pid)
    }

    /// Scans committed private pages above SCAN_MIN_ADDR for the
    /// feedcode marker. Caches the result so subsequent calls are O(1).
    /// Returns `FeedcodeMissing` when the game is still loading (marker
    /// hasn't been written yet).
    pub fn get_feedcode(&self) -> Result<u64> {
        if let Some(addr) = self.feedcode.get() {
            return Ok(addr);
        }
        for page in self.iter_committed_pages() {
            if let Some(addr) = self.find_in_page(page.base, page.size, FEEDCODE_MARKER)? {
                self.feedcode.set(Some(addr));
                return Ok(addr);
            }
        }
        Err(MemError::FeedcodeMissing)
    }

    /// Reads `dst.len()` bytes at `addr` via ReadProcessMemory. Short
    /// reads or protection failures come back as `MemError::Read`.
    fn read_bytes_win(&self, addr: u64, dst: &mut [u8]) -> Result<()> {
        let mut bytes_read: usize = 0;
        let ok = unsafe {
            ReadProcessMemory(
                self.handle,
                addr as *const c_void,
                dst.as_mut_ptr() as *mut c_void,
                dst.len(),
                Some(&mut bytes_read as *mut usize),
            )
        };
        if let Err(e) = ok {
            return Err(MemError::Read {
                addr,
                msg: format!("ReadProcessMemory: {e}"),
            });
        }
        if bytes_read != dst.len() {
            return Err(MemError::Read {
                addr,
                msg: format!("short read: got {bytes_read}, wanted {}", dst.len()),
            });
        }
        Ok(())
    }

    /// Iterates every committed private page above SCAN_MIN_ADDR up to
    /// SCAN_MAX_ADDR that isn't PAGE_NOACCESS.
    fn iter_committed_pages(&self) -> PageIter<'_> {
        PageIter {
            process: self,
            cursor: SCAN_MIN_ADDR,
        }
    }

    /// Scans a single memory region for `needle`, chunk-by-chunk to
    /// avoid allocating a page-sized buffer. Overlaps chunks by
    /// `needle.len() - 1` so a needle spanning a chunk boundary is still
    /// found.
    fn find_in_page(&self, base: u64, region_size: u64, needle: &[u8]) -> Result<Option<u64>> {
        if needle.is_empty() {
            return Ok(None);
        }
        let overlap = needle.len() - 1;
        let chunk_size = PAGE_READ_CHUNK.max(needle.len());
        let mut buf = vec![0u8; chunk_size];
        let end = base.saturating_add(region_size);
        let mut cursor = base;
        while cursor < end {
            let remain = (end - cursor) as usize;
            let want = remain.min(chunk_size);
            let slice = &mut buf[..want];
            // Ignore individual read failures inside a page: some
            // regions are legally committed but hostile to
            // ReadProcessMemory (guard pages inside a larger region,
            // etc). Just skip the rest of the page.
            if self.read_bytes_win(cursor, slice).is_err() {
                return Ok(None);
            }
            if let Some(pos) = memchr_slice(slice, needle) {
                return Ok(Some(cursor + pos as u64));
            }
            if want <= overlap {
                return Ok(None);
            }
            // Back off by overlap so a needle straddling a chunk gets
            // seen on the next pass.
            cursor += (want - overlap) as u64;
        }
        Ok(None)
    }
}

impl ReadProcess for Spel2Process {
    fn read_bytes(&self, addr: u64, dst: &mut [u8]) -> Result<()> {
        self.read_bytes_win(addr, dst)
    }
}

impl Drop for Spel2Process {
    fn drop(&mut self) {
        if !self.handle.is_invalid() {
            let _ = unsafe { CloseHandle(self.handle) };
        }
    }
}

// Handle is Send + Sync from the OS's perspective (kernel objects don't
// have thread affinity), but the `windows` crate doesn't mark HANDLE
// itself. Read-only access through the wrapping struct is safe.
unsafe impl Send for Spel2Process {}
unsafe impl Sync for Spel2Process {}

struct Page {
    base: u64,
    size: u64,
}

struct PageIter<'a> {
    process: &'a Spel2Process,
    cursor: u64,
}

impl<'a> Iterator for PageIter<'a> {
    type Item = Page;

    fn next(&mut self) -> Option<Page> {
        loop {
            if self.cursor >= SCAN_MAX_ADDR {
                return None;
            }
            let mut mbi = MEMORY_BASIC_INFORMATION::default();
            let written = unsafe {
                VirtualQueryEx(
                    self.process.handle,
                    Some(self.cursor as *const c_void),
                    &mut mbi as *mut MEMORY_BASIC_INFORMATION,
                    std::mem::size_of::<MEMORY_BASIC_INFORMATION>(),
                )
            };
            if written == 0 {
                return None;
            }
            let base = mbi.BaseAddress as u64;
            let size = mbi.RegionSize as u64;
            // Advance the cursor whether or not this region is yielded.
            self.cursor = base.saturating_add(size);
            let committed = mbi.State == MEM_COMMIT;
            let private = mbi.Type == MEM_PRIVATE;
            let accessible = (mbi.Protect.0 & PAGE_NOACCESS.0) == 0;
            if committed && private && accessible {
                return Some(Page { base, size });
            }
        }
    }
}

/// Enumerates every running process and returns the PID of the first
/// Spel2.exe. Returns None when the game isn't running.
pub fn find_spelunky2_pid() -> Option<u32> {
    let snapshot = unsafe { CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0) }.ok()?;
    let mut entry = PROCESSENTRY32 {
        dwSize: std::mem::size_of::<PROCESSENTRY32>() as u32,
        ..Default::default()
    };
    let result = unsafe { Process32First(snapshot, &mut entry as *mut PROCESSENTRY32) };
    let mut found: Option<u32> = None;
    if result.is_ok() {
        loop {
            if exe_name_matches(&entry.szExeFile, SPEL2_EXE_NAME) {
                found = Some(entry.th32ProcessID);
                break;
            }
            let next = unsafe { Process32Next(snapshot, &mut entry as *mut PROCESSENTRY32) };
            if next.is_err() {
                break;
            }
        }
    }
    let _ = unsafe { CloseHandle(snapshot) };
    found
}

/// PROCESSENTRY32::szExeFile is a null-terminated MAX_PATH byte array
/// containing the ANSI exe name. Compare case-sensitively after
/// trimming the null terminator.
fn exe_name_matches(bytes: &[i8; 260], target: &str) -> bool {
    // Iterate until null; treat bytes as u8 (they're actually i8 in the
    // `windows` crate binding but represent unsigned bytes).
    let nul = bytes.iter().position(|&b| b == 0).unwrap_or(bytes.len());
    let raw: Vec<u8> = bytes[..nul].iter().map(|&b| b as u8).collect();
    match std::str::from_utf8(&raw) {
        Ok(s) => s == target,
        Err(_) => false,
    }
}

/// Trivial substring search. Uses `memchr`'s crate optimizer path if
/// present in the tree; otherwise a naive walk. Since scan chunks are
/// 4 KiB and the needle is 5 bytes, byte-by-byte is fine here.
fn memchr_slice(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    if needle.is_empty() || needle.len() > haystack.len() {
        return None;
    }
    let first = needle[0];
    let last_start = haystack.len() - needle.len();
    let mut i = 0;
    while i <= last_start {
        if haystack[i] == first && &haystack[i..i + needle.len()] == needle {
            return Some(i);
        }
        i += 1;
    }
    None
}
