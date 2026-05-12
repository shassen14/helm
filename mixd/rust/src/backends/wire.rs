//! Cross-OS wire contract for `mixd-capture-*` helpers.
//!
//! All per-OS capture helpers (SCK on macOS, future PipeWire helper on Linux,
//! future WASAPI helper on Windows) speak the same protocol on stdout:
//!
//!   1. One JSON line: `{"sample_rate":48000,"channels":2,"format":"f32le"}\n`
//!   2. Raw PCM: interleaved stereo IEEE-754 f32 little-endian, no framing.
//!
//! This module owns the contract constants, header validation, the reader
//! thread loop, and helper-binary path resolution. OS-specific backends only
//! decide *which* binary to spawn and *with what args*.

use std::env;
use std::io::{BufRead, BufReader, Read};
use std::path::PathBuf;
use std::process::ChildStdout;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

use crate::mixer::Mixer;

pub const SAMPLE_RATE: u32 = 48_000;
pub const CHANNELS: u16 = 2;
pub const FORMAT_TAG: &str = "f32le";
pub const BYTES_PER_SAMPLE: usize = 4;

/// Optional env override pointing at a prebuilt helper binary. Honoured by
/// every OS backend so users can swap implementations without rebuilding.
pub const HELPER_PATH_ENV: &str = "MIXD_CAPTURE_HELPER";

pub type WireError = Box<dyn std::error::Error>;
pub type WireResult<T> = Result<T, WireError>;

/// Resolve a helper binary by checking, in order: the `MIXD_CAPTURE_HELPER`
/// env var, paths next to the running executable, paths relative to `cwd`,
/// and paths relative to `CARGO_MANIFEST_DIR`. `rel_candidates` are joined
/// onto each base so each OS backend can list its own build-output paths.
pub fn resolve_helper_path(
    binary_name: &str,
    rel_candidates: &[&str],
) -> WireResult<PathBuf> {
    if let Ok(env_path) = env::var(HELPER_PATH_ENV) {
        let p = PathBuf::from(env_path);
        if p.exists() {
            return Ok(p);
        }
    }
    let mut bases: Vec<PathBuf> = Vec::new();
    if let Ok(exe) = env::current_exe() {
        if let Some(parent) = exe.parent() {
            bases.push(parent.to_path_buf());
        }
    }
    if let Ok(cwd) = env::current_dir() {
        bases.push(cwd.join("mixd/rust"));
        bases.push(cwd.join("helm/mixd/rust"));
        bases.push(cwd);
    }
    if let Ok(manifest) = env::var("CARGO_MANIFEST_DIR") {
        bases.push(PathBuf::from(manifest));
    }
    for base in &bases {
        for rel in rel_candidates {
            let candidate = base.join(rel);
            if candidate.exists() {
                return Ok(candidate);
            }
        }
    }
    Err(format!(
        "{binary_name} not found; set {HELPER_PATH_ENV} or build the helper for this OS"
    )
    .into())
}

pub fn validate_header(line: &str) -> WireResult<()> {
    let v: serde_json::Value =
        serde_json::from_str(line.trim()).map_err(|e| -> WireError {
            format!("parse helper header {line:?}: {e}").into()
        })?;
    let sr = v.get("sample_rate").and_then(|x| x.as_u64()).unwrap_or(0);
    let ch = v.get("channels").and_then(|x| x.as_u64()).unwrap_or(0);
    let fmt = v.get("format").and_then(|x| x.as_str()).unwrap_or("");
    if sr as u32 != SAMPLE_RATE || ch as u16 != CHANNELS || fmt != FORMAT_TAG {
        return Err(format!(
            "helper wire format mismatch: sr={sr} ch={ch} fmt={fmt}; expected \
             {SAMPLE_RATE}/{CHANNELS}/{FORMAT_TAG}"
        )
        .into());
    }
    Ok(())
}

/// Drain a helper's stdout into one mixer channel: validate header, then
/// stream f32le interleaved stereo samples until EOF or `stop` is set.
pub fn run_pcm_reader(
    stdout: ChildStdout,
    channel: usize,
    mixer: Arc<Mixer>,
    stop: Arc<AtomicBool>,
) -> WireResult<()> {
    let mut reader = BufReader::new(stdout);
    let mut header = String::new();
    reader.read_line(&mut header).map_err(|e| -> WireError {
        format!("read header: {e}").into()
    })?;
    validate_header(&header)?;

    let mut byte_buf = vec![0u8; 8 * 1024];
    let mut leftover: Vec<u8> = Vec::with_capacity(BYTES_PER_SAMPLE);
    while !stop.load(Ordering::Acquire) {
        let n = reader.read(&mut byte_buf).map_err(|e| -> WireError {
            format!("read pcm: {e}").into()
        })?;
        if n == 0 {
            break;
        }
        let mut bytes: Vec<u8> = Vec::with_capacity(leftover.len() + n);
        bytes.extend_from_slice(&leftover);
        bytes.extend_from_slice(&byte_buf[..n]);
        let usable = bytes.len() - (bytes.len() % BYTES_PER_SAMPLE);
        let (whole, tail) = bytes.split_at(usable);
        let mut samples: Vec<f32> = Vec::with_capacity(usable / BYTES_PER_SAMPLE);
        for chunk in whole.chunks_exact(BYTES_PER_SAMPLE) {
            samples.push(f32::from_le_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]));
        }
        mixer.push_samples(channel, &samples);
        leftover = tail.to_vec();
    }
    Ok(())
}
