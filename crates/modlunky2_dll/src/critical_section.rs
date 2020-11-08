use winapi::um::processthreadsapi::{ResumeThread, SuspendThread};
use winapi::um::winnt::HANDLE;

pub struct CriticalSectionManager {
    main_thread: HANDLE,
}

impl CriticalSectionManager {
    pub fn new() -> CriticalSectionManager {
        // TODO: get main thread by enumerating all threads
        CriticalSectionManager {
            main_thread: 0 as HANDLE,
        }
    }
    pub unsafe fn lock(&self) -> CriticalSection {
        SuspendThread(self.main_thread);
        CriticalSection {
            thread: self.main_thread,
        }
    }
}

pub struct CriticalSection {
    thread: HANDLE,
}

impl Drop for CriticalSection {
    fn drop(&mut self) {
        unsafe {
            ResumeThread(self.thread);
        }
    }
}
