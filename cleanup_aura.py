#!/usr/bin/env python3
"""
Script de limpieza para procesos de Aura
Cierra procesos huérfanos que puedan estar ocupando puertos
"""

import os
import sys
import psutil
import subprocess
import time

def find_aura_processes():
    """Encuentra todos los procesos relacionados con Aura"""
    aura_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Buscar procesos de Python que ejecuten scripts de Aura
            if proc.info['name'] == 'python' or proc.info['name'] == 'python3':
                cmdline = proc.info['cmdline']
                if cmdline and any('aura' in arg.lower() or 'websocket_server' in arg.lower() for arg in cmdline):
                    aura_processes.append(proc)
            
            # Buscar procesos de Node.js que puedan ser del frontend
            elif proc.info['name'] == 'node':
                cmdline = proc.info['cmdline']
                if cmdline and any('stellar-voice-display' in arg.lower() for arg in cmdline):
                    aura_processes.append(proc)
            
            # Buscar procesos que usen el puerto 8765 (WebSocket)
            try:
                for conn in proc.connections(kind='inet'):
                    if hasattr(conn, 'laddr') and conn.laddr.port == 8765:
                        aura_processes.append(proc)
                        break
            except Exception:
                pass
                
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    return aura_processes

def kill_process_safely(proc, reason=""):
    """Mata un proceso de forma segura"""
    try:
        print(f"🔄 Cerrando proceso {proc.info['name']} (PID: {proc.info['pid']}) {reason}")
        
        # Intentar terminar suavemente
        proc.terminate()
        
        # Esperar hasta 3 segundos
        try:
            proc.wait(timeout=3)
            print(f"✅ Proceso {proc.info['name']} cerrado correctamente")
            return True
        except psutil.TimeoutExpired:
            # Si no responde, forzar cierre
            print(f"⚠️  Forzando cierre de {proc.info['name']}...")
            proc.kill()
            proc.wait()
            print(f"✅ Proceso {proc.info['name']} forzado a cerrar")
            return True
            
    except Exception as e:
        print(f"❌ Error cerrando proceso {proc.info['name']}: {e}")
        return False

def cleanup_aura():
    """Limpia todos los procesos de Aura"""
    print("🧹 Limpieza de procesos de Aura")
    print("=" * 40)
    
    # Encontrar procesos de Aura
    aura_processes = find_aura_processes()
    
    if not aura_processes:
        print("✅ No se encontraron procesos de Aura ejecutándose")
        return
    
    print(f"🔍 Encontrados {len(aura_processes)} procesos de Aura:")
    for proc in aura_processes:
        try:
            cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else 'N/A'
            print(f"  • PID {proc.info['pid']}: {proc.info['name']} - {cmdline}")
        except:
            print(f"  • PID {proc.info['pid']}: {proc.info['name']}")
    
    print("\n🛑 Cerrando procesos...")
    
    # Cerrar procesos
    closed_count = 0
    for proc in aura_processes:
        if kill_process_safely(proc):
            closed_count += 1
    
    print(f"\n✅ Cerrados {closed_count}/{len(aura_processes)} procesos")
    
    # Verificar si el puerto 8765 está libre
    print("\n🔍 Verificando puerto 8765...")
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 8765))
        sock.close()
        
        if result == 0:
            print("⚠️  El puerto 8765 aún está ocupado")
            print("💡 Puede que necesites reiniciar tu sistema o esperar unos minutos")
        else:
            print("✅ El puerto 8765 está libre")
    except Exception as e:
        print(f"⚠️  Error verificando puerto: {e}")

def main():
    """Función principal"""
    if len(sys.argv) > 1 and sys.argv[1] == '--force':
        # Modo forzado - no preguntar
        cleanup_aura()
    else:
        print("🧹 Limpieza de procesos de Aura")
        print("Este script cerrará todos los procesos de Aura que encuentre.")
        print("Esto incluye:")
        print("  • Servidor WebSocket (puerto 8765)")
        print("  • Frontend de voz")
        print("  • Cualquier proceso Python relacionado con Aura")
        print()
        
        response = input("¿Continuar? (s/n): ").strip().lower()
        if response in ['s', 'si', 'sí', 'y', 'yes']:
            cleanup_aura()
        else:
            print("❌ Operación cancelada")

if __name__ == "__main__":
    main() 