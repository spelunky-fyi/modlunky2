use std::fs::File;
use std::io::BufReader;
use std::path::Path;
use std::time::SystemTime;

use ml2_assets::AssetStore;

fn main() -> anyhow::Result<()> {
    let spel2_path =
        Path::new(r"C:\Program Files (x86)\Steam\steamapps\common\Spelunky 2\Spel2.exe");
    let file = File::open(spel2_path)?;
    let mut reader = BufReader::new(file);

    let mut store = AssetStore::from_handle(&mut reader)?;

    let start = SystemTime::now();

    store.extract(Path::new("test-extract"))?;
    let elapsed = start.elapsed()?;
    println!("Finished... {:?}ms", elapsed.as_millis());

    Ok(())
}
