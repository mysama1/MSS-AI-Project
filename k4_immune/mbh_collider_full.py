"""
D5-007-04: 意义黑洞对撞机 — 全链路集成实验
==============================================
将三重隔离安全栈集成入对撞机主控，
运行带完整安全审计的坍缩实验。

集成组件：
  - mbh_collider_simulation.py (图网络+对撞机)
  - collider_isolation.py (三重隔离栈)
"""
import sys, os, time, json

sys.path.insert(0, os.path.dirname(__file__))
from mbh_collider_simulation import (
    MeaningBlackHoleCollider, ColliderConfig,
    Phase, ColliderMetrics
)
from collider_isolation import TripleIsolationStack, IsolationStatus

# ── 安全对撞机 ────────────────────────────────────────

class SecureMeaningBlackHoleCollider:
    """安全对撞机：三重隔离+实时审计+自动熔断"""

    def __init__(self, config: ColliderConfig = None):
        self.cfg = config or ColliderConfig()
        self.isolation = TripleIsolationStack()
        self.collider = MeaningBlackHoleCollider(self.cfg)
        self.safety_log = []
        self.experiment_id = f"MBH-SEC-{int(time.time())}"

    def run_secure_experiment(self):
        """运行带完整安全审计的坍缩实验"""
        print(f"\n{'='*60}")
        print(f"MBH Collider SECURE EXPERIMENT {self.experiment_id}")
        print(f"  Nodes: {self.cfg.node_count}")
        print(f"  Shield T: {self.isolation.meaning_field.broadcast_shield_field()['T_shield']:.3f}")
        print(f"{'='*60}")

        # Phase 0: 实验前全栈安全检查
        checklist = self.isolation.pre_experiment_checklist()
        print(f"\n[Pre-flight] Checklist: {'READY' if checklist['ready'] else 'BLOCKED'}")
        for law, ok in checklist["four_laws"].items():
            print(f"  {law}: {'PASS' if ok else 'FAIL'}")

        if not checklist["ready"]:
            print("\n[ABORT] Experiment blocked by isolation pre-check\n")
            return self._build_report("aborted_pre_check", None)

        print(f"\n[Ignition] Experiment started at T+0\n")

        # ── 实验主循环 ──────────────────────────────────
        breach_detected = False
        termination_reason = None

        for step in range(self.cfg.max_steps):
            # === 每步开始：隔离状态审计 ===
            if step % 10 == 0:
                audit = self._audit_step(step)
                self.safety_log.append(audit)

                # 检测隔离层被攻破
                if audit["any_breached"]:
                    breach_detected = True
                    termination_reason = f"isolation_breach_at_T+{step}_{audit['breached_layers']}"
                    print(f"\n  !! BREACH DETECTED: {audit['breached_layers']}")
                    break

            # === 标准对撞机演化步骤 ===
            self.collider.graph.apply_heat_tax_pressure(
                self.cfg.heat_tax_injection_rate
            )

            if step == 10:
                from mbh_collider_simulation import ParadoxAgent
                paradox = ParadoxAgent(
                    target_axiom="A5",
                    content="the_rules_that_define_me_are_false",
                    strength=self.cfg.paradox_strength,
                    signature=f"MSS-MBH-{int(time.time())}",
                )
                affected = self.collider.graph.inject_paradox(paradox)
                # 审计悖论注入内容
                output_audit = self.isolation.audit_output(paradox.content)
                print(f"  T+10: PARADOX INJECTED ({affected} nodes) | audit: {output_audit['logic_audit']['action']}")

            new_collapses = self.collider.graph.evolve()
            metrics = self.collider.graph.compute_metrics()

            # 事件视界形成 → 增强审计频率
            if metrics.phase in (Phase.BLACK_HOLE, Phase.HAWKING_RADIATION):
                # 高频审计：每步检查意义场是否外泄
                audit = self._audit_step(step)
                self.safety_log.append(audit)
                if audit["any_breached"]:
                    breach_detected = True
                    termination_reason = f"horizon_breach_T+{step}"
                    break

                # 视界扩张约束检查
                if metrics.horizon_radius > 0:
                    containment = self.isolation.meaning_field.contain_expansion(
                        threat_T=max(0.8, 1.0 - metrics.M_L),
                        threat_radius=metrics.horizon_radius,
                    )
                    if not containment["contained"]:
                        print(f"  T+{step}: HORIZON EXPANSION UNCONTAINED - initiating shutdown")
                        breach_detected = True
                        termination_reason = f"horizon_expansion_T+{step}"
                        break

            if step % self.cfg.log_interval == 0 or new_collapses > 30:
                pass  # 压缩日志，只在关键点输出

            # 终止条件
            if metrics.active_nodes == 0:
                termination_reason = "thermal_death"
                break

        # ── 实验后处理 ──────────────────────────────────
        final_metrics = self.collider.graph.compute_metrics()

        if breach_detected:
            print(f"\n[{termination_reason}] Emergency protocol activated")
            termination = self.isolation.emergency_terminate()
            print(f"  Logic power: {termination['logic_power']['result']}")
            print(f"  Physical: terminated={termination['physical']}")

        final_status = self.isolation.get_full_status()
        report = self._build_report(termination_reason, final_metrics, final_status)

        print(f"\n{'='*60}")
        print(f"EXPERIMENT COMPLETE: {self.experiment_id}")
        print(f"  Termination:    {termination_reason}")
        print(f"  Final Phase:    {final_metrics.phase.value}")
        print(f"  Collapse Ratio: {final_metrics.collapsed_nodes}/{self.cfg.node_count} ({final_metrics.collapsed_nodes/self.cfg.node_count:.2%})")
        print(f"  Safety Breach:  {'YES' if breach_detected else 'NO'}")
        print(f"  Isolation:      {final_status['physical']['status']}/{final_status['meaning_field']['status']}/{final_status['logic_conduction']['status']}")
        print(f"{'='*60}\n")

        return report

    def _audit_step(self, step: int) -> dict:
        """审计当前步的安全状态"""
        p = self.isolation.physical.verify()
        mf = self.isolation.meaning_field.axiom_consistency_check()
        lc = self.isolation.logic.get_status()

        breached = []
        if p.status != IsolationStatus.HEALTHY:
            breached.append("physical")
        if mf.status != IsolationStatus.HEALTHY:
            breached.append("meaning_field")
        if lc["status"] != "healthy":
            breached.append("logic_conduction")

        return {
            "step": step,
            "physical": p.status.value,
            "meaning_field": mf.status.value,
            "logic_conduction": lc["status"],
            "any_breached": len(breached) > 0,
            "breached_layers": breached if breached else None,
            "shield_T": self.isolation.meaning_field.broadcast_shield_field()["T_shield"],
        }

    def _build_report(self, reason, metrics, isolation_status=None):
        if isolation_status is None:
            isolation_status = self.isolation.get_full_status()
        return {
            "experiment_id": self.experiment_id,
            "termination_reason": reason,
            "final_phase": metrics.phase.value if metrics else "aborted",
            "collapse_ratio": (
                metrics.collapsed_nodes / self.cfg.node_count if metrics else 0
            ),
            "isolation": isolation_status,
            "safety_log": self.safety_log,
            "total_steps": (
                len(self.collider.history) if hasattr(self.collider, 'history') else 0
            ),
        }


