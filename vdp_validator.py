#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MSS Verification Discipline Protocol (VDP) Validator v1.0"""
import sys, os, json, time, hashlib, re
from datetime import datetime
from typing import Optional, Any

class VDPResult:
    def __init__(self):
        self.passed = False
        self.discipline = ""
        self.message = ""
        self.confidence = 0.0
        self.is_inference = False
        self.errno_code = ""
        self.raw_output = ""
        self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {
            "passed": self.passed, "discipline": self.discipline,
            "message": self.message, "confidence": round(self.confidence, 2),
            "is_inference": self.is_inference, "errno": self.errno_code,
            "raw": self.raw_output[:500], "ts": self.timestamp
        }

class VDP:
    VERSION = "1.0"
    DISCIPLINES = ["V1_PATH", "V2_ERROR", "V3_ENCODING", "V4_ATOMIC", "V5_TIMEOUT", "V6_FACT"]

    def __init__(self, log_file=None):
        self.log_file = log_file or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs", "vdp_audit.log")
        self.failure_count = {}
        self._consecutive_failures = 0
        self._max_retries = 1

    def _log(self, result):
        entry = json.dumps(result.to_dict(), ensure_ascii=False)
        log_dir = os.path.dirname(self.log_file) or "."
        if os.path.isdir(log_dir):
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(entry + "\n")
            except Exception:
                pass  # Silent fail - don't block for logging issues

    # V1: Path Existence Pre-check
    def assert_path_exists(self, path, operation="read"):
        r = VDPResult()
        r.discipline = "V1_PATH"
        if not path:
            r.message = "EMPTY_PATH"; r.confidence = 0.0; self._log(r); return r
        expanded = os.path.expandvars(os.path.expanduser(path))
        exists = os.path.exists(expanded)
        r.passed = exists
        r.confidence = 1.0 if exists else 0.0
        r.raw_output = "path=%s exists=%s" % (expanded, exists)
        if not exists:
            parent = os.path.dirname(expanded)
            if os.path.exists(parent):
                siblings = os.listdir(parent)
                base = os.path.basename(expanded).lower()
                matches = [s for s in siblings if base in s.lower()]
                if matches:
                    r.message = "PATH_NOT_FOUND. Did you mean: %s? (parent=%s)" % (matches[:3], parent)
                    r.is_inference = True; r.confidence = 0.6
                else:
                    r.message = "PATH_NOT_FOUND: %s. Available: %s" % (expanded, siblings[:10])
                    r.confidence = 0.9
            else:
                r.message = "PATH_NOT_FOUND: %s (parent missing)" % expanded
                r.errno_code = "ENOENT"
        else:
            r.message = "PATH_OK: %s" % expanded
        self._log(r); return r

    # V2: Error Code Direct Report
    def report_error(self, result_obj, context=""):
        r = VDPResult()
        r.discipline = "V2_ERROR"
        errno = ""; stderr = ""; exc_type = ""
        if hasattr(result_obj, 'returncode'):
            errno = str(result_obj.returncode)
        if hasattr(result_obj, 'stderr'):
            stderr = (result_obj.stderr or "")[:500]
        if isinstance(result_obj, Exception):
            exc_type = type(result_obj).__name__
            errno = str(result_obj); stderr = str(result_obj)[:500]
        r.errno_code = errno; r.raw_output = stderr
        r.passed = (errno == "0" or errno == "")
        r.confidence = 1.0 if r.passed else 0.95
        prefix = "[%s] " % context if context else ""
        r.message = "%serrno=%s exc=%s" % (prefix, errno, exc_type)
        self._log(r); return r

    # V3: Encoding Declaration
    def check_encoding(self, data, declared_encoding="utf-8"):
        r = VDPResult()
        r.discipline = "V3_ENCODING"
        try:
            data.decode(declared_encoding)
            r.passed = True; r.message = "ENCODING_OK: %s len=%d" % (declared_encoding, len(data))
            r.confidence = 1.0
        except UnicodeDecodeError as e:
            for fallback in ["gbk", "gb18030", "latin-1"]:
                try:
                    data.decode(fallback)
                    r.message = "MISMATCH: declared=%s actual~=%s" % (declared_encoding, fallback)
                    r.confidence = 0.8; r.errno_code = "EILSEQ"; break
                except Exception:
                    continue
            else:
                r.message = "FAIL: %s error=%s" % (declared_encoding, e)
                r.confidence = 0.5; r.errno_code = "EILSEQ"
        self._log(r); return r

    # V4: Atomic Idempotent Write
    def safe_write_check(self, target_path, content="", mode="overwrite"):
        r = VDPResult()
        r.discipline = "V4_ATOMIC"
        target_expanded = os.path.expandvars(os.path.expanduser(target_path))
        exists = os.path.exists(target_expanded)
        if mode == "append" and exists:
            sz = os.path.getsize(target_expanded)
            h = hashlib.md5(content.encode("utf-8", errors="replace")).hexdigest()[:12]
            r.passed = True; r.confidence = 1.0
            r.message = "APPEND_MODE: %s (%d bytes) hash=%s" % (target_expanded, sz, h)
            r.raw_output = "\n<<<APPEND:%s>>>\n%s\n<<<END_APPEND>>>\n" % (datetime.now().isoformat(), content)
        elif mode == "overwrite" and exists:
            sz = os.path.getsize(target_expanded)
            r.passed = False; r.confidence = 0.3; r.errno_code = "EEXIST"
            r.message = "OVERWRITE_RISK: %s (%d bytes). Confirm?" % (target_expanded, sz)
        else:
            r.passed = True; r.confidence = 1.0
            r.message = "WRITE_SAFE: %s" % target_expanded
        self._log(r); return r

    # V5: Circuit Breaker
    def check_retry_limit(self, operation_key="default"):
        r = VDPResult()
        r.discipline = "V5_TIMEOUT"
        count = self.failure_count.get(operation_key, 0)
        if count >= self._max_retries + 1:
            r.passed = False; r.confidence = 1.0; r.errno_code = "ETOOMANY"
            r.message = "CIRCUIT_BREAKER: %s failed %d times -> DEGRADED_MODE" % (operation_key, count)
            self._consecutive_failures += 1
        else:
            r.passed = True; r.confidence = 1.0
            r.message = "RETRY_OK: %s attempts=%d/%d" % (operation_key, count, self._max_retries+1)
        self._log(r); return r

    def record_failure(self, operation_key="default"):
        self.failure_count[operation_key] = self.failure_count.get(operation_key, 0) + 1

    def reset_circuit(self, operation_key="default"):
        self.failure_count[operation_key] = 0; self._consecutive_failures = 0

    # V6: Fact vs Inference Separation
    INFERENCE_MARKERS = [
        "\u53ef\u80fd\u662f", "\u5927\u6982", "\u5e94\u8be5", "\u4f30\u8ba1", "\u63a8\u6d4b",
        "maybe", "probably", "likely", "might be", "could be",
        "\u6211\u89c9\u5f97", "\u6211\u8ba4\u4e3a", "\u4f3c\u4e4e\u662f",
        "I think", "I believe", "seems like", "appears to be"
    ]

    def classify_statement(self, statement, source="internal"):
        r = VDPResult()
        r.discipline = "V6_FACT"
        r.raw_output = statement[:200]
        lower = statement.lower()
        is_inference = any(m.lower() in lower for m in self.INFERENCE_MARKERS)
        # Check unverified paths
        if not is_inference:
            paths = re.findall(r'[A-Za-z]:\\\\[^\s"\']+', statement)
            for p in paths:
                if not os.path.exists(p):
                    is_inference = True; break
        r.is_inference = is_inference
        tagged = "[\u63a8\u65ad]" in statement or "[INFERENCE]" in statement.upper()
        r.passed = not is_inference or (is_inference and tagged)
        if is_inference:
            if tagged:
                r.confidence = 0.7; r.message = "LABELED_INFERENCE: OK"
            else:
                r.confidence = 0.2; r.errno_code = "EINFER"
                r.message = "UNLABELED_INFERENCE: tag with [\u63a8\u65ad] or [INFERENCE]"
        else:
            r.confidence = 0.95; r.message = "FACT: no markers"
        self._log(r); return r

    # Self-check
    def self_check(self):
        results = {"version": self.VERSION, "disciplines": {}}
        r1 = self.assert_path_exists(sys.executable)
        results["disciplines"]["V1_PATH"] = {"status": "OK" if r1.passed else "FAIL", "sample": r1.message}
        data = "\u9ece\u66fc\u6d4b\u8bd5".encode("utf-8")
        r3 = self.check_encoding(data, "utf-8")
        results["disciplines"]["V3_ENCODING"] = {"status": "OK" if r3.passed else "FAIL", "sample": r3.message}
        rf = self.classify_statement("Python at " + sys.executable)
        ri = self.classify_statement("\u8def\u5f84\u53ef\u80fd\u662f E:\\QClaw-Data\\skills")
        results["disciplines"]["V6_FACT"] = {
            "fact": "OK" if rf.passed else "FAIL",
            "inference": "OK" if ri.is_inference else "BROKEN"
        }
        ok = sum(1 for v in results["disciplines"].values() if isinstance(v, dict) and v.get("status") == "OK")
        results["score"] = "%d/%d" % (ok, len(results["disciplines"]))
        return results


def main():
    import argparse
    p = argparse.ArgumentParser(description="MSS VDP Validator v%s" % VDP.VERSION)
    p.add_argument("--check-path", help="V1: verify path exists")
    p.add_argument("--self-check", action="store_true", help="Run self-check")
    p.add_argument("--classify", help="V6: classify statement")
    args = p.parse_args()
    vdp = VDP()
    if args.self_check:
        print(json.dumps(vdp.self_check(), ensure_ascii=False, indent=2))
    elif args.check_path:
        r = vdp.assert_path_exists(args.check_path)
        print(json.dumps(r.to_dict(), ensure_ascii=False, indent=2))
    elif args.classify:
        r = vdp.classify_statement(args.classify)
        print(json.dumps(r.to_dict(), ensure_ascii=False, indent=2))
    else:
        print("MSS VDP Validator v" + VDP.VERSION)
        print("Use --self-check / --check-path PATH / --classify STATEMENT")

if __name__ == "__main__":
    main()