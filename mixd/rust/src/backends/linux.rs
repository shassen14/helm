//! Linux helper locator (PLACEHOLDER).
//!
//! When the Linux backend lands, build a `mixd-capture-linux` helper (likely
//! a small Rust or C binary that talks to PipeWire's per-node capture) and
//! point this locator at it. The helper must emit the wire-format described
//! in `backends::wire` (JSON header line + f32le interleaved stereo PCM at
//! 48 kHz). Everything else — subprocess lifecycle, ring-buffer plumbing,
//! cpal output and mic input — already works via `HelperBackend`.

use super::helper::HelperLocator;

const BINARY: &str = "mixd-capture-linux";

const SEARCH_PATHS: &[&str] = &[
    "../linux/target/release/mixd-capture-linux",
    "../linux/target/debug/mixd-capture-linux",
];

pub struct LinuxLocator;

impl HelperLocator for LinuxLocator {
    fn binary_name(&self) -> &'static str {
        BINARY
    }
    fn search_paths(&self) -> &'static [&'static str] {
        SEARCH_PATHS
    }
    fn app_capture_args(&self, app_id: &str) -> Vec<String> {
        // `app_id` is expected to be a PipeWire node name or a PID — the
        // helper decides. Mirror the macOS shape: subcommand + flag + value.
        vec![
            "capture".into(),
            "--header".into(),
            "--node".into(),
            app_id.to_string(),
        ]
    }
    fn system_capture_args(&self) -> Vec<String> {
        vec!["capture".into(), "--header".into(), "--system".into()]
    }
}
