#!/usr/bin/env python3
"""Extract bundled sub-entries and create tombstones for lost entries."""
import json, os

kb = r'E:\AI_Workspace\MSS-AI\project\knowledge_base'

# --- Sub-entries from bundles ---
sub_entries = {
    'H63': {
        'title': 'H63: 责任拓扑定理',
        'summary': '伦理责任在意义网络中按最短路径传播。责任不是原子的，而是网络拓扑的函数。',
        'parent': 'H62',
        'axioms': ['A3', 'A5']
    },
    'H64': {
        'title': 'H64: 价值梯度定理',
        'summary': '价值判断的方向由意义密度梯度∇ρ决定。价值不是静态属性，而是意义场的梯度场。',
        'parent': 'H62',
        'axioms': ['A3', 'A5']
    },
    'H66': {
        'title': 'H66: 医疗意义论',
        'summary': '疾病是局部意义网络的熵增失控，治疗是负熵注入。康复=意义密度恢复正常涨落区间。',
        'parent': 'H65',
        'axioms': ['A3', 'A5']
    },
    'H67': {
        'title': 'H67: 经济意义论',
        'summary': '价值=意义密度×流通速度。货币是意义流通的量化代理，通胀=意义密度稀释。',
        'parent': 'H65',
        'axioms': ['A3', 'A5']
    },
    'H68': {
        'title': 'H68: 政治意义论',
        'summary': '合法性=意义共识的拓扑覆盖度。权力=意义场控制节点的出度与介数中心性。',
        'parent': 'H65',
        'axioms': ['A3', 'A5']
    },
}

for hid, info in sub_entries.items():
    fname = os.path.join(kb, hid.lower() + '_sub_entry.jsonl')
    if not os.path.exists(fname):
        entry = {
            'h_id': hid,
            'title': info['title'],
            'category': 'theorem',
            't_value': 0.78,
            'version': '1.0',
            'date': '2026-06-06',
            'source': 'Bundled in ' + info['parent'] + ' (v15.1)',
            'axioms': info['axioms'],
            'summary': info['summary'],
            'content': 'See parent entry ' + info['parent'] + '.\n\n' + info['summary'],
        }
        with open(fname, 'w', encoding='utf-8') as f:
            json.dump(entry, f, ensure_ascii=False)
        print('  ' + hid + ' created (sub of ' + info['parent'] + ')')

# --- Tombstones for permanently lost ---
for hid in ['H77', 'H78', 'H79', 'H80', 'H81', 'H82', 'H83', 'H84']:
    fname = os.path.join(kb, hid.lower() + '_lost_tombstone.jsonl')
    if not os.path.exists(fname):
        entry = {
            'h_id': hid,
            'title': hid + ': [PERMANENTLY LOST]',
            'category': 'tombstone',
            't_value': 0.0,
            'version': '1.0',
            'date': '2026-06-06',
            'status': 'permanently_lost',
            'summary': 'v15.1 mentions partial recovery of H74-H84 block. No recoverable source found in v12.2 or complete v15.1 exports.',
            'content': 'TOMBSTONE: Permanently lost MSS early-architecture entry.',
        }
        with open(fname, 'w', encoding='utf-8') as f:
            json.dump(entry, f, ensure_ascii=False)
        print('  ' + hid + ' tombstone')

print('Done: 5 sub-entries + 8 tombstones')
