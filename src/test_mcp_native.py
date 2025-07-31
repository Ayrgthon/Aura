#!/usr/bin/env python3
"""
Script de prueba para verificar la funcionalidad MCP nativa
"""

import asyncio
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

async def test_mcp_native():
    """Test básico del cliente MCP nativo"""
    
    print("🧪 Iniciando pruebas del cliente MCP nativo")
    print("=" * 50)
    
    try:
        # Importar cliente MCP nativo
        from mcp_client_native import NativeMCPClient
        print("✅ Cliente MCP nativo importado correctamente")
        
        # Crear cliente
        client = NativeMCPClient()
        print("✅ Cliente MCP instanciado")
        
        # Configuración de prueba (filesystem básico)
        home_dir = os.path.expanduser("~")
        test_config = {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", home_dir],
                "transport": "stdio"
            }
        }
        
        print("🔧 Intentando configurar servidor MCP de prueba...")
        success = await client.setup_servers(test_config)
        
        if success:
            print("✅ Servidor MCP configurado exitosamente")
            print(f"📊 Herramientas disponibles: {len(client.tools)}")
            
            for tool in client.tools:
                print(f"  - {tool.name}: {tool.description}")
            
            # Intentar obtener herramientas para Gemini
            gemini_tools = client.get_tools_for_gemini()
            print(f"🤖 Herramientas para Gemini: {len(gemini_tools)}")
            
        else:
            print("❌ No se pudo configurar el servidor MCP")
            print("💡 Asegúrate de tener Node.js y npm instalados")
            print("💡 Ejecuta: npm install -g @modelcontextprotocol/server-filesystem")
        
        # Limpiar recursos
        await client.cleanup()
        print("🧹 Recursos limpiados")
        
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        print("💡 Instala MCP SDK con: pip install mcp")
        
    except Exception as e:
        print(f"❌ Error en prueba: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🏁 Pruebas completadas")

async def test_gemini_native():
    """Test básico del cliente Gemini nativo"""
    
    print("\n🧪 Iniciando pruebas del cliente Gemini nativo")
    print("=" * 50)
    
    try:
        # Verificar API key
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("❌ GOOGLE_API_KEY no encontrada")
            print("💡 Configura tu API key en el archivo .env")
            return
        
        # Importar cliente Gemini
        from gemini_client import GeminiClient, Message
        print("✅ Cliente Gemini nativo importado correctamente")
        
        # Crear cliente
        client = GeminiClient()
        print("✅ Cliente Gemini instanciado")
        
        # Prueba básica de generación
        test_messages = [Message(role="user", content="Hola, di simplemente 'Prueba exitosa'")]
        
        print("🤖 Probando generación básica...")
        response = client.generate(test_messages)
        print(f"📝 Respuesta: {response}")
        
        if "exitosa" in response.lower() or "éxito" in response.lower():
            print("✅ Prueba de generación exitosa")
        else:
            print("⚠️  Respuesta inesperada, pero funciona")
        
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        print("💡 Instala Google Generative AI con: pip install google-generativeai")
        
    except Exception as e:
        print(f"❌ Error en prueba Gemini: {e}")
        import traceback
        traceback.print_exc()
    
    print("🏁 Pruebas Gemini completadas")

async def main():
    """Función principal de pruebas"""
    await test_mcp_native()
    await test_gemini_native()

if __name__ == "__main__":
    asyncio.run(main())