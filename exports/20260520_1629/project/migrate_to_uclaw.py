"""
MSS-AI 项目迁移脚本
从 QClaw → u-claw 完整备份

功能：
1. 打包所有项目代码
2. 导出记忆/任务/配置
3. 生成迁移清单
4. 创建 u-claw 导入包

作者：QClaw
日期：2026-05-20
"""

import os
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

class MSSMigrator:
    """MSS项目迁移器"""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        self.export_dir = f"C:\\MSS-AI-Export_{self.timestamp}"
        self.export_file = f"C:\\MSS-AI-Export_{self.timestamp}.zip"
        
        # 源路径
        self.project_dir = "C:\\MSS-AI-Project"
        self.workspace_dir = "C:\\Users\\Administrator\\.qclaw\\workspace"
        self.memory_dir = os.path.join(self.workspace_dir, "memory")
        self.config_dir = "C:\\Users\\Administrator\\.qclaw"
        
        # 导出清单
        self.manifest = {
            "export_time": datetime.now().isoformat(),
            "version": "1.0",
            "source": "QClaw",
            "target": "u-claw",
            "files": [],
            "warnings": []
        }
    
    def run(self):
        """执行完整迁移"""
        print("=" * 60)
        print("MSS-AI 项目迁移工具")
        print(f"时间：{self.timestamp}")
        print("=" * 60)
        
        # 创建导出目录
        os.makedirs(self.export_dir, exist_ok=True)
        
        # 1. 导出项目代码
        self._export_project_code()
        
        # 2. 导出记忆文件
        self._export_memory()
        
        # 3. 导出任务系统
        self._export_tasks()
        
        # 4. 导出配置文件
        self._export_config()
        
        # 5. 生成清单
        self._generate_manifest()
        
        # 6. 打包
        self._create_zip()
        
        # 7. 生成迁移指南
        self._generate_guide()
        
        print("\n" + "=" * 60)
        print("迁移完成！")
        print(f"导出文件：{self.export_file}")
        print(f"文件大小：{self._get_file_size(self.export_file)}")
        print("=" * 60)
    
    def _export_project_code(self):
        """导出项目代码"""
        print("\n[1/6] 导出项目代码...")
        
        target = os.path.join(self.export_dir, "project")
        os.makedirs(target, exist_ok=True)
        
        # 复制项目文件（排除__pycache__和.pyc）
        for root, dirs, files in os.walk(self.project_dir):
            # 排除目录
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
        
        print(f"  ✅ 已导出项目代码")
    
    def _export_memory(self):
        """导出记忆文件"""
        print("\n[2/6] 导出记忆文件...")
        
        target = os.path.join(self.export_dir, "memory")
        os.makedirs(target, exist_ok=True)
        
        # 核心记忆文件
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
        
        # 每日记忆
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
        
        print(f"  ✅ 已导出记忆文件")
    
    def _export_tasks(self):
        """导出任务系统"""
        print("\n[3/6] 导出任务系统...")
        
        target = os.path.join(self.export_dir, "tasks")
        os.makedirs(target, exist_ok=True)
        
        # 任务数据
        task_file = os.path.join(self.project_dir, "task_system_data.json")
        if os.path.exists(task_file):
            shutil.copy2(task_file, target)
            self.manifest["files"].append({
                "type": "tasks",
                "path": "task_system_data.json",
                "size": os.path.getsize(task_file)
            })
        
        # 旧版任务栏
        legacy_file = os.path.join(self.project_dir, "task_bar_current.json")
        if os.path.exists(legacy_file):
            shutil.copy2(legacy_file, target)
        
        # 路线图
        roadmap_files = [f for f in os.listdir(self.project_dir) if 'ROADMAP' in f]
        for fname in roadmap_files:
            src = os.path.join(self.project_dir, fname)
            shutil.copy2(src, target)
        
        print(f"  ✅ 已导出任务系统")
    
    def _export_config(self):
        """导出配置"""
        print("\n[4/6] 导出配置文件...")
        
        target = os.path.join(self.export_dir, "config")
        os.makedirs(target, exist_ok=True)
        
        # OpenClaw配置（脱敏）
        config_files = [
            "openclaw.json",
        ]
        
        for fname in config_files:
            src = os.path.join(self.config_dir, fname)
            if os.path.exists(src):
                # 读取并脱敏
                with open(src, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 移除敏感信息
                self._sanitize_config(config)
                
                # 保存脱敏版本
                dst = os.path.join(target, fname)
                with open(dst, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                
                self.manifest["files"].append({
                    "type": "config",
                    "path": fname,
                    "size": os.path.getsize(dst)
                })
        
        print(f"  ✅ 已导出配置文件（已脱敏）")
    
    def _sanitize_config(self, config: dict):
        """配置脱敏"""
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
        """生成清单文件"""
        print("\n[5/6] 生成迁移清单...")
        
        # 统计
        total_size = sum(f["size"] for f in self.manifest["files"])
        self.manifest["total_files"] = len(self.manifest["files"])
        self.manifest["total_size"] = total_size
        
        # 按类型统计
        type_counts = {}
        for f in self.manifest["files"]:
            t = f["type"]
            type_counts[t] = type_counts.get(t, 0) + 1
        self.manifest["type_counts"] = type_counts
        
        # 保存清单
        manifest_path = os.path.join(self.export_dir, "manifest.json")
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(self.manifest, f, ensure_ascii=False, indent=2)
        
        print(f"  ✅ 清单已生成")
        print(f"  📊 总计：{len(self.manifest['files'])} 个文件")
        print(f"  📦 大小：{total_size / 1024 / 1024:.2f} MB")
    
    def _create_zip(self):
        """创建ZIP包"""
        print("\n[6/6] 打包...")
        
        with zipfile.ZipFile(self.export_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(self.export_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.dirname(self.export_dir))
                    zf.write(file_path, arcname)
        
        print(f"  ✅ ZIP包已创建")
    
    def _generate_guide(self):
        """生成迁移指南"""
        guide = f"""# MSS-AI 迁移指南

## 导出信息

- **导出时间**：{datetime.now().isoformat()}
- **源平台**：QClaw
- **目标平台**：u-claw
- **文件总数**：{self.manifest['total_files']}
- **总大小**：{self.manifest['total_size'] / 1024 / 1024:.2f} MB

## 目录结构

```
MSS-AI-Export_{self.timestamp}/
├── project/          # 项目代码（C:\MSS-AI-Project）
│   ├── symbolic_engine_v4/
│   ├── knowledge_base/
│   └── ...
├── memory/           # 记忆文件
│   ├── MEMORY.md     # 长期记忆
│   ├── AGENTS.md     # Agent配置
│   ├── USER.md       # 用户画像
│   └── daily/        # 每日记忆
├── tasks/            # 任务系统
│   ├── task_system_data.json
│   └── ROADMAP*.md
└── config/           # 配置文件（脱敏）
    └── openclaw.json
```

## u-claw 导入步骤

### 1. 解压
```bash
unzip MSS-AI-Export_{self.timestamp}.zip
cd MSS-AI-Export_{self.timestamp}
```

### 2. 部署项目代码
```bash
# 复制到u-claw工作区
cp -r project/* /path/to/uclaw/workspace/
```

### 3. 恢复记忆
```bash
# 复制记忆文件
cp memory/MEMORY.md /path/to/uclaw/workspace/
cp memory/AGENTS.md /path/to/uclaw/workspace/
cp memory/USER.md /path/to/uclaw/workspace/
cp memory/SOUL.md /path/to/uclaw/workspace/

# 恢复每日记忆
cp memory/daily/* /path/to/uclaw/workspace/memory/
```

### 4. 恢复任务系统
```bash
# 复制任务数据
cp tasks/task_system_data.json /path/to/uclaw/workspace/
```

### 5. 安装依赖
```bash
cd /path/to/uclaw/workspace
pip install -r requirements.txt
```

### 6. 验证
```bash
python task_system.py
python test_core.py
```

## 注意事项

1. **API密钥**：config目录中的密钥已脱敏，需重新配置
2. **路径差异**：Windows路径（C:\）需改为Linux路径（/home/）
3. **u-claw兼容性**：部分QClaw特有功能可能需要适配
4. **IMA知识库**：需手动重新上传至u-claw的知识库系统

## 联系

如有问题，请联系项目管理员。
"""
        
        guide_path = os.path.join(self.export_dir, "MIGRATION_GUIDE.md")
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write(guide)
        
        print(f"  ✅ 迁移指南已生成")
    
    def _get_file_size(self, path: str) -> str:
        """获取文件大小"""
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
