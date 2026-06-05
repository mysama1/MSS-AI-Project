#!/usr/bin/env python3
"""IMA recovery: search for missing H76-H84, H91-H99 entries."""
import urllib.request, json, os, sys

CLIENT_ID = '6165e4d1fbbc58d18eb76b820f4bba97'
API_KEY = 'eZ2Yu6VwX2N8RKLsdt/SfWm7EpbH04BhiJN4jtxc4aUHIL4J47sUJ9pz3Z1F3fIIHYml93JTTg=='
BASE = 'http://127.0.0.1:11435'
KB_DIR = r'E:\AI_Workspace\MSS-AI\project\knowledge_base'

headers = {
    'X-Client-ID': CLIENT_ID,
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json',
}

def api_get(path, data=None, timeout=10):
    url = BASE + path
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, headers=headers, data=body, method='POST' if data else 'GET')
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())

# Step 1: Search for MSS entries
print('=== Searching IMA for MSS entries ===')
try:
    result = api_get('/api/search', {'query': 'MSS H7 H8 H9 knowledge base', 'limit': 50})
    if isinstance(result, list):
        print('Found %d results' % len(result))
        for item in result[:10]:
            title = item.get('title', item.get('name', '?'))
            doc_id = item.get('id', item.get('doc_id', '?'))
            print('  [%s] %s' % (doc_id, str(title)[:80]))
    else:
        print('Response:', json.dumps(result, ensure_ascii=False)[:500])
except Exception as e:
    print('Search failed: %s' % e)

# Step 2: Try direct doc fetch
print('\n=== Attempting direct doc fetch ===')
missing_ranges = [
    list(range(76, 85)),   # H76-H84
    list(range(91, 100)),  # H91-H99
]

recovered = 0
for rng in missing_ranges:
    for hid in rng:
        h = 'H%d' % hid
        # Check if already exists in KB
        existing = [f for f in os.listdir(KB_DIR) if f.startswith('h%d_' % hid) or f.startswith('H%d_' % hid)]
        if existing:
            continue

        # Try IMA
        try:
            result = api_get('/api/knowledge/get', {'doc_id': h.lower(), 'query': h})
            if result and result.get('content'):
                content = result['content']
                # Save to KB
                entry = {
                    'h_id': h,
                    'title': result.get('title', 'IMA recovered entry %s' % h),
                    'category': 'ima_recovered',
                    't_value': result.get('confidence', 0.7),
                    'version': '1.0',
                    'date': '2026-06-06',
                    'summary': content[:200],
                    'content': content[:5000],
                }
                fname = os.path.join(KB_DIR, '%s_ima_recovered.jsonl' % h.lower())
                with open(fname, 'w', encoding='utf-8') as f:
                    json.dump(entry, f, ensure_ascii=False)
                recovered += 1
                print('  %s ✅ recovered (%d chars)' % (h, len(content)))
            else:
                print('  %s ❌ no content' % h)
        except Exception as e:
            err = str(e)[:80]
            print('  %s ❌ %s' % (h, err))

print('\nRecovered: %d entries' % recovered)
