use ::dll_injector::{rpc, Process};

fn main() {
    env_logger::Builder::new()
        .filter(None, log::LevelFilter::Debug)
        .init();

    let path = std::env::current_exe()
        .unwrap()
        .parent()
        .unwrap()
        .join("modlunky2.dll");

    if !path.exists() {
        log::error!("DLL not found! {}", path.to_str().unwrap());
        return;
    }

    unsafe {
        match Process::from_name("Spel2.exe", path.to_str().unwrap().into()) {
            None => println!("Cannot find process!"),
            Some(mut proc) => {
                log::info!("Found spelunky 2 PID: {}", proc.pid);
                proc.inject_dll();
                proc.main(std::process::id());
                rpc("load_entity|514|1|1");
            }
        }
    }
}
