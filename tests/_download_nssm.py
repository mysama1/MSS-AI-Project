"""Download NSSM and extract nssm.exe"""
import urllib.request, ssl, zipfile, shutil, os

TOOLS = "tools"
os.makedirs(TOOLS, exist_ok=True)

URL = "https://nssm.cc/release/nssm-2.24.zip"
ZIP_PATH = os.path.join(TOOLS, "nssm.zip")
EXTRACT_DIR = os.path.join(TOOLS, "_nssm_extract")

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

print(f"Downloading {URL} ...")
req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, context=ctx, timeout=120) as resp:
    data = resp.read()
    with open(ZIP_PATH, "wb") as f:
        f.write(data)
print(f"Downloaded: {len(data)} bytes")

os.makedirs(EXTRACT_DIR, exist_ok=True)
with zipfile.ZipFile(ZIP_PATH, "r") as zf:
    zf.extractall(EXTRACT_DIR)

# Find nssm.exe, prefer 64-bit
found_win64 = None
found_win32 = None
for root, dirs, files in os.walk(EXTRACT_DIR):
    for f in files:
        if f.lower() == "nssm.exe":
            src = os.path.join(root, f)
            if "win64" in root.lower():
                found_win64 = src
            elif "win32" in root.lower():
                found_win32 = src

src = found_win64 or found_win32
dst = os.path.join(TOOLS, "nssm.exe")
if src:
    shutil.copy2(src, dst)
    print(f"Installed: {dst} ({os.path.getsize(dst)} bytes)")

# Cleanup
os.remove(ZIP_PATH)
shutil.rmtree(EXTRACT_DIR, ignore_errors=True)

# Verify
size = os.path.getsize(dst)
print(f"Final size: {size} bytes")
assert 300000 < size < 600000, f"Unexpected size: {size}"
print("OK")
