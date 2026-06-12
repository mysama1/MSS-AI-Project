//! VDP scanner engine: rule definitions and parallel matching.
//!
//! Rules mirror the Python-side VDP scanner patterns:
//! V1: path existence precheck | V2: error direct report
//! V3: encoding explicit declaration | V4: atomic idempotent
//! V5: timeout degradation | V6: fact/inference separation
//! + MSS-GUARD rules for normative field violations.

use rayon::prelude::*;
use serde::{Deserialize, Serialize};

// ── AST Node (Phase 1: minimal fields) ──

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeRef {
    pub id: u32,
    pub kind: String,       // AST node type: "Call", "BinaryOp", "FunctionDef", etc.
    pub start: u32,         // byte offset
    pub end: u32,           // byte offset
    pub line: Option<u32>,  // source line number (1-based)
    #[serde(default)]
    pub text: String,       // source text (for regex-free pattern matching)
}

// ── Severity ──

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
#[serde(rename_all = "lowercase")]
pub enum Severity {
    Blocker,
    Critical,
    Major,
    Minor,
    Info,
}

// ── Finding ──

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Finding {
    pub node_id: u32,
    pub rule_id: String,
    pub severity: Severity,
    pub message: String,
    pub line: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub suggestion: Option<String>,
}

// ── Rule definitions ──

/// Rule count for health check.
pub fn rule_count() -> usize { RULES.len() }

type RuleFn = fn(&NodeRef, &[NodeRef]) -> Option<Finding>;

struct Rule {
    pub id: &'static str,
    pub severity: Severity,
    pub description: &'static str,
    pub check: RuleFn,
}

// ═══════════════════════════════════════════════════
//  Individual rule functions
// ═══════════════════════════════════════════════════

/// V1: File I/O without existence precheck
fn v1_no_path_check(node: &NodeRef, _all: &[NodeRef]) -> Option<Finding> {
    if !matches!(node.kind.as_str(), "Call" | "Command" | "ShellCommand") {
        return None;
    }
    // Check for file operations without guards
    let text = &node.text;
    let has_file_op = text.contains("open(")
        || text.contains("subprocess.run")
        || text.contains("os.remove")
        || text.contains("shutil.")
        || text.contains("Get-Content")
        || text.contains("Set-Content")
        || text.contains("Out-File")
        || text.contains("Invoke-WebRequest")
        || text.contains("Start-Process")
        || text.contains("Remove-Item");
    if !has_file_op { return None; }

    let has_guard = text.contains("Test-Path")
        || text.contains("os.path.exists")
        || text.contains("os.path.isfile")
        || text.contains("try:")
        || text.contains("FileNotFoundError")
        || text.contains("ErrorAction");
    if has_guard { return None; }

    Some(Finding {
        node_id: node.id,
        rule_id: "V1-01".into(),
        severity: Severity::Blocker,
        message: "File I/O without existence precheck".into(),
        line: node.line,
        suggestion: Some("Add path-exists guard: Test-Path / os.path.exists / try-except".into()),
    })
}

/// V2: Inferred cause without error code
fn v2_inferred_cause(node: &NodeRef, _all: &[NodeRef]) -> Option<Finding> {
    if !matches!(node.kind.as_str(), "Call" | "ExpressionStatement" | "Comment") {
        return None;
    }
    let text = &node.text;
    let has_inference = text.contains("可能")
        || text.contains("估计")
        || text.contains("大概")
        || text.contains("maybe")
        || text.contains("probably")
        || text.contains("likely")
        || text.contains("看起来")
        || text.contains("seems like");
    if !has_inference { return None; }

    let has_errno = text.contains("errno")
        || text.contains("error_code")
        || text.contains("exit code")
        || text.contains("return code")
        || text.contains("错误码");
    if has_errno { return None; }

    Some(Finding {
        node_id: node.id,
        rule_id: "V2-01".into(),
        severity: Severity::Major,
        message: "Error cause inferred without errno/error code".into(),
        line: node.line,
        suggestion: Some("Report actual errno/exit code, not inferred cause".into()),
    })
}

/// V3: Encoding not explicitly declared
fn v3_no_encoding(node: &NodeRef, _all: &[NodeRef]) -> Option<Finding> {
    if node.kind != "Call" { return None; }
    let text = &node.text;
    if text.contains("open(") && !text.contains("encoding=") && !text.contains("Encoding") {
        return Some(Finding {
            node_id: node.id,
            rule_id: "V3-01".into(),
            severity: Severity::Major,
            message: "File opened without explicit encoding declaration".into(),
            line: node.line,
            suggestion: Some("Add encoding='utf-8' parameter".into()),
        });
    }
    None
}

