use std::array;
use std::sync::atomic::{AtomicBool, AtomicU32, Ordering};

pub const N_CHANNELS: usize = 16;

pub const OUT_STREAM: u32 = 0b001;
pub const OUT_MONITOR: u32 = 0b010;
pub const OUT_CHAT: u32 = 0b100;

pub struct RoutingMatrix {
    gains: [AtomicU32; N_CHANNELS],
    muted: [AtomicBool; N_CHANNELS],
    outputs: [AtomicU32; N_CHANNELS],
}

impl RoutingMatrix {
    pub fn new() -> Self {
        Self {
            gains: array::from_fn(|_| AtomicU32::new(1.0_f32.to_bits())),
            muted: array::from_fn(|_| AtomicBool::new(false)),
            outputs: array::from_fn(|_| AtomicU32::new(0)),
        }
    }

    pub fn gain(&self, ch: usize) -> f32 {
        f32::from_bits(self.gains[ch].load(Ordering::Acquire))
    }

    pub fn is_muted(&self, ch: usize) -> bool {
        self.muted[ch].load(Ordering::Acquire)
    }

    pub fn output_mask(&self, ch: usize) -> u32 {
        self.outputs[ch].load(Ordering::Acquire)
    }

    pub fn set_gain(&self, ch: usize, gain: f32) {
        if ch >= N_CHANNELS {
            return;
        }
        self.gains[ch].store(gain.clamp(0.0, 1.0).to_bits(), Ordering::Release);
    }

    pub fn set_muted(&self, ch: usize, muted: bool) {
        if ch >= N_CHANNELS {
            return;
        }
        self.muted[ch].store(muted, Ordering::Release);
    }

    pub fn set_outputs(&self, ch: usize, mask: u32) {
        if ch >= N_CHANNELS {
            return;
        }
        self.outputs[ch].store(mask, Ordering::Release);
    }
}
