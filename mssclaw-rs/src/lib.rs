//! mssclaw-rs: MSS-VDP Rust acceleration backend
//!
//! Phase 1: JSON bridge (compromise) with full FFI safety guardrails.
//! Phase 1.5 target: arena/buffer zero-copy instead of JSON round-trip.
//!
//! # Safety Contract (MUST NOT BREAK)
//! 1. Every #[pyfunction] MUST wrap body in `catch_unwind` — panic across FFI = UB
//! 2. Rayon parallel regions MUST NOT touch Python objects — extract to pure Rust first
//! 3. All alloc/free pairs MUST stay on Rust side — no exposing raw pointers to Python
//! 4. `--release` is NOT optional for benchmarks — debug PyO3 is ~10x slower

use pyo3::prelude::*;
use std::panic;

mod scanner;
mod benchmark;

use scanner::{NodeRef, Finding, scan_nodes};

/// Scan AST nodes for VDP violations.
///
/// Phase 1 bridge: accepts JSON string from Python, returns JSON string.
/// Each call's overhead (json.dumps + from_str + to_string + json.loads) is
/// part of `bridge_overhead_ratio` tracking.
#[pyfunction]
fn scan_ast_nodes(_py: Python<'_>, nodes_json: &str) -> PyResult<String> {
    let result = panic::catch_unwind(|| {
        // Phase 1: parse JSON. Phase 1.5: replace with &[u8] buffer protocol.
        let nodes: Vec<NodeRef> = serde_json::from_str(nodes_json)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Invalid AST node JSON: {}", e)
            ))?;

        // All data is now pure Rust — Rayon region may begin.
        let findings: Vec<Finding> = scan_nodes(&nodes);

        // Phase 1: serialize back. Phase 1.5: return structured buffer.
        serde_json::to_string(&findings)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Failed to serialize findings: {}", e)
            ))
    });

    match result {
        Ok(inner) => inner,
        Err(_panicked) => Err(pyo3::exceptions::PyRuntimeError::new_err(
            "mssclaw-rs: scanner panicked — caught by catch_unwind, no UB propagated"
        )),
    }
}

/// Health check — returns version, module status, and bridge type.
#[pyfunction]
fn health_check() -> PyResult<String> {
    let status = serde_json::json!({
        "module": "mssclaw-rs",
        "version": "0.1.0",
        "bridge": "JSON (Phase 1)",
        "rayon_threads": rayon::current_num_threads(),
        "scanner_rules": scanner::rule_count(),
    });
    Ok(status.to_string())
}

/// Run internal benchmark for bridge overhead measurement.
/// Returns { "bridge_overhead_ns": ..., "scan_ns": ..., "total_ns": ... }
#[pyfunction]
fn bench_scan_ast(_py: Python<'_>, nodes_json: &str, iterations: usize) -> PyResult<String> {
    use std::time::Instant;

    let result = panic::catch_unwind(|| {
        let nodes: Vec<NodeRef> = serde_json::from_str(nodes_json)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Invalid JSON: {}", e)
            ))?;

        let n = iterations.min(1000);
        let mut total_ns: u128 = 0;
        for _ in 0..n {
            let start = Instant::now();
            let _findings = scan_nodes(&nodes);
            total_ns += start.elapsed().as_nanos();
        }
        let avg_scan_ns = total_ns / n as u128;

        serde_json::to_string(&serde_json::json!({
            "iterations": n,
            "node_count": nodes.len(),
            "avg_scan_ns": avg_scan_ns,
        }))
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
    });

    match result {
        Ok(inner) => inner,
        Err(_) => Err(pyo3::exceptions::PyRuntimeError::new_err("benchmark panicked")),
    }
}

/// Python module entry point.
#[pymodule]
fn mssclaw_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(scan_ast_nodes, m)?)?;
    m.add_function(wrap_pyfunction!(health_check, m)?)?;
    m.add_function(wrap_pyfunction!(bench_scan_ast, m)?)?;
    Ok(())
}
