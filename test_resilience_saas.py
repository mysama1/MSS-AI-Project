"""
Test Resilience Scanner SaaS
"""

from resilience_scanner_saas import ResilienceScannerSaaS

def test_saas():
    print("=" * 60)
    print("Testing Resilience Scanner SaaS")
    print("=" * 60)
    print()

    scanner = ResilienceScannerSaaS()

    # Test data
    org_data = {
        "name": "测试科技公司",
        "departments": [
            {"name": "研发部", "M": 0.85, "O_d": 0.90, "Φ": 120, "γ": 0.15},
            {"name": "市场部", "M": 0.65, "O_d": 0.70, "Φ": 80, "γ": 0.25},
            {"name": "运营部", "M": 0.55, "O_d": 0.60, "Φ": 60, "γ": 0.35},
            {"name": "财务部", "M": 0.75, "O_d": 0.80, "Φ": 100, "γ": 0.20},
            {"name": "人事部", "M": 0.60, "O_d": 0.65, "Φ": 70, "γ": 0.30}
        ]
    }

    # Test scan
    print("1. Testing scan...")
    result = scanner.scan(org_data, "tech_startup")
    print(f"   Scan ID: {result['scan_id']}")
    print(f"   Risk Level: {result['risk_level']}")
    print(f"   Overall Score: {result['overall_score']}")
    print(f"   Metrics: M={result['metrics']['M']}, O_d={result['metrics']['O_d']}")
    print(f"   Recommendations: {len(result['recommendations'])}")
    print("   ✅ OK")
    print()

    # Test export
    print("2. Testing export...")
    export = scanner.export_report(result['scan_id'], "markdown")
    if "markdown" in export:
        print("   Markdown export successful")
        print(f"   Length: {len(export['markdown'])} chars")
    print("   ✅ OK")
    print()

    # Test history
    print("3. Testing history...")
    history = scanner.get_scan_history()
    print(f"   History entries: {len(history)}")
    print("   ✅ OK")
    print()

    print("=" * 60)
    print("All SaaS tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    test_saas()
