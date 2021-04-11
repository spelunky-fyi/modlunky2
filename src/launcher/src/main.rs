#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use anyhow::{anyhow, Result};
use clap::App;
use clap::AppSettings;
use clap::Arg;
use directories::ProjectDirs;
use std::ffi::OsStr;
use std::fs;
use std::path::{Path, PathBuf};

static MODLUNKY2_BUNDLE: &'static [u8] = include_bytes!(concat!(env!("OUT_DIR"), "/modlunky2.zip"));
static MODLUNKY2_VERSION: &'static str =
    include_str!(concat!(env!("OUT_DIR"), "/modlunky2.version"));

fn unzip(dest: &PathBuf) -> Result<()> {
    let mut archive = zip::ZipArchive::new(std::io::Cursor::new(MODLUNKY2_BUNDLE))?;

    for i in 0..archive.len() {
        let mut file = archive.by_index(i)?;

        let outpath = match file.enclosed_name() {
            Some(path) => dest.join(path.to_owned()),
            None => continue,
        };

        if (&*file.name()).ends_with('/') {
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

fn main() -> Result<()> {
    let launcher_matches = App::new("modlunky2")
        .setting(AppSettings::TrailingVarArg)
        .setting(AppSettings::DontDelimitTrailingValues)
        .setting(AppSettings::AllowLeadingHyphen)
        .setting(AppSettings::DisableVersion)
        .setting(AppSettings::DisableHelpFlags)
        .setting(AppSettings::DisableHelpSubcommand)
        .arg(
            Arg::with_name("clear-cache")
                .long("clear-cache")
                .required(false)
                .takes_value(false),
        )
        .arg(
            Arg::with_name("remainder")
                .multiple(true)
                .allow_hyphen_values(true),
        )
        .get_matches();

    let should_clear_cache: bool = launcher_matches.is_present("clear-cache");
    let remainder: Vec<_> = launcher_matches
        .values_of("remainder")
        .map_or_else(|| vec![], |v| v.collect());

    let project_dirs = ProjectDirs::from("", "spelunky.fyi", "modlunky2")
        .ok_or(anyhow!("Failed initialize project dirs..."))?;

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
    if release_dir.exists() && should_clear_cache {
        println!("Clearing cached directory at {:?}", release_dir);
        std::fs::remove_dir_all(&release_dir)?;
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
