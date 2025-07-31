#!/usr/bin/env python3
"""
Script de inicio para el sistema Aura
Inicia todos los servicios necesarios
"""

import subprocess
import sys
import os
import time
import signal
from pathlib import Path

# Obtener directorio del proyecto
PROJECT_DIR = Path(__file__).parent
SRC_DIR = PROJECT_DIR / "src"
FRONTEND_DIR = PROJECT_DIR / "frontend"

# Lista de procesos iniciados
processes = []

def signal_handler(sig, frame):
    """Maneja la señal de interrupción para cerrar todos los procesos"""
    print("\n🛑 Cerrando sistema Aura...")
    
    for process in processes:
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        except:
            pass
    
    print("👋 Sistema Aura cerrado")
    sys.exit(0)

def start_backend_services():
    """Inicia los servicios del backend"""
    print("🚀 Iniciando servicios del backend...")
    
    # 1. Iniciar API de estadísticas del sistema
    print("📊 Iniciando API de estadísticas del sistema...")
    stats_api = subprocess.Popen(
        [sys.executable, "system_stats_api.py"],
        cwd=SRC_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT
    )
    processes.append(stats_api)
    
    # Esperar un poco para que la API inicie
    time.sleep(2)
    
    # 2. Iniciar servidor WebSocket único
    print("🌐 Iniciando servidor WebSocket...")
    websocket_server = subprocess.Popen(
        [sys.executable, "websocket_server.py"],
        cwd=SRC_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT
    )
    processes.append(websocket_server)
    
    # Esperar un poco para que el WebSocket inicie
    time.sleep(3)
    
    return stats_api, websocket_server

def start_frontend():
    """Inicia el frontend"""
    print("🎨 Iniciando interfaz frontend...")
    
    # Verificar si existe package.json
    if not (FRONTEND_DIR / "package.json").exists():
        print("❌ Error: No se encontró package.json en el frontend")
        return None
    
    # Iniciar el frontend con npm run dev
    frontend = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=FRONTEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT
    )
    processes.append(frontend)
    
    return frontend

def check_requirements():
    """Verifica que los requisitos estén instalados"""
    print("🔍 Verificando requisitos...")
    
    # Verificar Python dependencies
    try:
        import websockets
        import vosk
        import psutil
        import fastapi
    except ImportError as e:
        print(f"❌ Error: Dependencia de Python faltante: {e}")
        print("💡 Ejecuta: pip install -r requirements.txt")
        return False
    
    # Verificar modelos de Vosk
    voice_dir = PROJECT_DIR / "voice"
    spanish_model = voice_dir / "vosk-model-es-0.42"
    english_model = voice_dir / "vosk-model-en-us-0.42-gigaspeech"
    
    if not spanish_model.exists() and not english_model.exists():
        print("❌ Error: No se encontraron modelos de Vosk")
        print("💡 Descarga al menos un modelo de Vosk y colócalo en la carpeta 'voice/'")
        return False
    
    print("✅ Requisitos verificados")
    return True

def main():
    """Función principal"""
    print("🌟 SISTEMA AURA - Asistente de IA con Voz")
    print("=" * 50)
    
    # Configurar manejo de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Verificar requisitos
    if not check_requirements():
        sys.exit(1)
    
    try:
        # Iniciar servicios del backend
        stats_api, websocket_server = start_backend_services()
        
        # Iniciar frontend
        frontend = start_frontend()
        
        print("\n✅ Sistema Aura iniciado correctamente!")
        print("=" * 50)
        print("📊 API Estadísticas: http://localhost:8000")
        print("🌐 WebSocket Server: ws://localhost:8765")
        print("🎨 Frontend: http://localhost:5173")
        print("\n💡 Presiona Ctrl+C para cerrar el sistema")
        print("=" * 50)
        
        # Mantener el script corriendo
        while True:
            time.sleep(5)  # Verificar cada 5 segundos
            
            # Verificar si algún proceso ha terminado inesperadamente
            dead_processes = []
            for i, process in enumerate(processes):
                if process.poll() is not None:
                    return_code = process.returncode
                    if return_code != 0:
                        print(f"⚠️  Proceso {i} ha terminado con código {return_code}")
                        dead_processes.append(i)
                    
            # Si hay procesos muertos, intentar reiniciar servicios críticos
            if dead_processes:
                print("🔄 Intentando reiniciar servicios...")
                # Solo mostrar el error, no reiniciar automáticamente
                for i in dead_processes:
                    if i == 0:
                        print("💔 API de estadísticas falló")
                    elif i == 1:
                        print("💔 Servidor WebSocket falló")
                    elif i == 2:
                        print("💔 Frontend falló")
                
                # Esperar un poco antes de continuar verificando
                time.sleep(10)
    
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        signal_handler(None, None)

if __name__ == "__main__":
    main()