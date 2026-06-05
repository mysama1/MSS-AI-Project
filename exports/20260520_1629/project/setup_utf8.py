#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows UTF-8环境配置脚本
配置PowerShell和Python默认使用UTF-8编码
"""

import os
import sys
import subprocess
from pathlib import Path


def setup_powershell_profile():
    """配置PowerShell配置文件，添加UTF-8设置"""
    # 获取PowerShell配置文件路径
    profile_paths = [
        os.path.expandvars(r"%USERPROFILE%\Documents\PowerShell\Microsoft.PowerShell_profile.ps1"),
        os.path.expandvars(r"%USERPROFILE%\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1"),
    ]
    
    utf8_commands = [
        "# UTF-8编码配置 (由MSS-AI项目自动添加)",
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8",
        "$OutputEncoding = [System.Text.Encoding]::UTF8",
        "chcp 65001 > $null",
        "",
    ]
    
    for profile_path in profile_paths:
        profile_dir = os.path.dirname(profile_path)
        if not os.path.exists(profile_dir):
            try:
                os.makedirs(profile_dir, exist_ok=True)
            except:
                continue
        
        # 读取现有内容
        existing_content = ""
        if os.path.exists(profile_path):
            try:
                with open(profile_path, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
            except:
                pass
        
        # 检查是否已配置
        if "UTF-8编码配置" in existing_content:
            print(f"✅ PowerShell配置文件已配置: {profile_path}")
            continue
        
        # 添加UTF-8配置
        try:
            with open(profile_path, 'a', encoding='utf-8') as f:
                if existing_content and not existing_content.endswith('\n'):
                    f.write('\n')
                f.write('\n'.join(utf8_commands))
            print(f"✅ 已配置PowerShell配置文件: {profile_path}")
        except Exception as e:
            print(f"❌ 无法配置 {profile_path}: {e}")


def setup_environment_variables():
    """设置系统环境变量"""
    env_vars = {
        'PYTHONIOENCODING': 'utf-8',
        'PYTHONLEGACYWINDOWSSTDIO': 'utf-8',
    }
    
    print("\n环境变量配置:")
    for key, value in env_vars.items():
        # 设置当前进程环境变量
        os.environ[key] = value
        print(f"  ✅ {key}={value}")
    
    # 提示用户添加到系统环境变量
    print("\n建议添加到系统环境变量（需要管理员权限）:")
    print("  [System.Environment]::SetEnvironmentVariable('PYTHONIOENCODING', 'utf-8', 'User')")
    print("  [System.Environment]::SetEnvironmentVariable('PYTHONLEGACYWINDOWSSTDIO', 'utf-8', 'User')")


def create_batch_wrapper():
    """创建批处理包装器"""
    batch_content = """@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSSTDIO=utf-8
cd /d C:\\MSS-AI-Project
echo [UTF-8模式已激活]
echo.
cmd /k
"""
    
    batch_path = r'C:\MSS-AI-Project\start_utf8.bat'
    try:
        with open(batch_path, 'w', encoding='utf-8') as f:
            f.write(batch_content)
        print(f"\n✅ 已创建UTF-8批处理启动器: {batch_path}")
    except Exception as e:
        print(f"\n❌ 无法创建批处理文件: {e}")


def verify_utf8():
    """验证UTF-8配置"""
    print("\n" + "=" * 60)
    print("UTF-8配置验证")
    print("=" * 60)
    
    # 测试Python编码
    test_str = "中文测试: 意义调谐 双奇点模型"
    print(f"\nPython默认编码: {sys.getdefaultencoding()}")
    print(f"控制台编码: {sys.stdout.encoding if hasattr(sys.stdout, 'encoding') else 'N/A'}")
    print(f"测试字符串: {test_str}")
    
    # 测试文件写入
    test_file = r'C:\MSS-AI-Project\.utf8_test.tmp'
    try:
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_str)
        with open(test_file, 'r', encoding='utf-8') as f:
            read_str = f.read()
        if read_str == test_str:
            print("✅ 文件读写测试通过")
        else:
            print("❌ 文件读写测试失败")
        os.remove(test_file)
    except Exception as e:
        print(f"❌ 文件测试失败: {e}")


def main():
    print("=" * 60)
    print("MSS-AI项目 UTF-8编码配置")
    print("=" * 60)
    
    setup_powershell_profile()
    setup_environment_variables()
    create_batch_wrapper()
    verify_utf8()
    
    print("\n" + "=" * 60)
    print("配置完成!")
    print("=" * 60)
    print("\n使用方法:")
    print("  1. 双击运行 start_utf8.bat 启动UTF-8环境")
    print("  2. 或在PowerShell中运行: chcp 65001")
    print("  3. 重启PowerShell以加载配置文件更改")
    print("=" * 60)


if __name__ == '__main__':
    main()
