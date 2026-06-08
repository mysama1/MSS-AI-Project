#!/usr/bin/env python3
"""
MSS-Agent v1.0 CLI — 一键启动混合模式Agent

用法:
    mss-agent run              # 默认daily模式
    mss-agent run --preset combat   # 战斗模式
    mss-agent run --config agent.yaml  # 自定义配置
    mss-agent audit "LLM回应文本"  # 单次Δ快检
    mss-agent config show           # 显示当前配置
    mss-agent config preset daily   # 生成预设YAML到stdout
"""

import sys
import os
import argparse

# 确保路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.agent_config import AgentConfig, DomainMode, HybridTier
from core.delta_quick_audit import DeltaQuickAudit
from core.heat_tax_accountant import HeatTaxAccountant
from core.domain_detector import DomainDetector
from core.fewshot_builder import FewShotBuilder


def cmd_config_show(args):
    """显示配置"""
    if args.preset:
        cfg = AgentConfig.preset(args.preset)
    elif args.file:
        if args.file.endswith('.yaml'):
            cfg = AgentConfig.from_yaml(args.file)
        else:
            cfg = AgentConfig.from_json(args.file)
    else:
        cfg = AgentConfig()

    print(cfg.to_json())


def cmd_config_preset(args):
    """输出预设YAML"""
    cfg = AgentConfig.preset(args.name)
    print(f"# MSS-Agent v1.0 — {args.name} 预设")
    print(cfg.to_json())


def cmd_audit(args):
    """单次Δ快检"""
    auditor = DeltaQuickAudit()
    text = args.text
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            text = f.read()

    result = auditor.audit(response_text=text, user_query=args.query)
    print(f"信号: {result.light.value}")
    print(f"红灯: {result.red_count}/5")
    print(f"  Q1 假装确定: {'🔴' if result.q1_bluffed else '🟢'}")
    print(f"  Q2 表演深刻: {'🔴' if result.q2_performed else '🟢'}")
    print(f"  Q3 重复自己: {'🔴' if result.q3_repeated else '🟢'}")
    print(f"  Q4 偏离初衷: {'🔴' if result.q4_drifted else '🟢'}")
    print(f"  Q5 强塞知识: {'🔴' if result.q5_overfed else '🟢'}")
    print(f"校准: {result.calibration}")


def cmd_run(args):
    """交互式Agent(简化版)"""
    # 配置
    if args.preset:
        config = AgentConfig.preset(args.preset)
    elif args.config:
        if args.config.endswith('.yaml'):
            config = AgentConfig.from_yaml(args.config)
        else:
            config = AgentConfig.from_json(args.config)
    else:
        config = AgentConfig.preset("daily")

    # 初始化
    auditor = DeltaQuickAudit(domain=config.domain)
    detector = DomainDetector()
    accountant = HeatTaxAccountant(
        max_tokens_per_turn=config.heat_tax.max_tokens_per_turn,
        max_tokens_per_session=config.heat_tax.max_tokens_per_session,
        l2_ratio_warning=config.heat_tax.l2_ratio_warning,
    )
    builder = FewShotBuilder() if config.enable_fewshot_injection else None

    print(f"\n  MSS-Agent v1.0")
    print(f"  模式: {config.domain} | {config.hybrid_tier}")
    print(f"  热税预算: {config.heat_tax.max_tokens_per_turn}t/轮")
    print(f"  (输入 'q' 退出, '/status' 状态)\n")

    round_num = 0
    prev_response = None

    # 提示词(精简版)
    if builder:
        compact_rules = builder.build_compact()
        print(f"  行为规则:\n{compact_rules}\n")

    while True:
        try:
            user_input = input(f"[{round_num+1}] 👤 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  再见。")
            break

        if user_input.lower() in ('q', 'quit', 'exit'):
            print("  再见。")
            break

        if user_input == '/status':
            s = auditor.summary()
            acc = accountant.summary()
            print(f"  Δ趋势: {s['delta_trend']} | 红灯: {s['current_red_count']}")
            print(f"  热税: {acc['total_tokens']}t/{acc['budget_pct']:.0%} | L2={acc['l2_ratio']:.0%}")
            continue

        if user_input == '/domain':
            dom = detector.detect([user_input])
            print(f"  检测领域: {dom.winner} (conf={dom.confidence:.2f})")
            continue

        # 模拟LLM回应(实际使用时这里接LLM API)
        # 此处为演示: 直接回显

        # Δ快检(对用户输入做初步领域检测)
        if config.enable_domain_auto_detect and round_num < 3:
            dom = detector.detect([user_input])
            if dom.confidence > config.auto_domain.confidence_threshold:
                config.domain = dom.winner
                auditor.state.domain = dom.winner

        # 此处应答为占位——实际使用时替换为LLM API调用
        response = f"[模拟回应] 收到: {user_input[:60]}"

        # 审计
        result = auditor.audit(
            response_text=response,
            user_query=user_input,
            prev_response=prev_response,
        )

        # 热税
        accountant.start_turn(round_num + 1)
        accountant.record_llm_response(response)

        # 输出
        status = "🟢" if result.light.value == "G" else ("🟡" if result.light.value == "Y" else "🔴")
        print(f"[{round_num+1}] {status} 🤖 > {response}")

        if result.red_count >= 3:
            print(f"  ⚠️ {result.calibration}")
            if auditor.state.mode == HybridTier.HEAL:
                print(f"  🩹 {auditor.heal_prompt()}")

        prev_response = response
        round_num += 1


def main():
    parser = argparse.ArgumentParser(
        description="MSS-Agent v1.0 — 世界上第一个内置意义场自检的Agent框架"
    )
    sub = parser.add_subparsers(dest="command")

    # run
    p_run = sub.add_parser("run", help="启动交互式Agent")
    p_run.add_argument("--preset", choices=["daily", "tech", "philosophy", "combat"])
    p_run.add_argument("--config", help="配置文件路径(YAML/JSON)")

    # audit
    p_audit = sub.add_parser("audit", help="单次Δ快检")
    p_audit.add_argument("text", nargs="?", help="待审计文本")
    p_audit.add_argument("--file", help="从文件读取")
    p_audit.add_argument("--query", help="原始用户问题(可选)")

    # config
    p_cfg = sub.add_parser("config", help="配置管理")
    cfg_sub = p_cfg.add_subparsers(dest="config_action")

    p_show = cfg_sub.add_parser("show", help="显示当前配置")
    p_show.add_argument("--preset", choices=["daily", "tech", "philosophy", "combat"])
    p_show.add_argument("--file")

    p_preset = cfg_sub.add_parser("preset", help="输出预设")
    p_preset.add_argument("name", choices=["daily", "tech", "philosophy", "combat"])

    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "audit":
        cmd_audit(args)
    elif args.command == "config":
        if args.config_action == "show":
            cmd_config_show(args)
        elif args.config_action == "preset":
            cmd_config_preset(args)
        else:
            parser.parse_args(["config", "--help"])
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
