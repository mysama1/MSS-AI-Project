#!/usr/bin/env python3
"""
导入整理后的分类文件到IMA知识库
"""

import os
import urllib.request
import json
import subprocess

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

def import_file(filepath):
    """导入单个文件"""
    fname = os.path.basename(filepath)
    file_size = os.path.getsize(filepath)

    print(f"📤 导入: {fname} ({file_size/1024:.1f} KB)")

    # 创建媒体
    result = api_call("create_media", {
        "file_name": fname,
        "file_size": file_size,
        "content_type": "text/markdown",
        "knowledge_base_id": KB_ID,
        "file_ext": "md"
    })

    if result.get("code") != 0:
        print(f"  ❌ create_media: {result.get('msg')}")
        return False

    data = result.get("data", {})
    media_id = data.get("media_id")
    cred = data.get("cos_credential")

    if not media_id or not cred:
        print(f"  ❌ missing cred")
        return False

    # 上传COS
    print(f"  ☁️  上传COS...")
    if not upload_cos(filepath, cred):
        print(f"  ❌ COS上传失败")
        return False

    # 添加到知识库
    print(f"  📥 添加到知识库...")
    result = api_call("add_knowledge", {
        "media_type": 7,
        "media_id": media_id,
        "title": fname,
        "knowledge_base_id": KB_ID,
        "file_info": {
            "cos_key": cred.get("cos_key"),
            "file_size": file_size,
            "file_name": fname
        }
    })

    if result.get("code") == 0:
        print(f"  ✅ 成功")
        return True
    else:
        print(f"  ❌ add_knowledge: {result.get('msg')}")
        return False

def main():
    print("=" * 60)
    print("导入整理后的分类文件到IMA")
    print("=" * 60)
    print()

    org_dir = r"C:\MSS-AI-Project\knowledge_base_organized"
    files = [
        "目录索引.md",
        "L1_硬核公理.md",
        "L2_保护带.md",
        "L3_试探法.md",
        "L4_污染池.md"
    ]

    success = 0
    fail = 0

    for fname in files:
        filepath = os.path.join(org_dir, fname)
        if os.path.exists(filepath):
            if import_file(filepath):
                success += 1
            else:
                fail += 1
        else:
            print(f"⚠️ 文件不存在: {fname}")
            fail += 1
        print()

    print("=" * 60)
    print(f"完成: {success} 成功, {fail} 失败")
    print("=" * 60)

if __name__ == "__main__":
    main()
