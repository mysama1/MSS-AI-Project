import zipfile, shutil, os

TOOLS = "tools"
ZFP = os.path.join(TOOLS, "nssm-101.zip")
EXT = os.path.join(TOOLS, "_ext")
DST = os.path.join(TOOLS, "nssm.exe")

os.makedirs(EXT, exist_ok=True)
with zipfile.ZipFile(ZFP, "r") as zf:
    zf.extractall(EXT)

for root, dirs, files in os.walk(EXT):
    for f in files:
        if f.lower() == "nssm.exe":
            src = os.path.join(root, f)
            if "win64" in root.lower():
                shutil.copy2(src, DST)
                print(f"WIN64 installed: {os.path.getsize(DST)} bytes")
            elif "win32" in root.lower() and not os.path.exists(DST):
                shutil.copy2(src, DST)
                print(f"WIN32 installed: {os.path.getsize(DST)} bytes")

os.remove(ZFP)
shutil.rmtree(EXT, ignore_errors=True)

# Verify
import subprocess
result = subprocess.run([DST], capture_output=True, text=True, timeout=5)
print(f"Version info: {result.stdout[:200]}")
print(f"NSSM ready: {os.path.getsize(DST)} bytes")
