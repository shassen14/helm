use std::sync::Arc;

use crate::backends::{make_backend, AudioBackend, CaptureSource};
use crate::mixer::Mixer;
use crate::routing::{N_BUSES, RoutingMatrix};

pub struct Engine {
    pub matrix: Arc<RoutingMatrix>,
    backend: Box<dyn AudioBackend>,
}

impl Engine {
    pub fn new() -> Result<Self, Box<dyn std::error::Error>> {
        let mixer = Arc::new(Mixer::new());
        let matrix = Arc::clone(&mixer.matrix);
        let backend = make_backend(mixer);
        let mut engine = Self { matrix, backend };
        // Open every bus on the OS default device by default. Python pushes
        // explicit device choices via `open_bus` after loading mixer.toml.
        for bus in 0..N_BUSES {
            if let Err(e) = engine.backend.open_bus(bus, None) {
                eprintln!("[mixd] open default bus {bus}: {e}");
            }
        }
        Ok(engine)
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

    pub fn set_bus_volume(&self, bus: usize, gain: f32) {
        self.matrix.set_bus_gain(bus, gain);
    }

    pub fn open_bus(
        &mut self,
        bus: usize,
        device_name: Option<&str>,
    ) -> Result<(), Box<dyn std::error::Error>> {
        self.backend.open_bus(bus, device_name)
    }

    pub fn close_bus(&mut self, bus: usize) {
        self.backend.close_bus(bus);
    }

    pub fn list_output_devices(&self) -> Vec<String> {
        self.backend.list_output_devices()
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
