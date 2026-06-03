#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MSS-AI项目编码修复工具
功能：
1. 检查所有Python文件编码
2. 修复GBK编码文件为UTF-8
3. 配置Windows UTF-8环境
"""

import os
import sys
import glob
from pathlib import Path

def check_file_encoding(filepath):
    """检测文件编码"""
    try:
        with open(filepath, 'rb') as f:
            raw = f.read(4)
        
        # 检查BOM
        if raw.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'
        
        # 尝试UTF-8解码
        with open(filepath, 'r', encoding='utf-8') as f:
            f.read()
        return 'utf-8'
    except UnicodeDecodeError:
        try:
            with open(filepath, 'r', encoding='gbk') as f:
                f.read()
            return 'gbk'
        except:
            return 'unknown'
    except Exception as e:
        return f'error: {e}'

def fix_gbk_to_utf8(filepath):
    """将GBK文件转换为UTF-8"""
    try:
        with open(filepath, 'r', encoding='gbk') as f:
            content = f.read()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True, f"已修复: {filepath}"
    except Exception as e:
        return False, f"修复失败 {filepath}: {e}"

def main():
    project_dir = r'C:\MSS-AI-Project'
    
    print("=" * 60)
    print("MSS-AI项目编码检查与修复")
    print("=" * 60)
    print()
    
    # 检查所有Python文件
    py_files = glob.glob(os.path.join(project_dir, '*.py'))
    
    print(f"发现 {len(py_files)} 个Python文件")
    print()
    
    gbk_files = []
    
    for filepath in sorted(py_files):
        filename = os.path.basename(filepath)
        encoding = check_file_encoding(filepath)
        
        status = "✅"
        if encoding == 'gbk':
            status = "❌ GBK"
            gbk_files.append(filepath)
        elif encoding == 'utf-8-sig':
            status = "⚠️  UTF-8 BOM"
        elif encoding == 'utf-8':
            status = "✅ UTF-8"
        else:
            status = f"❓ {encoding}"
        
        print(f"{status:12} {filename}")
    
    print()
    
    # 修复GBK文件
    if gbk_files:
        print(f"发现 {len(gbk_files)} 个GBK编码文件，开始修复...")
        for filepath in gbk_files:
            success, msg = fix_gbk_to_utf8(filepath)
            print(f"  {'✅' if success else '❌'} {msg}")
    else:
        print("未发现GBK编码文件，无需修复")
    
    print()
    print("=" * 60)
    print("建议：设置Windows默认编码为UTF-8")
    print("  1. 控制面板 → 区域 → 管理 → 更改系统区域设置")
    print("  2. 勾选 'Beta: 使用Unicode UTF-8提供全球语言支持'")
    print("  3. 重启计算机")
    print("=" * 60)
    
    # 等待用户按键
    input("\n按Enter键退出...")

if __name__ == '__main__':
    main()
