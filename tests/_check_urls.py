import urllib.request, ssl, sys

urls = [
    "https://nssm.cc/release/nssm-2.24.zip",
    "https://nssm.cc/builds/nssm-2.24-101-g897c7ad.zip",
    "https://github.com/fightroad/nssm/releases/download/v3.0.0/nssm-3.0.0.zip",
]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

for url in urls:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            print(f"OK  {resp.status}  {url}")
            size = resp.headers.get("Content-Length", "?")
            print(f"    size={size}")
    except Exception as e:
        print(f"FAIL  {url}")
        print(f"      {type(e).__name__}: {e}")
    print()
