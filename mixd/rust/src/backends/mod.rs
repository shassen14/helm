//! Audio backend layer.
//!
//! ```text
//!                 Engine + Mixer + RoutingMatrix         (OS-agnostic)
//!                              │
//!                              ▼
//!                       AudioBackend trait               (this file)
//!                              │
//!                              ▼
//!                       HelperBackend<L>                 (helper.rs)
//!              ┌───────────────┼───────────────┐
//!              ▼               ▼               ▼
//!         MacosLocator    LinuxLocator    WindowsLocator
//!              │               │               │
//!              ▼               ▼               ▼
//!     mixd-capture-darwin   mixd-capture-linux   mixd-capture-windows.exe
//!         (ScreenCaptureKit)   (PipeWire, TBD)    (WASAPI loopback, TBD)
//! ```
//!
//! All three OSes share `wire` (helper protocol), `cpal_io` (output + mic
//! streams via cpal), and `helper::HelperBackend` (subprocess lifecycle and
//! ring-buffer plumbing). Adding a new OS = implement `HelperLocator` and
//! add a `cfg` arm to `make_backend`.

use std::sync::Arc;

use crate::mixer::Mixer;

pub mod cpal_io;
pub mod helper;
pub mod wire;

#[cfg(target_os = "macos")]
mod macos;
#[cfg(target_os = "linux")]
mod linux;
#[cfg(target_os = "windows")]
mod windows;

pub type BackendError = Box<dyn std::error::Error>;
pub type BackendResult<T> = Result<T, BackendError>;

#[derive(Clone, Debug)]
pub enum CaptureSource {
    /// Capture one specific application's audio output. `bundle_id` is the
    /// OS-specific identifier: bundle ID on macOS, PipeWire node or PID on
    /// Linux, Win32 process id on Windows.
    App { bundle_id: String },
    /// Capture the OS default input device (microphone) via cpal.
    Mic,
    /// Diagnostic capture of the full system mix.
    System,
}

pub trait AudioBackend {
    fn open_output(&mut self) -> BackendResult<()>;
    fn start_capture(&mut self, channel: usize, source: CaptureSource) -> BackendResult<()>;
    fn stop_capture(&mut self, channel: usize) -> BackendResult<()>;
}

#[cfg(target_os = "macos")]
pub fn make_backend(mixer: Arc<Mixer>) -> Box<dyn AudioBackend> {
    Box::new(helper::HelperBackend::new(mixer, macos::MacosLocator))
}

#[cfg(target_os = "linux")]
pub fn make_backend(mixer: Arc<Mixer>) -> Box<dyn AudioBackend> {
    Box::new(helper::HelperBackend::new(mixer, linux::LinuxLocator))
}

#[cfg(target_os = "windows")]
pub fn make_backend(mixer: Arc<Mixer>) -> Box<dyn AudioBackend> {
    Box::new(helper::HelperBackend::new(mixer, windows::WindowsLocator))
}

#[cfg(not(any(target_os = "macos", target_os = "linux", target_os = "windows")))]
pub fn make_backend(_mixer: Arc<Mixer>) -> Box<dyn AudioBackend> {
    panic!("no AudioBackend implemented for this platform")
}
