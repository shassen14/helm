mod engine;
mod ipc;
mod routing;

use std::ffi::c_void;

use engine::Engine;

#[no_mangle]
pub extern "C" fn mixd_create() -> *mut c_void {
    match Engine::new() {
        Ok(e) => Box::into_raw(Box::new(e)) as *mut c_void,
        Err(e) => {
            eprintln!("mixd_create: {e}");
            std::ptr::null_mut()
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn mixd_destroy(ptr: *mut c_void) {
    if !ptr.is_null() {
        drop(Box::from_raw(ptr as *mut Engine));
    }
}

#[no_mangle]
pub unsafe extern "C" fn mixd_set_level(ptr: *mut c_void, ch: u32, gain: f32) {
    if let Some(e) = (ptr as *mut Engine).as_ref() {
        e.set_level(ch as usize, gain);
    }
}

#[no_mangle]
pub unsafe extern "C" fn mixd_set_muted(ptr: *mut c_void, ch: u32, muted: u32) {
    if let Some(e) = (ptr as *mut Engine).as_ref() {
        e.set_muted(ch as usize, muted != 0);
    }
}

#[no_mangle]
pub unsafe extern "C" fn mixd_set_outputs(ptr: *mut c_void, ch: u32, mask: u32) {
    if let Some(e) = (ptr as *mut Engine).as_ref() {
        e.set_outputs(ch as usize, mask);
    }
}
