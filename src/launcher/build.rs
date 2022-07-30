use std::fs;
use std::io;
use std::path::Path;
use std::{collections::HashMap, env};
#[cfg(windows)]
use winres::WindowsResource;

use std::fs::File;
use std::io::prelude::*;
use std::io::{Seek, Write};
use std::iter::Iterator;

use sha2::Digest;
use sha2::Sha256;
use walkdir::{DirEntry, WalkDir};
use zip::write::FileOptions;

fn zip_dir<T>(
    it: &mut dyn Iterator<Item = DirEntry>,
    prefix: &str,
    writer: T,
    method: zip::CompressionMethod,
) -> zip::result::ZipResult<HashMap<String, String>>
where
    T: Write + Seek,
{
    let mut hashes: HashMap<String, String> = HashMap::new();

    let mut zip = zip::ZipWriter::new(writer);
    let options = FileOptions::default()
        .compression_method(method)
        .unix_permissions(0o755);

    let mut buffer = Vec::new();
    for entry in it {
        let path = entry.path();
        let name = path.strip_prefix(Path::new(prefix)).unwrap();

        // Write file or directory explicitly
        // Some unzip tools unzip files with directory paths correctly, some do not!
        if path.is_file() {
            println!("adding file {:?} as {:?} ...", path, name);
            #[allow(deprecated)]
            zip.start_file_from_path(name, options)?;
            let mut f = File::open(path)?;

            f.read_to_end(&mut buffer)?;
            zip.write_all(&*buffer)?;
            let digest = Sha256::digest(&buffer);
            buffer.clear();
            hashes.insert(name.to_str().unwrap().into(), format!("{:x}", digest));
        } else if !name.as_os_str().is_empty() {
            // Only if not root! Avoids path spec / warning
            // and mapname conversion failed error on unzip
            println!("adding dir {:?} as {:?} ...", path, name);
            #[allow(deprecated)]
            zip.add_directory_from_path(name, options)?;
        }
    }
    zip.finish()?;
    Result::Ok(hashes)
}

fn main() -> io::Result<()> {
    #[cfg(windows)]
    {
        WindowsResource::new()
            .set_icon("../modlunky2/static/images/icon.ico")
            .compile()?;
    }

    let out_dir = env::var_os("OUT_DIR").unwrap();

    // Grab version from modlunky2 dist directory so we know where to cache
    // the payload
    let version: String = fs::read_to_string("../../dist/modlunky2/VERSION")?
        .trim()
        .into();
    let dest_path = Path::new(&out_dir).join("modlunky2.version");
    fs::write(&dest_path, version)?;

    // Zip up and bundle the modlunky2 dist
    let src_dir = "../../dist/modlunky2";
    let dest_path = Path::new(&out_dir).join("modlunky2.zip");
    let out_file = File::create(&dest_path).unwrap();
    let walkdir = WalkDir::new(src_dir);
    let it = walkdir.into_iter();
    let hashes = zip_dir(
        &mut it.filter_map(|e| e.ok()),
        src_dir,
        out_file,
        zip::CompressionMethod::Deflated,
    )?;

    let dest_path = Path::new(&out_dir).join("hashes.rs");
    let mut out_file = File::create(&dest_path).unwrap();

    writeln!(out_file, "static KNOWN_FILES: &[&str] = &[")?;
    for key in hashes.keys() {
        writeln!(out_file, "    r\"{}\",", key)?;
    }
    write!(out_file, "];\n\n")?;

    writeln!(out_file, "fn get_hash(filename: &str) -> Option<&str> {{")?;
    writeln!(out_file, "    match filename {{")?;

    for (key, value) in &hashes {
        let path = Path::new(key);

        if path.starts_with("tcl/") {
            continue;
        }

        if path.starts_with("tk/") {
            continue;
        }

        writeln!(out_file, "        r\"{}\" => Some(r\"{}\"),", key, value)?;
    }

    writeln!(out_file, "        _ => None,")?;
    writeln!(out_file, "    }}")?;
    writeln!(out_file, "}}")?;

    println!("cargo:rerun-if-changed=build.rs");
    println!("cargo:rerun-if-changed=../../dist/modlunky2");

    Ok(())
}
