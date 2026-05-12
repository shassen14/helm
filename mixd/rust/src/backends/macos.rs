//! macOS helper locator: ScreenCaptureKit-based `mixd-capture-darwin`.

use super::helper::HelperLocator;

const BINARY: &str = "mixd-capture-darwin";

const SEARCH_PATHS: &[&str] = &[
    "../swift/.build/arm64-apple-macosx/release/mixd-capture-darwin",
    "../swift/.build/release/mixd-capture-darwin",
    "../swift/.build/arm64-apple-macosx/debug/mixd-capture-darwin",
    "../swift/.build/debug/mixd-capture-darwin",
];

pub struct MacosLocator;

impl HelperLocator for MacosLocator {
    fn binary_name(&self) -> &'static str {
        BINARY
    }
    fn search_paths(&self) -> &'static [&'static str] {
        SEARCH_PATHS
    }
    fn app_capture_args(&self, bundle_id: &str) -> Vec<String> {
        vec![
            "capture".into(),
            "--header".into(),
            "--bundle-id".into(),
            bundle_id.to_string(),
        ]
    }
    fn system_capture_args(&self) -> Vec<String> {
        vec!["capture".into(), "--header".into(), "--system".into()]
    }
}