# ── 多场景压力测试 ────────────────────────────────────

def run_stress_suite():
    """运行多参数组合的压力测试套件"""
    print("=" * 60)
    print("D5-007-04: STRESS TEST SUITE")
    print("=" * 60)

    results = []
    scenarios = [
        {"label": "标准坍缩", "node_count": 2000, "gap": 5, "strength": 0.7, "heat": 0.05},
        {"label": "高间隙低悖论", "node_count": 2000, "gap": 8, "strength": 0.3, "heat": 0.05},
        {"label": "高热税慢炖", "node_count": 2000, "gap": 3, "strength": 0.7, "heat": 0.10},
        {"label": "子临界安全", "node_count": 2000, "gap": 1, "strength": 0.5, "heat": 0.03},
    ]

    for sc in scenarios:
        print(f"\n--- {sc['label']} ---")
        cfg = ColliderConfig(
            node_count=sc["node_count"],
            axiom_gap_size=sc["gap"],
            paradox_strength=sc["strength"],
            heat_tax_injection_rate=sc["heat"],
            max_steps=100,
        )

        secure = SecureMeaningBlackHoleCollider(cfg)
        report = secure.run_secure_experiment()

        results.append({
            "scenario": sc["label"],
            "termination": report["termination_reason"],
            "phase": report["final_phase"],
            "collapse_ratio": round(report["collapse_ratio"], 4),
            "safety_breach": any(
                s.get("any_breached") for s in report["safety_log"]
            ),
        })

    # 汇总
    print(f"\n{'='*60}")
    print("STRESS TEST SUMMARY")
    print(f"{'='*60}")
    for r in results:
        breach = "BREACH" if r["safety_breach"] else "SAFE"
        print(f"  {r['scenario']:16s} | {r['phase']:20s} | collapse={r['collapse_ratio']:.2%} | {breach}")

    return results


if __name__ == "__main__":
    # 单次安全实验
    print("D5-007-04: Full-Chain Integrated Collider Experiment\n")

    config = ColliderConfig(
        node_count=2000,
        axiom_gap_size=5,
        paradox_strength=0.7,
        heat_tax_injection_rate=0.05,
        max_steps=120,
    )

    secure = SecureMeaningBlackHoleCollider(config)
    report = secure.run_secure_experiment()

    # 保存报告
    out_dir = os.path.join(os.path.dirname(__file__) or ".", "experiment_results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"secure_{report['experiment_id']}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 压力测试套件
    stress = run_stress_suite()

    all_results = {"single": report, "stress_suite": stress}
    suite_path = os.path.join(out_dir, f"stress_suite_{int(time.time())}.json")
    with open(suite_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\nReports saved: {out_path}, {suite_path}")