use std::sync::Arc;

use crate::backends::{make_backend, AudioBackend, CaptureSource};
use crate::mixer::Mixer;
use crate::routing::RoutingMatrix;

pub struct Engine {
    pub mixer: Arc<Mixer>,
    pub matrix: Arc<RoutingMatrix>,
    backend: Box<dyn AudioBackend>,
}

impl Engine {
    pub fn new() -> Result<Self, Box<dyn std::error::Error>> {
        let mixer = Arc::new(Mixer::new());
        let matrix = Arc::clone(&mixer.matrix);
        let mut backend = make_backend(Arc::clone(&mixer));
        backend.open_output()?;
        Ok(Self { mixer, matrix, backend })
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

    pub fn start_capture(
        &mut self,
        ch: usize,
        source: CaptureSource,
    ) -> Result<(), Box<dyn std::error::Error>> {
        self.backend.start_capture(ch, source)
    }

    pub fn stop_capture(&mut self, ch: usize) -> Result<(), Box<dyn std::error::Error>> {
        self.backend.stop_capture(ch)
    }
}
