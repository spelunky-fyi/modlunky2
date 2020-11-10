use std::convert::TryInto;
use std::ffi;
use std::mem;
use std::ptr;
use std::str;
use std::sync::Mutex;
use std::time::Duration;

use log;

use pyo3::prelude::*;
use pyo3::types::PyType;

use sysinfo::{Pid, ProcessExt, System, SystemExt};
use winapi::shared::minwindef::{DWORD, LPVOID};
use winapi::um::errhandlingapi::GetLastError;
use winapi::um::libloaderapi::{GetProcAddress, LoadLibraryA};
use winapi::um::memoryapi::{VirtualAllocEx, VirtualQueryEx, WriteProcessMemory};
use winapi::um::minwinbase::LPTHREAD_START_ROUTINE;
use winapi::um::processthreadsapi::{CreateRemoteThread, GetExitCodeThread, OpenProcess};
use winapi::um::psapi::GetModuleBaseNameA;
use winapi::um::synchapi::WaitForSingleObject;
use winapi::um::winbase::INFINITE;
use winapi::um::winnt::MEMORY_BASIC_INFORMATION;
use winapi::um::winnt::{HANDLE, MEM_COMMIT, PROCESS_ALL_ACCESS};

pub struct MemoryMap {
    addr: usize,
    name: String,
}

pub struct Process {
    handle: HANDLE,
    pub pid: Pid,
    dll: String,
    remote_handle: Option<u64>,
}

unsafe impl Send for Process {}

impl Process {
    pub unsafe fn from_name(name: &str, dll: String) -> Option<Process> {
        let mut system = System::new_all();
        log::debug!("Refreshing the process list...");
        system.refresh_processes();

        log::debug!(
            "Iterating through {} processes...",
            system.get_processes().len()
        );

        for (pid, proc) in system.get_processes() {
            if proc.name().to_lowercase() == name.to_lowercase() {
                let handle = OpenProcess(PROCESS_ALL_ACCESS, 0, *pid as u32);
                return Some(Process {
                    handle: handle,
                    pid: *pid,
                    dll: dll,
                    remote_handle: None,
                });
            }
        }

        None
    }

    unsafe fn alloc(&self, size: usize) -> LPVOID {
        let res = VirtualAllocEx(
            self.handle,
            ptr::null_mut(),
            size + 0xFFF & !0xFFF,
            MEM_COMMIT,
            0x40,
        );
        if res == ptr::null_mut() {
            panic!(format!("Allocation failed: {:x}", GetLastError()))
        }
        log::debug!(
            "Allocated memory: {:x}",
            std::mem::transmute::<LPVOID, usize>(res)
        );
        res
    }

    pub unsafe fn find_base(&self, name: &str) -> Option<usize> {
        let map = self.memory_map();
        let mut res = map
            .iter()
            .filter(|item| name.to_lowercase().contains(&item.name.to_lowercase()));
        Some(res.next()?.addr)
    }

    unsafe fn alloc_str(&self, buf: &str) -> LPVOID {
        let addr = self.alloc(buf.len() + 1);
        self.write_mem(addr, buf.as_ptr() as LPVOID, buf.len());
        return addr;
    }

    unsafe fn write_mem(&self, addr: LPVOID, buf: LPVOID, size: usize) {
        WriteProcessMemory(self.handle, addr, buf, size, ptr::null_mut());
    }

    pub unsafe fn inject_dll(&self) {
        let buf = self.alloc_str(&self.dll);
        log::debug!("Injecting DLL into process... {}", self.dll);
        self.call(self.find_function("kernel32.dll", "LoadLibraryA"), buf);
        println!("Inject: {:?}", self.dll);
    }

    pub unsafe fn eject_dll(&self) {
        log::info!("Ejecting DLL from process...");
        if let Some(handle) = self.remote_handle {
            log::info!("Asking dll to shutdown...");
            rpc("shutdown");

            log::info!("Freeing DLL...");
            self.call(
                self.find_function("kernel32.dll", "FreeLibrary"),
                handle as *mut winapi::ctypes::c_void,
            );
            println!("Ejected: {:?}", self.dll);
        }
    }