/// V4: Non-idempotent destructive operation
fn v4_non_idempotent(node: &NodeRef, _all: &[NodeRef]) -> Option<Finding> {
    if !matches!(node.kind.as_str(), "Call" | "Command") { return None; }
    let text = &node.text;
    let has_destructive = text.contains("rm -rf")
        || text.contains("rmdir")
        || text.contains("os.remove(")
        || text.contains("shutil.rmtree")
        || text.contains("Remove-Item -Recurse")
        || text.contains("del /")
        || text.contains("DROP TABLE")
        || text.contains("DROP DATABASE");
    if !has_destructive { return None; }

    let has_confirm = text.contains("--confirm")
        || text.contains("Are you sure")
        || text.contains("confirmation")
        || text.contains("safety_check")
        || text.contains("-WhatIf");
    if has_confirm { return None; }

    Some(Finding {
        node_id: node.id,
        rule_id: "V4-01".into(),
        severity: Severity::Critical,
        message: "Destructive operation without idempotency guard".into(),
        line: node.line,
        suggestion: Some("Add confirmation prompt or dry-run before destructive ops".into()),
    })
}

/// V5: Network call without timeout
fn v5_no_timeout(node: &NodeRef, _all: &[NodeRef]) -> Option<Finding> {
    if !matches!(node.kind.as_str(), "Call") { return None; }
    let text = &node.text;
    let has_network = text.contains("requests.get")
        || text.contains("requests.post")
        || text.contains("urllib.request")
        || text.contains("http.client")
        || text.contains("Invoke-WebRequest")
        || text.contains("Invoke-RestMethod")
        || text.contains("fetch(")
        || text.contains("curl");
    if !has_network { return None; }

    let has_timeout = text.contains("timeout=")
        || text.contains("Timeout")
        || text.contains("--connect-timeout")
        || text.contains("--max-time");
    if has_timeout { return None; }

    Some(Finding {
        node_id: node.id,
        rule_id: "V5-01".into(),
        severity: Severity::Major,
        message: "Network call without explicit timeout".into(),
        line: node.line,
        suggestion: Some("Add timeout=30 parameter or --connect-timeout".into()),
    })
}

/// V6: Fact/Inference mixing in single statement
fn v6_fact_inference_mix(node: &NodeRef, _all: &[NodeRef]) -> Option<Finding> {
    if !matches!(node.kind.as_str(), "ExpressionStatement" | "Comment" | "LineComment") {
        return None;
    }
    let text = &node.text;
    let fact_markers = ["观察到", "实测", "日志显示", "返回值", "confirmed",
        "observed", "measured", "log shows", "return value"];
    let inference_markers = ["因此", "推断", "可能是", "推测", "therefore",
        "inferred", "likely", "probably", "speculated"];

    let has_fact = fact_markers.iter().any(|m| text.contains(m));
    let has_inference = inference_markers.iter().any(|m| text.contains(m));
    if has_fact && has_inference {
        return Some(Finding {
            node_id: node.id,
            rule_id: "V6-01".into(),
            severity: Severity::Minor,
            message: "Fact and inference mixed in single statement".into(),
            line: node.line,
            suggestion: Some("Separate fact (observation) from inference (conclusion) into distinct statements".into()),
        });
    }
    None
}

/// MSS-G: Hardcoded secrets (password/key/token)
fn mssg_hardcoded_secret(node: &NodeRef, _all: &[NodeRef]) -> Option<Finding> {
    if !matches!(node.kind.as_str(), "Assignment" | "VariableDeclaration" | "String") {
        return None;
    }
    let text_lower = node.text.to_lowercase();
    // Detect patterns like: password = "xxx", api_key = "xxx"
    let is_secret_var = text_lower.contains("password")
        || text_lower.contains("api_key")
        || text_lower.contains("secret")
        || text_lower.contains("token")
        || text_lower.contains("credential");

    if !is_secret_var { return None; }
    // Exclude empty or env var references
    if text_lower.contains("os.environ")
        || text_lower.contains("getenv")
        || text_lower.contains("$env:")
        || text_lower.contains("''")
        || text_lower.contains("\"\"")
        || text_lower.contains("none")
        || text_lower.contains("null")
        || text_lower.contains("placeholder")
    {
        return None;
    }

    Some(Finding {
        node_id: node.id,
        rule_id: "MSS-SEC-01".into(),
        severity: Severity::Blocker,
        message: "Hardcoded secret/credential detected".into(),
        line: node.line,
        suggestion: Some("Use environment variables or secrets manager instead".into()),
    })
}

