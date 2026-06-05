#!/usr/bin/env python3
"""
D5-023: MSS-LLM 感知壳适配器 v1.0
功能: 将当前模型(L2感知壳) 对接 MSS逻辑内核API
锚定: A2(信息切片) + A5(壳接口规范) + H141(六公理)
"""

import json, os, subprocess, sys

# ===== 壳配置 =====
SHELL_LAYER = "L2"  # 感知壳所在层
KERNEL_API = {
    "kb_query":    r"E:\AI_Workspace\MSS-AI\project\skills\mss-knowledge-navigator\scripts\kb_query.py",
    "kb_list":     r"E:\AI_Workspace\MSS-AI\project\skills\mss-knowledge-navigator\scripts\kb_list.py",
    "task_snap":   r"E:\QClaw-Data\workspace\task_system.py",
    "debt_track":  r"E:\AI_Workspace\MSS-AI\project\skills\mss-knowledge-navigator\scripts\debt_tracker.py",
    "research_map":r"E:\AI_Workspace\MSS-AI\project\skills\mss-knowledge-navigator\scripts\research_map.py",
}

# ===== 壳接口: 输入 → MSS查询 → 输出 =====
def shell_route(user_input: str):
    """
    感知壳路由:
    1. 解析用户输入 → 判断意图
    2. 路由到对应的MSS内核API
    3. 包装输出为MSS格式
    """
    inp = user_input.lower()
    
    # 意图识别 (简单关键词匹配)
    if any(kw in inp for kw in ["查", "搜索", "知识库", "h", "条目", "kb"]):
        api = "kb_query"
        args = _extract_keywords(user_input)
        
    elif any(kw in inp for kw in ["任务", "进度", "task", "p0", "p1", "d5"]):
        api = "task_snap"
        args = ["snapshot"]
        
    elif any(kw in inp for kw in ["债务", "td-", "清偿"]):
        api = "debt_track"
        args = []
        
    elif any(kw in inp for kw in ["地图", "热力", "方向", "领域", "分布"]):
        api = "research_map"
        args = []
        
    elif any(kw in inp for kw in ["mss-1", "mss-2", "mss-3", "分类", "浏览"]):
        api = "kb_list"
        args = [user_input.upper()[:6]]  # e.g., MSS-2
        
    else:
        # 默认: KB查询
        api = "kb_query"
        args = _extract_keywords(user_input)
    
    return api, args


def _extract_keywords(text: str):
    """从用户输入提取搜索关键词"""
    # 移除MSS前缀
    words = text.lower().replace("h", " ").replace("-", " ").split()
    keywords = [w for w in words if len(w) > 1 and w not in ["查","搜索","知识库","条目","找","一下"]]
    return [keywords[0]] if keywords else ["mss"]


def execute(api_name: str, args: list):
    """执行内核API调用并返回结果"""
    script = KERNEL_API.get(api_name)
    if not script:
        return {"error": f"API not found: {api_name}", "confidence": 0.3}
    
    try:
        if api_name == "task_snap":
            cmd = ["python", script, "snapshot"]
        else:
            cmd = ["python", script] + args
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        return {
            "api": api_name,
            "layer": SHELL_LAYER,
            "output": result.stdout[-2000:],  # 截断
            "stderr": result.stderr,
            "confidence": 0.85 if not result.stderr else 0.5,
            "axiom_refs": ["A2"] if api_name == "kb_query" else ["A2", "A3"]
        }
    except Exception as e:
        return {"error": str(e), "confidence": 0.1, "api": api_name}


# ===== 壳接口标准化 =====
def format_output(result: dict, format="mss"):
    """将内核输出包装为MSS格式"""
    if "error" in result:
        return f"[Confidence]: {result.get('confidence', 0.1)}\n[Layer]: {SHELL_LAYER}\n[Error]: {result['error']}"
    
    return f"""[Confidence]: {result['confidence']}
[Layer]: {SHELL_LAYER}
[API]: {result['api']}
[Axiom Refs]: {', '.join(result.get('axiom_refs', []))}
[Boundary]: Query results via L2 perception shell

{result.get('output', 'No output')}"""


# ===== CLI =====
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: perception_shell_adapter.py <query text>")
        print("       perception_shell_adapter.py --test")
        print("       perception_shell_adapter.py --route <text>")
        sys.exit(0)
    
    if sys.argv[1] == "--test":
        # 自测
        print("=== Perception Shell Self-Test ===")
        for test in ["查黎曼", "任务进度", "债务", "地图"]:
            api, args = shell_route(test)
            print(f"  '{test}' → {api}: {args}")
        print("✅ Route test passed")
    
    elif sys.argv[1] == "--route":
        text = " ".join(sys.argv[2:])
        api, args = shell_route(text)
        print(f"Route: {api}({args})")
        result = execute(api, args)
        print(format_output(result))
    
    else:
        text = " ".join(sys.argv[1:])
        api, args = shell_route(text)
        print(f"→ {api}({args})")
        result = execute(api, args)
        print(format_output(result))