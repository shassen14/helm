use std::array;
use std::collections::VecDeque;
use std::sync::{Arc, Mutex};

use crate::routing::{RoutingMatrix, N_CHANNELS};

/// One second of interleaved stereo f32 at the wire-format sample rate.
/// Sized to absorb scheduling jitter between capture and output threads
/// without forcing realtime priority on the producers.
pub const RING_CAPACITY_SAMPLES: usize = 48_000 * 2;

/// Per-channel ring buffers + shared `RoutingMatrix`. Producers (capture
/// subprocess readers, mic input callback, tests) push interleaved stereo
/// f32 samples; the output callback drains them through `mix_into`.
pub struct Mixer {
    pub matrix: Arc<RoutingMatrix>,
    rings: [Mutex<VecDeque<f32>>; N_CHANNELS],
}

impl Mixer {
    pub fn new() -> Self {
        Self {
            matrix: Arc::new(RoutingMatrix::new()),
            rings: array::from_fn(|_| {
                Mutex::new(VecDeque::with_capacity(RING_CAPACITY_SAMPLES))
            }),
        }
    }

    pub fn push_samples(&self, ch: usize, samples: &[f32]) {
        if ch >= N_CHANNELS {
            return;
        }
        let mut ring = self.rings[ch].lock().unwrap();
        let overflow = (ring.len() + samples.len()).saturating_sub(RING_CAPACITY_SAMPLES);
        for _ in 0..overflow {
            ring.pop_front();
        }
        ring.extend(samples.iter().copied());
    }

    pub fn clear_channel(&self, ch: usize) {
        if ch >= N_CHANNELS {
            return;
        }
        self.rings[ch].lock().unwrap().clear();
    }

    /// Sum every channel routed to `output_bit` into `out` (interleaved stereo).
    /// Channels with no samples queued contribute silence rather than blocking,
    /// so a slow producer does not starve the output stream.
    pub fn mix_into(&self, out: &mut [f32], output_bit: u32) {
        out.fill(0.0);
        for ch in 0..N_CHANNELS {
            if self.matrix.is_muted(ch) {
                continue;
            }
            if self.matrix.output_mask(ch) & output_bit == 0 {
                continue;
            }
            let gain = self.matrix.gain(ch);
            let mut ring = self.rings[ch].lock().unwrap();
            for slot in out.iter_mut() {
                if let Some(s) = ring.pop_front() {
                    *slot += s * gain;
                }
            }
        }
    }
}