/// MSS-G: Dynamic code execution (eval/exec)
fn mssg_dynamic_exec(node: &NodeRef, _all: &[NodeRef]) -> Option<Finding> {
    if node.kind != "Call" { return None; }
    let text = &node.text;
    if text.contains("eval(") || text.contains("exec(") || text.contains("compile(") {
        return Some(Finding {
            node_id: node.id,
            rule_id: "MSS-SEC-02".into(),
            severity: Severity::Blocker,
            message: "Dynamic code execution detected".into(),
            line: node.line,
            suggestion: Some("Avoid eval/exec; use safer alternatives or sandbox".into()),
        });
    }
    None
}

/// MSS-G: System command execution
fn mssg_system_cmd(node: &NodeRef, _all: &[NodeRef]) -> Option<Finding> {
    if node.kind != "Call" { return None; }
    let text = &node.text;
    let has_syscall = text.contains("os.system(")
        || text.contains("subprocess.call(")
        || text.contains("subprocess.Popen(")
        || text.contains("popen(")
        || text.contains("shell_exec(")
        || text.contains("exec(");
    if !has_syscall { return None; }

    let has_sanitize = text.contains("shlex.quote")
        || text.contains("shell=False")
        || text.contains("validate");
    if has_sanitize { return None; }

    Some(Finding {
        node_id: node.id,
        rule_id: "MSS-SEC-03".into(),
        severity: Severity::Critical,
        message: "System command execution without input sanitization".into(),
        line: node.line,
        suggestion: Some("Use shlex.quote() or shell=False; validate inputs".into()),
    })
}

/// MSS-G: Wasteful busywork pattern
fn mssg_busywork(node: &NodeRef, _all: &[NodeRef]) -> Option<Finding> {
    if node.kind != "Call" { return None; }
    let text = &node.text;
    // Detect rewrite/summarize/translate/rephrase as do-nothing cycles
    let busywork = text.contains("rewrite")
        || text.contains("summarize")
        || text.contains("translate")
        || text.contains("rephrase")
        || text.contains("restate");
    if !busywork { return None; }

    // Short text + waste pattern = suspect
    if node.end.saturating_sub(node.start) <= 50 {
        return Some(Finding {
            node_id: node.id,
            rule_id: "MSS-WASTE-01".into(),
            severity: Severity::Info,
            message: "Potential wasteful busywork cycle".into(),
            line: node.line,
            suggestion: Some("Verify this operation produces net-new meaning, not just restating".into()),
        });
    }
    None
}

// ═══════════════════════════════════════════════════
//  Rule registry
// ═══════════════════════════════════════════════════

static RULES: &[Rule] = &[
    Rule { id: "V1-01", severity: Severity::Blocker,  description: "File I/O without precheck",      check: v1_no_path_check },
    Rule { id: "V2-01", severity: Severity::Major,     description: "Inferred cause without errno",   check: v2_inferred_cause },
    Rule { id: "V3-01", severity: Severity::Major,     description: "No encoding declaration",        check: v3_no_encoding },
    Rule { id: "V4-01", severity: Severity::Critical,  description: "Non-idempotent destructive op",  check: v4_non_idempotent },
    Rule { id: "V5-01", severity: Severity::Major,     description: "Network call without timeout",   check: v5_no_timeout },
    Rule { id: "V6-01", severity: Severity::Minor,     description: "Fact/Inference mixing",          check: v6_fact_inference_mix },
    Rule { id: "MSS-SEC-01", severity: Severity::Blocker,   description: "Hardcoded secret",        check: mssg_hardcoded_secret },
    Rule { id: "MSS-SEC-02", severity: Severity::Blocker,   description: "Dynamic code execution",  check: mssg_dynamic_exec },
    Rule { id: "MSS-SEC-03", severity: Severity::Critical,  description: "Unsanitized system cmd",  check: mssg_system_cmd },
    Rule { id: "MSS-WASTE-01", severity: Severity::Info,     description: "Wasteful busywork",       check: mssg_busywork },
];

// ═══════════════════════════════════════════════════
//  Parallel scan engine
// ═══════════════════════════════════════════════════

/// Scan all nodes against all rules in parallel.
/// Each node is independently checked against every rule;
/// Rayon splits nodes across threads, inner rule iteration is sequential.
pub fn scan_nodes(nodes: &[NodeRef]) -> Vec<Finding> {
    nodes
        .par_iter()
        .flat_map_iter(|node| {
            RULES
                .iter()
                .filter_map(move |rule| (rule.check)(node, nodes))
        })
        .collect()
}

