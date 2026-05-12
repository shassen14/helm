//! Windows helper locator (PLACEHOLDER).
//!
//! When the Windows backend lands, build a `mixd-capture-windows.exe` helper
//! (likely a small C++/Rust binary using the WASAPI Process Loopback API,
//! `ActivateAudioInterfaceAsync` with `AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK`).
//! Match the wire-format spec in `backends::wire` and `HelperBackend` will
//! take care of subprocess lifecycle, mixing, cpal output and mic input.

use super::helper::HelperLocator;

const BINARY: &str = "mixd-capture-windows.exe";

const SEARCH_PATHS: &[&str] = &[
    "../windows/target/release/mixd-capture-windows.exe",
    "../windows/target/debug/mixd-capture-windows.exe",
];

pub struct WindowsLocator;

impl HelperLocator for WindowsLocator {
    fn binary_name(&self) -> &'static str {
        BINARY
    }
    fn search_paths(&self) -> &'static [&'static str] {
        SEARCH_PATHS
    }
    fn app_capture_args(&self, app_id: &str) -> Vec<String> {
        // `app_id` is expected to be a Win32 process id (decimal string)
        // for WASAPI process-loopback capture.
        vec![
            "capture".into(),
            "--header".into(),
            "--pid".into(),
            app_id.to_string(),
        ]
    }
    fn system_capture_args(&self) -> Vec<String> {
        vec!["capture".into(), "--header".into(), "--system".into()]
    }
}
