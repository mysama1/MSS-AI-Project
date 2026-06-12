//! Internal benchmark instrumentation.
//! Tracks bridge overhead vs. pure scan time for Phase 1→1.5 migration decisions.

/// Timing breakdown for a single scan call.
#[derive(Debug, Clone)]
pub struct ScanTiming {
    pub nodes_count: usize,
    pub deserialize_ns: u128,   // T1: json.dumps (measured in Python)
    pub scan_ns: u128,           // T2: pure Rust scan
    pub serialize_ns: u128,      // T3: to_string (measured in Rust)
}

impl ScanTiming {
    pub fn bridge_overhead_ratio(&self) -> f64 {
        let total = self.deserialize_ns + self.scan_ns + self.serialize_ns;
        if total == 0 { return 0.0; }
        (self.deserialize_ns + self.serialize_ns) as f64 / total as f64
    }

    /// Phase 1.5 migration trigger: > 0.4 means bridge is the bottleneck.
    pub fn should_migrate(&self) -> bool {
        self.bridge_overhead_ratio() > 0.4
    }
}
