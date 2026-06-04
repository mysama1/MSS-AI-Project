#!/usr/bin/env python3
"""
paradigm_purge.py v2.0 — FIXED: 正确路径 + 安全备份
原版bug: PROJECT_ROOT = C:\MSS-AI-Project (错误路径)
修复:    自动检测项目路径 + 操作前创建.bak备份
"""
import os, re, sys, shutil
from datetime import datetime

# FIXED: 自动检测项目路径
def find_project_root():
    candidates = [
        r'E:\AI_Workspace\MSS-AI\project',
        r'C:\MSS-AI-Project',
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.exists(os.path.join(c, 'knowledge_base')):
            return c
    return os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = find_project_root()
EXCLUDE_DIRS = {'__pycache__', 'dist', 'node_modules', '.git', '.pytest_cache', 'tools_backup', 'unsloth_compiled_cache'}
BACKUP_DIR = os.path.join(os.path.dirname(PROJECT_ROOT), 'paradigm_purge_backups', datetime.now().strftime('%Y%m%d_%H%M%S'))

# 替换规则
REPLACEMENTS = [
    (r'训练数据集', '调谐锚定案例库'),
    (r'基准数据集', '基准锚定案例库'),
    (r'数据集', '锚定案例库'),
    (r'训练数据', '统计拟合数据'),
    (r'训练算法', '统计拟合算法'),
    (r'训练流程', '统计拟合流程'),
    (r'训练目标', '统计拟合目标'),
    (r'训练迭代', '调谐迭代'),
    (r'端到端训练', '端到端统计拟合'),
    (r'预训练', '预统计拟合'),
    (r'AI训练', 'AI调谐'),
    (r'用于训练', '用于统计拟合'),
    (r'通过训练', '通过统计拟合'),
    (r'偷数据训练', '偷数据统计拟合'),
    (r'存在论训练', '存在论调谐'),
    (r'身体训练', '身体调谐'),
    (r'训练数据边界', '统计拟合数据边界'),
    (r'训练数据自我污染', '统计拟合数据自我污染'),
    (r'模型训练', '模型统计拟合'),
    (r'训练模型', '统计拟合模型'),
    (r'纯逻辑样本', '纯逻辑锚定案例'),
    (r'样本量有限', '锚定案例量有限'),
]

SKIP_PATTERNS = ['大样本统计', 'random_sample', '抽样', 'cartoon_set_sample']
SKIP_FILES = ['paradigm_purge.py', 'paradigm_purge_v2.py']


def backup_file(filepath):
    """创建备份"""
    rel = os.path.relpath(filepath, PROJECT_ROOT)
    backup_path = os.path.join(BACKUP_DIR, rel)
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    shutil.copy2(filepath, backup_path)
    return backup_path


def should_skip_line(line):
    for skip in SKIP_PATTERNS:
        if skip in line:
            return True
    return False


def process_file(filepath, dry_run=False):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return 0

    original = content
    lines = content.split('\n')
    modified_lines = []
    changed = False

    for line in lines:
        if should_skip_line(line):
            modified_lines.append(line)
            continue
        new_line = line
        for pattern, replacement in REPLACEMENTS:
            test = re.sub(pattern, replacement, new_line)
            if test != new_line:
                new_line = test
                changed = True
        modified_lines.append(new_line)

    if not changed:
        return 0

    # 创建备份
    backup_file(filepath)

    content = '\n'.join(modified_lines)
    count = sum(1 for p, _ in REPLACEMENTS if re.search(p, original))

    if not dry_run:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    return count


def main(dry_run=False):
    print('=' * 60)
    print('MSS-AI Paradigm Purge v2.0 (FIXED)')
    print('Project: %s' % PROJECT_ROOT)
    print('Backup:  %s' % BACKUP_DIR)
    print('Mode:    %s' % ('DRY RUN' if dry_run else 'LIVE'))
    print('=' * 60)

    total_files = 0
    total_replaced = 0

    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for filename in files:
            if filename in SKIP_FILES:
                continue
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ('.py', '.md', '.json', '.txt', '.jsonl'):
                continue

            filepath = os.path.join(root, filename)
            count = process_file(filepath, dry_run)
            total_files += 1

            if count > 0:
                total_replaced += count
                rel = os.path.relpath(filepath, PROJECT_ROOT)
                print('  %s (%d replacements)' % (rel, count))

    print('\nScanned: %d | Modified: %d | Backups: %s' % (
        total_files, total_replaced, BACKUP_DIR if total_replaced > 0 else 'none needed'))

    return 0


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    sys.exit(main(dry_run=args.dry_run))