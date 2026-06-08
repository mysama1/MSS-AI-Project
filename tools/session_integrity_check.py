#!/usr/bin/env python3
"""
Session Transcript Integrity Checker
检测孤儿 toolResult (role=tool 无前导 tool_calls) → 防止 499 循环

用法:
  python session_integrity_check.py <session_transcript.jsonl>
  python session_integrity_check.py <session_transcript.jsonl> --fix

根因:
  402 积分耗尽 → tool_use 被 LCM 压缩切除
  → 对应的 toolResult 成为孤儿 (role=tool 无前导 tool_calls)
  → API 拒绝 (499 invalid_request_error)
  → 后续所有消息陷入 499 循环
"""

import json
import sys
import shutil
from datetime import datetime
from collections import defaultdict


def load_messages(path: str) -> list:
    messages = []
    with open(path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                msg['_line'] = line_num
                messages.append(msg)
            except json.JSONDecodeError:
                pass
    return messages


def check_integrity(messages: list) -> dict:
    """扫描会话，返回诊断报告"""
    report = {
        'total': len(messages),
        'errors': {
            'orphan_tool_results': [],
            'error_499': [],
            'error_402': [],
            'tool_use_without_result': [],
        },
        'tool_call_ids': set(),
    }

    # Pass 1: 收集所有 tool_use 的 call_id
    for msg in messages:
        if msg.get('role') == 'assistant' and msg.get('tool_calls'):
            for tc in msg['tool_calls']:
                report['tool_call_ids'].add(tc['id'])

        content = msg.get('content', '')
        if isinstance(content, str):
            if '499' in content and ('invalid_request_error' in content or 'tool' in content.lower()):
                report['errors']['error_499'].append(msg['_line'])
            if '402' in content:
                report['errors']['error_402'].append(msg['_line'])

    # Pass 2: 检测孤儿
    for msg in messages:
        role = msg.get('role', '')
        
        # 孤儿 toolResult: role=tool 但 tool_call_id 不在已知的 tool_use 列表中
        if role == 'tool':
            call_id = msg.get('tool_call_id', '')
            if call_id not in report['tool_call_ids']:
                orphan = {
                    'line': msg['_line'],
                    'tool_call_id': call_id,
                    'tool_name': msg.get('name', '?'),
                    'content_preview': str(msg.get('content', ''))[:100],
                }
                report['errors']['orphan_tool_results'].append(orphan)

    return report


def fix_transcript(path: str, report: dict) -> str:
    """删除孤儿消息，返回备份路径"""
    backup = f"{path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(path, backup)
    
    orphan_lines = {o['line'] for o in report['errors']['orphan_tool_results']}
    error_499_lines = set(report['errors']['error_499'])
    remove_lines = orphan_lines | error_499_lines

    with open(path, 'r', encoding='utf-8') as fin:
        lines = fin.readlines()

    kept = 0
    removed = 0
    with open(path, 'w', encoding='utf-8') as fout:
        for i, line in enumerate(lines, 1):
            if i in remove_lines:
                removed += 1
                continue
            fout.write(line)
            kept += 1

    return backup


def main():
    if len(sys.argv) < 2:
        print("Usage: python session_integrity_check.py <transcript.jsonl> [--fix]")
        sys.exit(1)

    path = sys.argv[1]
    do_fix = '--fix' in sys.argv

    messages = load_messages(path)
    report = check_integrity(messages)

    print(f"📊 Session Integrity Report")
    print(f"   Total messages: {report['total']}")
    print(f"   Tool call IDs tracked: {len(report['tool_call_ids'])}")
    print()

    orphans = report['errors']['orphan_tool_results']
    errors_499 = report['errors']['error_499']
    errors_402 = report['errors']['error_402']

    if orphans:
        print(f"🔴 Orphan tool results: {len(orphans)}")
        for o in orphans:
            print(f"   Line #{o['line']}: {o['tool_name']}({o['tool_call_id'][:12]}...) — {o['content_preview']}")
    else:
        print(f"🟢 No orphan tool results")

    if errors_499:
        print(f"🔴 499 error messages: {len(errors_499)} at lines: {errors_499}")
    else:
        print(f"🟢 No 499 errors")

    if errors_402:
        print(f"🟡 402 credit exhaustion: {len(errors_402)} at lines: {errors_402}")

    has_issues = bool(orphans or errors_499)
    
    if has_issues and do_fix:
        print(f"\n🩹 Fixing: removing {len(orphans) + len(errors_499)} contaminated messages...")
        backup = fix_transcript(path, report)
        print(f"   Backup: {backup}")
        
        # Verify
        messages2 = load_messages(path)
        report2 = check_integrity(messages2)
        orphans2 = len(report2['errors']['orphan_tool_results'])
        errors_499_2 = len(report2['errors']['error_499'])
        if orphans2 == 0 and errors_499_2 == 0:
            print(f"   ✅ Clean! {report2['total']} messages, 0 errors")
        else:
            print(f"   ⚠️ Still has {orphans2} orphans, {errors_499_2} 499s")
    elif has_issues:
        print(f"\n💡 Run with --fix to auto-clean")
        sys.exit(1)
    else:
        print(f"\n✅ Session clean — no integrity issues")


if __name__ == '__main__':
    main()
