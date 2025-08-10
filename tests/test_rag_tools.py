#!/usr/bin/env python3
"""
Test script para sistema RAG de tools
Extrae las tools actuales y crea un vector database para testear queries
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import warnings

# Suprimir warnings
warnings.filterwarnings("ignore")

# Importar sistema actual para extraer tools
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'client'))

from client.config import get_mcp_servers_config
from client.mcp_client import SimpleMCPClient


class ToolVectorDB:
    """Vector Database para tools usando sentence transformers"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Inicializar vector DB con modelo de embeddings
        
        Args:
            model_name: Modelo de sentence transformers a usar
        """
        print(f"🔄 Cargando modelo de embeddings: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.tools_data = []
        self.tool_embeddings = None
        print(f"✅ Modelo cargado: {model_name}")
    
    def index_tools(self, tools: List[Dict[str, Any]]):
        """
        Indexar tools en la vector database
        
        Args:
            tools: Lista de tools con name, description, etc.
        """
        print(f"🔄 Indexando {len(tools)} tools...")
        
        # Preparar datos de tools
        self.tools_data = []
        texts_to_embed = []
        
        for tool in tools:
            tool_name = tool.get('name', 'unknown')
            tool_desc = tool.get('description', '')
            tool_schema = tool.get('input_schema', {})
            
            # Crear texto completo para embeddings
            # Combinamos nombre + descripción + propiedades del schema
            full_text = f"{tool_name}: {tool_desc}"
            
            # Agregar información del schema si existe
            if isinstance(tool_schema, dict) and 'properties' in tool_schema:
                properties = tool_schema['properties']
                if properties:
                    prop_names = list(properties.keys())
                    full_text += f" Parameters: {', '.join(prop_names)}"
            
            self.tools_data.append({
                'name': tool_name,
                'description': tool_desc,
                'full_text': full_text,
                'schema': tool_schema
            })
            
            texts_to_embed.append(full_text)
        
        # Generar embeddings
        start_time = time.time()
        self.tool_embeddings = self.model.encode(texts_to_embed)
        embedding_time = time.time() - start_time
        
        print(f"✅ {len(tools)} tools indexadas en {embedding_time:.2f}s")
        print(f"📊 Dimensión de embeddings: {self.tool_embeddings.shape}")
    
    def query_similar_tools(self, query_text: str, k: int = 10) -> List[Tuple[Dict[str, Any], float]]:
        """
        Buscar tools similares usando query vectorial
        
        Args:
            query_text: Texto de consulta del usuario
            k: Número de tools a retornar
            
        Returns:
            Lista de tuplas (tool_data, similarity_score)
        """
        if self.tool_embeddings is None:
            raise ValueError("No hay tools indexadas")
        
        # Generar embedding de la query
        start_time = time.time()
        query_embedding = self.model.encode([query_text])
        
        # Calcular similitudes con todas las tools
        similarities = cosine_similarity(query_embedding, self.tool_embeddings)[0]
        
        # Obtener índices de los k más similares
        top_k_indices = np.argsort(similarities)[::-1][:k]
        
        query_time = time.time() - start_time
        
        # Preparar resultados
        results = []
        for idx in top_k_indices:
            tool_data = self.tools_data[idx]
            similarity_score = similarities[idx]
            results.append((tool_data, similarity_score))
        
        print(f"⚡ Query completada en {query_time:.4f}s")
        return results


async def extract_current_tools() -> List[Dict[str, Any]]:
    """
    Extraer todas las tools actuales del sistema MCP
    
    Returns:
        Lista de tools con sus metadatos
    """
    print("🔄 Extrayendo tools del sistema actual...")
    
    try:
        # Configurar cliente MCP
        mcp_client = SimpleMCPClient(debug=False)
        
        # Obtener configuración de servidores
        server_configs = get_mcp_servers_config()
        print(f"📋 Configuraciones de servidores encontradas: {list(server_configs.keys())}")
        
        # Conectar a servidores
        success = await mcp_client.connect_to_servers(server_configs)
        if not success:
            print("❌ No se pudo conectar a servidores MCP")
            return []
        
        # Extraer tools
        tools_data = []
        for tool in mcp_client.tools:
            tool_data = {
                'name': tool.name,
                'description': tool.description,
                'input_schema': tool.input_schema
            }
            tools_data.append(tool_data)
        
        # Cleanup
        await mcp_client.cleanup()
        
        print(f"✅ Extraídas {len(tools_data)} tools del sistema")
        return tools_data
        
    except Exception as e:
        print(f"❌ Error extrayendo tools: {e}")
        return []


def print_query_results(query: str, results: List[Tuple[Dict[str, Any], float]]):
    """
    Mostrar resultados de query de forma bonita
    
    Args:
        query: Query original
        results: Resultados de la búsqueda
    """
    print(f"\n🔍 QUERY: {query}")
    print("=" * 80)
    print(f"📊 TOP {len(results)} TOOLS MÁS RELEVANTES:")
    print("-" * 80)
    
    for i, (tool_data, similarity) in enumerate(results, 1):
        print(f"{i:2d}. {tool_data['name']:<25} (Score: {similarity:.4f})")
        print(f"    📝 {tool_data['description'][:60]}...")
        
        # Mostrar parámetros si existen
        schema = tool_data.get('schema', {})
        if isinstance(schema, dict) and 'properties' in schema:
            properties = schema['properties']
            if properties:
                prop_names = list(properties.keys())[:3]  # Solo los primeros 3
                props_str = ', '.join(prop_names)
                if len(schema['properties']) > 3:
                    props_str += f", +{len(schema['properties'])-3} more"
                print(f"    🔧 Parámetros: {props_str}")
        print()


async def main():
    """Función principal del test"""
    print("🌟 TEST RAG SYSTEM PARA TOOLS")
    print("=" * 50)
    
    # 1. Extraer tools actuales
    tools_data = await extract_current_tools()
    if not tools_data:
        print("❌ No se pudieron extraer tools del sistema")
        return
    
    # 2. Crear e indexar vector database
    print(f"\n🔄 Creando Vector Database...")
    vector_db = ToolVectorDB()
    
    start_indexing = time.time()
    vector_db.index_tools(tools_data)
    indexing_time = time.time() - start_indexing
    
    print(f"⏱️  Tiempo total de indexación: {indexing_time:.2f}s")
    
    # 3. Test query específico
    test_query = "Investiga las últimas noticias sobre Spiderman. Luego, investiga las últimas noticias sobre Superman. Finalmente, en mis notas, dentro de una carpeta llamada \"Héroes\", guarda la información encontrada de cada una de las búsquedas."
    
    print(f"\n🎯 REALIZANDO TEST CON QUERY ESPECÍFICO...")
    
    # Realizar query
    start_query = time.time()
    results = vector_db.query_similar_tools(test_query, k=10)
    total_query_time = time.time() - start_query
    
    # Mostrar resultados
    print_query_results(test_query, results)
    
    # 4. Estadísticas de performance
    print("=" * 80)
    print("📊 ESTADÍSTICAS DE PERFORMANCE")
    print("-" * 80)
    print(f"📈 Tools totales indexadas: {len(tools_data)}")
    print(f"⏱️  Tiempo de indexación: {indexing_time:.2f}s")
    print(f"⚡ Tiempo de query: {total_query_time:.4f}s")
    print(f"🎯 Tools por segundo (query): {len(tools_data)/total_query_time:.0f}")
    
    # 5. Tests adicionales rápidos
    print(f"\n🧪 TESTS ADICIONALES RÁPIDOS:")
    print("-" * 40)
    
    additional_queries = [
        "search web for information",
        "save notes and create files", 
        "get current time and date",
        "think step by step"
    ]
    
    for query in additional_queries:
        start_time = time.time()
        quick_results = vector_db.query_similar_tools(query, k=3)
        query_time = time.time() - start_time
        
        top_tool = quick_results[0][0]['name'] if quick_results else "No results"
        print(f"Query: '{query[:30]}...' -> {top_tool} ({query_time:.4f}s)")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Test interrumpido")
    except Exception as e:
        print(f"❌ Error en test: {e}")
        import traceback
        traceback.print_exc()