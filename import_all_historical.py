#!/usr/bin/env python3
"""
批量导入所有历史JSONL文件到IMA知识库
"""

import json
import os
import urllib.request
from datetime import datetime

API_BASE = "https://ima.qq.com/openapi/wiki/v1"
CLIENT_ID = "6165e4d1fbbc58d18eb76b820f4bba97"
API_KEY = "eZ2Yu6VwX2N8RKLsdt/SfWm7EpbH04BhiJN4jtxc4aUHIL4J47sUJ9pz3Z1F3fIIHYml93JTTg=="
KB_ID = "p4nhLQRiY7NGW54ovyd45QPn-FYlcPPk3Xta0Oxh-Pc="

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

def load_all_jsonl_files(directory):
    """加载目录下所有JSONL文件（排除ima_开头的）"""
    entries = []
    files = [f for f in os.listdir(directory) if f.endswith('.jsonl') and not f.startswith('ima_')]

    for fname in sorted(files):
        filepath = os.path.join(directory, fname)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            # 添加来源文件标记
                            entry['_source_file'] = fname
                            entries.append(entry)
                        except json.JSONDecodeError:
                            print(f"  ⚠️  JSON parse error in {fname}")
        except Exception as e:
            print(f"  ❌ Error reading {fname}: {e}")

    return entries

def convert_entry_to_markdown(entry):
    """将JSON条目转换为Markdown内容"""
    lines = []
    lines.append(f"# {entry.get('title', 'Untitled')}")
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

    if 'version' in entry:
        lines.append(f"**版本**: {entry['version']}")
        lines.append("")

    lines.append("---")
    lines.append("")

    content = entry.get('content', entry.get('text', ''))
    lines.append(content)
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*来源: {entry.get('_source_file', 'unknown')}*")
    lines.append(f"*归档时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

    return '\n'.join(lines)

def import_entry(entry, temp_dir):
    """导入单条记录"""
    entry_id = entry.get('id', entry.get('title', 'unknown')).replace('/', '_').replace('\\', '_')

    # 生成markdown
    md_content = convert_entry_to_markdown(entry)

    # 保存临时文件
    temp_file = os.path.join(temp_dir, f"{entry_id}.md")
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(md_content)

    file_size = os.path.getsize(temp_file)
    file_name = f"{entry_id}.md"

    # 1. 创建媒体
    create_result = api_call("create_media", {
        "file_name": file_name,
        "file_size": file_size,
        "content_type": "text/markdown",
        "knowledge_base_id": KB_ID,
        "file_ext": "md"
    })

    if create_result.get("code") != 0:
        return False, f"create_media failed: {create_result.get('msg')}"

    media_data = create_result.get("data", {})
    media_id = media_data.get("media_id")
    cos_credential = media_data.get("cos_credential")

    if not media_id or not cos_credential:
        return False, "missing media_id or cos_credential"

    # 2. 上传到COS (简化版 - 实际需要调用cos-upload.cjs)
    # 这里使用直接PUT上传
    cos_key = cos_credential.get("cos_key")
    upload_url = f"https://{cos_credential.get('bucket_name')}.cos.{cos_credential.get('region')}.myqcloud.com/{cos_key}"

    with open(temp_file, 'rb') as f:
        file_data = f.read()

    # 构建COS上传请求
    upload_req = urllib.request.Request(
        upload_url,
        data=file_data,
        headers={
            "Content-Type": "text/markdown",
            "x-cos-security-token": cos_credential.get("token", "")
        },
        method='PUT'
    )

    try:
        with urllib.request.urlopen(upload_req, timeout=120) as resp:
            if resp.status != 200:
                return False, f"COS upload failed: {resp.status}"
    except Exception as e:
        return False, f"COS upload error: {e}"

    # 3. 添加到知识库
    add_result = api_call("add_knowledge", {
        "media_type": 7,
        "media_id": media_id,
        "title": file_name,
        "knowledge_base_id": KB_ID,
        "file_info": {
            "cos_key": cos_key,
            "file_size": file_size,
            "file_name": file_name
        }
    })

    if add_result.get("code") == 0:
        return True, "success"
    else:
        return False, f"add_knowledge failed: {add_result.get('msg')}"

def main():
    print("=" * 60)
    print("IMA知识库批量导入工具 - 历史内容迁移")
    print("=" * 60)
    print()

    kb_dir = r"C:\MSS-AI-Project\knowledge_base"
    temp_dir = r"C:\MSS-AI-Project\temp_ima_all"
    os.makedirs(temp_dir, exist_ok=True)

    # 加载所有历史条目
    print("📂 加载历史JSONL文件...")
    entries = load_all_jsonl_files(kb_dir)
    print(f"✅ 加载了 {len(entries)} 条历史记录")
    print()

    # 导入
    print("📤 开始导入...")
    success = 0
    fail = 0
    failed_items = []

    for i, entry in enumerate(entries, 1):
        entry_id = entry.get('id', entry.get('title', 'unknown'))
        print(f"[{i}/{len(entries)}] {entry_id}", end=" ")

        ok, msg = import_entry(entry, temp_dir)
        if ok:
            print("✅")
            success += 1
        else:
            print(f"❌ ({msg})")
            fail += 1
            failed_items.append((entry_id, msg))

        # 每10条清理一次临时文件
        if i % 10 == 0:
            for f in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, f))

    # 最终清理
    for f in os.listdir(temp_dir):
        os.remove(os.path.join(temp_dir, f))
    os.rmdir(temp_dir)

    print()
    print("=" * 60)
    print(f"导入完成: {success} 成功, {fail} 失败")
    print("=" * 60)

    if failed_items:
        print()
        print("失败项目:")
        for item, msg in failed_items[:10]:
            print(f"  - {item}: {msg}")

if __name__ == "__main__":
    main()
