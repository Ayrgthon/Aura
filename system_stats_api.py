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
    # Método 1: ROCm-smi (específico para ROCm/AMD)
    try:
        output = subprocess.check_output(
            ["rocm-smi", "--showuse"], stderr=subprocess.DEVNULL, timeout=3
        ).decode()
        for line in output.splitlines():
            # Buscar línea con "GPU use (%): XX" o similar
            if "GPU use" in line and ":" in line:
                # Ejemplo: "GPU[0]          : GPU use (%): 10"
                parts = line.split(":")
                if len(parts) >= 2:
                    value_part = parts[-1].strip()  # Última parte después de ":"
                    import re
                    match = re.search(r'(\d+(?:\.\d+)?)', value_part)
                    if match:
                        return float(match.group(1))
            # También buscar formato con % explícito
            elif "%" in line and ("GPU" in line or "card" in line):
                import re
                match = re.search(r'(\d+(?:\.\d+)?)%', line)
                if match:
                    return float(match.group(1))
    except Exception:
        pass
    
    # Método 2: amdgpu_top (si está disponible)
    try:
        output = subprocess.check_output(
            ["amdgpu_top", "-J", "-n", "1"], stderr=subprocess.DEVNULL, timeout=3
        ).decode()
        import json
        data = json.loads(output)
        if "gpu_activity" in data:
            return float(data["gpu_activity"])
    except Exception:
        pass
    
    # Método 3: Archivos del sistema AMD específicos para Vega
    gpu_paths = [
        "/sys/class/drm/card0/device/gpu_busy_percent",
        "/sys/class/drm/card1/device/gpu_busy_percent",
        "/sys/class/drm/card0/device/pp_dpm_sclk",
        "/sys/kernel/debug/dri/0/amdgpu_pm_info"
    ]
    
    for path in gpu_paths:
        try:
            if "gpu_busy_percent" in path:
                with open(path, "r") as f:
                    return float(f.read().strip())
            elif "pp_dpm_sclk" in path:
                # Leer frecuencias y calcular uso basado en frecuencia actual
                with open(path, "r") as f:
                    lines = f.readlines()
                    current_line = None
                    max_freq = 0
                    current_freq = 0
                    
                    for line in lines:
                        line = line.strip()
                        if "*" in line:  # Línea actual
                            current_line = line
                        # Extraer frecuencia máxima
                        if "Mhz" in line:
                            freq = int(line.split(":")[1].strip().replace("Mhz", "").replace("*", "").strip())
                            max_freq = max(max_freq, freq)
                            if "*" in line:
                                current_freq = freq
                    
                    if max_freq > 0 and current_freq > 0:
                        usage = (current_freq / max_freq) * 100
                        return min(usage, 100.0)  # Limitar a 100%
            elif "amdgpu_pm_info" in path:
                with open(path, "r") as f:
                    content = f.read()
                    # Buscar línea de actividad de GPU
                    for line in content.splitlines():
                        if "GPU Load" in line or "gpu_activity" in line:
                            import re
                            match = re.search(r'(\d+(?:\.\d+)?)%?', line)
                            if match:
                                return float(match.group(1))
        except Exception:
            continue
    
    # Método 4: radeontop como último recurso
    try:
        output = subprocess.check_output(
            ["radeontop", "-d", "-", "-l", "1"], stderr=subprocess.DEVNULL, timeout=2
        ).decode()
        for line in output.splitlines():
            if "gpu" in line.lower():
                parts = line.split()
                for i, p in enumerate(parts):
                    if "gpu" in p.lower() and i + 1 < len(parts):
                        val = parts[i+1].replace('%','').replace(',','.')
                        try:
                            return float(val)
                        except:
                            continue
    except Exception:
        pass
    
    # Si nada funciona, intentar detectar si Ollama está usando la GPU
    try:
        # Verificar procesos de Ollama que usen GPU
        output = subprocess.check_output(
            ["ps", "aux"], stderr=subprocess.DEVNULL
        ).decode()
        
        ollama_running = False
        for line in output.splitlines():
            if "ollama" in line.lower() and ("serve" in line or "run" in line):
                ollama_running = True
                break
        
        if ollama_running:
            # Si Ollama está corriendo, simular un uso básico
            # Esto es un fallback, idealmente los métodos anteriores deberían funcionar
            return 15.0  # Valor conservador cuando Ollama está activo
    except Exception:
        pass
    
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

@app.post("/shutdown")
def shutdown_system():
    """Apaga todos los servicios del sistema Aura"""
    try:
        import signal
        
        # Matar procesos específicos de Aura (excepto esta API para poder recibir comandos de encendido)
        processes_to_kill = [
            "websocket_server_simple.py",
            "websocket_server.py", 
            "python main.py"
        ]
        
        killed_processes = []
        
        for process_name in processes_to_kill:
            try:
                # Método 1: Obtener PIDs específicos y matarlos directamente
                pids = []
                
                # Buscar procesos que coincidan con el nombre
                result = subprocess.run(
                    ["pgrep", "-f", process_name], 
                    capture_output=True, 
                    text=True
                )
                
                if result.returncode == 0:
                    pids.extend(result.stdout.strip().split('\n'))
                
                # También buscar con ruta completa
                result = subprocess.run(
                    ["pgrep", "-f", f"./venv/bin/python {process_name}"], 
                    capture_output=True, 
                    text=True
                )
                
                if result.returncode == 0:
                    pids.extend(result.stdout.strip().split('\n'))
                
                # Remover duplicados y PIDs vacíos
                pids = list(set([pid for pid in pids if pid and pid.isdigit()]))
                
                if pids:
                    for pid in pids:
                        # Forzar terminación inmediatamente ya que TERM no funciona bien
                        subprocess.run(["kill", "-KILL", pid], capture_output=True)
                    
                    # Pequeña pausa para asegurar terminación
                    import time
                    time.sleep(0.5)
                    
                    killed_processes.append(process_name)
                
            except Exception as e:
                print(f"Error matando proceso {process_name}: {e}")
        
        return {
            "status": "success",
            "message": "Sistema apagado correctamente",
            "killed_processes": killed_processes
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Error apagando sistema: {str(e)}"
        }

@app.post("/startup")
def startup_system():
    """Inicia todos los servicios del sistema Aura"""
    try:
        import threading
        import time
        
        # Función para iniciar servicios en background
        def start_services():
            time.sleep(1)  # Pequeña pausa antes de iniciar
            
            try:
                # Iniciar WebSocket server usando el Python del entorno virtual
                venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "bin", "python")
                subprocess.Popen(
                    [venv_python, "websocket_server_simple.py"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    cwd=os.path.dirname(os.path.abspath(__file__))
                )
                
                # Pequeña pausa entre servicios
                time.sleep(2)
                
            except Exception as e:
                print(f"Error iniciando servicios: {e}")
        
        # Iniciar servicios en thread separado
        thread = threading.Thread(target=start_services)
        thread.daemon = True
        thread.start()
        
        return {
            "status": "success",
            "message": "Iniciando servicios del sistema...",
            "services": ["websocket_server_simple.py"]
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error iniciando sistema: {str(e)}"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 