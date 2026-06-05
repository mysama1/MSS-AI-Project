import json, os

fp = r'C:\MSS-AI-Project\task_bar_current.json'
with open(fp, 'r', encoding='utf-8') as f:
    tb = json.load(f)

# Sync reality
tb['last_sync'] = '2026-05-23T21:50:00.000000'
tb['system_status']['phase_progress'] = '55%'
tb['system_status']['note'] = 'D5-004完成+范式纯净度168处K3清零+QLoRA目标函数重定义'

# Update D5-004 to complete
for t in tb['active_tasks']:
    if t['id'] == 'D5-004':
        t['progress'] = '100%'
        t['note'] = '四模块68KB+17/17测试全通'
    if t['id'] == 'D5-001':
        t['progress'] = '75%'
        t['note'] = 'PyPI发布准备中'

# Add D5-005 + D5-006
D5_NEW = [
    {'id':'D5-005','name':'逻辑疫苗制备引擎','priority':10,'progress':'0%',
     'note':'病毒采集→解剖→疫苗生成→接种，7子任务','phase':'D5','week':'Week 3'},
    {'id':'D5-006','name':'双壳设计架构规范','priority':9,'progress':'0%',
     'note':'采集壳+交互壳+隔离协议+热税审计','phase':'D5','week':'Week 3'},
]
for dn in D5_NEW:
    if not any(t['id'] == dn['id'] for t in tb['active_tasks']):
        tb['active_tasks'].append(dn)

# Re-sort by priority
tb['active_tasks'].sort(key=lambda t: (-t['priority'], t['id']))

with open(fp, 'w', encoding='utf-8') as f:
    json.dump(tb, f, ensure_ascii=False, indent=2)

print('Synced: D5-004→100%, D5-001→75%, D5-005/D5-006 added')
print(f'Active: {len(tb["active_tasks"]}, Completed: {len(tb["completed_tasks"])}')