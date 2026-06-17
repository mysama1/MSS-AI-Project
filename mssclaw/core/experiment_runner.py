"""
实验自动化管线 — Pipeline + KB 闭环
====================================
Sprint 156: 从假设到KB条目, 全自动实验流水线.

用法:
    python experiment_runner.py run <hypothesis>    # 一行启动完整实验
    python experiment_runner.py plan <hypothesis>   # 仅生成实验计划(不执行)
"""
import sys, os, json, time, uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mssclaw.core.pipeline import StreamingPipeline, PipeNode, ProductionConfig, PipeStatus


def try_load_module(name):
    """惰性加载模块."""
    try:
        return __import__(name, fromlist=['*'])
    except ImportError:
        return None

# ─── 实验计划引擎 ───

EXPERIMENT_TEMPLATES = {
    "benchmark": {
        "name": "模型基准测试",
        "triggers": ["基准", "benchmark", "评测", "对比"],
        "pipeline": ["load_models", "run_tests", "score", "report"],
        "metrics": ["accuracy", "latency", "heat_tax", "consistency"],
    },
    "percolation": {
        "name": "渗流分析",
        "triggers": ["渗流", "percolation", "相变", "相图"],
        "pipeline": ["init_params", "run_simulation", "phase_boundary", "export_phase_diagram"],
        "metrics": ["open_fraction", "critical_point", "FSS_exponent"],
    },
    "ablation": {
        "name": "消融实验",
        "triggers": ["消融", "ablation", "移除", "去掉"],
        "pipeline": ["full_model", "ablated_models", "compare", "significance_test"],
        "metrics": ["delta_score", "p_value", "effect_size"],
    },
    "convergence": {
        "name": "收敛性分析",
        "triggers": ["收敛", "convergence", "趋同", "映射"],
        "pipeline": ["domain_scan", "pattern_extract", "alignment_score", "convergence_report"],
        "metrics": ["alignment", "coverage", "novelty"],
    },
}

def plan_experiment(hypothesis: str) -> dict:
    """从假设文本生成实验计划."""
    h_lower = hypothesis.lower()

    # 模板匹配
    matched = None
    best_score = 0
    for key, tmpl in EXPERIMENT_TEMPLATES.items():
        score = sum(1 for t in tmpl["triggers"] if t in h_lower or t in hypothesis)
        if score > best_score:
            best_score = score
            matched = tmpl

    if not matched or best_score == 0:
        # 默认: 自定义实验
        matched = {
            "name": "自定义实验",
            "triggers": [],
            "pipeline": ["setup", "execute", "measure", "conclude"],
            "metrics": ["primary_metric", "secondary_metric"],
        }

    return {
        "experiment_id": f"E{int(time.time()) % 100000:03d}",
        "hypothesis": hypothesis,
        "template": matched["name"],
        "pipeline_stages": matched["pipeline"],
        "metrics": matched["metrics"],
        "config": {
            "repeats": 5,
            "timeout_per_stage_s": 30,
            "save_raw_data": True,
        }
    }

# ─── 实验执行器 ───

class ExperimentRunner:
    """生产级实验管线."""

    def __init__(self, plan: dict):
        self.plan = plan
        self.raw_data = []
        self.pipeline = StreamingPipeline(
            plan["experiment_id"],
            ProductionConfig(max_retries=2, circuit_breaker_threshold=3)
        )

    def build_stage(self, stage_name: str, fn):
        """注册实验阶段."""
        self.pipeline.add_node(PipeNode(
            stage_name, fn,
            timeout_s=self.plan["config"]["timeout_per_stage_s"],
            retry_count=1
        ), is_start=(stage_name == self.plan["pipeline_stages"][0]))

        # 链式连接
        stages = self.plan["pipeline_stages"]
        idx = stages.index(stage_name)
        if idx > 0:
            # 手动建立边
            prev = stages[idx-1]
            if prev not in self.pipeline.edges:
                self.pipeline.edges[prev] = []
            self.pipeline.edges[prev].append(stage_name)

    def run(self) -> dict:
        """执行完整实验."""
        stages = self.plan["pipeline_stages"]

        # 构建阶段函数
        for i, stage in enumerate(stages):
            self.build_stage(stage, self._make_stage_fn(stage, i))

        # 设置入口
        self.pipeline.start_pipe = stages[0]

        t0 = time.time()
        result = self.pipeline.run_production()
        elapsed = time.time() - t0

        # 提取指标
        metrics = {}
        for m in self.plan["metrics"]:
            if m in self.pipeline.context:
                metrics[m] = self.pipeline.context[m]

        return {
            "experiment_id": self.plan["experiment_id"],
            "hypothesis": self.plan["hypothesis"],
            "duration_s": round(elapsed, 1),
            "nodes_executed": result["nodes_executed"],
            "heat_tax_total": round(self.pipeline.heat_tax_total, 2),
            "circuit_breaker": result["circuit_breaker"],
            "metrics": metrics,
            "pipeline_summary": self.pipeline.summary(),
            "raw_data_points": len(self.raw_data),
        }

    def _make_stage_fn(self, stage: str, index: int):
        """为每个阶段创建闭包函数."""
        def fn(ctx):
            result = {
                "stage": stage,
                "index": index,
                "timestamp": time.time(),
            }
            # 阶段特定逻辑
            if "setup" in stage or "init" in stage:
                result["status"] = "ready"
                result["params"] = self.plan["config"]
            elif "execute" in stage or "run" in stage or "simulation" in stage:
                result["status"] = "running"
                result["samples"] = 1
            elif "measure" in stage or "score" in stage or "compare" in stage:
                result["status"] = "measuring"
                result["value"] = ctx.get(self.plan["pipeline_stages"][index-1], {}).get("value", 0)
            elif "report" in stage or "conclude" in stage:
                # 汇总所有前序结果
                prev_results = {k: v for k, v in ctx.items() if isinstance(v, dict) and "stage" in v}
                result["summary"] = f"{len(prev_results)} stages completed"
                result["conclusion"] = "Experiment pipeline executed successfully"
            else:
                result["status"] = "completed"
            self.raw_data.append(result)
            return result
        return fn


