use std::fs::File;
use std::io::Write;

use ml2_assets::Soundbank;

fn main() -> std::io::Result<()> {
    let soundbank_path =
        r#"C:\Program Files (x86)\Steam\steamapps\common\Spelunky 2\Mods\Extracted\soundbank.bank"#;

    let soundbank = Soundbank::from_path(soundbank_path);
    for fsb in soundbank.fsbs {
        for track in fsb.tracks {
            if fsb.header.mode.file_extension() == "wav" {
                let out = track.rebuild_as(&fsb.header.mode);
                let filename = format!(
                    "test-extract/{}.{}",
                    &track.name,
                    fsb.header.mode.file_extension()
                );

                println!("{:?}", filename);

                let mut f = File::create(filename).unwrap();
                f.write_all(&out).unwrap();
            }
        }
    }

    Ok(())
}
