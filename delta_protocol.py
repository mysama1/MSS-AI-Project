#!/usr/bin/env python3
"""
MSS Δ Detection Protocol v2.0 — A6 Alignment Elevation runnable prototype.

L0 (Friston σ):      delta_status 4 signals as low-dim anchors
L1 (quorum-fast):    multi-projection convergence detection
L2 (Molting trigger): Δ drops 2 consecutive cycles → alert

Based on H525 A6 Alignment Elevation Protocol.
"""
import os, json, sys, math
from datetime import datetime, timedelta
from collections import defaultdict, deque

PROJECT_ROOT = os.environ.get('MSS_PROJECT_ROOT', r'E:\AI_Workspace\MSS-AI\project')
STATE_FILE = os.path.join(PROJECT_ROOT, 'tools', 'delta_protocol_state.json')

# ─── L0: delta_status as low-dim anchors ───

def collect_delta_signals(tau_months: int = 3):
    """Run delta_status logic and return 4 signals."""
    tau = timedelta(days=tau_months * 30)
    now = datetime.now()

    papers_dir = os.path.join(PROJECT_ROOT, 'papers')
    kb_dir = os.path.join(PROJECT_ROOT, 'knowledge_base')

    # S1: Theory incompleteness
    s1 = False
    incompleteness_terms = ['不完备', 'incomplete', 'known unknown', '没有完成', 'has not been', 'gap', '缺口']
    if os.path.isdir(papers_dir):
        for f in os.listdir(papers_dir):
            fp = os.path.join(papers_dir, f)
            if not f.endswith('.md'):
                continue
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(fp))
                if now - mtime < tau:
                    with open(fp, encoding='utf-8', errors='replace') as fh:
                        c = fh.read().lower()
                    if any(term in c for term in incompleteness_terms):
                        s1 = True
                        break
            except OSError:
                pass

    # S2: Counterexample response
    s2 = False
    fails_path = os.path.join(papers_dir, 'five_ways_mss_fails.md')
    if os.path.exists(fails_path):
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(fails_path))
            s2 = (now - mtime) < tau
        except OSError:
            pass

    # S3: Dissent space — recent paper activity
    s3 = False
    if os.path.isdir(papers_dir):
        for f in os.listdir(papers_dir):
            fp = os.path.join(papers_dir, f)
            if not f.endswith('.md'):
                continue
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(fp))
                if now - mtime < tau:
                    s3 = True
                    break
            except OSError:
                pass

    # S4: Output validity — rate of new KB entries
    s4 = False
    if os.path.isdir(kb_dir):
        recent_new, recent_total = 0, 0
        for root, dirs, files in os.walk(kb_dir):
            for f in files:
                if not f.endswith('.jsonl'):
                    continue
                fp = os.path.join(root, f)
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(fp))
                    recent_total += 1
                    if now - mtime < tau:
                        recent_new += 1
                except OSError:
                    pass
        if recent_total > 0:
            s4 = recent_new > 0 and recent_new < recent_total * 0.1  # <10% new = healthy restraint

    return {
        'S1_incompleteness': s1,
        'S2_counterexample': s2,
        'S3_dissent_space': s3,
        'S4_output_validity': s4,
        'active': sum([s1, s2, s3, s4])
    }


# ─── L1: Quorum-Fast — Convergence Detection ───

def quorum_check(signals: dict, methods: list = None):
    """Check convergence across multiple signal methods. Divergence = healthy."""
    if methods is None:
        # Single method: just report the active count
        return {
            'active_count': signals['active'],
            'quorum': signals['active'] / 4.0,
            'status': 'DIVERGENT (healthy)' if 1 <= signals['active'] <= 3 else 'CONVERGENT'
        }

    # Multi-method: check agreement
    results = {}
    for method in methods:
        try:
            method_signals = collect_delta_signals(method.get('tau', 3))
            results[method['name']] = method_signals['active']
        except Exception:
            results[method['name']] = 0

    if not results:
        return {'status': 'NO_DATA'}

    values = list(results.values())
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values) if values else 0

    return {
        'methods': results,
        'mean_active': round(mean, 2),
        'variance': round(variance, 2),
        'quorum': round(mean / 4.0, 3),
        'status': 'DIVERGENT (healthy)' if variance > 0.5 else 'CONVERGENT'
    }


