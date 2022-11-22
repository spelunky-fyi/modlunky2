use ml2_assets::Soundbank;

fn main() -> std::io::Result<()> {
    let soundbank_path =
        r#"C:\Program Files (x86)\Steam\steamapps\common\Spelunky 2\Mods\Extracted\soundbank.bank"#;

    let soundbank = Soundbank::from_path(soundbank_path);
    for fsb in soundbank.fsbs {
        for track in fsb.tracks {
            println!("{:?}", &track.name);
        }
    }

    Ok(())
}
