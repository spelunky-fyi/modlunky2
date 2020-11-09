use std::ffi;
use std::ptr;
use std::str;

use log;


use sysinfo::{Pid, ProcessExt, System, SystemExt};
//use pyo3::prelude::*;
//use pyo3::wrap_pyfunction;
use winapi::shared::minwindef::{LPVOID, DWORD};
use winapi::um::errhandlingapi::GetLastError;
use winapi::um::libloaderapi::{GetProcAddress, LoadLibraryA};
use winapi::um::memoryapi::{VirtualAllocEx, WriteProcessMemory};
use winapi::um::minwinbase::LPTHREAD_START_ROUTINE;
use winapi::um::processthreadsapi::{CreateRemoteThread, OpenProcess, GetExitCodeThread};
use winapi::um::synchapi::WaitForSingleObject;
use winapi::um::winbase::INFINITE;
use winapi::um::winnt::{HANDLE, MEM_COMMIT, PROCESS_ALL_ACCESS};

pub struct Process {
    handle: HANDLE,
    pub pid: Pid,
    dll: String,

}

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

    unsafe fn alloc_str(&self, buf: &str) -> LPVOID {
        let addr = self.alloc(buf.len() + 1);
        self.write_mem(addr, buf.as_ptr() as LPVOID, buf.len());
        return addr;
    }

    unsafe fn write_mem(&self, addr: LPVOID, buf: LPVOID, size: usize) {
        WriteProcessMemory(
            self.handle,
            addr,
            buf,
            size,
            ptr::null_mut(),
        );
    }

    pub unsafe fn inject_dll(&self, name: &str) {
        let buf = self.alloc_str(name);
        log::debug!("Injecting DLL into process... {}", name);
        self.call(find_function("kernel32.dll", "LoadLibraryA"), buf);
        println!("Inject: {:?}", self.dll);
    }

    pub unsafe fn main(&self) {
        self.call(
            find_function(&self.dll, "main"),
            std::ptr::null_mut(),
        );
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
}

impl Drop for Process {
    fn drop(&mut self) {
        // TODO: Unload DLL
    }
}


pub unsafe fn find_function(library: &str, function: &str) -> LPTHREAD_START_ROUTINE {
    let library_name = ffi::CString::new(library).unwrap();
    let function_name = ffi::CString::new(function).unwrap();
    let library_ptr = LoadLibraryA(library_name.as_ptr());
    std::mem::transmute(GetProcAddress(library_ptr, function_name.as_ptr()))
}