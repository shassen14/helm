use std::array;
use std::collections::VecDeque;
use std::sync::{Arc, Mutex};

use crate::routing::{bus_index, RoutingMatrix, BUS_BITS, N_BUSES, N_CHANNELS};

/// One second of interleaved stereo f32 at the wire-format sample rate.
/// Sized to absorb scheduling jitter between capture and output threads
/// without forcing realtime priority on the producers.
pub const RING_CAPACITY_SAMPLES: usize = 48_000 * 2;

/// Per-(channel, bus) ring buffers + shared `RoutingMatrix`.
///
/// Each bus drains its own queue, so the three output streams (stream /
/// monitor / chat) can run on independent cpal callbacks without racing for
/// the same samples. On push we fan a copy out to every bus whose mask
/// currently includes the channel; routing changes affect future samples.
pub struct Mixer {
    pub matrix: Arc<RoutingMatrix>,
    rings: [[Mutex<VecDeque<f32>>; N_BUSES]; N_CHANNELS],
}

impl Mixer {
    pub fn new() -> Self {
        Self {
            matrix: Arc::new(RoutingMatrix::new()),
            rings: array::from_fn(|_| {
                array::from_fn(|_| Mutex::new(VecDeque::with_capacity(RING_CAPACITY_SAMPLES)))
            }),
        }
    }

    pub fn push_samples(&self, ch: usize, samples: &[f32]) {
        if ch >= N_CHANNELS {
            return;
        }
        let mask = self.matrix.output_mask(ch);
        for (bus, bit) in BUS_BITS.iter().enumerate() {
            if mask & bit == 0 {
                continue;
            }
            self.push_to_bus(ch, bus, samples);
        }
    }

    fn push_to_bus(&self, ch: usize, bus: usize, samples: &[f32]) {
        let mut ring = self.rings[ch][bus].lock().unwrap();
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
        for bus in 0..N_BUSES {
            self.rings[ch][bus].lock().unwrap().clear();
        }
    }

    /// Sum every channel routed to `output_bit` into `out` (interleaved stereo),
    /// applying per-channel gain × per-bus master gain. Channels with no
    /// samples queued contribute silence rather than blocking.
    pub fn mix_into(&self, out: &mut [f32], output_bit: u32) {
        out.fill(0.0);
        let Some(bus) = bus_index(output_bit) else {
            return;
        };
        let bus_gain = self.matrix.bus_gain(bus);
        for ch in 0..N_CHANNELS {
            if self.matrix.is_muted(ch) {
                continue;
            }
            if self.matrix.output_mask(ch) & output_bit == 0 {
                continue;
            }
            let gain = self.matrix.gain(ch) * bus_gain;
            let mut ring = self.rings[ch][bus].lock().unwrap();
            for slot in out.iter_mut() {
                if let Some(s) = ring.pop_front() {
                    *slot += s * gain;
                }
            }
        }
    }
}