# ─── L2: Molting Trigger ───

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {
        'history': [],
        'molting_alerts': 0,
        'created': datetime.now().isoformat()
    }


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def check_molting(state, active_count, quorum_val):
    """Δ proxy = active_count/4 * (1 - |quorum - 0.5| * 2). Max at quorum=0.5."""
    delta_proxy = (active_count / 4.0) * (1.0 - abs(quorum_val - 0.5) * 2.0)

    history = state['history']
    alert = False
    cause = None

    # Need at least 2 prior cycles to detect 2-consecutive-drop
    if len(history) >= 2:
        prev1 = history[-1].get('delta_proxy', 0)
        prev2 = history[-2].get('delta_proxy', 0)
        if delta_proxy < prev1 < prev2 and delta_proxy < 0.3:
            alert = True
            cause = f'Δ↓2-cycle: {prev2:.3f}→{prev1:.3f}→{delta_proxy:.3f} (<0.3)'
            state['molting_alerts'] += 1

    return {'molting_alert': alert, 'cause': cause, 'delta_proxy': round(delta_proxy, 4),
            'molting_alert_count': state['molting_alerts']}


def run_protocol(output_json=False):
    now = datetime.now()
    signals = collect_delta_signals()
    quorum = quorum_check(signals)
    state = load_state()
    molt = check_molting(state, signals['active'], quorum['quorum'])

    state['history'].append({
        'ts': now.isoformat(),
        'active': signals['active'],
        'quorum': quorum['quorum'],
        'delta_proxy': molt['delta_proxy'],
        'signals': {k: v for k, v in signals.items() if k.startswith('S')}
    })
    state['history'] = state['history'][-30:]
    save_state(state)

    status = 'HEALTHY'
    if molt['molting_alert']:
        status = 'MOLTING_ALERT'
    elif quorum['quorum'] > 0.9 or quorum['quorum'] < 0.1:
        status = 'CONVERGENT'

    result = {
        'timestamp': now.strftime('%Y-%m-%d %H:%M'),
        'L0_signals': {k: v for k, v in signals.items() if k.startswith('S')},
        'L0_active': signals['active'],
        'L1_quorum': quorum,
        'L2_molting': molt,
        'history_cycles': len(state['history']),
        'protocol_status': status
    }

    if output_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print('=== MSS Δ Detection Protocol v2.0 ===')
        print(f'Time: {result["timestamp"]}')
        for k, v in signals.items():
            if k.startswith('S'):
                label = "ACTIVE" if v else "INACTIVE"
                print(f"  {k}: {label}")
        active = signals['active']
        qval = quorum['quorum']
        qstatus = quorum['status']
        dproxy = molt['delta_proxy']
        malert = molt['molting_alert']
        mcause = molt['cause']
        hist_len = len(state['history'])
        alerts = state['molting_alerts']
        
        print(f'  Total: {active}/4')
        print(f'  L1 Quorum: {qval} ({qstatus})')
        if malert:
            print(f'\n  ⚠️  MOLTING ALERT: {mcause}')
        else:
            print(f'  L2 Molting: clear (Δ={dproxy})')
        print(f'  Status: {status} | History: {hist_len} cycles | Alerts: {alerts}')

    return 0 if not molt['molting_alert'] else 1


def main():
    import argparse
    p = argparse.ArgumentParser(description='MSS Δ Detection Protocol v2.0')
    p.add_argument('--json', action='store_true', help='JSON output')
    p.add_argument('--reset', action='store_true', help='Reset state')
    args = p.parse_args()
    if args.reset and os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        print('State reset.')
    sys.exit(run_protocol(output_json=args.json))


if __name__ == '__main__':
    main()
