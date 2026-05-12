use mixd::mixer::Mixer;
use mixd::routing::{N_CHANNELS, OUT_CHAT, OUT_MONITOR, OUT_STREAM};

const SR: usize = 48_000;
const CH: usize = 2;

fn tone(frames: usize, freq: f32, amp: f32) -> Vec<f32> {
    let mut out = Vec::with_capacity(frames * CH);
    for i in 0..frames {
        let t = i as f32 / SR as f32;
        let s = amp * (2.0 * std::f32::consts::PI * freq * t).sin();
        out.push(s);
        out.push(s);
    }
    out
}

fn rms(buf: &[f32]) -> f32 {
    if buf.is_empty() {
        return 0.0;
    }
    let s: f32 = buf.iter().map(|x| x * x).sum();
    (s / buf.len() as f32).sqrt()
}

#[test]
fn tone_passes_through_at_unit_gain() {
    let mixer = Mixer::new();
    mixer.matrix.set_outputs(0, OUT_STREAM);
    mixer.matrix.set_gain(0, 1.0);

    let frames = 1024;
    let input = tone(frames, 440.0, 0.5);
    let expected_rms = rms(&input);
    mixer.push_samples(0, &input);

    let mut out = vec![0.0f32; frames * CH];
    mixer.mix_into(&mut out, OUT_STREAM);

    let got_rms = rms(&out);
    assert!(
        (got_rms - expected_rms).abs() < 1e-5,
        "unit gain: expected rms {expected_rms}, got {got_rms}"
    );
}

#[test]
fn gain_scales_output() {
    let mixer = Mixer::new();
    mixer.matrix.set_outputs(0, OUT_STREAM);
    mixer.matrix.set_gain(0, 0.5);

    let frames = 1024;
    let input = tone(frames, 440.0, 0.5);
    let expected_rms = rms(&input) * 0.5;
    mixer.push_samples(0, &input);

    let mut out = vec![0.0f32; frames * CH];
    mixer.mix_into(&mut out, OUT_STREAM);

    let got_rms = rms(&out);
    assert!(
        (got_rms - expected_rms).abs() < 1e-5,
        "0.5 gain: expected rms {expected_rms}, got {got_rms}"
    );
}

#[test]
fn mute_silences_channel() {
    let mixer = Mixer::new();
    mixer.matrix.set_outputs(0, OUT_STREAM);
    mixer.matrix.set_muted(0, true);

    let frames = 256;
    mixer.push_samples(0, &tone(frames, 440.0, 0.5));

    let mut out = vec![0.0f32; frames * CH];
    mixer.mix_into(&mut out, OUT_STREAM);
    assert_eq!(rms(&out), 0.0);
}

#[test]
fn routing_mask_gates_output_bus() {
    let mixer = Mixer::new();
    // Channel routed only to MONITOR; STREAM render should be silent.
    mixer.matrix.set_outputs(0, OUT_MONITOR);
    mixer.matrix.set_gain(0, 1.0);

    let frames = 256;
    let input = tone(frames, 440.0, 0.5);
    let expected_rms = rms(&input);
    mixer.push_samples(0, &input);

    let mut stream_out = vec![0.0f32; frames * CH];
    mixer.mix_into(&mut stream_out, OUT_STREAM);
    assert_eq!(rms(&stream_out), 0.0, "STREAM should not receive MONITOR-only channel");

    mixer.push_samples(0, &input);
    let mut monitor_out = vec![0.0f32; frames * CH];
    mixer.mix_into(&mut monitor_out, OUT_MONITOR);
    assert!((rms(&monitor_out) - expected_rms).abs() < 1e-5);

    // Sanity: an unrouted bus stays silent.
    let mut chat_out = vec![0.0f32; frames * CH];
    mixer.mix_into(&mut chat_out, OUT_CHAT);
    assert_eq!(rms(&chat_out), 0.0);
}

#[test]
fn bus_gain_scales_output() {
    let mixer = Mixer::new();
    mixer.matrix.set_outputs(0, OUT_STREAM);
    mixer.matrix.set_gain(0, 1.0);
    mixer.matrix.set_bus_gain(0, 0.25);

    let frames = 512;
    let input = tone(frames, 440.0, 0.5);
    let expected_rms = rms(&input) * 0.25;
    mixer.push_samples(0, &input);

    let mut out = vec![0.0f32; frames * CH];
    mixer.mix_into(&mut out, OUT_STREAM);

    let got_rms = rms(&out);
    assert!(
        (got_rms - expected_rms).abs() < 1e-5,
        "bus gain: expected rms {expected_rms}, got {got_rms}"
    );
}

#[test]
fn buses_drain_independently() {
    // Channel routed to STREAM + MONITOR: each bus must see the full signal.
    // (Pre-Milestone-4 single-ring design would have starved one of them.)
    let mixer = Mixer::new();
    mixer.matrix.set_outputs(0, OUT_STREAM | OUT_MONITOR);
    mixer.matrix.set_gain(0, 1.0);

    let frames = 512;
    let input = tone(frames, 440.0, 0.5);
    let expected_rms = rms(&input);
    mixer.push_samples(0, &input);

    let mut stream_out = vec![0.0f32; frames * CH];
    let mut monitor_out = vec![0.0f32; frames * CH];
    mixer.mix_into(&mut stream_out, OUT_STREAM);
    mixer.mix_into(&mut monitor_out, OUT_MONITOR);

    assert!((rms(&stream_out) - expected_rms).abs() < 1e-5);
    assert!((rms(&monitor_out) - expected_rms).abs() < 1e-5);
}

#[test]
fn channels_sum_into_same_bus() {
    let mixer = Mixer::new();
    assert!(N_CHANNELS >= 2);
    for ch in 0..2 {
        mixer.matrix.set_outputs(ch, OUT_STREAM);
        mixer.matrix.set_gain(ch, 1.0);
    }

    let frames = 512;
    // Two identical tones → sum is 2× amplitude on each frame.
    let input = tone(frames, 440.0, 0.25);
    mixer.push_samples(0, &input);
    mixer.push_samples(1, &input);

    let mut out = vec![0.0f32; frames * CH];
    mixer.mix_into(&mut out, OUT_STREAM);

    let expected_rms = rms(&input) * 2.0;
    let got_rms = rms(&out);
    assert!(
        (got_rms - expected_rms).abs() < 1e-5,
        "sum: expected rms {expected_rms}, got {got_rms}"
    );
}
