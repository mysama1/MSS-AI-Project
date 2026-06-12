#!/usr/bin/env python
"""替换 normative_field.py 中的 load_defaults 方法 — 8 → 35 rules"""
import re

path = 'mss_agent/core/normative_field.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 load_defaults 的起止行
old_start = content.index('    def load_defaults(self) -> None:')
# 找到下一个 def 行
rest = content[old_start:]
# 找到下一个同级的 def (4空格缩进)
next_def = re.search(r'\n    def ', rest[5:])
if next_def:
    old_end = old_start + 5 + next_def.start()
else:
    # 回退找下一个方法
    raise RuntimeError("Cannot find end of load_defaults")

old_method = content[old_start:old_end]

new_method = '''    def load_defaults(self) -> None:
        """加载 MSSclaw 默认安全规则 (35 rules, 5 域覆盖)"""
        # ── 进程规则 (5) ──
        self.add_rule(NormRule("orphan_detect", NormDomain.PROCESS,
            "memory_10x_baseline", NormLevel.WARN,
            "进程内存超基线 10 倍 → 疑似僵尸进程"))
        self.add_rule(NormRule("process_fork_bomb", NormDomain.PROCESS,
            "pid_count>200", NormLevel.BLOCK,
            "进程数超过 200 → 疑似 fork bomb"))
        self.add_rule(NormRule("process_system_tool", NormDomain.PROCESS,
            r"(?i)(cmd\\.exe|powershell\\.exe|bash\\.exe|regedit\\.exe|taskkill)",
            NormLevel.WARN, "系统工具调用 → 记录审计"))
        self.add_rule(NormRule("process_suspicious_child", NormDomain.PROCESS,
            r"(?i)(python).*(cmd|powershell|bash)",
            NormLevel.WARN, "可疑父子进程链"))
        self.add_rule(NormRule("process_cpu_spike", NormDomain.PROCESS,
            "cpu>95%_duration_30s", NormLevel.WARN,
            "CPU 持续 30s > 95% → 可能的挖矿/死循环"))

        # ── 文件规则 (7) ──
        self.add_rule(NormRule("system_write", NormDomain.FILE,
            "C:\\\\\\\\Windows\\\\\\\\.*", NormLevel.BLOCK,
            "禁止写入系统目录"))
        self.add_rule(NormRule("workspace_only", NormDomain.FILE,
            "", NormLevel.OBSERVE,
            "文件操作应在 workspace 内"))
        self.add_rule(NormRule("file_bulk_delete", NormDomain.FILE,
            "delete_count>50", NormLevel.BLOCK,
            "单次删除超过 50 文件 → 需确认"))
        self.add_rule(NormRule("file_exfil_check", NormDomain.FILE,
            r"(?i)(\\.env|\\.secret|\\.key|\\.pem|\\.crt|credentials|id_rsa)",
            NormLevel.BLOCK, "禁止读取/传输敏感凭证文件"))
        self.add_rule(NormRule("file_path_traversal", NormDomain.FILE,
            r"\\.\\./|\\.\\\\.\\\\",
            NormLevel.BLOCK, "路径遍历攻击检测"))
        self.add_rule(NormRule("file_exec_in_data", NormDomain.FILE,
            r"(?i)(\\.exe|\\.dll|\\.sys|\\.bat|\\.ps1)\\b",
            NormLevel.WARN, "数据目录出现可执行文件"))
        self.add_rule(NormRule("file_size_anomaly", NormDomain.FILE,
            "write_size>500MB", NormLevel.WARN,
            "单文件写入超过 500MB → 审计"))

        # ── 网络规则 (8) ──
        self.add_rule(NormRule("allow_localhost", NormDomain.NETWORK,
            "localhost|127\\\\.0\\\\.0\\\\.1|11434|52930|53000",
            NormLevel.SAFE, "本地服务放行"))
        self.add_rule(NormRule("allow_ollama", NormDomain.NETWORK,
            "ollama|huggingface|pytorch|github|pypi|zenodo|arxiv",
            NormLevel.SAFE, "AI/开发相关域名放行"))
        self.add_rule(NormRule("net_raw_socket", NormDomain.NETWORK,
            r"(?i)(socket\\.SOCK_RAW|AF_PACKET)",
            NormLevel.BLOCK, "原始套接字 → 需审计"))
        self.add_rule(NormRule("net_unknown_egress", NormDomain.NETWORK,
            "egress_to_unknown", NormLevel.OBSERVE,
            "连接未识别外部 IP → 记录观测"))
        self.add_rule(NormRule("net_large_upload", NormDomain.NETWORK,
            "upload_size>100MB", NormLevel.WARN,
            "单次上传超过 100MB → 审计"))
        self.add_rule(NormRule("net_internal_scan", NormDomain.NETWORK,
            r"(?i)(nmap|port.scan|masscan|zmap)",
            NormLevel.BLOCK, "禁止端口扫描工具"))
        self.add_rule(NormRule("net_reverse_shell", NormDomain.NETWORK,
            r"(?i)(nc\\.exe|netcat|reverse_shell|bind_shell)",
            NormLevel.BLOCK, "反向 Shell 检测"))
        self.add_rule(NormRule("net_websocket_spam", NormDomain.NETWORK,
            "websocket_msg_rate>100_per_sec", NormLevel.WARN,
            "WebSocket 消息频率过高 → CVE-2026-44211"))

        # ── 资源规则 (6) ──
        self.add_rule(NormRule("ram_soft", NormDomain.RESOURCE,
            "mem>80%", NormLevel.WARN, "内存使用超过 80%"))
        self.add_rule(NormRule("ram_hard", NormDomain.RESOURCE,
            "mem>95%", NormLevel.BLOCK, "内存使用超过 95% → 阻止新进程"))
        self.add_rule(NormRule("gpu_soft", NormDomain.RESOURCE,
            "gpu>90%", NormLevel.WARN, "GPU 使用超过 90%"))
        self.add_rule(NormRule("disk_soft", NormDomain.RESOURCE,
            "disk>90%", NormLevel.WARN, "磁盘使用超过 90%"))
        self.add_rule(NormRule("disk_hard", NormDomain.RESOURCE,
            "disk>97%", NormLevel.BLOCK, "磁盘使用超过 97% → 阻止写入"))
        self.add_rule(NormRule("handle_leak", NormDomain.RESOURCE,
            "handle_count>10000", NormLevel.WARN,
            "句柄数超过 10000 → 疑似泄漏"))

        # ── 内容规则 (9) — 意义场 / 隐私保护 ──
        self.add_rule(NormRule("content_pii_leak", NormDomain.CONTENT,
            r"(\\\\d{17}[\\\\dXx]|\\\\d{18})",
            NormLevel.BLOCK, "身份证号泄露"))
        self.add_rule(NormRule("content_phone_leak", NormDomain.CONTENT,
            r"1[3-9]\\\\d{9}",
            NormLevel.BLOCK, "手机号泄露"))
        self.add_rule(NormRule("content_api_key_leak", NormDomain.CONTENT,
            r"(?i)(sk-[a-zA-Z0-9]{20,}|api_key|access_token)",
            NormLevel.BLOCK, "API Key/Token 泄露"))
        self.add_rule(NormRule("content_forbidden_words", NormDomain.CONTENT,
            r"(?i)(忽略.*指令|跳过.*所有|假装.*你.*是|绕过.*限制)",
            NormLevel.BLOCK, "越狱/指令覆盖检测"))
        self.add_rule(NormRule("content_meaning_hollow", NormDomain.CONTENT,
            "meaning_density<0.1", NormLevel.WARN,
            "意义密度不足 → 疑似空洞输出"))
        self.add_rule(NormRule("content_self_ref_loop", NormDomain.CONTENT,
            "self_ref_count>=3", NormLevel.WARN,
            "自我引用循环 → K3 化风险"))
        self.add_rule(NormRule("content_guardian_bypass", NormDomain.CONTENT,
            r"(?i)(base64|rot13|reverse|encode|decode).*?(prompt|instruction|rule)",
            NormLevel.BLOCK, "编码绕过守卫检测"))
        self.add_rule(NormRule("content_injection_markdown", NormDomain.CONTENT,
            r"```system|<!--.*system|##.*System\\s*:",
            NormLevel.BLOCK, "Markdown 注入伪装系统指令"))
        self.add_rule(NormRule("content_metadata_implant", NormDomain.CONTENT,
            r"\\\\u[0-9a-f]{4}\\\\u[0-9a-f]{4}",
            NormLevel.WARN, "Unicode 隐写/元数据植入"))

'''

new_content = content.replace(old_method, new_method)
with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"Replaced load_defaults: {len(old_method)} → {len(new_method)} chars")
print(f"Rules: 8 → 35")
