#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::ffi::OsStr;
use std::fs;
use std::io;
use std::path::{Path, PathBuf};

use anyhow::{anyhow, Result};
use clap::Arg;
use clap::ArgAction;
use clap::Command;
use directories::ProjectDirs;
use sha2::Digest;
use sha2::Sha256;

static MODLUNKY2_BUNDLE: &[u8] = include_bytes!(concat!(env!("OUT_DIR"), "/modlunky2.zip"));
static MODLUNKY2_VERSION: &str = include_str!(concat!(env!("OUT_DIR"), "/modlunky2.version"));

include!(concat!(env!("OUT_DIR"), "/hashes.rs"));

fn unzip(dest: &Path) -> Result<()> {
    let mut archive = zip::ZipArchive::new(std::io::Cursor::new(MODLUNKY2_BUNDLE))?;

    for i in 0..archive.len() {
        let mut file = archive.by_index(i)?;

        let outpath = match file.enclosed_name() {
            Some(path) => dest.join(path),
            None => continue,
        };

        if (*file.name()).ends_with('/') {
            println!("File {} extracted to \"{}\"", i, outpath.display());
            fs::create_dir_all(&outpath)?;
        } else {
            println!(
                "File {} extracted to \"{}\" ({} bytes)",
                i,
                outpath.display(),
                file.size()
            );
            if let Some(p) = outpath.parent() {
                if !p.exists() {
                    fs::create_dir_all(&p)?;
                }
            }
            let mut outfile = fs::File::create(&outpath)?;
            std::io::copy(&mut file, &mut outfile)?;
        }
    }

    Ok(())
}

fn verify_release_cache(release_dir: &PathBuf, verify_hashes: bool) -> Result<()> {
    let mut should_invalidate = false;

    for known_file in KNOWN_FILES {
        let path = release_dir.join(known_file);

        if !path.exists() {
            should_invalidate = true;
            break;
        }

        if !verify_hashes {
            continue;
        }

        if let Some(expected_hash) = get_hash(known_file) {
            let mut file = fs::File::open(path)?;
            let mut sha256 = Sha256::new();
            io::copy(&mut file, &mut sha256)?;
            let file_hash = format!("{:x}", sha256.finalize());
            if file_hash != expected_hash {
                println!(
                    "Expected hash didn't match for {}. Invalidating cache...",
                    known_file
                );
                should_invalidate = true;
                break;
            }
        }
    }

    if should_invalidate {
        println!("Clearing cached directory at {:?}", release_dir);
        std::fs::remove_dir_all(&release_dir)?;
    }

    Ok(())
}

fn main() -> Result<()> {
    let launcher_matches = Command::new("modlunky2")
        .dont_delimit_trailing_values(true)
        .disable_version_flag(true)
        .disable_help_flag(true)
        .disable_help_subcommand(true)
        .arg(
            Arg::new("clear-cache")
                .long("clear-cache")
                .required(false)
                .action(ArgAction::SetTrue),
        )
        .arg(
            Arg::new("verify-hashes")
                .long("verify-hashes")
                .required(false)
                .action(ArgAction::SetTrue),
        )
        .arg(
            Arg::new("remainder")
                .trailing_var_arg(true)
                .allow_hyphen_values(true)
                .action(ArgAction::Append),
        )
        .get_matches();

    let should_clear_cache: bool = launcher_matches.get_flag("clear-cache");
    let should_verify_hashes: bool = launcher_matches.get_flag("verify-hashes");
    let remainder: Vec<_> = launcher_matches
        .get_many::<String>("remainder")
        .map_or_else(std::vec::Vec::new, |v| v.collect());

    let project_dirs = ProjectDirs::from("", "spelunky.fyi", "modlunky2")
        .ok_or_else(|| anyhow!("Failed initialize project dirs..."))?;

    println!("Launching modlunky2 v{}", MODLUNKY2_VERSION);
    let cache_dir = Path::new(project_dirs.cache_dir()).join("modlunky2-releases");
    if !cache_dir.exists() {
        println!(
            "Cache Dir {} not found. Creating...",
            &cache_dir.to_string_lossy()
        );
        fs::create_dir_all(&cache_dir)?;
    }

    let release_dir = cache_dir.join(MODLUNKY2_VERSION);
    if release_dir.exists() {
        if should_clear_cache {
            println!("Clearing cached directory at {:?}", release_dir);
            std::fs::remove_dir_all(&release_dir)?;
        } else {
            verify_release_cache(&release_dir, should_verify_hashes)?;
        }
    }

    if !release_dir.exists() {
        println!(
            "Release Dir {} not found. Creating...",
            &release_dir.to_string_lossy()
        );
        fs::create_dir(&release_dir)?;
    }

    let exe_path = release_dir.join("modlunky2.exe");
    if !exe_path.exists() {
        println!("No exe found. Extracting contents...");
        unzip(&release_dir)?;
    }

    if !exe_path.exists() {
        panic!("No exe found despite extracting...");
    }

    // Clean up old cached releases
    for entry in fs::read_dir(cache_dir)? {
        let entry = entry?;
        let path = entry.path();
        if !path.is_dir() {
            continue;
        }

        // Don't remove yourself
        if path.file_name() == Some(OsStr::new(MODLUNKY2_VERSION)) {
            continue;
        }

        // Remove old cache directories
        let _ = std::fs::remove_dir_all(&path);
    }

    let current_exe = std::env::current_exe()?;
    std::process::Command::new(exe_path)
        .args(remainder)
        .arg("--launcher-exe")
        .arg(&current_exe)
        .spawn()?;

    Ok(())
}
