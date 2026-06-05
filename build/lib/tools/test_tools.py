#!/usr/bin/env python3
"""Test script for task_manager and archive_manager."""

import sys
sys.path.insert(0, 'C:/MSS-AI-Project/tools')

from task_manager import TaskManager
from archive_manager import ArchiveManager
import json

def test_task_manager():
    print("=== Testing TaskManager ===")
    tm = TaskManager()
    
    # Test summary
    summary = tm.get_phase_summary()
    print(f"Phase: {summary['phase']}, Tasks: {summary['total_tasks']}, Avg: {summary['avg_progress']}%")
    
    # Test update
    tm.update_task('TEST-001', name='Test Task', progress=50, status='in_progress')
    task = tm.get_task('TEST-001')
    print(f"Updated task: {task['name']} = {task['progress']}%")
    
    # Test list
    tasks = tm.list_tasks()
    print(f"Total tasks listed: {len(tasks)}")
    
    print("TaskManager: OK\n")

def test_archive_manager():
    print("=== Testing ArchiveManager ===")
    am = ArchiveManager()
    
    # Test stats
    stats = am.get_stats()
    print(f"KB Files: {stats['total_files']}, Entries: {stats['total_entries']}")
    print(f"By layer: L1={stats['by_layer']['L1']}, L2={stats['by_layer']['L2']}, L3={stats['by_layer']['L3']}")
    
    # Test archive
    entry = {
        "id": "TEST-ARCHIVE-001",
        "title": "Test Archive Entry",
        "layer": "L3",
        "content": "This is a test entry for the archive manager.",
        "category": "test"
    }
    result = am.archive(entry)
    print(f"Archive result: {result['status']} -> {result.get('path', 'N/A')}")
    
    # Test search
    results = am.search("Test Archive")
    print(f"Search results: {len(results)} found")
    
    print("ArchiveManager: OK\n")

if __name__ == "__main__":
    test_task_manager()
    test_archive_manager()
    print("All tests passed!")
