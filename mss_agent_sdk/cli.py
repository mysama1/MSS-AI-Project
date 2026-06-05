"""
MSS-Agent SDK 命令行工具
"""
import sys
import argparse
from pathlib import Path

from .client import MSSClient
from .config import SDKConfig


def main():
    parser = argparse.ArgumentParser(description="MSS-Agent 逻辑审计工具")
    parser.add_argument("text", nargs="?", help="待审计文本")
    parser.add_argument("-f", "--file", help="从文件读取文本")
    parser.add_argument("-c", "--config", help="配置文件路径")
    parser.add_argument("--local-only", action="store_true", help="仅本地模式")
    parser.add_argument("--anchor", choices=["objective", "actual", "subjective"],
                        help="意义锚定层级")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    
    args = parser.parse_args()
    
    # 获取文本
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        # 从stdin读取
        text = sys.stdin.read()
    
    if not text.strip():
        print("错误: 未提供待审计文本", file=sys.stderr)
        sys.exit(1)
    
    # 配置
    config = SDKConfig()
    if args.local_only:
        config.local_only = True
    
    client = MSSClient(config)
    
    # 执行审计或锚定
    if args.anchor:
        from .types import AnchorLevel
        level_map = {
            "objective": AnchorLevel.OBJECTIVE,
            "actual": AnchorLevel.ACTUAL,
            "subjective": AnchorLevel.SUBJECTIVE,
        }
        result = client.anchor(text, level_map[args.anchor])
        print(f"锚定层级: {result.level.name}")
        print(f"热税降低: {result.heat_tax_before:.3f} → {result.heat_tax_after:.3f}")
        print(f"节省比例: {result.savings:.1%}")
        print(f"锚定文本: {result.text}")
    else:
        result = client.audit(text)
        if args.json:
            import json
            print(json.dumps({
                "passed": result.passed,
                "logic_rigidity": result.logic_rigidity,
                "heat_tax": result.heat_tax,
                "confidence": result.confidence.value,
                "layer": result.layer,
                "contradictions": result.contradictions,
                "suggestions": result.suggestions,
            }, ensure_ascii=False, indent=2))
        else:
            print(result.to_markdown())
        
        sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