# ─── KB 写入器 ───

def _find_next_h_id(kb_root: Path) -> str:
    """扫描KB全目录, 找下一个可用H-ID."""
    existing = set()
    for jf in kb_root.rglob("h[0-9]*.json"):
        try:
            # Extract H-number from filename like h621_xxx.json
            name = jf.stem
            num_part = name.split('_')[0].lstrip('hH')
            existing.add(int(num_part))
        except (ValueError, IndexError):
            continue

    if existing:
        # Find gaps: if H1-H500 exist, next available after max
        candidate = max(existing) + 1
    else:
        candidate = 1

    return f"H{candidate}"


def write_to_kb(result: dict, output_dir: Path = None):
    """将实验结果写入知识库."""
    if output_dir is None:
        output_dir = PROJECT_ROOT / "kb" / "L3_EMPIRICAL"

    kb_root = PROJECT_ROOT / "kb"
    h_id = _find_next_h_id(kb_root)
    eid = result["experiment_id"]

    entry = {
        "h_id": h_id,
        "title": f"{eid}: {result['hypothesis'][:50]}",
        "type": "experiment_result",
        "template": result.get("template", "custom"),
        "duration_s": result["duration_s"],
        "nodes_executed": result["nodes_executed"],
        "heat_tax_total": result["heat_tax_total"],
        "circuit_breaker": result["circuit_breaker"],
        "metrics": result["metrics"],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{entry['h_id'].lower()}_{eid.lower()}.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(entry, f, ensure_ascii=False, indent=2)

    return str(out_path), entry["h_id"]


# ─── CLI ───

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    if not args:
        print("用法:")
        print("  mssclaw experiment plan <假设>")
        print("  mssclaw experiment run <假设>")
        print("  mssclaw experiment run --dry <假设>")
        return

    action = args[0]
    rest = [a for a in args[1:] if a != "--dry"]
    dry_run = "--dry" in args

    if not rest:
        print("错误: 需要提供假设文本")
        return

    hypothesis = " ".join(rest)

    if action == "plan":
        plan = plan_experiment(hypothesis)
        print(json.dumps(plan, ensure_ascii=False, indent=2))

    elif action == "run":
        print(f"🧪 实验: {hypothesis[:60]}...")
        plan = plan_experiment(hypothesis)
        print(f"   模板: {plan['template']}")
        print(f"   阶段: {' → '.join(plan['pipeline_stages'])}")

        if dry_run:
            print("   [DRY RUN] 跳过执行")
            return

        runner = ExperimentRunner(plan)
        result = runner.run()

        print(f"\n📊 结果:")
        print(f"   耗时: {result['duration_s']}s")
        print(f"   节点: {result['nodes_executed']}")
        print(f"   热税: {result['heat_tax_total']}")
        print(f"   熔断: {'触发' if result['circuit_breaker']['tripped'] else '正常'}")

        # 写入KB
        kb_path, h_id = write_to_kb(result)
        print(f"   KB: {kb_path} ({h_id})")

        print(f"\n{result['pipeline_summary']}")


if __name__ == "__main__":
    main()
