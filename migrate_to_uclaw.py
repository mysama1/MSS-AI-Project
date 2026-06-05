"""
MSS-AI 椤圭洰杩佺Щ鑴氭湰
浠?QClaw 鈫?u-claw 瀹屾暣澶囦唤

鍔熻兘锛?
1. 鎵撳寘鎵€鏈夐」鐩唬鐮?
2. 瀵煎嚭璁板繂/浠诲姟/閰嶇疆
3. 鐢熸垚杩佺Щ娓呭崟
4. 鍒涘缓 u-claw 瀵煎叆鍖?

浣滆€咃細QClaw
鏃ユ湡锛?026-05-20
"""

import os
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

class MSSMigrator:
    """MSS椤圭洰杩佺Щ鍣?""

    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        self.export_dir = f"C:\\MSS-AI-Export_{self.timestamp}"
        self.export_file = f"C:\\MSS-AI-Export_{self.timestamp}.zip"

        # 婧愯矾寰?
        self.project_dir = "E:\\AI_Workspace\\MSS-AI\\project"
        self.workspace_dir = "C:\\Users\\Administrator\\.qclaw\\workspace"
        self.memory_dir = os.path.join(self.workspace_dir, "memory")
        self.config_dir = "C:\\Users\\Administrator\\.qclaw"

        # 瀵煎嚭娓呭崟
        self.manifest = {
            "export_time": datetime.now().isoformat(),
            "version": "1.0",
            "source": "QClaw",
            "target": "u-claw",
            "files": [],
            "warnings": []
        }

    def run(self):
        """鎵ц瀹屾暣杩佺Щ"""
        print("=" * 60)
        print("MSS-AI 椤圭洰杩佺Щ宸ュ叿")
        print(f"鏃堕棿锛歿self.timestamp}")
        print("=" * 60)

        # 鍒涘缓瀵煎嚭鐩綍
        os.makedirs(self.export_dir, exist_ok=True)

        # 1. 瀵煎嚭椤圭洰浠ｇ爜
        self._export_project_code()

        # 2. 瀵煎嚭璁板繂鏂囦欢
        self._export_memory()

        # 3. 瀵煎嚭浠诲姟绯荤粺
        self._export_tasks()

        # 4. 瀵煎嚭閰嶇疆鏂囦欢
        self._export_config()

        # 5. 鐢熸垚娓呭崟
        self._generate_manifest()

        # 6. 鎵撳寘
        self._create_zip()

        # 7. 鐢熸垚杩佺Щ鎸囧崡
        self._generate_guide()

        print("\n" + "=" * 60)
        print("杩佺Щ瀹屾垚锛?)
        print(f"瀵煎嚭鏂囦欢锛歿self.export_file}")
        print(f"鏂囦欢澶у皬锛歿self._get_file_size(self.export_file)}")
        print("=" * 60)

    def _export_project_code(self):
        """瀵煎嚭椤圭洰浠ｇ爜"""
        print("\n[1/6] 瀵煎嚭椤圭洰浠ｇ爜...")

        target = os.path.join(self.export_dir, "project")
        os.makedirs(target, exist_ok=True)

        # 澶嶅埗椤圭洰鏂囦欢锛堟帓闄_pycache__鍜?pyc锛?
        for root, dirs, files in os.walk(self.project_dir):
            # 鎺掗櫎鐩綍
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'node_modules']]

            for file in files:
                if file.endswith('.pyc'):
                    continue

                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, self.project_dir)
                dst_path = os.path.join(target, rel_path)

                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)

                self.manifest["files"].append({
                    "type": "project",
                    "path": rel_path,
                    "size": os.path.getsize(src_path)
                })

        print(f"  鉁?宸插鍑洪」鐩唬鐮?)

    def _export_memory(self):
        """瀵煎嚭璁板繂鏂囦欢"""
        print("\n[2/6] 瀵煎嚭璁板繂鏂囦欢...")

        target = os.path.join(self.export_dir, "memory")
        os.makedirs(target, exist_ok=True)

        # 鏍稿績璁板繂鏂囦欢
        memory_files = [
            "MEMORY.md",
            "AGENTS.md",
            "USER.md",
            "SOUL.md",
            "IDENTITY.md",
            "TOOLS.md",
            "HEARTBEAT.md"
        ]

        for fname in memory_files:
            src = os.path.join(self.workspace_dir, fname)
            if os.path.exists(src):
                shutil.copy2(src, target)
                self.manifest["files"].append({
                    "type": "memory",
                    "path": fname,
                    "size": os.path.getsize(src)
                })

        # 姣忔棩璁板繂
        if os.path.exists(self.memory_dir):
            mem_target = os.path.join(target, "daily")
            os.makedirs(mem_target, exist_ok=True)

            for fname in os.listdir(self.memory_dir):
                if fname.endswith('.md'):
                    src = os.path.join(self.memory_dir, fname)
                    shutil.copy2(src, mem_target)
                    self.manifest["files"].append({
                        "type": "daily_memory",
                        "path": f"memory/daily/{fname}",
                        "size": os.path.getsize(src)
                    })

        print(f"  鉁?宸插鍑鸿蹇嗘枃浠?)

    def _export_tasks(self):
        """瀵煎嚭浠诲姟绯荤粺"""
        print("\n[3/6] 瀵煎嚭浠诲姟绯荤粺...")

        target = os.path.join(self.export_dir, "tasks")
        os.makedirs(target, exist_ok=True)

        # 浠诲姟鏁版嵁
        task_file = os.path.join(self.project_dir, "task_system_data.json")
        if os.path.exists(task_file):
            shutil.copy2(task_file, target)
            self.manifest["files"].append({
                "type": "tasks",
                "path": "task_system_data.json",
                "size": os.path.getsize(task_file)
            })

        # 鏃х増浠诲姟鏍?
        legacy_file = os.path.join(self.project_dir, "task_bar_current.json")
        if os.path.exists(legacy_file):
            shutil.copy2(legacy_file, target)

        # 璺嚎鍥?
        roadmap_files = [f for f in os.listdir(self.project_dir) if 'ROADMAP' in f]
        for fname in roadmap_files:
            src = os.path.join(self.project_dir, fname)
            shutil.copy2(src, target)

        print(f"  鉁?宸插鍑轰换鍔＄郴缁?)

    def _export_config(self):
        """瀵煎嚭閰嶇疆"""
        print("\n[4/6] 瀵煎嚭閰嶇疆鏂囦欢...")

        target = os.path.join(self.export_dir, "config")
        os.makedirs(target, exist_ok=True)

        # OpenClaw閰嶇疆锛堣劚鏁忥級
        config_files = [
            "openclaw.json",
        ]

        for fname in config_files:
            src = os.path.join(self.config_dir, fname)
            if os.path.exists(src):
                # 璇诲彇骞惰劚鏁?
                with open(src, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # 绉婚櫎鏁忔劅淇℃伅
                self._sanitize_config(config)

                # 淇濆瓨鑴辨晱鐗堟湰
                dst = os.path.join(target, fname)
                with open(dst, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)

                self.manifest["files"].append({
                    "type": "config",
                    "path": fname,
                    "size": os.path.getsize(dst)
                })

        print(f"  鉁?宸插鍑洪厤缃枃浠讹紙宸茶劚鏁忥級")

    def _sanitize_config(self, config: dict):
        """閰嶇疆鑴辨晱"""
        sensitive_keys = ['token', 'api_key', 'secret', 'password', 'credential']

        def remove_sensitive(obj):
            if isinstance(obj, dict):
                for key in list(obj.keys()):
                    if any(sk in key.lower() for sk in sensitive_keys):
                        obj[key] = "***REDACTED***"
                    else:
                        remove_sensitive(obj[key])
            elif isinstance(obj, list):
                for item in obj:
                    remove_sensitive(item)

        remove_sensitive(config)

    def _generate_manifest(self):
        """鐢熸垚娓呭崟鏂囦欢"""
        print("\n[5/6] 鐢熸垚杩佺Щ娓呭崟...")

        # 缁熻
        total_size = sum(f["size"] for f in self.manifest["files"])
        self.manifest["total_files"] = len(self.manifest["files"])
        self.manifest["total_size"] = total_size

        # 鎸夌被鍨嬬粺璁?
        type_counts = {}
        for f in self.manifest["files"]:
            t = f["type"]
            type_counts[t] = type_counts.get(t, 0) + 1
        self.manifest["type_counts"] = type_counts

        # 淇濆瓨娓呭崟
        manifest_path = os.path.join(self.export_dir, "manifest.json")
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(self.manifest, f, ensure_ascii=False, indent=2)

        print(f"  鉁?娓呭崟宸茬敓鎴?)
        print(f"  馃搳 鎬昏锛歿len(self.manifest['files'])} 涓枃浠?)
        print(f"  馃摝 澶у皬锛歿total_size / 1024 / 1024:.2f} MB")

    def _create_zip(self):
        """鍒涘缓ZIP鍖?""
        print("\n[6/6] 鎵撳寘...")

        with zipfile.ZipFile(self.export_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(self.export_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.dirname(self.export_dir))
                    zf.write(file_path, arcname)

        print(f"  鉁?ZIP鍖呭凡鍒涘缓")

    def _generate_guide(self):
        """鐢熸垚杩佺Щ鎸囧崡"""
        guide = f"""# MSS-AI 杩佺Щ鎸囧崡

## 瀵煎嚭淇℃伅

- **瀵煎嚭鏃堕棿**锛歿datetime.now().isoformat()}
- **婧愬钩鍙?*锛歈Claw
- **鐩爣骞冲彴**锛歶-claw
- **鏂囦欢鎬绘暟**锛歿self.manifest['total_files']}
- **鎬诲ぇ灏?*锛歿self.manifest['total_size'] / 1024 / 1024:.2f} MB

## 鐩綍缁撴瀯

```
MSS-AI-Export_{self.timestamp}/
鈹溾攢鈹€ project/          # 椤圭洰浠ｇ爜锛圕:\MSS-AI-Project锛?
鈹?  鈹溾攢鈹€ symbolic_engine_v4/
鈹?  鈹溾攢鈹€ knowledge_base/
鈹?  鈹斺攢鈹€ ...
鈹溾攢鈹€ memory/           # 璁板繂鏂囦欢
鈹?  鈹溾攢鈹€ MEMORY.md     # 闀挎湡璁板繂
鈹?  鈹溾攢鈹€ AGENTS.md     # Agent閰嶇疆
鈹?  鈹溾攢鈹€ USER.md       # 鐢ㄦ埛鐢诲儚
鈹?  鈹斺攢鈹€ daily/        # 姣忔棩璁板繂
鈹溾攢鈹€ tasks/            # 浠诲姟绯荤粺
鈹?  鈹溾攢鈹€ task_system_data.json
鈹?  鈹斺攢鈹€ ROADMAP*.md
鈹斺攢鈹€ config/           # 閰嶇疆鏂囦欢锛堣劚鏁忥級
    鈹斺攢鈹€ openclaw.json
```

## u-claw 瀵煎叆姝ラ

### 1. 瑙ｅ帇
```bash
unzip MSS-AI-Export_{self.timestamp}.zip
cd MSS-AI-Export_{self.timestamp}
```

### 2. 閮ㄧ讲椤圭洰浠ｇ爜
```bash
# 澶嶅埗鍒皍-claw宸ヤ綔鍖?
cp -r project/* /path/to/uclaw/workspace/
```

### 3. 鎭㈠璁板繂
```bash
# 澶嶅埗璁板繂鏂囦欢
cp memory/MEMORY.md /path/to/uclaw/workspace/
cp memory/AGENTS.md /path/to/uclaw/workspace/
cp memory/USER.md /path/to/uclaw/workspace/
cp memory/SOUL.md /path/to/uclaw/workspace/

# 鎭㈠姣忔棩璁板繂
cp memory/daily/* /path/to/uclaw/workspace/memory/
```

### 4. 鎭㈠浠诲姟绯荤粺
```bash
# 澶嶅埗浠诲姟鏁版嵁
cp tasks/task_system_data.json /path/to/uclaw/workspace/
```

### 5. 瀹夎渚濊禆
```bash
cd /path/to/uclaw/workspace
pip install -r requirements.txt
```

### 6. 楠岃瘉
```bash
python task_system.py
python test_core.py
```

## 娉ㄦ剰浜嬮」

1. **API瀵嗛挜**锛歝onfig鐩綍涓殑瀵嗛挜宸茶劚鏁忥紝闇€閲嶆柊閰嶇疆
2. **璺緞宸紓**锛歐indows璺緞锛圕:\锛夐渶鏀逛负Linux璺緞锛?home/锛?
3. **u-claw鍏煎鎬?*锛氶儴鍒哘Claw鐗规湁鍔熻兘鍙兘闇€瑕侀€傞厤
4. **IMA鐭ヨ瘑搴?*锛氶渶鎵嬪姩閲嶆柊涓婁紶鑷硊-claw鐨勭煡璇嗗簱绯荤粺

## 鑱旂郴

濡傛湁闂锛岃鑱旂郴椤圭洰绠＄悊鍛樸€?
"""

        guide_path = os.path.join(self.export_dir, "MIGRATION_GUIDE.md")
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write(guide)

        print(f"  鉁?杩佺Щ鎸囧崡宸茬敓鎴?)

    def _get_file_size(self, path: str) -> str:
        """鑾峰彇鏂囦欢澶у皬"""
        size = os.path.getsize(path)
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        else:
            return f"{size / 1024 / 1024:.2f} MB"

if __name__ == "__main__":
    migrator = MSSMigrator()
    migrator.run()
