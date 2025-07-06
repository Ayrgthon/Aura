#!/bin/bash

# Script para limpiar API keys del historial de Git
# ⚠️  ATENCIÓN: Esta operación reescribe TODO el historial

echo "🔥 LIMPIEZA CRÍTICA DE API KEYS EN HISTORIAL DE GIT"
echo "=================================================="
echo ""
echo "⚠️  ADVERTENCIA: Esta operación:"
echo "   - Reescribe TODO el historial de commits"
echo "   - Es IRREVERSIBLE"
echo "   - Cambiará todos los hashes de commit"
echo "   - Forzará push al repositorio remoto"
echo ""

# Confirmar que el usuario quiere proceder
read -p "¿Continuar con la limpieza? (escriba 'SI' para confirmar): " confirm
if [ "$confirm" != "SI" ]; then
    echo "❌ Operación cancelada"
    exit 1
fi

echo ""
echo "🚀 Iniciando limpieza del historial..."

# Verificar que estamos en un repo git
if [ ! -d ".git" ]; then
    echo "❌ Error: No estamos en un repositorio git"
    exit 1
fi

# Crear archivo temporal con el script de filtro
cat > /tmp/git_filter_script.sh << 'EOF'
#!/bin/bash

# Reemplazar API keys con placeholders en todos los archivos
sed -i 's/YOUR_GOOGLE_API_KEY_HERE/YOUR_GOOGLE_API_KEY_HERE/g' "$1" 2>/dev/null || true
sed -i 's/YOUR_BRAVE_API_KEY_HERE/YOUR_BRAVE_API_KEY_HERE/g' "$1" 2>/dev/null || true
sed -i 's/YOUR_ELEVENLABS_API_KEY_HERE/YOUR_ELEVENLABS_API_KEY_HERE/g' "$1" 2>/dev/null || true

# También buscar patrones más generales
sed -i 's/AIzaSy[A-Za-z0-9_-]\{35\}/YOUR_GOOGLE_API_KEY_HERE/g' "$1" 2>/dev/null || true
sed -i 's/sk_[A-Za-z0-9]\{48\}/YOUR_ELEVENLABS_API_KEY_HERE/g' "$1" 2>/dev/null || true
EOF

chmod +x /tmp/git_filter_script.sh

echo "📝 Reescribiendo historial de git..."
echo "   Esto puede tomar varios minutos..."

# Usar git filter-branch para reescribir todo el historial
git filter-branch --force --tree-filter '
    # Aplicar el filtro a todos los archivos del árbol
    find . -type f \( -name "*.py" -o -name "*.js" -o -name "*.md" -o -name "*.txt" -o -name "*.sh" \) -exec /tmp/git_filter_script.sh {} \;
' --tag-name-filter cat -- --all

echo ""
if [ $? -eq 0 ]; then
    echo "✅ Historial reescrito exitosamente"
    
    # Limpiar referencias temporales
    echo "🧹 Limpiando referencias temporales..."
    git for-each-ref --format="%(refname)" refs/original/ | xargs -n 1 git update-ref -d
    
    # Limpiar reflogs
    git reflog expire --expire=now --all
    git gc --prune=now --aggressive
    
    echo ""
    echo "🔍 Verificando limpieza..."
    if git log --all -p | grep -E "(AIzaSy|BSAKTRlZWWM|sk_54f6df0d)" | head -5; then
        echo "⚠️  Aún se encontraron rastros de API keys"
    else
        echo "✅ No se encontraron API keys en el historial"
    fi
    
    echo ""
    echo "🚀 SIGUIENTE PASO CRÍTICO:"
    echo "   Para limpiar el repositorio remoto, ejecuta:"
    echo "   git push --force-with-lease origin main"
    echo ""
    echo "⚠️  ADVERTENCIA FINAL:"
    echo "   - Esto sobrescribirá el historial en GitHub"
    echo "   - Otros colaboradores necesitarán re-clonar el repo"
    echo "   - Los API keys pueden seguir visibles en forks/caches"
    echo ""
    echo "🔐 RECOMENDACIÓN URGENTE:"
    echo "   - Revoca y regenera TODAS las API keys inmediatamente"
    echo "   - Especialmente la de ElevenLabs y Google Gemini"
    
else
    echo "❌ Error durante la reescritura del historial"
    exit 1
fi

# Limpiar archivo temporal
rm -f /tmp/git_filter_script.sh

echo ""
echo "✅ Script de limpieza completado" 