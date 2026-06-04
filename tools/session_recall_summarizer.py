#!/usr/bin/env python3
"""P1: Session Recall Summariser - Generates compact session summaries for interrupt recovery."""
import json, os, datetime, hashlib

SUMMARY_DIR = r'E:\QClaw-Data\workspace\session_summaries'
MEMORY_DIR = r'C:\Users\Administrator\.openclaw\workspace\memory'

def generate_summary(session_id=None, topics=None, decisions=None, files=None, next_steps=None):
    """Generate a compact session summary for fast recovery."""
    os.makedirs(SUMMARY_DIR, exist_ok=True)
    
    now = datetime.datetime.now()
    tid = session_id or hashlib.md5(str(now.timestamp()).encode()).hexdigest()[:8]
    
    summary = {
        'session_id': tid,
        'timestamp': now.isoformat(),
        'topics': topics or [],
        'decisions': decisions or [],
        'files_modified': files or [],
        'next_steps': next_steps or [],
        'recovery_prompt': f"Resume session {tid}. Key topics: {', '.join(topics or ['unknown'])}"
    }
    
    out = os.path.join(SUMMARY_DIR, f'session_{tid}_{now.strftime("%Y%m%d_%H%M")}.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    return out

def list_recent_sessions(limit=5):
    """List recent session summaries for recovery."""
    if not os.path.exists(SUMMARY_DIR):
        return []
    files = sorted([f for f in os.listdir(SUMMARY_DIR) if f.endswith('.json')], reverse=True)
    results = []
    for f in files[:limit]:
        with open(os.path.join(SUMMARY_DIR, f), 'r', encoding='utf-8') as fp:
            results.append(json.load(fp))
    return results

def quick_recovery_message():
    """Generate a recovery message from the most recent session."""
    sessions = list_recent_sessions(1)
    if not sessions:
        return "No previous session found."
    s = sessions[0]
    return (
        f"[Session Recovery] {s['timestamp'][:16]}\n"
        f"Topics: {', '.join(s['topics'])}\n"
        f"Decisions: {'; '.join(s['decisions'])}\n"
        f"Next: {s['next_steps'][0] if s['next_steps'] else 'proceed'}"
    )

if __name__ == '__main__':
    # Quick test
    out = generate_summary(
        topics=['KB v15.1 cleanup', 'H74-H84 recovery', 'auto_archive test'],
        decisions=['H144 L1->L2', 'Scripts persist to E:\\QClaw-Data'],
        files=['MSS-AI_KnowledgeBase_Complete_v15.1.md', 'auto_archive.py'],
        next_steps=['Fix 18 malformed jsonl', 'Create P1 tool_output_budget_gate']
    )
    print(f'Test summary: {out}')
    print(quick_recovery_message())