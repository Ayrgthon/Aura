# 🌐 Guía de Playwright MCP para Aura

## 📋 Descripción

Playwright MCP es un servidor que permite a Aura automatizar navegadores web para realizar tareas como:
- Búsquedas de productos en sitios de ecommerce
- Comparación de precios
- Extracción de información de páginas web
- Navegación automatizada

## 🚀 Instalación

Playwright MCP ya está integrado en Aura. Para verificar que funciona:

```bash
# Verificar instalación
python test_playwright_mcp.py
```

## 🔧 Configuración

### Opción 1: Interfaz de Terminal
Al ejecutar `python src/main.py`, selecciona:
- **Opción 4**: Solo Playwright
- **Opción 8**: Filesystem + Brave Search + Playwright (recomendado para ecommerce)
- **Opción 9**: Todos los MCPs

### Opción 2: Interfaz Web
Playwright MCP se configura automáticamente en el servidor WebSocket.

## 🛠️ Herramientas Disponibles

### Navegación Básica
- **`goto`**: Navegar a una URL específica
- **`click`**: Hacer clic en elementos de la página
- **`fill`**: Llenar formularios
- **`type`**: Escribir texto
- **`press`**: Presionar teclas

### Extracción de Datos
- **`textContent`**: Obtener texto de elementos
- **`innerHTML`**: Obtener HTML interno
- **`screenshot`**: Capturar pantalla
- **`pdf`**: Generar PDF de la página

### Interacción Avanzada
- **`evaluate`**: Ejecutar JavaScript personalizado
- **`waitForSelector`**: Esperar elementos específicos
- **`waitForLoadState`**: Esperar estados de carga
- **`selectOption`**: Seleccionar opciones en dropdowns

## 💡 Ejemplos de Uso

### Búsqueda de Productos en Amazon
```
"Ve a amazon.com, busca 'laptop gaming' y extrae los precios de los primeros 5 resultados"
```

### Comparación de Precios
```
"Ve a mercadolibre.com y busca 'iPhone 15', luego ve a amazon.com y busca lo mismo, compara los precios"
```

### Extracción de Información
```
"Ve a ebay.com, busca 'Nintendo Switch' y extrae título, precio y envío de los primeros 3 resultados"
```

## 🎯 Casos de Uso para Ecommerce

### 1. Búsqueda de Precios
```python
# Ejemplo de consulta
"Busca el precio del iPhone 15 Pro en Amazon, MercadoLibre y eBay"
```

### 2. Monitoreo de Ofertas
```python
# Ejemplo de consulta
"Ve a las ofertas del día en Amazon y extrae productos con descuento mayor al 50%"
```

### 3. Comparación de Especificaciones
```python
# Ejemplo de consulta
"Compara las especificaciones del MacBook Air M2 en Apple Store y Amazon"
```

## ⚠️ Consideraciones

### Rendimiento
- Playwright es más lento que APIs de búsqueda
- Usar para tareas específicas, no búsquedas generales
- Considerar límites de rate limiting de sitios web

### Legalidad
- Respetar robots.txt de los sitios
- No hacer scraping excesivo
- Usar para investigación personal, no comercial

### Confiabilidad
- Los sitios pueden cambiar su estructura
- Algunos sitios pueden bloquear automatización
- Siempre tener fallbacks (como Brave Search)

## 🔧 Solución de Problemas

### Error: "Playwright no está instalado"
```bash
npx playwright install
```

### Error: "Dependencias faltantes"
```bash
sudo pacman -S icu libxml2 harfbuzz libwebp enchant hyphen libffi
```

### Error: "Sitio web bloquea automatización"
- Usar diferentes user agents
- Agregar delays entre acciones
- Considerar usar Brave Search como alternativa

## 📚 Recursos Adicionales

- [Documentación oficial de Playwright](https://playwright.dev/)
- [MCP Playwright Server](https://www.npmjs.com/package/@playwright/mcp)
- [Ejemplos de automatización web](https://playwright.dev/docs/examples)

## 🎉 ¡Listo!

Playwright MCP está integrado y listo para usar. Prueba con consultas como:
- "Busca el precio del último iPhone en Amazon"
- "Compara precios de laptops gaming en diferentes tiendas"
- "Extrae información de productos de MercadoLibre" 