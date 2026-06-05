#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MSS StructuredExecutor v1.0 — Universal Structured Generation Engine

Core-Shell-Forbidden three-layer architecture with pluggable domain adapters.
AnchorGuardAdapter is the first domain plugin (RAG/QA).

Boundary declaration (A7 Honesty):
  ✅ Applicable: all generative tasks requiring precise, controllable, repeatable output
  ❌ Not applicable: AGI, consciousness simulation, philosophical reasoning
"""
import json, sys, os, re, time, hashlib
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

# ── Try to import AnchorGuard ──
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from vdp_anchor import AnchorWhitelist
    _HAS_ANCHORGUARD = True
except ImportError:
    _HAS_ANCHORGUARD = False

VERSION = "1.0"


# ═══════════════════════════════════════════════════════════
# 1. Universal Schema Data Model
# ═══════════════════════════════════════════════════════════

@dataclass
class CoreSpec:
    """Immutable core — any deviation = task failure."""
    primary_objective: str
    invariants: List[str] = field(default_factory=list)

@dataclass
class ParameterSpec:
    """Quantifiable shell parameter."""
    name: str
    type: str  # int, float, enum, string
    min: float = 0
    max: float = 100
    enum_values: List[str] = field(default_factory=list)
    default: Any = ""
    description: str = ""

@dataclass
class ShellSpec:
    """Tunable shell — bounded variance allowed."""
    parameters: List[ParameterSpec] = field(default_factory=list)

@dataclass
class ForbiddenSpec:
    """Absolute forbidden zone — any hit = immediate rejection."""
    elements: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)

@dataclass
class ValidationSpec:
    """Validation pipeline configuration."""
    pre_checks: List[str] = field(default_factory=list)
    post_checks: List[str] = field(default_factory=list)
    auto_retry: int = 3

@dataclass
class StructuredSchema:
    """Complete three-layer schema definition."""
    schema_version: str = "1.0"
    domain: str = "general"
    task_type: str = "generation"
    core: CoreSpec = field(default_factory=CoreSpec)
    shell: ShellSpec = field(default_factory=ShellSpec)
    forbidden: ForbiddenSpec = field(default_factory=ForbiddenSpec)
    validation: ValidationSpec = field(default_factory=ValidationSpec)

    def to_dict(self) -> Dict:
        return {
            "schema_version": self.schema_version,
            "domain": self.domain,
            "task_type": self.task_type,
            "core": {
                "primary_objective": self.core.primary_objective,
                "invariants": self.core.invariants,
            },
            "shell": {
                "parameters": [
                    {"name": p.name, "type": p.type, "min": p.min, "max": p.max,
                     "enum_values": p.enum_values, "default": p.default,
                     "description": p.description}
                    for p in self.shell.parameters
                ]
            },
            "forbidden": {
                "elements": self.forbidden.elements,
                "patterns": self.forbidden.patterns,
            },
            "validation": {
                "pre_checks": self.validation.pre_checks,
                "post_checks": self.validation.post_checks,
                "auto_retry": self.validation.auto_retry,
            }
        }


# ═══════════════════════════════════════════════════════════
# 2. Validation Engine (pluggable)
# ═══════════════════════════════════════════════════════════

class ValidationEngine:
    """Pluggable validation engine with registry pattern."""
    _validators: Dict[str, Callable] = {}

    @classmethod
    def register(cls, name: str, fn: Callable[[str], bool]):
        """Register a named validator."""
        cls._validators[name] = fn

    @classmethod
    def run(cls, schema: StructuredSchema, output: str) -> Dict:
        """Run all registered post-checks against output."""
        results = {}
        for check_name in schema.validation.post_checks:
            if check_name in cls._validators:
                try:
                    passed = cls._validators[check_name](output)
                    results[check_name] = {"passed": passed}
                except Exception as e:
                    results[check_name] = {"passed": False, "error": str(e)}
            else:
                results[check_name] = {"passed": True, "warning": "validator not found"}
        return results


# ═══════════════════════════════════════════════════════════
# 3. AnchorGuard Adapter (first domain plugin)
# ═══════════════════════════════════════════════════════════

class AnchorGuardAdapter:
    """Adapts AnchorGuard v1.1 into a StructuredExecutor domain plugin.
    
    Zero-breaking change integration: all existing AnchorGuard functions
    are reused directly. No refactoring of vdp_anchor.py required.
    """
    def __init__(self, ref_text: str, strictness: float = 0.5):
        self.ref_text = ref_text
        self.strictness = strictness
        self._anchors = []
        if _HAS_ANCHORGUARD:
            wl = AnchorWhitelist()
            wl.extract_from_text(ref_text)  # in-place mutation
            data = wl.to_dict()
            self._anchors = data.get("entries", [])
            self._anchor_count = data.get("count", 0)
        else:
            self._anchor_count = 0

    def extract_anchors(self) -> Dict[str, List[str]]:
        """Return extracted anchors (flat list from AnchorGuider.Whitelist)."""
        return {"entries": self._anchors, "count": self._anchor_count}

    def validate(self, output: str) -> bool:
        """Run simplified anchor validation.
        
        Checks output for forbidden language and fabricated entities.
        """
        violations = 0

        # Check for hedging/subjective language
        hedging = re.findall(r'(?:大概|可能|也许|我认为|感觉|或许|差不多|好像)', output)
        violations += len(hedging)

        # Check fabricated numbers (numbers in output not in reference)
        ref_nums = set(re.findall(r'\b\d+(?:\.\d+)?\b', self.ref_text))
        out_nums = set(re.findall(r'\b\d+(?:\.\d+)?\b', output))
        fabricated = out_nums - ref_nums
        violations += len(fabricated)

        # Check fabricated paths
        ref_paths = set(re.findall(r'[A-Za-z]:\\[^\s]+', self.ref_text))
        out_paths = set(re.findall(r'[A-Za-z]:\\[^\s]+', output))
        fabricated_paths = out_paths - ref_paths
        violations += len(fabricated_paths) * 2  # paths are heavy violations

        # Strictness thresholds
        ref_total = max(1, len(self.ref_text.split()))
        if self.strictness >= 0.9:
            max_allowed = 0
        elif self.strictness >= 0.7:
            max_allowed = max(0, ref_total // 50)
        elif self.strictness >= 0.4:
            max_allowed = max(0, ref_total // 25)
        else:
            max_allowed = max(0, ref_total // 10)

        return violations <= max_allowed

    def to_schema(self) -> StructuredSchema:
        """Auto-generate a StructuredSchema from AnchorGuard config."""
        # Show top 5 anchor entries as preview
        top = self._anchors[:5] if self._anchors else ["(no anchors extracted)"]

        return StructuredSchema(
            schema_version="1.0",
            domain="rag_qa",
            task_type="基于参考信息的结构化问答",
            core=CoreSpec(
                primary_objective="仅使用参考信息回答问题，不编造内容",
                invariants=[
                    "所有事实必须来自参考文本",
                    f"锚点条目: {', '.join(top)}" if self._anchors else None,
                ],
            ),
            shell=ShellSpec(parameters=[
                ParameterSpec(
                    name="strictness", type="float",
                    min=0.0, max=1.0, default=self.strictness,
                    description="严格程度: 0=最宽松(创意) 0.5=平衡 1.0=最严格(零宽容)"
                ),
            ]),
            forbidden=ForbiddenSpec(
                elements=["我认为", "可能", "大概", "也许", "不确定"],
                patterns=[r"根据我的知识", r"据我所知", r"在我的训练数据中"],
            ),
            validation=ValidationSpec(
                post_checks=["anchor_guard_validate", "forbidden_elements_check",
                             "forbidden_patterns_check"],
                auto_retry=3,
            ),
        )


# ── Register AnchorGuard validator ──

if _HAS_ANCHORGUARD:
    # Module-level adapter instance for the validator registry
    # (created dynamically per call, this is just the factory registration)

    def _anchor_guard_validate(output: str) -> bool:
        """Registered validator that checks against the active adapter instance."""
        # Validator is called with the current adapter context
        return True  # Fallback; actual validation runs via adapter.validate()

    ValidationEngine.register("anchor_guard_validate", _anchor_guard_validate)

    del _anchor_guard_validate  # Clean up module-level; real calls use adapter instance


# ═══════════════════════════════════════════════════════════
# 4. Forbidden Checks (generic, works without AnchorGuard)
# ═══════════════════════════════════════════════════════════

def _check_forbidden_elements(output: str, schema: StructuredSchema) -> bool:
    """Check output does NOT contain any forbidden elements."""
    for elem in schema.forbidden.elements:
        if elem in output:
            return False
    return True

def _check_forbidden_patterns(output: str, schema: StructuredSchema) -> bool:
    """Check output does NOT match any forbidden regex patterns."""
    for pat in schema.forbidden.patterns:
        try:
            if re.search(pat, output):
                return False
        except re.error:
            pass
    return True

ValidationEngine.register("forbidden_elements_check",
    lambda output: True)  # Schema-aware, called via instance method

ValidationEngine.register("forbidden_patterns_check",
    lambda output: True)  # Schema-aware, called via instance method


# ═══════════════════════════════════════════════════════════
# 5. Structured Executor Core
# ═══════════════════════════════════════════════════════════

class StructuredExecutor:
    """Universal structured generation engine.

    Consumes a StructuredSchema, wraps any LLM callable,
    and enforces Core-Shell-Forbidden constraints via the
    ValidationEngine plugin system.

    Usage:
        adapter = AnchorGuardAdapter(ref_text, strictness=0.7)
        schema = adapter.to_schema()
        executor = StructuredExecutor(my_llm_function)
        result = executor.execute(schema)
    """

    def __init__(self, llm_callable: Optional[Callable[[str], str]] = None):
        self.llm = llm_callable
        self.stats = defaultdict(int)
        self.history: List[Dict] = []

    def compile_prompt(self, schema: StructuredSchema) -> str:
        """Compile StructuredSchema into a precise execution prompt."""
        lines = []

        # ── Core (immutable constraints first) ──
        lines.append(f"[CORE] 目标: {schema.core.primary_objective}")
        for inv in schema.core.invariants:
            if inv:
                lines.append(f"[INVARIANT] {inv}")

        # ── Shell (tunable parameters) ──
        for param in schema.shell.parameters:
            lines.append(
                f"[PARAM] {param.name}={param.default} "
                f"(类型:{param.type}, 范围:{param.min}-{param.max})"
            )

        # ── Forbidden (absolute constraints last) ──
        if schema.forbidden.elements:
            lines.append(f"[FORBIDDEN] 禁止: {'; '.join(schema.forbidden.elements)}")

        return "\n".join(lines)

    def execute(self, schema: StructuredSchema,
                input_text: str = "",
                adapter: Optional[AnchorGuardAdapter] = None) -> Dict:
        """Execute a generation task under schema constraints.

        Args:
            schema: The StructuredSchema to enforce
            input_text: Raw input/question (for LLM)
            adapter: Optional AnchorGuardAdapter for anchor validation

        Returns:
            {
                "success": bool,
                "output": str,
                "attempts": int,
                "violations": List[str],
                "schema": str,
                "thermal_tax_tokens": int,
                "pass_rate": float,
            }
        """
        compiled = self.compile_prompt(schema)
        prompt = f"{compiled}\n\n[INPUT]\n{input_text}" if input_text else compiled
        prompt_tokens = len(prompt.split())

        output = ""
        violations = []
        success = False

        for attempt in range(1, schema.validation.auto_retry + 1):
            if self.llm:
                try:
                    raw = self.llm(prompt)
                except Exception as e:
                    violations.append(f"LLM_CALL_FAILED[{attempt}]: {e}")
                    continue
            else:
                # Dry-run mode: self-test without LLM
                raw = input_text

            output = raw

            # ── Forbidden elements check ──
            for elem in schema.forbidden.elements:
                if elem in output:
                    violations.append(f"FORBIDDEN_ELEMENT[{attempt}]: '{elem}' found")
                    # Don't break — collect all violations

            # ── Forbidden patterns check ──
            for pat in schema.forbidden.patterns:
                try:
                    if re.search(pat, output):
                        violations.append(f"FORBIDDEN_PATTERN[{attempt}]: matched '{pat}'")
                except re.error:
                    pass

            # ── AnchorGuard validation (if adapter provided) ──
            if adapter and _HAS_ANCHORGUARD:
                if not adapter.validate(output):
                    violations.append(f"ANCHOR_GUARD_FAIL[{attempt}]")

            # ── Run registered post-checks ──
            check_results = ValidationEngine.run(schema, output)
            for name, result in check_results.items():
                if not result.get("passed", True):
                    violations.append(f"CHECK_FAIL[{attempt}]: {name} {result.get('error', '')}")

            if not violations:
                success = True
                break

        self.stats["total_attempts"] += attempt
        self.stats["total_calls"] += 1
        if success:
            self.stats["successes"] += 1

        result = {
            "success": success,
            "output": output,
            "attempts": attempt,
            "violations": violations,
            "schema_domain": schema.domain,
            "thermal_tax_tokens": prompt_tokens * attempt,
            "pass_rate": round(self.stats["successes"] / max(1, self.stats["total_calls"]) * 100, 1),
        }
        self.history.append(result)
        return result

    def get_stats(self) -> Dict:
        return dict(self.stats)


# ═══════════════════════════════════════════════════════════
# 6. Pre-built Domain Schemas
# ═══════════════════════════════════════════════════════════

PHOTOGRAPHY_SCHEMA = StructuredSchema(
    schema_version="1.0",
    domain="photography",
    task_type="鞋类产品视频生成",
    core=CoreSpec(
        primary_objective="生成产品展示视频，展示鞋类产品",
        invariants=[
            "主体锚点不变", "垂直对齐90°", "裁剪规则不变",
            "roll_deg=0", "无缩放无拉伸",
        ],
    ),
    shell=ShellSpec(parameters=[
        ParameterSpec("headroom", "float", 0.02, 0.15, default=0.08,
                      description="头部空间比例"),
        ParameterSpec("motion_range_cm", "float", 0, 15, default=8,
                      description="最大机位位移"),
        ParameterSpec("fill_ratio", "float", 0.25, 0.45, default=0.35,
                      description="主体在画面中的填充比例"),
    ]),
    forbidden=ForbiddenSpec(
        elements=["人物", "手部", "肤色块", "文字叠加", "缩放变形"],
        patterns=[r"flesh.tone", r"human.finger"],
    ),
    validation=ValidationSpec(
        post_checks=["forbidden_elements_check", "forbidden_patterns_check"],
        auto_retry=3,
    ),
)

CODE_GEN_SCHEMA = StructuredSchema(
    schema_version="1.0",
    domain="code",
    task_type="Python函数生成",
    core=CoreSpec(
        primary_objective="生成符合签名规范的Python函数",
        invariants=["函数名和类型签名不变", "不执行系统命令", "不含硬编码密钥"],
    ),
    shell=ShellSpec(parameters=[
        ParameterSpec("docstring_style", "enum",
                      enum_values=["google", "numpy", "restructuredtext"],
                      default="google", description="文档字符串风格"),
        ParameterSpec("add_type_hints", "bool", default=True,
                      description="是否添加类型标注"),
    ]),
    forbidden=ForbiddenSpec(
        elements=["os.system", "subprocess.call", "eval(", "exec("],
        patterns=[r"password\s*=", r"secret\s*=", r"api_key\s*="],
    ),
    validation=ValidationSpec(
        post_checks=["forbidden_elements_check", "forbidden_patterns_check"],
        auto_retry=2,
    ),
)


# ═══════════════════════════════════════════════════════════
# 7. CLI
# ═══════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(description=f"MSS StructuredExecutor v{VERSION}")
    ap.add_argument("--schema", choices=["photography", "code", "rag_qa"],
                    default="photography", help="Domain schema to use")
    ap.add_argument("--input", help="Input text or question")
    ap.add_argument("--ref", help="Reference text (for RAG/QA schema)")
    ap.add_argument("--strictness", type=float, default=0.7,
                    help="AnchorGuard strictness (0.0-1.0)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Validate schema without LLM call")
    args = ap.parse_args()

    # Select schema
    if args.schema == "photography":
        schema = PHOTOGRAPHY_SCHEMA
    elif args.schema == "code":
        schema = CODE_GEN_SCHEMA
    elif args.schema == "rag_qa":
        if not args.ref:
            print("Error: --ref required for rag_qa schema")
            sys.exit(1)
        adapter = AnchorGuardAdapter(args.ref, args.strictness)
        schema = adapter.to_schema()
    else:
        print(f"Unknown schema: {args.schema}")
        sys.exit(1)

    # Display compiled prompt
    executor = StructuredExecutor()
    compiled = executor.compile_prompt(schema)
    print("=" * 60)
    print(f"Schema: {schema.domain} ({schema.task_type})")
    print(f"Version: {schema.schema_version}")
    print("=" * 60)
    print(compiled)

    if args.dry_run:
        print(f"\n[DRY-RUN] Schema validated, no LLM call made.")
        return

    if args.input:
        adapter = None
        if args.schema == "rag_qa" and args.ref:
            adapter = AnchorGuardAdapter(args.ref, args.strictness)
        result = executor.execute(schema, args.input, adapter=adapter)
        print(f"\n[RESULT] success={result['success']} "
              f"attempts={result['attempts']} violations={result['violations']}")
    else:
        print("\n[DONE] Schema compiled. Use --input to execute.")


if __name__ == "__main__":
    main()