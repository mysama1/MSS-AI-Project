#!/usr/bin/env python3
"""
MSS Android 物理投影验证器
核心: 5条铁律 + 3层缓存清理 + 多锚点验证
100% 复用 Python/PowerShell 的三层归因 + 伪沙盒同源理论
"""
import subprocess, sys, os, json, re
from pathlib import Path
from datetime import datetime

# ── ADB 基础操作 ──

def adb(cmd: str, timeout=15) -> tuple:
    """执行 adb 命令, 返回 (stdout, stderr, returncode)"""
    try:
        r = subprocess.run(f'adb {cmd}', shell=True, capture_output=True,
                         text=True, timeout=timeout, encoding='utf-8', errors='replace')
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except Exception as e:
        return '', str(e), -1

def adb_ok() -> bool:
    out, _, _ = adb('devices')
    return 'device' in out

# ── 3层缓存清理 (铁律1) ──

THREE_LAYER_CACHE = {
    'layer1_app': lambda pkg: f'shell pm clear {pkg}',
    'layer2_uninstall': lambda pkg: f'uninstall {pkg}',
    'layer3_external': lambda pkg: f'shell rm -rf /sdcard/Android/data/{pkg}',
}

def clean_three_layers(package: str) -> dict:
    """执行三层缓存清理, 返回每一步结果"""
    results = {}
    for layer, cmd_fn in THREE_LAYER_CACHE.items():
        out, err, rc = adb(cmd_fn(package))
        results[layer] = {'ok': rc == 0, 'output': out, 'error': err}
    return results

# ── 物理投影验证 (铁律2) ──

def verify_resource(package: str, resource_path: str) -> dict:
    """验证设备上资源文件的物理存在性 + inode"""
    full_path = f'/data/data/{package}/files/{resource_path}'
    out, err, rc = adb(f'shell stat {full_path}')
    
    result = {
        'path': full_path,
        'exists': rc == 0,
        'file_id': None,
        'size': None,
        'error': err if not rc == 0 else None,
    }
    
    if rc == 0:
        m_size = re.search(r'Size:\s+(\d+)', out)
        m_inode = re.search(r'Inode:\s+(\d+)', out)
        if m_size:
            result['size'] = int(m_size.group(1))
        if m_inode:
            result['file_id'] = m_inode.group(1)
    
    return result

# ── APK 资源比对 (多锚点) ──

def list_apk_resources(apk_path: str) -> dict:
    """列出 APK 中的资源文件及大小"""
    out, err, rc = subprocess.run(
        f'aapt list -v "{apk_path}"', shell=True,
        capture_output=True, text=True, timeout=15,
        encoding='utf-8', errors='replace'
    ).stdout.strip(), '', 0 if subprocess.run(
        f'aapt list -v "{apk_path}"', shell=True,
        capture_output=True, text=True, timeout=15,
        encoding='utf-8', errors='replace'
    ).returncode == 0 else 1
    
    if rc != 0:
        return {'error': f'aapt not found. Install: Android SDK Build-Tools'}
    
    resources = {}
    for line in out.split('\n'):
        if 'resource' in line or '.png' in line or '.jpg' in line:
            m = re.search(r"resource\s+'?([^']+)'?\s+\((\d+)\s+bytes\)", line)
            if m:
                resources[m.group(1)] = int(m.group(2))
    
    return {'apk_path': apk_path, 'resources': resources, 'count': len(resources)}

# ── 矛盾信号检测 ──

CONTRADICTION_SIGNALS = {
    'local_ok_remote_fail': '模拟器正常，真机崩溃',
    'code_changed_stale': '改了代码运行还是旧版',
    'reinstall_no_effect': '卸载重装后问题依旧',
    'partial_device': '部分设备正常，部分异常',
    'ci_ok_run_fail': '构建成功，运行失败',
}

def check_signals(signals: list) -> tuple:
    """矛盾信号计数, ≥2 触发诊断流水线"""
    matched = [s for s in signals if s in CONTRADICTION_SIGNALS]
    trigger = len(matched) >= 2
    return trigger, matched

# ── 一键诊断 ──

class AndroidDiagnostic:
    def __init__(self, package: str, apk_path: str = None):
        self.package = package
        self.apk_path = apk_path
    
    def run(self) -> dict:
        if not adb_ok():
            return {'error': 'No ADB device connected. 请: adb devices'}
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'package': self.package,
            'device': adb('shell getprop ro.product.model')[0] or 'unknown',
            
            # 1. 三层缓存状态
            'cache_layers': {
                'app_data': bool(adb(f'shell ls /data/data/{self.package}')[0]),
                'external': bool(adb(f'shell ls /sdcard/Android/data/{self.package}')[0]),
                'installed': bool(adb(f'shell pm list packages {self.package}')[0]),
            },
            
            # 2. 资源投影验证
            'resources': self._verify_resource_dir(),
            
            # 3. 执行建议
            'fix_commands': {
                'full_clean': f'adb uninstall {self.package} && adb shell rm -rf /sdcard/Android/data/{self.package}',
                'reinstall': f'adb install -r "{self.apk_path}"' if self.apk_path else None,
                'fresh_install': f'adb install "{self.apk_path}"' if self.apk_path else None,
            }
        }
        
        return report
    
    def _verify_resource_dir(self):
        out, _, _ = adb(f'shell ls -la /data/data/{self.package}/files/')
        if not out:
            return {'status': 'empty_or_no_access', 'files': []}
        
        files = []
        for line in out.split('\n'):
            parts = line.split()
            if len(parts) >= 5:
                files.append({
                    'name': parts[-1],
                    'size': parts[3],
                })
        return {'status': 'ok', 'count': len(files), 'files': files[:20]}


