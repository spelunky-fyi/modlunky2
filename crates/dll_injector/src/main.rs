use ::dll_injector::{find_process, inject_dll};

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

    let (_, temp_path) = tempfile::Builder::new()
        .suffix(".dll")
        .tempfile()
        .unwrap()
        .keep()
        .unwrap();

    match std::fs::copy(path, temp_path.clone()) {
        Err(_) => panic!("Error!"),
        Ok(_) => {}
    }

    unsafe {
        match find_process("Spel2.exe") {
            None => println!("Cannot find process!"),
            Some(proc) => {
                log::info!("Found spelunky 2 PID: {}", proc.pid);
                inject_dll(&proc, temp_path.to_str().unwrap());
            }
        }
    }
}
