# Publish v0.2.1 to PyPI
# Usage: set PYPI_TOKEN=your-token && py -3.11 publish_v021.py
import os, subprocess, sys

token = os.environ.get("PYPI_TOKEN", "")
if not token:
    token = input("PyPI token: ").strip()
    if not token:
        print("No token provided. Set PYPI_TOKEN env var or paste here.")
        sys.exit(1)

os.environ["TWINE_USERNAME"] = "__token__"
os.environ["TWINE_PASSWORD"] = token

subprocess.run([
    sys.executable, "-m", "twine", "upload",
    "mss_agent/dist/mss_agent-0.2.1-py3-none-any.whl",
    "mss_agent/dist/mss-agent-0.2.1.tar.gz",
], cwd=r"E:\AI_Workspace\MSS-AI\project", check=True)
print("Done! https://pypi.org/project/mss-agent/0.2.1/")
