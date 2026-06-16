import zipfile, shutil, os

TOOLS = "tools"
ZFP = os.path.join(TOOLS, "nssm-2.24.zip")
EXT = os.path.join(TOOLS, "_ext")

os.makedirs(EXT, exist_ok=True)
with zipfile.ZipFile(ZFP, "r") as zf:
    zf.extractall(EXT)

for root, dirs, files in os.walk(EXT):
    for f in files:
        if f.lower() == "nssm.exe":
            src = os.path.join(root, f)
            dst = os.path.join(TOOLS, "nssm.exe")
            if "win64" in root.lower():
                shutil.copy2(src, dst)
                print(f"WIN64: {os.path.getsize(dst)} bytes")
            elif "win32" in root.lower():
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
                    print(f"WIN32: {os.path.getsize(dst)} bytes")

os.remove(ZFP)
shutil.rmtree(EXT, ignore_errors=True)

size = os.path.getsize(os.path.join(TOOLS, "nssm.exe"))
print(f"OK: tools/nssm.exe = {size} bytes")
