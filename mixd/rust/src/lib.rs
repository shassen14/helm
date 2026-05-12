pub mod backends;
mod engine;
pub mod mixer;
pub mod routing;

use std::ffi::{c_char, c_void, CStr, CString};

use backends::CaptureSource;
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

#[no_mangle]
pub unsafe extern "C" fn mixd_start_capture_app(
    ptr: *mut c_void,
    ch: u32,
    bundle_id: *const c_char,
) -> i32 {
    let Some(engine) = (ptr as *mut Engine).as_mut() else {
        return -1;
    };
    if bundle_id.is_null() {
        return -1;
    }
    let Ok(id) = CStr::from_ptr(bundle_id).to_str() else {
        return -1;
    };
    match engine.start_capture(
        ch as usize,
        CaptureSource::App { bundle_id: id.to_string() },
    ) {
        Ok(()) => 0,
        Err(e) => {
            eprintln!("mixd_start_capture_app ch {ch}: {e}");
            -1
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn mixd_start_capture_mic(ptr: *mut c_void, ch: u32) -> i32 {
    let Some(engine) = (ptr as *mut Engine).as_mut() else {
        return -1;
    };
    match engine.start_capture(ch as usize, CaptureSource::Mic) {
        Ok(()) => 0,
        Err(e) => {
            eprintln!("mixd_start_capture_mic ch {ch}: {e}");
            -1
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn mixd_start_capture_system(ptr: *mut c_void, ch: u32) -> i32 {
    let Some(engine) = (ptr as *mut Engine).as_mut() else {
        return -1;
    };
    match engine.start_capture(ch as usize, CaptureSource::System) {
        Ok(()) => 0,
        Err(e) => {
            eprintln!("mixd_start_capture_system ch {ch}: {e}");
            -1
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn mixd_set_bus_volume(ptr: *mut c_void, bus: u32, gain: f32) {
    if let Some(e) = (ptr as *mut Engine).as_ref() {
        e.set_bus_volume(bus as usize, gain);
    }
}

/// Open or re-open the output stream for `bus`. Pass `device_name = null` (or
/// empty) to use the OS default device. Returns 0 on success, -1 on error.
#[no_mangle]
pub unsafe extern "C" fn mixd_open_bus(
    ptr: *mut c_void,
    bus: u32,
    device_name: *const c_char,
) -> i32 {
    let Some(engine) = (ptr as *mut Engine).as_mut() else {
        return -1;
    };
    let name: Option<String> = if device_name.is_null() {
        None
    } else {
        match CStr::from_ptr(device_name).to_str() {
            Ok("") => None,
            Ok(s) => Some(s.to_string()),
            Err(_) => return -1,
        }
    };
    match engine.open_bus(bus as usize, name.as_deref()) {
        Ok(()) => 0,
        Err(e) => {
            eprintln!("mixd_open_bus bus {bus}: {e}");
            -1
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn mixd_close_bus(ptr: *mut c_void, bus: u32) {
    if let Some(engine) = (ptr as *mut Engine).as_mut() {
        engine.close_bus(bus as usize);
    }
}

/// Return a newline-separated, NUL-terminated list of host output device
/// names. Caller owns the buffer and must release it via `mixd_free_string`.
/// Returns null on error.
#[no_mangle]
pub unsafe extern "C" fn mixd_list_output_devices(ptr: *mut c_void) -> *mut c_char {
    let Some(engine) = (ptr as *mut Engine).as_ref() else {
        return std::ptr::null_mut();
    };
    let joined = engine.list_output_devices().join("\n");
    match CString::new(joined) {
        Ok(s) => s.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

#[no_mangle]
pub unsafe extern "C" fn mixd_free_string(s: *mut c_char) {
    if !s.is_null() {
        drop(CString::from_raw(s));
    }
}

#[no_mangle]
pub unsafe extern "C" fn mixd_stop_capture(ptr: *mut c_void, ch: u32) -> i32 {
    let Some(engine) = (ptr as *mut Engine).as_mut() else {
        return -1;
    };
    match engine.stop_capture(ch as usize) {
        Ok(()) => 0,
        Err(e) => {
            eprintln!("mixd_stop_capture ch {ch}: {e}");
            -1
        }
    }
}
