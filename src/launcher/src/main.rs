#![windows_subsystem = "windows"]

use anyhow::{anyhow, Result};
use directories::ProjectDirs;
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

    let current_exe = std::env::current_exe()?;
    let exe_dir = current_exe
        .parent()
        .ok_or(anyhow!("Failed to get parent dir"))?;

    let args: Vec<String> = std::env::args().collect();
    std::process::Command::new(exe_path)
        .args(&args[1..])
        .arg("--exe-dir")
        .arg(&exe_dir)
        .spawn()?;

    Ok(())
}
