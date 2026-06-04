# ENG-2026-002: How to Add a New Check to verify_all.py

## Architecture

```
verify_all.py
  ├── check_z3_kernel()      → test_mss_z3_kernel.py  (71 tests)
  ├── check_vdp_self_scan()  → vdp_scan.py            (6 rules)
  ├── check_kb_health()      → daily_audit.py (KB)    (JSON parse)
  ├── check_vdp_vaccine()    → vdp_vaccine.py          (audit)
  ├── check_api_health()     → http://localhost:53000  (5 endpoints)
  ├── check_blackhole()      → blackhole_monitor.py    (4D)
  └── check_git_status()     → git log -1              (HEAD)
```

## Adding a New Check

### Step 1: Create the check function

```python
def check_my_new_feature():
    """Check description — what does this verify?"""
    try:
        # ... run your verification ...
        return {"name": "My Feature", "status": "OK", "details": "..."}
    except Exception as e:
        return {"name": "My Feature", "status": "FAIL", "error": str(e)}
```

### Step 2: Add to the checks list

```python
CHECKS.append(check_my_new_feature)
```

### Step 3: Update status.py quick commands

```python
# In status.py, add:
print('python my_check.py    — my feature check')
```

## Example: Adding Link Validator

```python
def check_link_health():
    """Monthly external link health"""
    try:
        report = json.load(open(r'E:\QClaw-Data\reports\network\link_health_2026-06.json'))
        health = report.get('health_pct', 1.0)
        status = "OK" if health >= 0.6 else "WARN"
        return {"name": "Link Health", "status": status, "details": f"{health:.0%}"}
    except FileNotFoundError:
        return {"name": "Link Health", "status": "WARN", "details": "No report yet"}
```

## Failure Handling

- `OK` → green, no action
- `WARN` → yellow, investigate at convenience
- `FAIL` → red, immediate fix required
- Exception → treated as FAIL
