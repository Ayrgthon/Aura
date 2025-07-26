#!/usr/bin/env python3
"""
Script de prueba para verificar la configuración del Notion MCP Server
"""

import os
import json
import subprocess
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_notion_mcp_config():
    """Prueba la configuración del Notion MCP Server"""
    
    print("🧪 Probando configuración del Notion MCP Server")
    print("=" * 50)
    
    # Verificar que existe la API key
    notion_api_key = os.getenv("NOTION_API_KEY")
    if not notion_api_key:
        print("❌ NOTION_API_KEY no encontrada en .env")
        print("💡 Añade tu API key de Notion al archivo .env")
        return False
    
    print(f"✅ API key encontrada: {notion_api_key[:10]}...")
    
    # Verificar que el paquete está instalado
    try:
        result = subprocess.run(
            ["node", "node_modules/@notionhq/notion-mcp-server/bin/cli.mjs", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("✅ Notion MCP Server instalado correctamente")
        else:
            print("❌ Error ejecutando Notion MCP Server")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error verificando instalación: {e}")
        return False
    
    # Probar la configuración de headers
    headers_config = {
        "Authorization": f"Bearer {notion_api_key}",
        "Notion-Version": "2022-06-28"
    }
    
    print(f"📋 Configuración de headers:")
    print(f"   Authorization: Bearer {notion_api_key[:10]}...")
    print(f"   Notion-Version: 2022-06-28")
    
    # Probar una llamada simple a la API
    print("\n🔍 Probando conexión con Notion API...")
    
    try:
        # Crear el comando para probar la API
        env_vars = os.environ.copy()
        env_vars["OPENAPI_MCP_HEADERS"] = json.dumps(headers_config)
        
        # Ejecutar una búsqueda simple
        result = subprocess.run(
            ["node", "node_modules/@notionhq/notion-mcp-server/bin/cli.mjs"],
            input=json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }),
            capture_output=True,
            text=True,
            env=env_vars,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Conexión con Notion API exitosa")
            print("📋 Herramientas disponibles:")
            
            try:
                response = json.loads(result.stdout)
                if "result" in response and "tools" in response["result"]:
                    tools = response["result"]["tools"]
                    for tool in tools:
                        print(f"   - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
                else:
                    print("   (No se pudieron obtener las herramientas)")
            except json.JSONDecodeError:
                print("   (Respuesta no válida)")
                
        else:
            print("❌ Error en la conexión con Notion API")
            print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Timeout al conectar con Notion API")
        return False
    except Exception as e:
        print(f"❌ Error probando conexión: {e}")
        return False
    
    print("\n✅ Configuración del Notion MCP Server verificada correctamente")
    return True

if __name__ == "__main__":
    success = test_notion_mcp_config()
    if success:
        print("\n🎉 ¡Todo listo! Puedes usar Notion con Aura")
    else:
        print("\n❌ Hay problemas con la configuración")
        print("💡 Revisa los pasos de configuración en la documentación")
        sys.exit(1) 