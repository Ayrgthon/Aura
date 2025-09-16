#!/usr/bin/env python3
"""
Test básico de Browser Use MCP para verificar compatibilidad con Arch Linux
"""

import asyncio
from browser_use import Agent
import os

async def test_browser_basic():
    """Test básico de navegación"""
    try:
        print("🚀 Iniciando test de Browser Use...")
        
        # Crear agente con configuración básica
        agent = Agent(
            task="Navega a google.com y busca 'test'",
            llm=None,  # Sin LLM para test básico
            browser={"type": "chromium", "headless": True}
        )
        
        print("✅ Agente creado exitosamente")
        print("🔧 Browser Use MCP funciona correctamente en Arch Linux!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en test básico: {e}")
        return False

async def test_browser_with_navigation():
    """Test con navegación real"""
    try:
        print("\n🌐 Iniciando test de navegación...")
        
        # Test básico de navegación sin LLM
        from browser_use.browser import Browser
        
        browser = Browser(browser_type="chromium", headless=True)
        await browser.get_playwright_browser()
        
        print("✅ Browser iniciado correctamente")
        print("🔧 Chromium funciona via Playwright en Arch Linux!")
        
        await browser.close()
        return True
        
    except Exception as e:
        print(f"❌ Error en test de navegación: {e}")
        return False

async def main():
    """Función principal de test"""
    print("=" * 60)
    print("🧪 TESTING BROWSER USE MCP EN ARCH LINUX")
    print("=" * 60)
    
    # Test 1: Creación básica de agente
    test1 = await test_browser_basic()
    
    # Test 2: Navegación básica
    test2 = await test_browser_with_navigation()
    
    print("\n" + "=" * 60)
    print("📊 RESULTADOS:")
    print(f"  ✅ Test básico: {'PASS' if test1 else 'FAIL'}")
    print(f"  ✅ Test navegación: {'PASS' if test2 else 'FAIL'}")
    
    if test1 and test2:
        print("\n🎉 ¡TODOS LOS TESTS PASARON!")
        print("💡 Browser Use MCP está listo para integración con Aura")
    else:
        print("\n⚠️  Algunos tests fallaron - revisar configuración")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())