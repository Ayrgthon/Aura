#!/bin/bash

# Script de instalación para MCP (Model Context Protocol) con Aura
# Este script configura automáticamente todos los requisitos para usar MCPs

set -e  # Salir si hay errores

echo "🌟 === INSTALADOR MCP PARA AURA ==="
echo "Este script instalará todos los requisitos para usar MCP"
echo ""

# Función para detectar el sistema operativo
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &> /dev/null; then
            OS="ubuntu"
        elif command -v yum &> /dev/null; then
            OS="centos"
        else
            OS="linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
    else
        OS="unknown"
    fi
}

# Función para instalar Node.js
install_nodejs() {
    echo "🔧 Instalando Node.js..."
    
    if [[ "$OS" == "ubuntu" ]]; then
        # Ubuntu/Debian
        curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
        sudo apt-get install -y nodejs
    elif [[ "$OS" == "centos" ]]; then
        # CentOS/RHEL
        curl -fsSL https://rpm.nodesource.com/setup_lts.x | sudo bash -
        sudo yum install -y nodejs npm
    elif [[ "$OS" == "macos" ]]; then
        # macOS con Homebrew
        if command -v brew &> /dev/null; then
            brew install node
        else
            echo "❌ Homebrew no encontrado. Instala desde: https://nodejs.org/"
            exit 1
        fi
    else
        echo "❌ Sistema operativo no soportado automáticamente"
        echo "💡 Instala Node.js manualmente desde: https://nodejs.org/"
        exit 1
    fi
}

# Función para verificar Node.js
check_nodejs() {
    if command -v node &> /dev/null && command -v npm &> /dev/null; then
        NODE_VERSION=$(node --version)
        NPM_VERSION=$(npm --version)
        echo "✅ Node.js $NODE_VERSION detectado"
        echo "✅ npm $NPM_VERSION detectado"
        return 0
    else
        echo "❌ Node.js no encontrado"
        return 1
    fi
}

# Función para instalar servidores MCP
install_mcp_servers() {
    echo "📦 Instalando servidores MCP..."
    
    # Filesystem MCP Server (principal)
    echo "   - Instalando filesystem MCP server..."
    npm install -g @modelcontextprotocol/server-filesystem
    
    # Otros servidores MCP útiles (opcionales)
    echo "   - Instalando servidores MCP adicionales..."
    
    # Everything server (para testing)
    npm install -g @modelcontextprotocol/server-everything
    
    echo "✅ Servidores MCP instalados"
}

# Función para verificar Python
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version)
        echo "✅ $PYTHON_VERSION detectado"
        return 0
    else
        echo "❌ Python 3 no encontrado"
        return 1
    fi
}

# Función para instalar dependencias Python
install_python_deps() {
    echo "🐍 Instalando dependencias Python..."
    
    # Verificar si existe requirements.txt
    if [[ -f "requirements.txt" ]]; then
        python3 -m pip install -r requirements.txt
        echo "✅ Dependencias Python instaladas"
    else
        echo "❌ requirements.txt no encontrado"
        exit 1
    fi
}

# Función para probar MCP
test_mcp() {
    echo "🧪 Probando configuración MCP..."
    
    # Probar que el filesystem server funciona
    if npx @modelcontextprotocol/server-filesystem --help &> /dev/null; then
        echo "✅ Filesystem MCP server funciona"
    else
        echo "❌ Error en filesystem MCP server"
        return 1
    fi
    
    # Verificar que las dependencias Python están instaladas
    if python3 -c "import langchain_mcp_adapters" 2>/dev/null; then
        echo "✅ langchain-mcp-adapters disponible"
    else
        echo "❌ Error en langchain-mcp-adapters"
        return 1
    fi
    
    echo "✅ MCP configurado correctamente"
}

# Función para crear configuración de ejemplo
create_example_config() {
    echo "📝 Creando configuración de ejemplo..."
    
    cat > mcp_test_config.py << 'EOF'
#!/usr/bin/env python3
"""
Configuración de ejemplo para MCP
"""

import os
from pathlib import Path

# Configuración básica de MCP
MCP_CONFIG = {
    "filesystem": {
        "command": "npx",
        "args": [
            "-y",
            "@modelcontextprotocol/server-filesystem",
            str(Path.home()),                    # Directorio home
            str(Path.home() / "Documents"),      # Documentos
            str(Path.home() / "Desktop"),        # Escritorio
            str(Path.home() / "Downloads"),      # Descargas
        ],
        "transport": "stdio"
    }
}

# Configuración de seguridad (solo directorios específicos)
MCP_CONFIG_SECURE = {
    "filesystem": {
        "command": "npx",
        "args": [
            "-y",
            "@modelcontextprotocol/server-filesystem",
            "/tmp",  # Solo acceso a temporal
        ],
        "transport": "stdio"
    }
}

if __name__ == "__main__":
    print("📋 Configuraciones MCP disponibles:")
    print("1. MCP_CONFIG - Acceso amplio")
    print("2. MCP_CONFIG_SECURE - Acceso limitado")
EOF
    
    echo "✅ Configuración de ejemplo creada: mcp_test_config.py"
}

# Función para mostrar instrucciones finales
show_final_instructions() {
    echo ""
    echo "🎉 === INSTALACIÓN COMPLETADA ==="
    echo ""
    echo "📋 Próximos pasos:"
    echo "1. Ejecuta: python main.py"
    echo "2. Prueba comandos como: 'lista mis archivos de escritorio'"
    echo "3. Para ejemplos: python example_mcp_usage.py"
    echo ""
    echo "🔧 Herramientas MCP disponibles:"
    echo "   • read_file - Leer archivos"
    echo "   • write_file - Escribir archivos"
    echo "   • list_directory - Listar directorios"
    echo "   • search_files - Buscar archivos"
    echo "   • create_directory - Crear directorios"
    echo "   • move_file - Mover archivos"
    echo ""
    echo "🛡️  Seguridad:"
    echo "   • MCPs solo acceden a directorios especificados"
    echo "   • Todas las operaciones están registradas"
    echo ""
    echo "💡 Para ayuda: python example_mcp_usage.py"
    echo ""
}

# MAIN SCRIPT
main() {
    echo "🚀 Iniciando instalación MCP..."
    
    # Detectar sistema operativo
    detect_os
    echo "🖥️  Sistema operativo detectado: $OS"
    
    # Verificar Python
    if ! check_python; then
        echo "❌ Instala Python 3.8+ antes de continuar"
        exit 1
    fi
    
    # Verificar/instalar Node.js
    if ! check_nodejs; then
        echo "🔧 Node.js no encontrado, instalando..."
        install_nodejs
        
        # Verificar instalación
        if ! check_nodejs; then
            echo "❌ Error instalando Node.js"
            exit 1
        fi
    fi
    
    # Instalar servidores MCP
    install_mcp_servers
    
    # Instalar dependencias Python
    install_python_deps
    
    # Probar configuración
    test_mcp
    
    # Crear ejemplos
    create_example_config
    
    # Mostrar instrucciones finales
    show_final_instructions
    
    echo "✅ ¡Instalación MCP completada exitosamente!"
}

# Ejecutar script principal
main "$@" 