from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psutil
import subprocess
import os

app = FastAPI()

# Permitir CORS para el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_cpu_usage():
    return psutil.cpu_percent(interval=0.5)

def get_ram_usage():
    mem = psutil.virtual_memory()
    return mem.percent

def get_ssd_usage():
    disk = psutil.disk_usage('/')
    return disk.percent

def get_gpu_usage():
    # Intentar con radeontop (AMD)
    try:
        output = subprocess.check_output(
            ["radeontop", "-d", "-", "-l", "1"], stderr=subprocess.DEVNULL, timeout=2
        ).decode()
        for line in output.splitlines():
            if "gpu" in line:
                # Ejemplo: gpu  3.45% ...
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "gpu":
                        val = parts[i+1].replace('%','').replace(',','.')
                        return float(val)
        return None
    except Exception:
        # Alternativa: leer /sys/class/drm/card0/device/gpu_busy_percent
        try:
            with open("/sys/class/drm/card0/device/gpu_busy_percent") as f:
                return float(f.read().strip())
        except Exception:
            return None

@app.get("/system-stats")
def system_stats():
    cpu = get_cpu_usage()
    ram = get_ram_usage()
    ssd = get_ssd_usage()
    gpu = get_gpu_usage()
    return {
        "cpu": cpu,
        "ram": ram,
        "ssd": ssd,
        "gpu": gpu
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 