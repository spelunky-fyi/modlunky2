use std::ffi::CString;
use std::net::UdpSocket;
use std::ptr;
use std::str;
use std::sync::mpsc::{sync_channel, SyncSender};
use std::thread;

use byteorder::{ByteOrder, LE};
use hex_literal::hex;
use winapi::shared::minwindef::HMODULE;
use winapi::um::libloaderapi::GetModuleHandleA;
use winapi::um::libloaderapi::LoadLibraryA;
use winapi::um::wincon::AttachConsole;

use crate::critical_section::CriticalSectionManager;
use crate::models::{Memory, State};
use crate::search::{find_after_bundle, find_inst};

mod critical_section;
mod models;
mod search;

#[no_mangle]
unsafe extern "C" fn DllMain(_: *const u8, _reason: u32, _: *const u8) -> u32 {
    1
}

unsafe fn memory_view<'a>(addr: *mut u8) -> &'a mut [u8] {
    std::slice::from_raw_parts_mut(addr, usize::MAX)
}

fn get_load_item(exe: &[u8], start: usize) -> usize {
    let needle = &hex!("BA 88 02 00 00");
    let off = find_inst(exe, needle, start);
    let off: usize = find_inst(exe, needle, off + 5) + 8;

    off.wrapping_add(LE::read_i32(&exe[off + 1..]) as usize) + 5
}

unsafe fn attach_stdout(pid: u32) {
    env_logger::Builder::new()
        .filter(None, log::LevelFilter::Debug)
        .init();
    AttachConsole(pid);
}

struct Server {
    port: u16,
    module_handle: HMODULE,
    started_channel: SyncSender<bool>,
}

impl Server {
    fn new(port: u16, module_handle: HMODULE, started_channel: SyncSender<bool>) -> Self {
        Self {
            port,
            module_handle,
            started_channel,
        }
    }

    fn dispatch(&self, payload: &[u8]) -> Option<Vec<u8>> {
        let s = str::from_utf8(payload).unwrap();
        let parts: Vec<&str> = s.split("|").collect();
        if parts.is_empty() {
            return Some(vec![]);
        }

        log::info!("Command: {:?}", parts[0]);
        match parts[0] {
            "get_module_handle" => Some(self.get_module_handle()),
            "load_entity" => Some(self.load_entity(&parts[1..])),
            "shutdown" => None,
            _ => Some(vec![]),
        }
    }

    fn serve(&self) {
        let socket = UdpSocket::bind(("127.0.0.1", self.port)).unwrap();
        self.started_channel.send(true).unwrap();
        loop {
            let mut buf = [0; 1024];
            let (amt, src) = socket.recv_from(&mut buf).unwrap();
            match self.dispatch(&buf[0..amt]) {
                Some(response) => socket.send_to(&response, &src).unwrap(),
                None => {
                    log::info!("Goodbye!");
                    socket.send_to(&[], &src).unwrap();
                    return;
                }
            };
        }
    }

    fn get_module_handle(&self) -> Vec<u8> {
        (self.module_handle as usize).to_le_bytes().into()
    }

    fn load_entity(&self, parts: &[&str]) -> Vec<u8> {
        if parts.len() != 3 {
            return vec![];
        }

        let item_num = parts[0].parse::<usize>().unwrap();
        let rel_x = parts[1].parse::<f32>().unwrap();
        let rel_y = parts[2].parse::<f32>().unwrap();

        unsafe {
            let spel2_name = CString::new("Spel2.exe").unwrap();
            let spel2_ptr = LoadLibraryA(spel2_name.as_ptr());
            let exe = memory_view(std::mem::transmute(spel2_ptr));
            let mem = memory_view(std::ptr::null_mut());
            // Skipping bundle for faster memory search
            let after_bundle = find_after_bundle(exe);
            let memory = Memory { mem, exe };
            let state = State::new(&memory, after_bundle);
            let load_item: extern "C" fn(usize, usize, f32, f32) -> usize =
                std::mem::transmute(get_load_item(exe, after_bundle) + spel2_ptr as usize);
            let c = CriticalSectionManager::new();
            {
                // This is RAII-style implementation for suspending the main thread, for preventing race conditions.
                let mut _lock = c.lock();
                let (x, y) = state.items().player(0).position();
                load_item(state.layer(0), item_num, x + rel_x, y + rel_y);
            }
        }
        vec![]
    }
}

#[no_mangle]
unsafe extern "C" fn main(pid: u32) {
    attach_stdout(pid);
    log::info!("Welcome to Modlunky 2!");

    let (tx, rx) = sync_channel::<bool>(1);
    thread::spawn(|| {
        let module_handle = GetModuleHandleA(CString::new("modlunky2.dll").unwrap().as_ptr());
        log::info!("modlunky2.dll Loaded at {:?}", module_handle);
        let server = Server::new(8041, module_handle, tx);
        server.serve();
    });

    // Wait for server to be up before allowing main to complete.
    rx.recv().unwrap();
}

// Prevent compiler to skip return values for DllMain
pub unsafe fn eyo() {
    println!("{}", DllMain(ptr::null(), 0, ptr::null()));
}
