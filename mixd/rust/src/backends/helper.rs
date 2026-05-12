//! Generic subprocess-helper backend.
//!
//! Per-OS capture helpers (`mixd-capture-darwin`, future `mixd-capture-linux`,
//! `mixd-capture-windows.exe`) all speak the same `wire` protocol on stdout.
//! This module owns the subprocess lifecycle (spawn, read, kill) and routes
//! captured PCM into the shared `Mixer`. OS modules supply only a
//! `HelperLocator` describing where their binary lives and how to invoke it.

use std::process::{Child, Command, Stdio};
use std::sync::atomic::AtomicBool;
use std::sync::Arc;
use std::thread::{self, JoinHandle};

use super::wire::{self, WireResult};
use super::{cpal_io, AudioBackend, BackendError, BackendResult, CaptureSource};
use crate::mixer::Mixer;
use crate::routing::{N_CHANNELS, OUT_STREAM};

/// OS-specific knowledge needed to launch a `wire`-speaking helper binary.
/// Implementors should be cheap to construct and free of any mutable state.
pub trait HelperLocator: Send + Sync + 'static {
    fn binary_name(&self) -> &'static str;
    fn search_paths(&self) -> &'static [&'static str];
    /// CLI args for capturing a single application by its OS-specific id
    /// (bundle ID on macOS, process id or window class on Linux, etc.).
    fn app_capture_args(&self, app_id: &str) -> Vec<String>;
    /// CLI args for capturing the system mix (diagnostic / fallback).
    fn system_capture_args(&self) -> Vec<String>;
}

struct CaptureHandle {
    child: Option<Child>,
    reader: Option<JoinHandle<()>>,
    mic_stream: Option<cpal::Stream>,
    stop: Arc<AtomicBool>,
}

impl Drop for CaptureHandle {
    fn drop(&mut self) {
        self.stop
            .store(true, std::sync::atomic::Ordering::Release);
        if let Some(mut child) = self.child.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
        if let Some(stream) = self.mic_stream.take() {
            drop(stream);
        }
        if let Some(handle) = self.reader.take() {
            let _ = handle.join();
        }
    }
}

/// Backend implementation parameterised by an OS-specific `HelperLocator`.
/// All three target OSes are expected to use this — only the locator differs.
pub struct HelperBackend<L: HelperLocator> {
    mixer: Arc<Mixer>,
    locator: L,
    captures: [Option<CaptureHandle>; N_CHANNELS],
    output_stream: Option<cpal::Stream>,
}

impl<L: HelperLocator> HelperBackend<L> {
    pub fn new(mixer: Arc<Mixer>, locator: L) -> Self {
        Self {
            mixer,
            locator,
            captures: Default::default(),
            output_stream: None,
        }
    }

    fn spawn_helper(&self, channel: usize, args: &[String]) -> BackendResult<Child> {
        let path = wire::resolve_helper_path(
            self.locator.binary_name(),
            self.locator.search_paths(),
        )
        .map_err(|e| -> BackendError { e.to_string().into() })?;
        let child = Command::new(&path)
            .args(args)
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit())
            .spawn()
            .map_err(|e| -> BackendError {
                format!("spawn {} for ch {channel}: {e}", self.locator.binary_name()).into()
            })?;
        Ok(child)
    }

    fn start_subprocess_capture(
        &mut self,
        channel: usize,
        args: Vec<String>,
    ) -> BackendResult<()> {
        let mut child = self.spawn_helper(channel, &args)?;
        let stdout = child
            .stdout
            .take()
            .ok_or_else(|| -> BackendError { "child stdout missing".into() })?;
        let mixer = Arc::clone(&self.mixer);
        let stop = Arc::new(AtomicBool::new(false));
        let stop_thread = Arc::clone(&stop);
        let reader = thread::Builder::new()
            .name(format!("mixd-capture-{channel}"))
            .spawn(move || {
                if let Err(e) = wire::run_pcm_reader(stdout, channel, mixer, stop_thread)
                    as WireResult<()>
                {
                    eprintln!("[mixd] capture reader ch {channel} ended: {e}");
                }
            })
            .map_err(|e| -> BackendError { format!("spawn reader thread: {e}").into() })?;
        self.captures[channel] = Some(CaptureHandle {
            child: Some(child),
            reader: Some(reader),
            mic_stream: None,
            stop,
        });
        Ok(())
    }

    fn start_mic_capture(&mut self, channel: usize) -> BackendResult<()> {
        let stream = cpal_io::open_default_input_stream(Arc::clone(&self.mixer), channel)
            .map_err(|e| -> BackendError { e.to_string().into() })?;
        self.captures[channel] = Some(CaptureHandle {
            child: None,
            reader: None,
            mic_stream: Some(stream),
            stop: Arc::new(AtomicBool::new(false)),
        });
        Ok(())
    }
}

impl<L: HelperLocator> AudioBackend for HelperBackend<L> {
    fn open_output(&mut self) -> BackendResult<()> {
        let stream = cpal_io::open_default_output_stream(Arc::clone(&self.mixer), OUT_STREAM)
            .map_err(|e| -> BackendError { e.to_string().into() })?;
        self.output_stream = Some(stream);
        Ok(())
    }

    fn start_capture(&mut self, channel: usize, source: CaptureSource) -> BackendResult<()> {
        if channel >= N_CHANNELS {
            return Err(format!("channel {channel} out of range").into());
        }
        self.captures[channel] = None;
        self.mixer.clear_channel(channel);
        match source {
            CaptureSource::App { bundle_id } => {
                let args = self.locator.app_capture_args(&bundle_id);
                self.start_subprocess_capture(channel, args)
            }
            CaptureSource::System => {
                let args = self.locator.system_capture_args();
                self.start_subprocess_capture(channel, args)
            }
            CaptureSource::Mic => self.start_mic_capture(channel),
        }
    }

    fn stop_capture(&mut self, channel: usize) -> BackendResult<()> {
        if channel >= N_CHANNELS {
            return Err(format!("channel {channel} out of range").into());
        }
        self.captures[channel] = None;
        self.mixer.clear_channel(channel);
        Ok(())
    }
}