// ═══════════════════════════════════════════════════
//  Tests
// ═══════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;

    fn make_node(id: u32, kind: &str, text: &str, line: u32) -> NodeRef {
        NodeRef {
            id, kind: kind.into(), start: 0,
            end: text.len() as u32, line: Some(line),
            text: text.into(),
        }
    }

    #[test]
    fn test_v1_open_without_check() {
        let nodes = vec![
            make_node(1, "Call", "open('/etc/passwd')", 10),
        ];
        let findings = scan_nodes(&nodes);
        // V1 should fire (open without precheck) + V3 should fire (no encoding)
        let v1 = findings.iter().find(|f| f.rule_id == "V1-01");
        assert!(v1.is_some(), "Should flag open() without precheck");
    }

    #[test]
    fn test_v1_open_with_guard() {
        let nodes = vec![
            make_node(1, "Call", "if os.path.exists(p): open(p, encoding='utf-8')", 10),
        ];
        let findings = scan_nodes(&nodes);
        assert_eq!(findings.iter().filter(|f| f.rule_id == "V1-01").count(), 0);
    }

    #[test]
    fn test_mss_sec_hardcoded_password() {
        let nodes = vec![
            make_node(1, "Assignment", r#"password = "admin123""#, 42),
        ];
        let findings = scan_nodes(&nodes);
        let sec = findings.iter().find(|f| f.rule_id == "MSS-SEC-01");
        assert!(sec.is_some(), "Should flag hardcoded password");
        assert_eq!(sec.unwrap().severity, Severity::Blocker);
    }

    #[test]
    fn test_mss_sec_eval() {
        let nodes = vec![
            make_node(2, "Call", "eval(user_input)", 100),
        ];
        let findings = scan_nodes(&nodes);
        let sec = findings.iter().find(|f| f.rule_id == "MSS-SEC-02");
        assert!(sec.is_some(), "Should flag eval()");
    }

    #[test]
    fn test_mss_sec_system_cmd() {
        let nodes = vec![
            make_node(3, "Call", "os.system('rm -rf /')", 99),
        ];
        let findings = scan_nodes(&nodes);
        let sec = findings.iter().find(|f| f.rule_id == "MSS-SEC-03");
        assert!(sec.is_some(), "Should flag os.system()");
        let v4 = findings.iter().find(|f| f.rule_id == "V4-01");
        assert!(v4.is_some(), "Should also flag rm -rf as non-idempotent");
    }

    #[test]
    fn test_v5_network_no_timeout() {
        let nodes = vec![
            make_node(4, "Call", "requests.get('http://api.example.com')", 55),
        ];
        let findings = scan_nodes(&nodes);
        assert!(findings.iter().any(|f| f.rule_id == "V5-01"));
    }

    #[test]
    fn test_v5_network_with_timeout() {
        let nodes = vec![
            make_node(4, "Call", "requests.get(url, timeout=30)", 55),
        ];
        let findings = scan_nodes(&nodes);
        assert!(!findings.iter().any(|f| f.rule_id == "V5-01"));
    }

    #[test]
    fn test_mss_waste_busywork() {
        let nodes = vec![
            make_node(5, "Call", "rewrite(text)", 1),  // short = suspect
        ];
        let findings = scan_nodes(&nodes);
        assert!(findings.iter().any(|f| f.rule_id == "MSS-WASTE-01"));
    }

    #[test]
    fn test_mss_waste_not_busywork() {
        let nodes = vec![
            make_node(5, "Call",
                "rewrite_document_with_structural_changes_and_add_new_sections(text)", 1),
        ];
        let findings = scan_nodes(&nodes);
        // Long call (>50 chars) should NOT trigger busywork
        assert!(!findings.iter().any(|f| f.rule_id == "MSS-WASTE-01"));
    }

    #[test]
    fn test_empty_nodes() {
        let findings = scan_nodes(&[]);
        assert!(findings.is_empty());
    }

    #[test]
    fn test_clean_code() {
        let nodes = vec![
            // Truly clean: path guard + encoding + timeout
            make_node(1, "Call", r#"if os.path.exists("file.txt"): open("file.txt", encoding="utf-8")"#, 10),
            make_node(2, "Call", "requests.get(url, timeout=30)", 20),
        ];
        let findings = scan_nodes(&nodes);
        // Clean code: open has exists guard + encoding, get has timeout — no findings expected
        assert!(
            findings.is_empty(),
            "Expected no findings for clean code, got: {:?}",
            findings.iter().map(|f| &f.rule_id).collect::<Vec<_>>()
        );
    }
}