# ── 5条铁律 (AI 提示词) ──

ANDROID_5_RULES_A7 = """
【MSS Android 开发强制规则 — 5条铁律】
与 Python/PowerShell 铁律完全同源，适用于所有 Android AI 工作流：

铁律1：任何运行前强制三层缓存清理
  每次生成代码修改后，AI 必须建议：
    adb shell pm clear com.your.package    # 应用数据缓存
    adb uninstall com.your.package         # 完全卸载
    adb shell rm -rf /sdcard/Android/data/com.your.package  # 外部存储

铁律2：路径操作前强制物理投影验证
  任何资源文件的读写/替换，AI 必须插入：
    adb shell stat /data/data/pkg/files/resource.png
  验证 Size/Inode → 确保物理投影正确，不依赖文件名的"存在感"

铁律3：禁止依赖临时状态，全量自包含
  ❌ 禁止: 依赖上一次构建的中间产物（Gradle cache, build/目录残留）
  ✅ 必须: 每次修改后 ./gradlew clean build 全新构建
  ❌ 禁止: 依赖模拟器的热更新缓存
  ✅ 必须: 每次运行前完全卸载+重装

铁律4：多设备锚点验证
  任何功能至少在 2 个不同锚点上验证：
    锚点1: 本地模拟器（emulator-5554）
    锚点2: 真机或不同版本模拟器
  判定标准: 2个锚点的资源 inode + 行为完全一致，否则返回铁律1

铁律5：结构化日志，禁止 print("成功")
  ❌ 禁止: Log.d("TAG", "loaded")
  ✅ 必须: Log.d("MSS", "resource: path=$path size=$size inode=$inode from=${source}")
  任何时候crash必有 MSS 标签的物理上下文

【⚠️ A7 诚实边界 — 移动平台原生硬伤】
以下问题无法通过代码/工具解决，必须提前告知用户：
1. iOS沙盒绝对隔离 — 应用无法访问其他应用数据或系统文件
2. Android厂商定制ROM差异 — 不同厂商缓存机制不可预测
3. 热更新审计限制 — iOS禁止JIT热更新
4. APK签名验证 — 修改后必须重新签名才能安装
5. 系统级缓存 — 某些系统缓存需要重启设备才能完全清除

唯一可靠的终极方案：完全卸载 → 清理所有缓存目录 → 全新安装
"""


# ── CLI ──
def main():
    import argparse
    ap = argparse.ArgumentParser(description='MSS Android 物理投影验证器')
    sub = ap.add_subparsers(dest='cmd')
    
    p_diag = sub.add_parser('diagnose', help='一键诊断Android设备')
    p_diag.add_argument('package', help='应用包名 (如 com.example.app)')
    p_diag.add_argument('--apk', help='APK路径 (用于资源比对)')
    p_diag.add_argument('--json', action='store_true')
    
    p_clean = sub.add_parser('clean', help='三层缓存清理')
    p_clean.add_argument('package', help='应用包名')
    
    p_verify = sub.add_parser('verify', help='验证资源文件的物理投影')
    p_verify.add_argument('package', help='应用包名')
    p_verify.add_argument('resource', help='资源路径 (如 images/logo.png)')
    
    p_rules = sub.add_parser('rules', help='输出Android 5条铁律 + A7边界')
    
    args = ap.parse_args()
    
    if args.cmd == 'diagnose':
        d = AndroidDiagnostic(args.package, args.apk)
        r = d.run()
        if args.json:
            print(json.dumps(r, indent=2, ensure_ascii=False))
        else:
            if 'error' in r:
                print(f"❌ {r['error']}")
                return
            print(f"设备: {r['device']}")
            print(f"应用: {r['package']}")
            print(f"\n缓存状态:")
            for layer, status in r['cache_layers'].items():
                print(f"  {'✅' if status else '❌'} {layer}: {status}")
            print(f"\n资源文件: {r['resources']['count']} 个")
            for f in r['resources'].get('files', [])[:10]:
                print(f"    {f['name']:30s} {f['size']} bytes")
            
            print(f"\n修复命令:")
            for name, cmd in r['fix_commands'].items():
                if cmd:
                    print(f"  {name}: {cmd}")
    
    elif args.cmd == 'clean':
        results = clean_three_layers(args.package)
        for layer, r in results.items():
            icon = '✅' if r['ok'] else '❌'
            print(f"{icon} {layer}: {r.get('error', r.get('output', '?')[:80])}")
    
    elif args.cmd == 'verify':
        r = verify_resource(args.package, args.resource)
        print(json.dumps(r, indent=2, ensure_ascii=False))
    
    elif args.cmd == 'rules':
        print(ANDROID_5_RULES_A7)
    
    else:
        ap.print_help()


if __name__ == '__main__':
    main()
