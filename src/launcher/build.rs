use std::env;
use std::fs;
use std::io;
use std::path::Path;
#[cfg(windows)]
use winres::WindowsResource;

use std::io::prelude::*;
use std::io::{Seek, Write};
use std::iter::Iterator;
use zip::write::FileOptions;

use std::fs::File;
use walkdir::{DirEntry, WalkDir};

fn zip_dir<T>(
    it: &mut dyn Iterator<Item = DirEntry>,
    prefix: &str,
    writer: T,
    method: zip::CompressionMethod,
) -> zip::result::ZipResult<()>
where
    T: Write + Seek,
{
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
            buffer.clear();
        } else if name.as_os_str().len() != 0 {
            // Only if not root! Avoids path spec / warning
            // and mapname conversion failed error on unzip
            println!("adding dir {:?} as {:?} ...", path, name);
            #[allow(deprecated)]
            zip.add_directory_from_path(name, options)?;
        }
    }
    zip.finish()?;
    Result::Ok(())
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
    zip_dir(
        &mut it.filter_map(|e| e.ok()),
        src_dir,
        out_file,
        zip::CompressionMethod::Deflated,
    )?;

    println!("cargo:rerun-if-changed=build.rs");
    println!("cargo:rerun-if-changed=../../dist/modlunky2");

    Ok(())
}
