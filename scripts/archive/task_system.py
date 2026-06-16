"""Task System - Project task management and tracking."""
import json

DEFAULT_TASKS = [
    {"id": "mss-ai", "name": "MSS-AI Project", "description": "MSS theory AI engineering deployment"},
    {"id": "mss-research", "name": "MSS Research", "description": "Theory construction and validation"},
    {"id": "mss-product", "name": "MSS Products", "description": "Tools and product development"},
    {"id": "mss-infra", "name": "MSS Infrastructure", "description": "Infrastructure and deployment"},
]

def get_tasks():
    return DEFAULT_TASKS

def find_task(command):
    keywords = ["list", "show", "status"]
    if any(kw in command.lower() for kw in keywords):
        return DEFAULT_TASKS
    return []
