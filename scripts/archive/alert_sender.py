#!/usr/bin/env python3
"""
MSS 告警发送器 — Lark/Slack Webhook 通知
集成 rate_limiter TokenBucket 防止平台限流
"""
import os, json, urllib.request, time
from datetime import datetime
from rate_limiter import TokenBucket

# ── Webhook 地址 (环境变量) ──
LARK_WEBHOOK = os.getenv("LARK_WEBHOOK_URL", "")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "")

# ── 告警限速器: 1条/分钟, burst 2 (防同一事件多次触发) ──
_alert_limiter = TokenBucket(rate=1/60, burst=2)

# ── 颜色映射 ──
COLORS = {"ERROR": "red", "WARN": "orange", "INFO": "green"}


def send_alert(platform: str, title: str, content: str, level: str = "ERROR") -> bool:
    """发送告警到 Lark 或 Slack (自动限速)"""
    if not _alert_limiter.consume(1):
        print(f"[ALERT] Rate limited: {title[:60]}")
        return False
    
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if platform == "lark":
        if not LARK_WEBHOOK:
            print("[ALERT] LARK_WEBHOOK_URL not configured")
            return False
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": COLORS.get(level, "blue"),
                },
                "elements": [{
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": f"**时间**: {ts}\n{content}"}
                }]
            }
        }
        url = LARK_WEBHOOK
    
    elif platform == "slack":
        if not SLACK_WEBHOOK:
            print("[ALERT] SLACK_WEBHOOK_URL not configured")
            return False
        payload = {
            "attachments": [{
                "color": COLORS.get(level, "#36a64f"),
                "title": title,
                "text": f"*{ts}*\n{content}",
                "footer": "MSS VDP Monitor",
            }]
        }
        url = SLACK_WEBHOOK
    
    else:
        return False
    
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[ALERT] Send failed: {e}")
        return False


def send_both(title: str, content: str, level: str = "ERROR"):
    """同时发送到 Lark 和 Slack"""
    ok_l = send_alert("lark", title, content, level) if LARK_WEBHOOK else None
    ok_s = send_alert("slack", title, content, level) if SLACK_WEBHOOK else None
    return ok_l, ok_s


# ── 预定义告警模板 ──

def alert_service_down(service_name: str, port: int, detail: str = "") -> bool:
    return send_both(
        f"🚨 服务 {service_name} 下线",
        f"端口 `{port}` 无响应\n{detail}",
        "ERROR"
    )

def alert_service_up(service_name: str, port: int) -> bool:
    return send_both(
        f"✅ 服务 {service_name} 恢复",
        f"端口 `{port}` 已恢复正常",
        "INFO"
    )

def alert_rate_limit(ip: str, endpoint: str, count: int) -> bool:
    return send_both(
        f"🛡️ 速率限制触发",
        f"IP `{ip}` 在 `{endpoint}` 被拦截 {count} 次",
        "WARN"
    )

def alert_vdp_scan_complete(files: int, violations: int, rejects: int, duration_ms: float) -> bool:
    level = "ERROR" if rejects > 0 else "INFO"
    return send_both(
        f"{'❌' if rejects else '✅'} VDP 扫描完成",
        f"文件: {files} | 违规: {violations} | 拒绝: {rejects} | 耗时: {duration_ms:.0f}ms",
        level
    )

def alert_memory_warning(process: str, current_mb: float, limit_mb: float) -> bool:
    return send_both(
        f"⚠️ 内存使用告警",
        f"进程 `{process}` 使用 {current_mb:.1f}MB / 限制 {limit_mb:.1f}MB",
        "WARN"
    )


# ── CLI ──

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description='MSS 告警发送器')
    ap.add_argument('--test', action='store_true', help='发送测试告警')
    ap.add_argument('--platform', choices=['lark','slack','both'], default='both')
    args = ap.parse_args()
    
    if args.test:
        print(f"Testing alert...")
        print(f"  Lark webhook:  {'configured' if LARK_WEBHOOK else 'NOT SET'}")
        print(f"  Slack webhook: {'configured' if SLACK_WEBHOOK else 'NOT SET'}")
        
        ok = alert_service_down("test-service", 9999, "这是一个测试告警")
        print(f"  Sent: {ok}")
    else:
        ap.print_help()