    pub unsafe fn main(&mut self, pid: u32) {
        self.call(
            self.find_function(&self.dll, "main"),
            pid as *mut winapi::ctypes::c_void,
        );
        let hmodule = rpc("get_module_handle");
        self.remote_handle = Some(u64::from_le_bytes(hmodule[0..8].try_into().unwrap()));
    }

    pub unsafe fn call(&self, addr: LPTHREAD_START_ROUTINE, args: LPVOID) -> DWORD {
        let handle = CreateRemoteThread(
            self.handle,
            ptr::null_mut(),
            0,
            addr,
            args,
            0,
            ptr::null_mut(),
        );
        WaitForSingleObject(handle, INFINITE);
        let mut ret: DWORD = 0;
        GetExitCodeThread(handle, &mut ret);
        ret
    }

    pub unsafe fn memory_map(&self) -> Vec<MemoryMap> {
        let mut result: Vec<MemoryMap> = vec![];
        let mut cur = 0;
        let mut mbf: MEMORY_BASIC_INFORMATION = mem::zeroed();
        let mut buffer = vec![0u8; 0x1000];
        while VirtualQueryEx(
            self.handle,
            mem::transmute(cur),
            &mut mbf,
            mem::size_of::<MEMORY_BASIC_INFORMATION>(),
        ) != 0
        {
            let res = GetModuleBaseNameA(
                self.handle,
                mem::transmute(cur),
                buffer.as_mut_ptr() as *mut i8,
                buffer.len() as u32,
            );
            if res != 0 {
                let name = std::str::from_utf8_unchecked(&buffer[0..res as usize]);
                result.push(MemoryMap {
                    addr: cur,
                    name: name.to_string(),
                })
            };
            cur += mbf.RegionSize;
        }
        result
    }

    pub unsafe fn find_function(&self, library: &str, function: &str) -> LPTHREAD_START_ROUTINE {
        let library_name = ffi::CString::new(library).unwrap();
        let function_name = ffi::CString::new(function).unwrap();
        let library_ptr = LoadLibraryA(library_name.as_ptr());

        std::mem::transmute(
            GetProcAddress(library_ptr, function_name.as_ptr()) as usize - library_ptr as usize
                + self.find_base(library).unwrap(),
        )
    }
}

use std::net::UdpSocket;

pub fn rpc(cmd: &str) -> Vec<u8> {
    let socket = UdpSocket::bind("127.0.0.1:0").expect("couldn't bind to address");
    socket.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
    socket.set_write_timeout(Some(Duration::from_secs(2))).unwrap();
    socket
        .connect("127.0.0.1:8041")
        .expect("connect function failed");

    socket.send(cmd.as_bytes()).expect("send failed.");

    let mut buf = [0; 1024];
    let (number_of_bytes, _) = socket.recv_from(&mut buf).expect("Didn't receive data");
    buf[..number_of_bytes].into()
}

impl Drop for Process {
    fn drop(&mut self) {
        unsafe {
            println!("EJECTED");
            self.eject_dll();
        };
    }
}

#[pyclass]
struct Injector {
    process: Mutex<Process>,
}

#[pymethods]
impl Injector {
    #[classmethod]
    fn from_name(_cls: &PyType, name: &str, dll: String) -> PyResult<Option<Injector>> {
        match unsafe { Process::from_name(name, dll) } {
            Some(process) => Ok(Some(Injector {
                process: Mutex::new(process),
            })),
            None => Ok(None),
        }
    }

    fn inject(&self) -> PyResult<()> {
        let mut proc = self.process.lock().unwrap();
        unsafe {
            proc.inject_dll();
            proc.main(std::process::id());
        }

        Ok(())
    }

    fn load_entity(&self, item_num: usize, rel_x: f32, rel_y: f32) -> PyResult<()> {
        rpc(&format!("load_entity|{}|{}|{}", item_num, rel_x, rel_y));
        Ok(())
    }
}
#[pymodule]
fn dll_injector(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Injector>()?;
    Ok(())
}
