#!/usr/bin/env python3
"""
Script de prueba para el nuevo websocket server
"""

import sys
import os

# Agregar paths necesarios
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'voice'))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'client'))

def test_imports():
    """Probar que todas las importaciones funcionen"""
    try:
        # Probar importaciones básicas
        print("🔍 Probando importaciones básicas...")
        import asyncio
        import json
        import logging
        import websockets
        print("✅ Importaciones básicas OK")
        
        # Probar importación de voice modules
        print("🔍 Probando módulos de voz...")
        try:
            from hear import SpeechToText
            from speak import TextToSpeech
            print("✅ Módulos de voz OK")
        except ImportError as e:
            print(f"⚠️ Módulos de voz no disponibles: {e}")
        
        # Probar importación del cliente Gemini
        print("🔍 Probando cliente Gemini...")
        try:
            from gemini_client import SimpleGeminiClient
            from config import get_mcp_servers_config
            print("✅ Cliente Gemini OK")
        except ImportError as e:
            print(f"❌ Cliente Gemini no disponible: {e}")
            return False
        
        # Probar WebRTC (opcional)
        print("🔍 Probando WebRTC...")
        try:
            import aiortc
            from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
            print("✅ WebRTC disponible")
        except ImportError as e:
            print(f"⚠️ WebRTC no disponible: {e}")
        
        # Probar importación del servidor
        print("🔍 Probando servidor principal...")
        from aura_websocket_server import AuraWebSocketServer, TTSBuffer, TTSQueueItem
        print("✅ Servidor principal OK")
        
        print("\n🎉 Todas las importaciones críticas funcionan correctamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba de importaciones: {e}")
        return False

def test_server_creation():
    """Probar que el servidor se puede crear"""
    try:
        print("🔍 Probando creación del servidor...")
        from aura_websocket_server import AuraWebSocketServer
        
        server = AuraWebSocketServer()
        print(f"✅ Servidor creado en {server.host}:{server.port}")
        
        # Verificar atributos básicos
        assert hasattr(server, 'clients')
        assert hasattr(server, 'voice_initialized')
        assert hasattr(server, 'aura_ready')
        print("✅ Atributos del servidor OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando servidor: {e}")
        return False

def test_tts_buffer():
    """Probar el buffer TTS"""
    try:
        print("🔍 Probando buffer TTS...")
        from aura_websocket_server import TTSBuffer, TTSQueueItem
        
        # Mock TTS para pruebas
        class MockTTS:
            def speak(self, text):
                print(f"Mock TTS: {text}")
        
        mock_tts = MockTTS()
        buffer = TTSBuffer(mock_tts)
        
        assert hasattr(buffer, 'queue')
        assert hasattr(buffer, 'is_playing')
        print("✅ Buffer TTS OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en buffer TTS: {e}")
        return False

async def test_basic_functionality():
    """Probar funcionalidad básica async"""
    try:
        print("🔍 Probando funcionalidad async...")
        from aura_websocket_server import AuraWebSocketServer
        
        server = AuraWebSocketServer()
        
        # Probar que los métodos básicos existen
        assert hasattr(server, 'register_client')
        assert hasattr(server, 'init_voice_system')
        assert hasattr(server, 'init_aura_client')
        print("✅ Métodos básicos OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en funcionalidad básica: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando pruebas del nuevo WebSocket server...\n")
    
    # Prueba 1: Importaciones
    if not test_imports():
        print("❌ Falló prueba de importaciones")
        sys.exit(1)
    
    # Prueba 2: Creación del servidor
    if not test_server_creation():
        print("❌ Falló prueba de creación del servidor")
        sys.exit(1)
    
    # Prueba 3: Buffer TTS
    if not test_tts_buffer():
        print("❌ Falló prueba del buffer TTS")
        sys.exit(1)
    
    # Prueba 4: Funcionalidad async
    import asyncio
    if not asyncio.run(test_basic_functionality()):
        print("❌ Falló prueba de funcionalidad async")
        sys.exit(1)
    
    print("\n🎉 Todas las pruebas pasaron! El nuevo WebSocket server está listo.")
    print("\n📋 Próximos pasos:")
    print("1. Detener el servidor anterior si está ejecutándose")
    print("2. Ejecutar: python aura_websocket_server.py")
    print("3. Conectar desde el frontend y probar con reasoning")
    
    sys.exit(0)