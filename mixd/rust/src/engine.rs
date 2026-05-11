use std::sync::Arc;

use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};

use crate::routing::{RoutingMatrix, N_CHANNELS};

pub struct Engine {
    pub matrix: Arc<RoutingMatrix>,
    _streams: Vec<cpal::Stream>,
}

impl Engine {
    pub fn new() -> Result<Self, Box<dyn std::error::Error>> {
        let host = cpal::default_host();
        let matrix = Arc::new(RoutingMatrix::new());

        let in_dev = host.default_input_device().ok_or("no input device")?;
        let in_cfg = in_dev.default_input_config()?;

        let m_in = Arc::clone(&matrix);
        let in_stream = in_dev.build_input_stream(
            &in_cfg.into(),
            move |data: &[f32], _: &cpal::InputCallbackInfo| {
                for (i, &sample) in data.iter().enumerate() {
                    let ch = i % N_CHANNELS;
                    let gain = if m_in.is_muted(ch) { 0.0 } else { m_in.gain(ch) * sample };
                    let _mask = m_in.output_mask(ch);
                    let _ = gain;
                }
            },
            |err| eprintln!("input error: {err}"),
            None,
        )?;
        in_stream.play()?;

        Ok(Self { matrix, _streams: vec![in_stream] })
    }

    pub fn set_level(&self, ch: usize, gain: f32) {
        self.matrix.set_gain(ch, gain);
    }

    pub fn set_muted(&self, ch: usize, muted: bool) {
        self.matrix.set_muted(ch, muted);
    }

    pub fn set_outputs(&self, ch: usize, mask: u32) {
        self.matrix.set_outputs(ch, mask);
    }
}
