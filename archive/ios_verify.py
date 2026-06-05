#!/usr/bin/env python3
"""
MSS iOS 诊断工具
命令由 xcrun/simctl 组成，可在 Windows 上生成供 Mac 执行。
"""
import sys, os, json, datetime

IOS_5_RULES = """
【MSS iOS 开发强制规则 — 5条铁律】
与 Android/Python/PowerShell 铁律完全同源。

铁律1：每次构建前强制清理 DerivedData
  rm -rf ~/Library/Developer/Xcode/DerivedData
  → 解决 65% 的 "改了代码运行还是旧版" 问题

铁律2：资源路径物理投影验证
  xcrun simctl spawn booted stat /path/to/resource.png
  → 验证 Size + Inode，不依赖文件名的"存在感"

铁律3：禁止依赖临时状态
  ❌ 依赖 Xcode 增量编译缓存
  ✅ 每次 Product → Clean Build Folder (Cmd+Shift+K)

铁律4：多设备锚点验证
  锚点1: 本地模拟器 (iPhone 15 Pro)
  锚点2: 真机 (至少一台物理设备)
  判定: 资源 inode + 行为完全一致

铁律5：结构化日志
  os_log("MSS resource: path=%@ size=%d inode=%lld", path, size, inode)

⚠️ A7 边界:
1. iOS 沙盒绝对隔离 — 应用完全无法访问其他应用或系统文件
2. JIT 热更新被禁止 — iOS 不允许动态代码生成
3. 签名校验 — 修改后必须重新签名
4. 唯一可靠方案: 完全卸载 → Clean Build Folder → 全新安装
"""

IOS_COMMANDS = {
    'clean_derivedata': 'rm -rf ~/Library/Developer/Xcode/DerivedData',
    'clean_build': 'xcodebuild clean -workspace App.xcworkspace -scheme App',
    'uninstall_sim': 'xcrun simctl uninstall booted com.your.bundle',
    'install_sim': 'xcrun simctl install booted build/App.app',
    'reset_sim': 'xcrun simctl erase booted',
    'list_sims': 'xcrun simctl list devices | grep Booted',
    'verify_resource': 'xcrun simctl spawn booted stat /path/to/resource',
    'check_bundle': 'xcrun simctl get_app_container booted com.your.bundle',
}

def main():
    import argparse
    ap = argparse.ArgumentParser(description='MSS iOS 诊断工具 (命令生成器)')
    sub = ap.add_subparsers(dest='cmd')
    sub.add_parser('rules', help='iOS 5条铁律 + A7边界')
    sub.add_parser('clean', help='输出三层清理命令')
    sub.add_parser('verify', help='输出物理投影验证命令')
    sub.add_parser('diagnose', help='输出完整诊断流水线')
    args = ap.parse_args()
    
    if args.cmd == 'rules':
        print(IOS_5_RULES)
    
    elif args.cmd == 'clean':
        print("# === MSS iOS 三层缓存清理 ===\n")
        for name, cmd in [
            ('Layer 1: 清 DerivedData', IOS_COMMANDS['clean_derivedata']),
            ('Layer 2: 卸载应用', IOS_COMMANDS['uninstall_sim']),
            ('Layer 3: 重置模拟器 (谨慎!)', IOS_COMMANDS['reset_sim']),
        ]:
            print(f"# {name}")
            print(f"{cmd}\n")
    
    elif args.cmd == 'verify':
        print("# === MSS iOS 物理投影验证 ===\n")
        print("# 1. 查看模拟器状态")
        print(IOS_COMMANDS['list_sims'])
        print("\n# 2. 验证资源文件物理投影")
        print(IOS_COMMANDS['verify_resource'].replace('/path/to/resource', 'Documents/config.json'))
        print("\n# 3. 验证 Bundle 容器")
        print(IOS_COMMANDS['check_bundle'])
    
    elif args.cmd == 'diagnose':
        print("# === MSS iOS 5步诊断流水线 ===\n")
        steps = [
            ("Step 1: 矛盾信号计数", "检查 ≥2 个信号:\n  - 本地模拟器正常，真机崩溃\n  - 改了代码运行旧版\n  - 卸载重装问题依旧\n  - 部分设备异常"),
            ("Step 2: 物理投影验证", IOS_COMMANDS['verify_resource']),
            ("Step 3: 三层缓存清理", f"{IOS_COMMANDS['clean_derivedata']}\n{IOS_COMMANDS['reset_sim']}"),
            ("Step 4: 全量重建", IOS_COMMANDS['clean_build']),
            ("Step 5: 多锚点验证", "在模拟器 + 真机上分别执行，比对行为一致性"),
        ]
        for title, cmd in steps:
            print(f"# {title}")
            print(f"{cmd}\n")
    else:
        ap.print_help()

if __name__ == '__main__':
    main()
