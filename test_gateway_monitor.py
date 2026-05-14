#!/usr/bin/env python3
"""
Gateway Monitor 测试脚本
验证监控功能是否正常工作
"""

import subprocess
import sys
import os

def test_process_check():
    """测试进程检测功能"""
    print("=" * 50)
    print("测试1: 进程检测")
    print("=" * 50)
    
    result = subprocess.run(
        ['tasklist', '/FI', 'IMAGENAME eq QClaw.exe'],
        capture_output=True, text=True, encoding='utf-8', errors='ignore',
        timeout=5
    )
    
    if 'QClaw.exe' in result.stdout and 'INFO: No tasks' not in result.stdout:
        print("✓ QClaw.exe 进程正在运行")
        # 提取进程信息
        lines = result.stdout.strip().split('\n')
        for line in lines[3:]:  # 跳过表头
            if line.strip():
                print(f"  {line.strip()}")
        return True
    else:
        print("✗ QClaw.exe 进程未找到")
        return False

def test_http_port():
    """测试HTTP端口检测"""
    print("\n" + "=" * 50)
    print("测试2: HTTP端口检测 (端口28789)")
    print("=" * 50)
    
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('localhost', 28789))
        sock.close()
        
        if result == 0:
            print("✓ HTTP端口28789可连接")
            return True
        else:
            print(f"✗ HTTP端口连接失败 (错误码: {result})")
            return False
    except Exception as e:
        print(f"✗ HTTP检测失败: {e}")
        return False

def test_monitor_script():
    """测试监控脚本"""
    print("\n" + "=" * 50)
    print("测试3: 监控脚本执行")
    print("=" * 50)
    
    monitor_script = r"C:\MSS-AI-Project\gateway_monitor.py"
    if not os.path.exists(monitor_script):
        print(f"✗ 监控脚本不存在: {monitor_script}")
        return False
    
    print(f"✓ 监控脚本存在: {monitor_script}")
    
    # 测试帮助信息
    result = subprocess.run(
        ['python', monitor_script, '--help'],
        capture_output=True, text=True, encoding='utf-8', errors='ignore',
        timeout=10
    )
    
    if result.returncode == 0:
        print("✓ 监控脚本可执行")
        print("\n帮助信息:")
        print(result.stdout)
        return True
    else:
        print("✗ 监控脚本执行失败")
        print(result.stderr)
        return False

def test_task_exists():
    """测试计划任务是否存在"""
    print("\n" + "=" * 50)
    print("测试4: 计划任务检查")
    print("=" * 50)
    
    result = subprocess.run(
        ['schtasks', '/query', '/tn', 'OpenClawGatewayMonitor', '/fo', 'list'],
        capture_output=True, text=True, encoding='utf-8', errors='ignore',
        timeout=10
    )
    
    if result.returncode == 0:
        print("✓ 计划任务 'OpenClawGatewayMonitor' 已创建")
        # 显示任务信息
        for line in result.stdout.split('\n'):
            if line.strip():
                print(f"  {line.strip()}")
        return True
    else:
        print("✗ 计划任务未找到")
        print("  提示: 以管理员身份运行 setup_monitor_task.bat 创建任务")
        return False

def main():
    print("\n" + "=" * 60)
    print("OpenClaw Gateway Monitor 测试套件")
    print("=" * 60)
    
    results = []
    
    # 运行所有测试
    results.append(("进程检测", test_process_check()))
    results.append(("HTTP端口", test_http_port()))
    results.append(("监控脚本", test_monitor_script()))
    results.append(("计划任务", test_task_exists()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("\n🎉 所有测试通过！监控功能正常工作。")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查上述错误信息。")
        return 1

if __name__ == '__main__':
    sys.exit(main())
