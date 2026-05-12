//! Cross-platform audio I/O via cpal.
//!
//! cpal already abstracts CoreAudio (macOS), WASAPI (Windows), and
//! ALSA / JACK / PipeWire (Linux), so the default-output stream and the
//! default-input (mic) stream live here and are shared by every OS backend.

use std::sync::Arc;

use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};

use super::wire::SAMPLE_RATE;
use crate::mixer::Mixer;

pub type IoError = Box<dyn std::error::Error>;
pub type IoResult<T> = Result<T, IoError>;

/// Open the OS default output device and start a stream that pulls a mix of
/// every channel routed to `output_bit` on each callback. Stereo passes
/// straight through; mono downmixes; >2-ch device layouts get L/R into the
/// first two slots with the rest zeroed.
pub fn open_default_output_stream(
    mixer: Arc<Mixer>,
    output_bit: u32,
) -> IoResult<cpal::Stream> {
    let host = cpal::default_host();
    let device = host
        .default_output_device()
        .ok_or_else(|| -> IoError { "no default output device".into() })?;
    let cfg = device.default_output_config().map_err(|e| -> IoError {
        format!("default_output_config: {e}").into()
    })?;
    let sample_format = cfg.sample_format();
    let out_channels = cfg.channels() as usize;
    let out_sample_rate = cfg.sample_rate().0;
    if out_sample_rate != SAMPLE_RATE {
        eprintln!(
            "[mixd] warning: output runs at {out_sample_rate} Hz, wire is \
             {SAMPLE_RATE} Hz — pitch will drift until a resampler is added"
        );
    }
    let stream_cfg: cpal::StreamConfig = cfg.into();
    let stream = match sample_format {
        cpal::SampleFormat::F32 => device.build_output_stream(
            &stream_cfg,
            move |data: &mut [f32], _: &cpal::OutputCallbackInfo| {
                write_output(&mixer, data, out_channels, output_bit);
            },
            |err| eprintln!("[mixd] output error: {err}"),
            None,
        ),
        other => {
            return Err(format!("unsupported output format: {other:?}; need F32").into())
        }
    }
    .map_err(|e| -> IoError { format!("build output stream: {e}").into() })?;
    stream
        .play()
        .map_err(|e| -> IoError { format!("play output stream: {e}").into() })?;
    Ok(stream)
}

/// Open the OS default input device and push samples into `channel` of the
/// mixer. Mono input is upmixed by duplication; >2-ch is downmixed to L/R.
pub fn open_default_input_stream(
    mixer: Arc<Mixer>,
    channel: usize,
) -> IoResult<cpal::Stream> {
    let host = cpal::default_host();
    let device = host
        .default_input_device()
        .ok_or_else(|| -> IoError { "no default input device".into() })?;
    let cfg = device.default_input_config().map_err(|e| -> IoError {
        format!("default_input_config: {e}").into()
    })?;
    let sample_format = cfg.sample_format();
    let channels = cfg.channels() as usize;
    let stream_cfg: cpal::StreamConfig = cfg.into();
    let stream = match sample_format {
        cpal::SampleFormat::F32 => device.build_input_stream(
            &stream_cfg,
            move |data: &[f32], _: &cpal::InputCallbackInfo| {
                push_input_interleaved(&mixer, channel, channels, data);
            },
            |err| eprintln!("[mixd] mic input error: {err}"),
            None,
        ),
        other => {
            return Err(
                format!("unsupported mic sample format: {other:?}; need F32").into()
            )
        }
    }
    .map_err(|e| -> IoError { format!("build mic input stream: {e}").into() })?;
    stream
        .play()
        .map_err(|e| -> IoError { format!("play mic input stream: {e}").into() })?;
    Ok(stream)
}

fn push_input_interleaved(
    mixer: &Arc<Mixer>,
    channel: usize,
    channels: usize,
    data: &[f32],
) {
    if channels == 2 {
        mixer.push_samples(channel, data);
        return;
    }
    if channels == 1 {
        let mut stereo = Vec::with_capacity(data.len() * 2);
        for &s in data {
            stereo.push(s);
            stereo.push(s);
        }
        mixer.push_samples(channel, &stereo);
        return;
    }
    let mut stereo = Vec::with_capacity((data.len() / channels) * 2);
    for frame in data.chunks_exact(channels) {
        stereo.push(frame[0]);
        stereo.push(frame[1]);
    }
    mixer.push_samples(channel, &stereo);
}

fn write_output(mixer: &Arc<Mixer>, data: &mut [f32], out_channels: usize, bus: u32) {
    if out_channels == 2 {
        mixer.mix_into(data, bus);
        return;
    }
    let frames = data.len() / out_channels;
    let mut stereo = vec![0.0f32; frames * 2];
    mixer.mix_into(&mut stereo, bus);
    if out_channels == 1 {
        for (i, slot) in data.iter_mut().enumerate() {
            *slot = 0.5 * (stereo[i * 2] + stereo[i * 2 + 1]);
        }
        return;
    }
    for (i, frame) in data.chunks_exact_mut(out_channels).enumerate() {
        frame[0] = stereo[i * 2];
        frame[1] = stereo[i * 2 + 1];
        for slot in &mut frame[2..] {
            *slot = 0.0;
        }
    }
}
