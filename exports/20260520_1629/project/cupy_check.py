"""CuPy安装验证脚本"""
import sys

try:
    import cupy as cp
    print(f"CuPy version: {cp.__version__}")
    print(f"CUDA available: {cp.cuda.is_available()}")
    
    if cp.cuda.is_available():
        props = cp.cuda.runtime.getDeviceProperties(0)
        print(f"GPU: {props['name'].decode()}")
        
        # Basic test
        a = cp.ones((100, 100))
        s = cp.sum(a)
        print(f"Basic GPU test: OK (sum={float(s)})")
        
        # Matmul test
        import time
        a = cp.random.rand(1000, 1000)
        cp.cuda.Device(0).synchronize()
        t0 = time.time()
        c = cp.dot(a, a.T)
        cp.cuda.Device(0).synchronize()
        t1 = time.time()
        print(f"Matmul 1000x1000: {(t1-t0)*1000:.2f} ms")
        print("CUPY-001: FIXED")
    else:
        print("CUDA not available")
        print("CUPY-001: FAILED")
except Exception as e:
    print(f"Error: {e}")
    print("CUPY-001: FAILED")
