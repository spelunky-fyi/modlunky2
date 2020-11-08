use std::ffi;
use std::ptr;

use log;
use sysinfo::{Pid, ProcessExt, System, SystemExt};
use winapi::shared::minwindef::LPVOID;
use winapi::um::errhandlingapi::GetLastError;
use winapi::um::libloaderapi::{GetProcAddress, LoadLibraryA};
use winapi::um::memoryapi::{VirtualAllocEx, WriteProcessMemory};
use winapi::um::minwinbase::LPTHREAD_START_ROUTINE;
use winapi::um::processthreadsapi::{CreateRemoteThread, OpenProcess};
use winapi::um::synchapi::WaitForSingleObject;
use winapi::um::winbase::INFINITE;
use winapi::um::winnt::{HANDLE, MEM_COMMIT, PROCESS_ALL_ACCESS};

pub struct Process {
    handle: HANDLE,
    pub pid: Pid,
}

unsafe fn alloc(proc: &Process, size: usize) -> LPVOID {
    let res = VirtualAllocEx(
        proc.handle,
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

unsafe fn alloc_str(proc: &Process, str: &str) -> LPVOID {
    let addr = alloc(proc, str.len() + 1);
    write_mem(proc, addr, str);
    return addr;
}

unsafe fn write_mem(proc: &Process, addr: LPVOID, str: &str) {
    WriteProcessMemory(
        proc.handle,
        addr,
        str.as_ptr() as LPVOID,
        str.len(),
        ptr::null_mut(),
    );
}

pub unsafe fn find_function(library: &str, function: &str) -> LPTHREAD_START_ROUTINE {
    let library_name = ffi::CString::new(library).unwrap();
    let function_name = ffi::CString::new(function).unwrap();
    let library_ptr = LoadLibraryA(library_name.as_ptr());
    std::mem::transmute(GetProcAddress(library_ptr, function_name.as_ptr()))
}

pub unsafe fn inject_dll(proc: &Process, name: &str) {
    let str = alloc_str(proc, name);
    log::debug!("Injecting DLL into process... {}", name);
    call(proc, find_function("kernel32.dll", "LoadLibraryA"), str);
}

pub unsafe fn call(proc: &Process, addr: LPTHREAD_START_ROUTINE, args: LPVOID) {
    let handle = CreateRemoteThread(
        proc.handle,
        ptr::null_mut(),
        0,
        addr,
        args,
        0,
        ptr::null_mut(),
    );
    WaitForSingleObject(handle, INFINITE);
}

pub unsafe fn find_process(name: &str) -> Option<Process> {
    let mut system = System::new_all();
    log::debug!("Refreshing the process list...");
    system.refresh_processes();

    log::debug!(
        "Iterating through {} processes...",
        system.get_processes().len()
    );

    for (pid, proc_) in system.get_processes() {
        if proc_.name().to_lowercase() == name.to_lowercase() {
            let handle = OpenProcess(PROCESS_ALL_ACCESS, 0, *pid as u32);
            return Some(Process {
                handle: handle,
                pid: *pid,
            });
        }
    }

    None
}
