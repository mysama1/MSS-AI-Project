#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows UTF-8鐜閰嶇疆鑴氭湰
閰嶇疆PowerShell鍜孭ython榛樿浣跨敤UTF-8缂栫爜
"""

import os
import sys
import subprocess
from pathlib import Path

def setup_powershell_profile():
    """閰嶇疆PowerShell閰嶇疆鏂囦欢锛屾坊鍔燯TF-8璁剧疆"""
    # 鑾峰彇PowerShell閰嶇疆鏂囦欢璺緞
    profile_paths = [
        os.path.expandvars(r"%USERPROFILE%\Documents\PowerShell\Microsoft.PowerShell_profile.ps1"),
        os.path.expandvars(r"%USERPROFILE%\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1"),
    ]

    utf8_commands = [
        "# UTF-8缂栫爜閰嶇疆 (鐢盡SS-AI椤圭洰鑷姩娣诲姞)",
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

        # 璇诲彇鐜版湁鍐呭
        existing_content = ""
        if os.path.exists(profile_path):
            try:
                with open(profile_path, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
            except:
                pass

        # 妫€鏌ユ槸鍚﹀凡閰嶇疆
        if "UTF-8缂栫爜閰嶇疆" in existing_content:
            print(f"鉁?PowerShell閰嶇疆鏂囦欢宸查厤缃? {profile_path}")
            continue

        # 娣诲姞UTF-8閰嶇疆
        try:
            with open(profile_path, 'a', encoding='utf-8') as f:
                if existing_content and not existing_content.endswith('\n'):
                    f.write('\n')
                f.write('\n'.join(utf8_commands))
            print(f"鉁?宸查厤缃甈owerShell閰嶇疆鏂囦欢: {profile_path}")
        except Exception as e:
            print(f"鉂?鏃犳硶閰嶇疆 {profile_path}: {e}")

def setup_environment_variables():
    """璁剧疆绯荤粺鐜鍙橀噺"""
    env_vars = {
        'PYTHONIOENCODING': 'utf-8',
        'PYTHONLEGACYWINDOWSSTDIO': 'utf-8',
    }

    print("\n鐜鍙橀噺閰嶇疆:")
    for key, value in env_vars.items():
        # 璁剧疆褰撳墠杩涚▼鐜鍙橀噺
        os.environ[key] = value
        print(f"  鉁?{key}={value}")

    # 鎻愮ず鐢ㄦ埛娣诲姞鍒扮郴缁熺幆澧冨彉閲?
    print("\n寤鸿娣诲姞鍒扮郴缁熺幆澧冨彉閲忥紙闇€瑕佺鐞嗗憳鏉冮檺锛?")
    print("  [System.Environment]::SetEnvironmentVariable('PYTHONIOENCODING', 'utf-8', 'User')")
    print("  [System.Environment]::SetEnvironmentVariable('PYTHONLEGACYWINDOWSSTDIO', 'utf-8', 'User')")

def create_batch_wrapper():
    """鍒涘缓鎵瑰鐞嗗寘瑁呭櫒"""
    batch_content = """@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSSTDIO=utf-8
cd /d E:\\AI_Workspace\\MSS-AI\\project
echo [UTF-8妯″紡宸叉縺娲籡
echo.
cmd /k
"""

    batch_path = r'E:\AI_Workspace\MSS-AI\project\start_utf8.bat'
    try:
        with open(batch_path, 'w', encoding='utf-8') as f:
            f.write(batch_content)
        print(f"\n鉁?宸插垱寤篣TF-8鎵瑰鐞嗗惎鍔ㄥ櫒: {batch_path}")
    except Exception as e:
        print(f"\n鉂?鏃犳硶鍒涘缓鎵瑰鐞嗘枃浠? {e}")

def verify_utf8():
    """楠岃瘉UTF-8閰嶇疆"""
    print("\n" + "=" * 60)
    print("UTF-8閰嶇疆楠岃瘉")
    print("=" * 60)

    # 娴嬭瘯Python缂栫爜
    test_str = "涓枃娴嬭瘯: 鎰忎箟璋冭皭 鍙屽鐐规ā鍨?
    print(f"\nPython榛樿缂栫爜: {sys.getdefaultencoding()}")
    print(f"鎺у埗鍙扮紪鐮? {sys.stdout.encoding if hasattr(sys.stdout, 'encoding') else 'N/A'}")
    print(f"娴嬭瘯瀛楃涓? {test_str}")

    # 娴嬭瘯鏂囦欢鍐欏叆
    test_file = r'E:\AI_Workspace\MSS-AI\project\.utf8_test.tmp'
    try:
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_str)
        with open(test_file, 'r', encoding='utf-8') as f:
            read_str = f.read()
        if read_str == test_str:
            print("鉁?鏂囦欢璇诲啓娴嬭瘯閫氳繃")
        else:
            print("鉂?鏂囦欢璇诲啓娴嬭瘯澶辫触")
        os.remove(test_file)
    except Exception as e:
        print(f"鉂?鏂囦欢娴嬭瘯澶辫触: {e}")

def main():
    print("=" * 60)
    print("MSS-AI椤圭洰 UTF-8缂栫爜閰嶇疆")
    print("=" * 60)

    setup_powershell_profile()
    setup_environment_variables()
    create_batch_wrapper()
    verify_utf8()

    print("\n" + "=" * 60)
    print("閰嶇疆瀹屾垚!")
    print("=" * 60)
    print("\n浣跨敤鏂规硶:")
    print("  1. 鍙屽嚮杩愯 start_utf8.bat 鍚姩UTF-8鐜")
    print("  2. 鎴栧湪PowerShell涓繍琛? chcp 65001")
    print("  3. 閲嶅惎PowerShell浠ュ姞杞介厤缃枃浠舵洿鏀?)
    print("=" * 60)

if __name__ == '__main__':
    main()
