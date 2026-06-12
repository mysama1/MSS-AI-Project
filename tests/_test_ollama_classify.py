import json, urllib.request

content = "推荐好看的电影"
prompt = f"""Classify this message: "{content}"

Categories: life(calendar/reminder/weather/health/food/exercise/shopping), entertain(movie/music/game/book/show), social(message/reply/wechat/email/tone)

Return JSON: {{"category": "..."}}"""

req = urllib.request.Request('http://localhost:11434/api/generate',
    data=json.dumps({
        'model': 'qwen2.5:0.5b',
        'prompt': prompt,
        'stream': False,
        'options': {'num_predict': 30, 'temperature': 0.1}
    }).encode(),
    headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req, timeout=10) as resp:
    r = json.loads(resp.read())
    print('RAW:', repr(r.get('response', '')))
