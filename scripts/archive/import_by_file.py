#!/usr/bin/env python3
"""
按文件批量导入 - 每个JSONL文件合并为一个Markdown上传
减少API调用次数
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
        print(f"    COS error: {e}")
        return False

def process_jsonl_file(filepath, fname):
    """处理单个JSONL文件，合并为一个大Markdown"""
    entries = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except:
                    pass

    if not entries:
        return None, 0

    # 生成合并的Markdown
    lines = []
    lines.append(f"# {fname.replace('.jsonl', '')}")
    lines.append(f"\n*文件包含 {len(entries)} 条记录*")
    lines.append(f"*导入时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
    lines.append("=" * 60)
    lines.append("")

    for i, entry in enumerate(entries, 1):
        lines.append(f"\n## [{i}] {entry.get('id', 'N/A')} - {entry.get('title', 'Untitled')}\n")

        meta = []
        if 'layer' in entry:
            meta.append(f"层级: {entry['layer']}")
        if 'category' in entry:
            meta.append(f"分类: {entry['category']}")
        if 'tags' in entry and entry['tags']:
            meta.append(f"标签: {', '.join(entry['tags'])}")
        if meta:
            lines.append(f"*{'; '.join(meta)}*\n")

        content = entry.get('content', entry.get('text', ''))
        lines.append(content)
        lines.append("")
        lines.append("-" * 40)
        lines.append("")

    return '\n'.join(lines), len(entries)

def import_file(fname, temp_dir):
    """导入单个文件"""
    filepath = os.path.join(r"C:\MSS-AI-Project\knowledge_base", fname)

    # 处理文件
    md_content, entry_count = process_jsonl_file(filepath, fname)
    if not md_content:
        return False, "no entries"

    # 保存临时文件
    safe_name = fname.replace('.jsonl', '.md')
    temp_file = os.path.join(temp_dir, safe_name)

    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(md_content)

    file_size = os.path.getsize(temp_file)

    # 创建媒体
    result = api_call("create_media", {
        "file_name": safe_name,
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
        return False, "missing cred"

    # 上传COS
    if not upload_cos(temp_file, cred):
        return False, "COS failed"

    # 添加到知识库
    result = api_call("add_knowledge", {
        "media_type": 7,
        "media_id": media_id,
        "title": safe_name,
        "knowledge_base_id": KB_ID,
        "file_info": {
            "cos_key": cred.get("cos_key"),
            "file_size": file_size,
            "file_name": safe_name
        }
    })

    if result.get("code") == 0:
        return True, f"{entry_count} entries"
    else:
        return False, f"add: {result.get('msg')}"

def main():
    print("=" * 60)
    print("IMA知识库批量导入 - 按文件合并")
    print("=" * 60)
    print()

    # 获取文件列表
    kb_dir = r"C:\MSS-AI-Project\knowledge_base"
    files = sorted([f for f in os.listdir(kb_dir) if f.endswith('.jsonl') and not f.startswith('ima_')])

    print(f"📂 发现 {len(files)} 个历史文件")
    print()

    # 创建临时目录
    temp_dir = r"C:\MSS-AI-Project\temp_ima_files"
    os.makedirs(temp_dir, exist_ok=True)

    # 导入
    success = 0
    fail = 0
    total_entries = 0

    for i, fname in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {fname}", end=" ", flush=True)

        ok, msg = import_file(fname, temp_dir)
        if ok:
            print(f"✅ ({msg})")
            success += 1
            total_entries += int(msg.split()[0])
        else:
            print(f"❌ {msg}")
            fail += 1

        # 清理临时文件
        for f in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, f))

    # 清理
    os.rmdir(temp_dir)

    print()
    print("=" * 60)
    print(f"完成: {success} 文件成功, {fail} 失败")
    print(f"总计导入: ~{total_entries} 条记录")
    print("=" * 60)

if __name__ == "__main__":
    main()
