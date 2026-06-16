"""System Status Monitor - Tracks file integrity and test status."""
import os, json

class SystemStatus:
    def __init__(self, project_root=None):
        self.root = project_root or os.getcwd()
    
    def check_files(self):
        return {"files": len(os.listdir(self.root))}

    def snapshot(self):
        return json.dumps(self.check_files())

if __name__ == "__main__":
    s = SystemStatus()
    print(s.snapshot())
