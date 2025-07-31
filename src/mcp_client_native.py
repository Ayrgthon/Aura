#!/usr/bin/env python3
"""
Cliente MCP nativo usando la librería oficial de Python
Reemplaza langchain-mcp-adapters
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional
from contextlib import AsyncExitStack
from pathlib import Path

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  MCP SDK no disponible: {e}")
    print("💡 Instala con: pip install mcp")
    MCP_AVAILABLE = False


class MCPTool:
    """Representa una herramienta MCP"""
    def __init__(self, name: str, description: str, input_schema: Dict[str, Any]):
        self.name = name
        self.description = description
        self.input_schema = input_schema
    
    def __repr__(self):
        return f"MCPTool(name='{self.name}', description='{self.description[:50]}...')"


class NativeMCPClient:
    """Cliente MCP nativo usando la librería oficial"""
    
    def __init__(self):
        self.servers = {}
        self.tools = []
        self.exit_stack = None
        self.initialized = False
    
    async def setup_servers(self, mcp_configs: Dict[str, Dict]) -> bool:
        """
        Configura servidores MCP usando la librería oficial
        
        Args:
            mcp_configs: Configuración de servidores MCP
            
        Returns:
            True si se configuró exitosamente
        """
        if not MCP_AVAILABLE:
            print("❌ MCP SDK no está disponible")
            return False
        
        try:
            self.exit_stack = AsyncExitStack()
            
            for server_name, config in mcp_configs.items():
                print(f"🔧 Configurando servidor MCP: {server_name}")
                
                # Configurar parámetros del servidor
                if config.get("transport") == "stdio":
                    command = config.get("command")
                    args = config.get("args", [])
                    env = config.get("env", {})
                    
                    if command == "npx":
                        # Para servidores de Node.js
                        server_params = StdioServerParameters(
                            command=command,
                            args=args,
                            env=env
                        )
                    elif command == "node":
                        # Para servidores JavaScript locales
                        server_params = StdioServerParameters(
                            command=command,
                            args=args,
                            env=env
                        )
                    else:
                        print(f"⚠️  Comando no soportado: {command}")
                        continue
                    
                    # Conectar al servidor
                    try:
                        # Usar el patrón correcto según la documentación oficial de MCP
                        read_stream, write_stream = await self.exit_stack.enter_async_context(
                            stdio_client(server_params)
                        )
                        
                        # Crear sesión de cliente
                        session = await self.exit_stack.enter_async_context(
                            ClientSession(read_stream, write_stream)
                        )
                        
                        # Inicializar sesión
                        await session.initialize()
                        
                        # Obtener herramientas disponibles
                        list_tools_result = await session.list_tools()
                        
                        # Procesar herramientas
                        server_tools = []
                        for tool in list_tools_result.tools:
                            mcp_tool = MCPTool(
                                name=tool.name,
                                description=tool.description or "",
                                input_schema=tool.inputSchema or {}
                            )
                            server_tools.append(mcp_tool)
                            self.tools.append(mcp_tool)
                        
                        # Guardar referencia del servidor
                        self.servers[server_name] = {
                            'session': session,
                            'tools': server_tools
                        }
                        
                        print(f"✅ {server_name} conectado - {len(server_tools)} herramientas disponibles")
                        
                    except Exception as e:
                        print(f"❌ Error conectando a {server_name}: {e}")
                        continue
                        
                else:
                    print(f"⚠️  Transport no soportado: {config.get('transport')}")
                    continue
            
            if self.servers:
                self.initialized = True
                print(f"✅ MCPs configurados correctamente. {len(self.tools)} herramientas totales disponibles:")
                for tool in self.tools:
                    print(f"  - {tool.name}: {tool.description}")
                return True
            else:
                print("❌ No se pudo configurar ningún servidor MCP")
                return False
                
        except Exception as e:
            print(f"❌ Error configurando servidores MCP: {e}")
            return False
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Ejecuta una herramienta MCP
        
        Args:
            tool_name: Nombre de la herramienta
            arguments: Argumentos para la herramienta
            
        Returns:
            Resultado de la herramienta
        """
        if not self.initialized:
            raise Exception("Cliente MCP no inicializado")
        
        # Buscar la herramienta y su servidor
        target_server = None
        target_tool = None
        
        for server_name, server_info in self.servers.items():
            for tool in server_info['tools']:
                if tool.name == tool_name:
                    target_server = server_info['session']
                    target_tool = tool
                    break
            if target_tool:
                break
        
        if not target_tool or not target_server:
            raise Exception(f"Herramienta '{tool_name}' no encontrada")
        
        try:
            # Ejecutar la herramienta
            result = await target_server.call_tool(tool_name, arguments)
            
            # Procesar resultado
            if result.content:
                if len(result.content) == 1:
                    content = result.content[0]
                    if hasattr(content, 'text'):
                        return content.text
                    else:
                        return str(content)
                else:
                    # Múltiples contenidos, combinar
                    texts = []
                    for content in result.content:
                        if hasattr(content, 'text'):
                            texts.append(content.text)
                        else:
                            texts.append(str(content))
                    return "\n".join(texts)
            else:
                return "Herramienta ejecutada sin resultado"
                
        except Exception as e:
            raise Exception(f"Error ejecutando herramienta '{tool_name}': {e}")
    
    def get_tools_for_gemini(self) -> List[Dict[str, Any]]:
        """
        Convierte las herramientas MCP al formato esperado por Gemini
        
        Returns:
            Lista de herramientas en formato Gemini
        """
        if not self.initialized:
            return []
        
        function_declarations = []
        
        for tool in self.tools:
            try:
                # Verificar que la herramienta tiene los campos necesarios
                if not tool or not hasattr(tool, 'name') or not tool.name:
                    print(f"⚠️  Herramienta inválida omitida: {tool}")
                    continue
                
                # Limpiar el schema para Gemini (remover campos no soportados)
                clean_schema = self._clean_schema_for_gemini(tool.input_schema)
                
                function_declaration = {
                    "name": tool.name,
                    "description": tool.description or "Sin descripción",
                    "parameters": clean_schema
                }
                
                function_declarations.append(function_declaration)
                
            except Exception as e:
                print(f"⚠️  Error procesando herramienta {getattr(tool, 'name', 'desconocida')}: {e}")
                continue
        
        # Gemini espera una sola lista de function_declarations
        return [{
            "function_declarations": function_declarations
        }]
    
    def _clean_schema_for_gemini(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Limpia el schema JSON para hacerlo compatible con Gemini
        
        Args:
            schema: Schema original de MCP
            
        Returns:
            Schema limpio compatible con Gemini
        """
        if not schema or not isinstance(schema, dict):
            # Si el schema es None o vacío, devolver un schema básico
            return {"type": "object", "properties": {}}
        
        # Crear copia para no modificar el original
        clean_schema = {}
        
        # Campos permitidos por Gemini
        allowed_fields = {
            "type", "properties", "required", "items", "enum", 
            "description", "format", "minimum", "maximum"
        }
        
        for key, value in schema.items():
            if value is None:
                continue  # Saltar valores None
                
            if key in allowed_fields:
                if key == "properties" and isinstance(value, dict):
                    # Limpiar recursivamente las propiedades
                    cleaned_props = {}
                    for prop_name, prop_schema in value.items():
                        if prop_schema is not None:
                            cleaned_props[prop_name] = self._clean_schema_for_gemini(prop_schema)
                    clean_schema[key] = cleaned_props
                elif key == "items" and isinstance(value, dict):
                    # Limpiar recursivamente los items de arrays
                    clean_schema[key] = self._clean_schema_for_gemini(value)
                else:
                    clean_schema[key] = value
        
        # Asegurar que tenga al menos el tipo
        if "type" not in clean_schema:
            clean_schema["type"] = "object"
        
        # Asegurar que tenga properties si es object
        if clean_schema.get("type") == "object" and "properties" not in clean_schema:
            clean_schema["properties"] = {}
        
        return clean_schema
    
    async def cleanup(self):
        """Limpia recursos y cierra conexiones"""
        if self.exit_stack:
            try:
                await self.exit_stack.aclose()
                print("🧹 Recursos MCP limpiados")
            except Exception as e:
                print(f"⚠️  Error limpiando recursos MCP: {e}")
        
        self.servers.clear()
        self.tools.clear()
        self.initialized = False
    
    def __del__(self):
        """Destructor para limpiar recursos"""
        if self.exit_stack:
            # Crear un nuevo loop si no existe uno
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Si el loop está corriendo, programar la limpieza
                    loop.create_task(self.cleanup())
                else:
                    # Si no está corriendo, ejecutar directamente
                    loop.run_until_complete(self.cleanup())
            except RuntimeError:
                # No hay loop, crear uno nuevo
                asyncio.run(self.cleanup())


class MCPToolCall:
    """Representa una llamada a herramienta MCP para compatibilidad"""
    def __init__(self, name: str, args: Dict[str, Any]):
        self.name = name
        self.args = args
    
    def __repr__(self):
        return f"MCPToolCall(name='{self.name}', args={self.args})"


def create_mcp_client() -> NativeMCPClient:
    """Factory function para crear un cliente MCP nativo"""
    return NativeMCPClient()


# Alias para compatibilidad con el código existente
MultiServerMCPClient = NativeMCPClient
