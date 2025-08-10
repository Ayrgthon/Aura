from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psutil
import subprocess
import os
import logging
from typing import Optional, Dict, Union
from fastapi.responses import JSONResponse

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='backend_stats.log'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Permitir CORS para el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_cpu_usage() -> Optional[float]:
    """Obtiene el uso de CPU de forma segura"""
    try:
        # Usar intervalo más corto para no bloquear
        return psutil.cpu_percent(interval=0.1)
    except Exception as e:
        logger.error(f"Error obteniendo uso de CPU: {e}")
        return None

def get_ram_usage() -> Optional[float]:
    """Obtiene el uso de RAM de forma segura"""
    try:
        mem = psutil.virtual_memory()
        return mem.percent
    except Exception as e:
        logger.error(f"Error obteniendo uso de RAM: {e}")
        return None

def get_ssd_usage() -> Optional[float]:
    """Obtiene el uso de disco de forma segura"""
    try:
        disk = psutil.disk_usage('/')
        return disk.percent
    except Exception as e:
        logger.error(f"Error obteniendo uso de disco: {e}")
        return None

def get_gpu_usage() -> Optional[float]:
    """Obtiene el uso de GPU de forma segura"""
    try:
        # Método 1: ROCm-smi
        try:
            output = subprocess.check_output(
                ["rocm-smi", "--showuse"], 
                stderr=subprocess.DEVNULL, 
                timeout=1
            ).decode()
            
            for line in output.splitlines():
                if "GPU use" in line and ":" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        value_part = parts[-1].strip()
                        import re
                        match = re.search(r'(\d+(?:\.\d+)?)', value_part)
                        if match:
                            return float(match.group(1))
                elif "%" in line and ("GPU" in line or "card" in line):
                    match = re.search(r'(\d+(?:\.\d+)?)%', line)
                    if match:
                        return float(match.group(1))
        except Exception as e:
            logger.debug(f"ROCm-smi falló: {e}")
        
        # Método 2: amdgpu_top
        try:
            output = subprocess.check_output(
                ["amdgpu_top", "-J", "-n", "1"], 
                stderr=subprocess.DEVNULL, 
                timeout=1
            ).decode()
            import json
            data = json.loads(output)
            if "gpu_activity" in data:
                return float(data["gpu_activity"])
        except Exception as e:
            logger.debug(f"amdgpu_top falló: {e}")
        
        # Método 3: Archivos del sistema
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
                    with open(path, "r") as f:
                        lines = f.readlines()
                        max_freq = 0
                        current_freq = 0
                        
                        for line in lines:
                            line = line.strip()
                            if "Mhz" in line:
                                freq = int(line.split(":")[1].strip().replace("Mhz", "").replace("*", "").strip())
                                max_freq = max(max_freq, freq)
                                if "*" in line:
                                    current_freq = freq
                        
                        if max_freq > 0 and current_freq > 0:
                            usage = (current_freq / max_freq) * 100
                            return min(usage, 100.0)
            except Exception as e:
                logger.debug(f"Error leyendo {path}: {e}")
                continue
        
        # Método 4: radeontop
        try:
            output = subprocess.check_output(
                ["radeontop", "-d", "-", "-l", "1"], 
                stderr=subprocess.DEVNULL, 
                timeout=1
            ).decode()
            
            for line in output.splitlines():
                if "gpu" in line.lower():
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if "gpu" in p.lower() and i + 1 < len(parts):
                            val = parts[i+1].replace('%','').replace(',','.')
                            try:
                                return float(val)
                            except ValueError:
                                continue
        except Exception as e:
            logger.debug(f"radeontop falló: {e}")
        
        # Método 5: Detección de Ollama
        try:
            output = subprocess.check_output(
                ["ps", "aux"], 
                stderr=subprocess.DEVNULL,
                timeout=1
            ).decode()
            
            if any("ollama" in line.lower() and ("serve" in line or "run" in line) 
                  for line in output.splitlines()):
                return 15.0  # Valor conservador cuando Ollama está activo
        except Exception as e:
            logger.debug(f"Detección de Ollama falló: {e}")
        
        return None
        
    except Exception as e:
        logger.error(f"Error general obteniendo uso de GPU: {e}")
        return None

@app.get("/system-stats")
async def system_stats() -> Dict[str, Optional[float]]:
    """Endpoint principal que devuelve todas las estadísticas del sistema"""
    try:
        stats = {
            "cpu": get_cpu_usage(),
            "ram": get_ram_usage(),
            "ssd": get_ssd_usage(),
            "gpu": get_gpu_usage()
        }
        
        # Log si algún valor es None
        none_values = [k for k, v in stats.items() if v is None]
        if none_values:
            logger.warning(f"Valores None en stats: {none_values}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error general en /system-stats: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Error interno obteniendo estadísticas",
                "detail": str(e)
            }
        )

@app.post("/shutdown")
def shutdown_system():
    """Apaga todos los servicios del sistema Aura"""
    try:
        import signal
        
        # Matar procesos específicos de Aura (excepto esta API para poder recibir comandos de encendido)
        processes_to_kill = [
            "websocket_server_simple.py",
            "websocket_server.py",
            "aura_websocket_server.py",
            "integration_optimized.py",
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
                    ["pgrep", "-f", f"python {process_name}"], 
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
                # Iniciar nuevo WebSocket server usando el Python del entorno virtual
                venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "bin", "python")
                subprocess.Popen(
                    [venv_python, "aura_websocket_server.py"],
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
            "services": ["aura_websocket_server.py"]
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error iniciando sistema: {str(e)}"
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Iniciando API de estadísticas del sistema...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 
