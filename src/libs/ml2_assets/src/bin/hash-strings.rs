use std::fs::File;
use std::io::BufRead;
use std::io::BufReader;
use std::path::Path;

use ml2_assets::StringHasher;

fn main() -> std::io::Result<()> {
    let strings_path = Path::new(
        r#"C:\Program Files (x86)\Steam\steamapps\common\Spelunky 2\Mods\Extracted\strings00.str"#,
    );
    let file = File::open(strings_path)?;
    let reader = BufReader::new(file);

    let hasher = StringHasher::from_reader(reader);

    let reader = BufReader::new(File::open(strings_path)?);
    let lines: Vec<String> = reader.lines().collect::<Result<_, _>>().unwrap();
    let mut stdout = std::io::stdout().lock();
    hasher.merge_hashes(&lines, &mut stdout);

    Ok(())
}
