#!/usr/bin/env python3
"""Monthly external link validator — implements H480 network fallback routing."""
import json, os, time, urllib.request, urllib.error, sys
from datetime import datetime

REPORT_DIR = r'E:\QClaw-Data\reports\network'
LINK_REGISTRY = r'E:\QClaw-Data\config\external_links.json'

def init_registry():
    """Create default link registry if none exists."""
    if os.path.exists(LINK_REGISTRY):
        return
    os.makedirs(os.path.dirname(LINK_REGISTRY), exist_ok=True)
    template = {
        "links": [
            {"id": "zenodo_mss_collatz", "primary": "https://zenodo.org/records/20537026",
             "mirrors": ["https://doi.org/10.5281/zenodo.20537026"], "region": "overseas_high_risk",
             "accessed": 0, "last_ok": None, "consecutive_failures": 0},
            {"id": "arxiv_collatz", "primary": "https://arxiv.org",
             "mirrors": [], "region": "overseas_high_risk",
             "accessed": 0, "last_ok": None, "consecutive_failures": 0},
            {"id": "github_mss_repo", "primary": "https://github.com/mysama1/MSS-AI-Project",
             "mirrors": ["https://gitcode.com/mysama1/MSS-AI-Project"],
             "region": "overseas_high_risk",
             "accessed": 0, "last_ok": None, "consecutive_failures": 0},
        ],
        "settings": {"timeout": 10, "consecutive_threshold": 2, "monthly_health_threshold": 0.6}
    }
    with open(LINK_REGISTRY, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2)

def check_url(url, timeout=10):
    try:
        r = urllib.request.urlopen(url, timeout=timeout)
        return {"ok": True, "code": r.status, "url": url}
    except Exception as e:
        return {"ok": False, "error": str(e)[:100], "url": url}

def main():
    init_registry()
    with open(LINK_REGISTRY, 'r', encoding='utf-8') as f:
        registry = json.load(f)

    timeout = registry.get("settings", {}).get("timeout", 10)
    threshold = registry.get("settings", {}).get("consecutive_threshold", 2)
    health_pct = registry.get("settings", {}).get("monthly_health_threshold", 0.6)

    results = []
    for link in registry["links"]:
        # Check primary
        r = check_url(link["primary"], timeout)
        if r["ok"]:
            link["consecutive_failures"] = 0
            link["last_ok"] = datetime.now().isoformat()
            route = "primary"
        else:
            # Try mirrors
            route = None
            for mirror in link.get("mirrors", []):
                m = check_url(mirror, timeout)
                if m["ok"]:
                    route = f"mirror({m['url']})"
                    link["last_ok"] = datetime.now().isoformat()
                    break
            if route is None:
                link["consecutive_failures"] += 1
                route = "FAILED"

        link["accessed"] = link.get("accessed", 0) + 1
        results.append({"id": link["id"], "route": route, "consecutive_failures": link["consecutive_failures"]})

    # Write back updated registry
    with open(LINK_REGISTRY, 'w', encoding='utf-8') as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    # Generate report
    os.makedirs(REPORT_DIR, exist_ok=True)
    report_path = os.path.join(REPORT_DIR, f"link_health_{datetime.now().strftime('%Y-%m')}.json")
    total = len(results)
    ok = sum(1 for r in results if r["route"] != "FAILED")
    failing = sum(1 for r in results if r["consecutive_failures"] >= threshold)

    report = {
        "date": datetime.now().isoformat(),
        "total": total, "ok": ok, "failing": failing,
        "health_pct": ok / total if total > 0 else 1.0,
        "action_needed": failing > 0 or (ok / total < health_pct),
        "results": results
    }

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Link Health Check: {ok}/{total} reachable")
    if failing:
        for r in results:
            if r["consecutive_failures"] >= threshold:
                print(f"  ⚠ {r['id']}: {r['consecutive_failures']} consecutive failures → trigger fallback")

    return 1 if failing > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
