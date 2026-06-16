from mssclaw.core.watchdog import GatewayWatchdog, CHILD_FLAGS
import json

w = GatewayWatchdog("python -c \"print(42)\"")
print(f"All flags: 0x{CHILD_FLAGS:08X}")
ok = w.launch()
print(f"Launch: {ok}, PID={w.pid}")
if ok and w.process:
    w.process.wait(timeout=5)
    print(f"Exit code: {w.process.returncode}")
print(json.dumps(w.status(), indent=2))
