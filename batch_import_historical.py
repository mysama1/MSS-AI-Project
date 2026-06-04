#!/usr/bin/env python3
"""
批量导入所有历史JSONL到IMA知识库
使用cos-upload.cjs进行COS上传
"""

import json
import os
import subprocess
import urllib.request
from datetime import datetime

API_BASE = "https://ima.qq.com/openapi/wiki/v1"
CLIENT_ID = "6165e4d1fbbc58d18eb76b820f4bba97"
API_KEY = "eZ2Yu6VwX2N8RKLsdt/SfWm7EpbH04BhiJN4jtxc4aUHIL4J47sUJ9pz3Z1F3fIIHYml93JTTg=="
KB_ID = "p4nhLQRiY7NGW54ovyd45QPn-FYlcPPk3Xta0Oxh-Pc="
SKILL_DIR = r"C:\Program Files\QClaw\resources\openclaw\config\skills\ima\knowledge-base"

def api_call(path, body):
    data = json.dumps(body, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        f"{API_BASE}/{path}",
        data=data,
        headers={
            "ima-openapi-clientid": CLIENT_ID,
            "ima-openapi-apikey": API_KEY,
            "Content-Type": "application/json"
        },
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {"code": -1, "msg": str(e)}

def load_all_entries():
    """加载所有历史JSONL条目"""
    kb_dir = r"C:\MSS-AI-Project\knowledge_base"
    entries = []
    files = [f for f in os.listdir(kb_dir) if f.endswith('.jsonl') and not f.startswith('ima_')]

    print(f"📂 发现 {len(files)} 个历史文件")

    for fname in sorted(files):
        filepath = os.path.join(kb_dir, fname)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                file_count = 0
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            entry['_source'] = fname
                            entries.append(entry)
                            file_count += 1
                        except json.JSONDecodeError:
                            pass
                print(f"  ✅ {fname}: {file_count} 条")
        except Exception as e:
            print(f"  ❌ {fname}: {e}")

    return entries

def convert_to_markdown(entry):
    """转换为Markdown"""
    lines = []
    title = entry.get('title', 'Untitled')
    lines.append(f"# {title}")
    lines.append("")

    meta = []
    if 'id' in entry:
        meta.append(f"**ID**: {entry['id']}")
    if 'layer' in entry:
        meta.append(f"**层级**: {entry['layer']}")
    if 'category' in entry:
        meta.append(f"**分类**: {entry['category']}")
    if meta:
        lines.append(" | ".join(meta))
        lines.append("")

    if 'tags' in entry and entry['tags']:
        lines.append(f"**标签**: {', '.join(entry['tags'])}")
        lines.append("")

    lines.append("---")
    lines.append("")

    content = entry.get('content', entry.get('text', ''))
    lines.append(content)
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*来源文件: {entry.get('_source', 'unknown')}*")
    lines.append(f"*导入时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

    return '\n'.join(lines)

def upload_cos(file_path, cred):
    """使用cos-upload.cjs上传"""
    script = os.path.join(SKILL_DIR, "scripts", "cos-upload.cjs")
    cmd = [
        "node", script,
        "--file", file_path,
        "--secret-id", cred.get("secret_id", ""),
        "--secret-key", cred.get("secret_key", ""),
        "--token", cred.get("token", ""),
        "--bucket", cred.get("bucket_name", ""),
        "--region", cred.get("region", ""),
        "--cos-key", cred.get("cos_key", ""),
        "--content-type", "text/markdown",
        "--start-time", str(cred.get("start_time", "")),
        "--expired-time", str(cred.get("expired_time", ""))
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0
    except Exception as e:
        print(f"    COS upload error: {e}")
        return False

def import_single_entry(entry, temp_dir):
    """导入单条记录"""
    entry_id = entry.get('id', entry.get('title', 'unknown'))
    safe_id = entry_id.replace('/', '_').replace('\\', '_').replace(':', '_')[:50]

    # 生成markdown
    md = convert_to_markdown(entry)
    temp_file = os.path.join(temp_dir, f"{safe_id}.md")

    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(md)

    file_size = os.path.getsize(temp_file)
    file_name = f"{safe_id}.md"

    # 创建媒体
    result = api_call("create_media", {
        "file_name": file_name,
        "file_size": file_size,
        "content_type": "text/markdown",
        "knowledge_base_id": KB_ID,
        "file_ext": "md"
    })

    if result.get("code") != 0:
        return False, f"create_media: {result.get('msg')}"

    data = result.get("data", {})
    media_id = data.get("media_id")
    cred = data.get("cos_credential")

    if not media_id or not cred:
        return False, "missing media_id/cred"

    # 上传COS
    if not upload_cos(temp_file, cred):
        return False, "COS upload failed"

    # 添加到知识库
    result = api_call("add_knowledge", {
        "media_type": 7,
        "media_id": media_id,
        "title": file_name,
        "knowledge_base_id": KB_ID,
        "file_info": {
            "cos_key": cred.get("cos_key"),
            "file_size": file_size,
            "file_name": file_name
        }
    })

    if result.get("code") == 0:
        return True, "success"
    else:
        return False, f"add_knowledge: {result.get('msg')}"

def main():
    print("=" * 60)
    print("IMA知识库历史内容批量迁移")
    print("=" * 60)
    print()

    # 加载条目
    entries = load_all_entries()
    print(f"\n📊 总计: {len(entries)} 条记录待导入")
    print()

    # 创建临时目录
    temp_dir = r"C:\MSS-AI-Project\temp_ima_batch"
    os.makedirs(temp_dir, exist_ok=True)

    # 导入
    success = 0
    fail = 0

    for i, entry in enumerate(entries, 1):
        entry_id = entry.get('id', entry.get('title', 'unknown'))
        print(f"[{i}/{len(entries)}] {entry_id}", end=" ", flush=True)

        ok, msg = import_single_entry(entry, temp_dir)
        if ok:
            print("✅")
            success += 1
        else:
            print(f"❌ {msg}")
            fail += 1

        # 清理临时文件
        for f in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, f))

    # 清理目录
    os.rmdir(temp_dir)

    print()
    print("=" * 60)
    print(f"完成: {success} 成功, {fail} 失败")
    print("=" * 60)

if __name__ == "__main__":
    main()
