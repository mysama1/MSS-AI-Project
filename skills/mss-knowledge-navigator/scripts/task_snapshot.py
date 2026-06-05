#!/usr/bin/env python3
"""Task Snapshot — reads unified task system"""
import subprocess, sys

TS = r"E:\QClaw-Data\workspace\task_system.py"

def snap():
    result = subprocess.run(["python", TS, "snapshot"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"⚠️ {result.stderr}")

def add(task_id, name, priority, note=""):
    subprocess.run(["python", TS, "add", task_id, name, str(priority), note])

def done(task_id):
    subprocess.run(["python", TS, "done", task_id])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        snap()
    elif sys.argv[1] == "add" and len(sys.argv) >= 4:
        add(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else "")
    elif sys.argv[1] == "done" and len(sys.argv) >= 3:
        done(sys.argv[2])
    else:
        snap()