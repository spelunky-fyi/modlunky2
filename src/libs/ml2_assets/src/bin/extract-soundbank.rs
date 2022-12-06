use std::fs::{create_dir_all, File};
use std::io::Write;

use ml2_assets::Soundbank;

fn main() -> anyhow::Result<()> {
    let soundbank_path =
        r#"C:\Program Files (x86)\Steam\steamapps\common\Spelunky 2\Mods\Extracted\soundbank.bank"#;

    let soundbank = Soundbank::from_path(soundbank_path)?;
    for fsb in soundbank.fsbs {
        let extension = fsb.header.mode.file_extension();
        create_dir_all(format!("test-extract/soundbank/{extension}"))?;

        for track in fsb.tracks {
            let filename = format!(
                "test-extract/soundbank/{}/{}.{}",
                extension, &track.name, extension
            );
            println!("{filename:?}");

            let out = track.rebuild_as(&fsb.header.mode)?;
            let mut f = File::create(filename)?;
            f.write_all(&out)?;
        }
    }

    Ok(())
}
