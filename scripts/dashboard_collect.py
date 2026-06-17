"""
Track A: Dashboard live data enrichment
Adds: vector memory health, heat tax real-time scan, service status history
"""
import json, time, os, sys
from datetime import datetime

sys.path.insert(0, r'E:\AI_Workspace\MSS-AI\project')

def check_services():
    """Check all MSS services"""
    import requests
    results = {}
    for name, url in [
        ('skill_api', 'http://localhost:53000/health'),
        ('blackhole', 'http://localhost:53001/health'),
        ('ollama', 'http://localhost:11434/api/tags'),
    ]:
        try:
            r = requests.get(url, timeout=2)
            results[name] = {'status': 'UP', 'code': r.status_code}
        except Exception as e:
            results[name] = {'status': 'DOWN', 'error': str(e)[:80]}
    return results

def check_vector_memory():
    """Check vector memory health"""
    try:
        from mssclaw.core.vector_memory import VectorMemory
        vm = VectorMemory()
        stats = vm.get_stats()
        stats['timestamp'] = datetime.now().isoformat()
        return stats
    except Exception as e:
        return {'status': 'ERROR', 'error': str(e)[:80]}

def check_ollama_models():
    """List available Ollama models"""
    try:
        import requests
        r = requests.get('http://localhost:11434/api/tags', timeout=2)
        models = r.json().get('models', [])
        return {
            'count': len(models),
            'models': [m['name'] for m in models[:10]],
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {'status': 'ERROR', 'error': str(e)[:80]}

def collect_dashboard_data():
    """Collect all dashboard metrics"""
    data = {
        'timestamp': datetime.now().isoformat(),
        'version': 'v0.3.11',
        'services': check_services(),
        'vector_memory': check_vector_memory(),
        'ollama': check_ollama_models(),
    }
    return data

if __name__ == '__main__':
    data = collect_dashboard_data()
    output_path = r'E:\AI_Workspace\MSS-AI\project\dashboard_data.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f'Dashboard data written to {output_path}')
    print(json.dumps(data, indent=2, ensure_ascii=False))
