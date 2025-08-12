#!/usr/bin/env node

/**
 * Servidor MCP para Notion - Integración personalizada con Aura
 * Herramientas principales: crear_evento, crear_tarea
 * Compatible con la arquitectura MCP existente de Aura
 */

const https = require('https');
const { URL } = require('url');

// Configuración del servidor MCP
const MCP_CONFIG = {
    name: "notion",
    version: "1.0.0",
    api_key: process.env.NOTION_API_KEY,
    api_version: "2022-06-28",
    // IDs de bases de datos (obtenidos de las pruebas anteriores)
    arcos_db_id: "1f434b11-5002-8190-a341-d82effafcea6",
    quest_db_id: "1f434b11-5002-8130-94c4-e44a770d8c9e"
};

class NotionServer {
    constructor() {
        this.api_key = MCP_CONFIG.api_key;
        this.arcos_db_id = MCP_CONFIG.arcos_db_id;
        this.quest_db_id = MCP_CONFIG.quest_db_id;
        
        if (!this.api_key) {
            throw new Error('NOTION_API_KEY es requerida en las variables de entorno');
        }
        
        this.tools = [
            {
                name: "crear_evento",
                description: "CREAR ARCO/EVENTO: Crea un nuevo arco (evento principal) en Notion. Los arcos son conjuntos de tareas relacionadas (ej: 'Examen final', 'Proyecto web'). CUÁNDO USAR: Para definir un nuevo evento o proyecto que contendrá múltiples tareas. PARÁMETROS: nombre (requerido), descripción breve, estado de completado, contenido detallado opcional.",
                inputSchema: {
                    type: "object",
                    properties: {
                        nombre: {
                            type: "string",
                            description: "Nombre del arco/evento (requerido). Ejemplos: 'Examen final', 'Proyecto web', 'Notion Integration'"
                        },
                        descripcion: {
                            type: "string",
                            description: "Descripción breve del arco (opcional). Se mostrará en la propiedad Description."
                        },
                        completado: {
                            type: "boolean",
                            default: false,
                            description: "Si el arco está completado (marca la casilla clear!)"
                        },
                        contenido_detallado: {
                            type: "string",
                            description: "Contenido detallado a añadir dentro de la página (opcional). Se convertirá automáticamente en bloques de texto."
                        }
                    },
                    required: ["nombre"]
                }
            },
            {
                name: "crear_tarea",
                description: "CREAR QUEST/TAREA: Crea una nueva quest (tarea específica) en Notion. Las quests pertenecen a arcos y representan tareas individuales. LÓGICA INTELIGENTE: Si no especificas un arco, el sistema te mostrará arcos disponibles para elegir o te preguntará si quieres crear uno nuevo. CUÁNDO USAR: Para crear tareas específicas dentro de un proyecto/arco. PARÁMETROS: nombre (requerido), arco, descripción, fecha límite, importancia, estado.",
                inputSchema: {
                    type: "object",
                    properties: {
                        nombre: {
                            type: "string",
                            description: "Nombre de la tarea/quest (requerido). Ejemplos: 'Estudiar capítulo 5', 'Implementar API', 'Crear MCP de notion'"
                        },
                        descripcion: {
                            type: "string",
                            description: "Descripción breve de la tarea (opcional). Se mostrará en la propiedad Description."
                        },
                        arco: {
                            type: "string",
                            description: "Nombre del arco al que pertenece la tarea (opcional). Si no se especifica, el sistema sugerirá arcos disponibles o preguntará si crear uno nuevo."
                        },
                        fecha_vencimiento: {
                            type: "string",
                            description: "Fecha límite de la tarea en formato YYYY-MM-DD (opcional). Ejemplo: '2025-08-20'"
                        },
                        importancia: {
                            type: "string",
                            enum: ["urgente", "importante", "normal"],
                            default: "normal",
                            description: "Nivel de importancia de la tarea: urgente (rojo), importante (azul), normal (gris)"
                        },
                        status: {
                            type: "string",
                            enum: ["Pendiente", "En curso", "Terminada"],
                            default: "Pendiente",
                            description: "Estado actual de la tarea: Pendiente (rojo), En curso (morado), Terminada (azul)"
                        },
                        completado: {
                            type: "boolean",
                            default: false,
                            description: "Si la tarea está completada (marca la casilla completed!)"
                        },
                        contenido_detallado: {
                            type: "string",
                            description: "Contenido detallado a añadir dentro de la página (opcional). Se convertirá automáticamente en bloques de texto."
                        }
                    },
                    required: ["nombre"]
                }
            },
            {
                name: "actualizar_pagina",
                description: "ACTUALIZAR PÁGINA: Modifica propiedades de una página existente (arco o quest). Puede buscar por ID o por nombre. CUÁNDO USAR: Para cambiar estado, fechas, descripciones, o cualquier propiedad de páginas existentes. PARÁMETROS: identificador de página, tipo de base, propiedades a actualizar.",
                inputSchema: {
                    type: "object",
                    properties: {
                        pagina_id: {
                            type: "string",
                            description: "ID exacto de la página a actualizar (opcional si usas buscar_por_nombre)"
                        },
                        buscar_por_nombre: {
                            type: "string",
                            description: "Buscar página por su nombre exacto (opcional si usas pagina_id)"
                        },
                        tipo_base: {
                            type: "string",
                            enum: ["arcos", "quest"],
                            description: "Tipo de base de datos donde buscar: 'arcos' para eventos, 'quest' para tareas"
                        },
                        nombre: {
                            type: "string",
                            description: "Nuevo nombre para la página (opcional)"
                        },
                        descripcion: {
                            type: "string",
                            description: "Nueva descripción (opcional)"
                        },
                        status: {
                            type: "string",
                            enum: ["Pendiente", "En curso", "Terminada"],
                            description: "Nuevo estado (solo para quest)"
                        },
                        importancia: {
                            type: "string",
                            enum: ["urgente", "importante", "normal"],
                            description: "Nueva importancia (solo para quest)"
                        },
                        fecha_vencimiento: {
                            type: "string",
                            description: "Nueva fecha límite en formato YYYY-MM-DD (solo para quest)"
                        },
                        completado: {
                            type: "boolean",
                            description: "Marcar como completado (aplica a ambos tipos)"
                        }
                    }
                }
            },
            {
                name: "escribir_contenido",
                description: "ESCRIBIR CONTENIDO: Añade contenido detallado dentro de una página (arco o quest). Convierte automáticamente el texto en bloques formateados de Notion. CUÁNDO USAR: Para añadir información detallada, notas, o documentación dentro de páginas existentes. PARÁMETROS: identificador de página, contenido, modo de escritura.",
                inputSchema: {
                    type: "object",
                    properties: {
                        pagina_id: {
                            type: "string",
                            description: "ID exacto de la página donde escribir (opcional si usas buscar_por_nombre)"
                        },
                        buscar_por_nombre: {
                            type: "string",
                            description: "Buscar página por su nombre exacto (opcional si usas pagina_id)"
                        },
                        tipo_base: {
                            type: "string",
                            enum: ["arcos", "quest"],
                            description: "Tipo de base de datos donde buscar: 'arcos' para eventos, 'quest' para tareas"
                        },
                        contenido: {
                            type: "string",
                            description: "Contenido a añadir (requerido). Se convertirá automáticamente en párrafos, listas y títulos según el formato del texto."
                        },
                        modo: {
                            type: "string",
                            enum: ["append", "replace"],
                            default: "append",
                            description: "Modo de escritura: 'append' añade al final del contenido existente, 'replace' reemplaza todo el contenido"
                        }
                    },
                    required: ["contenido"]
                }
            },
            {
                name: "listar_arcos",
                description: "LISTAR ARCOS: Muestra todos los arcos (eventos) disponibles. Útil para sugerir arcos cuando se crea una tarea sin especificar arco. CUÁNDO USAR: Para ver qué arcos existen, o cuando el sistema necesita sugerir arcos para una nueva tarea. PARÁMETROS: filtros opcionales.",
                inputSchema: {
                    type: "object",
                    properties: {
                        incluir_completados: {
                            type: "boolean",
                            default: false,
                            description: "Incluir arcos que ya están completados (clear! = true)"
                        },
                        limite: {
                            type: "integer",
                            default: 20,
                            description: "Máximo número de arcos a mostrar (1-50)"
                        }
                    }
                }
            },
            {
                name: "buscar_paginas",
                description: "BUSCAR PÁGINAS: Busca páginas en las bases de datos por criterios específicos. CUÁNDO USAR: Para encontrar arcos o quests existentes por nombre, contenido, o propiedades. PARÁMETROS: tipo de base, término de búsqueda, filtros.",
                inputSchema: {
                    type: "object",
                    properties: {
                        tipo_base: {
                            type: "string",
                            enum: ["arcos", "quest", "ambas"],
                            default: "ambas",
                            description: "Donde buscar: 'arcos' solo en eventos, 'quest' solo en tareas, 'ambas' en ambas bases"
                        },
                        termino: {
                            type: "string",
                            description: "Término a buscar en títulos y contenido (requerido)"
                        },
                        limite: {
                            type: "integer",
                            default: 10,
                            description: "Máximo número de resultados (1-50)"
                        }
                    },
                    required: ["termino"]
                }
            }
        ];
    }

    async handleRequest(request) {
        try {
            const { method, params, id } = request;
            let result;
            
            switch (method) {
                case 'initialize':
                    result = this.initialize();
                    break;
                case 'tools/list':
                    result = { tools: this.tools };
                    break;
                case 'tools/call':
                    result = await this.callTool(params);
                    break;
                default:
                    return {
                        jsonrpc: "2.0",
                        id,
                        error: {
                            code: -1,
                            message: `Método desconocido: ${method}`
                        }
                    };
            }
            
            return { jsonrpc: "2.0", id, result };
        } catch (error) {
            return {
                jsonrpc: "2.0",
                id: request.id,
                error: {
                    code: -1,
                    message: error.message
                }
            };
        }
    }

    initialize() {
        return {
            protocolVersion: "2024-11-05",
            capabilities: {
                tools: {
                    listChanged: false
                }
            },
            serverInfo: {
                name: MCP_CONFIG.name,
                version: MCP_CONFIG.version
            }
        };
    }

    async callTool(params) {
        const { name, arguments: args } = params;

        switch (name) {
            case 'crear_evento':
                return await this.crearEvento(args);
            case 'crear_tarea':
                return await this.crearTarea(args);
            case 'actualizar_pagina':
                return await this.actualizarPagina(args);
            case 'escribir_contenido':
                return await this.escribirContenido(args);
            case 'listar_arcos':
                return await this.listarArcos(args);
            case 'buscar_paginas':
                return await this.buscarPaginas(args);
            default:
                throw new Error(`Herramienta desconocida: ${name}`);
        }
    }

    async crearEvento(args) {
        const { nombre, descripcion, completado = false, contenido_detallado } = args;
        
        if (!nombre || nombre.trim() === '') {
            throw new Error('Nombre del arco es requerido');
        }

        try {
            // Preparar datos para la página
            const pageData = {
                parent: {
                    database_id: this.arcos_db_id
                },
                properties: {
                    Name: {
                        title: [{ text: { content: nombre.trim() } }]
                    },
                    "clear!": {
                        checkbox: completado
                    }
                }
            };

            // Añadir descripción si se proporcionó (nota: la BD arcos no tiene campo Description en el schema que obtuvimos)
            // Pero podemos intentar añadirlo

            // Crear la página
            const response = await this.makeRequest('https://api.notion.com/v1/pages', 'POST', pageData);
            
            let output = `✅ **Arco creado exitosamente:**\n\n`;
            output += `📌 **Nombre:** ${response.properties.Name.title[0].plain_text}\n`;
            output += `🆔 **ID:** ${response.id}\n`;
            output += `📅 **Creado:** ${new Date(response.created_time).toLocaleString('es-ES')}\n`;
            output += `✅ **Completado:** ${completado ? 'Sí' : 'No'}\n`;
            output += `🔗 **Ver arco:** ${response.url}\n`;

            // Si hay contenido detallado, añadirlo
            if (contenido_detallado && contenido_detallado.trim()) {
                await this.añadirContenidoAPagina(response.id, contenido_detallado);
                output += `📝 **Contenido detallado:** Añadido dentro de la página\n`;
            }

            return {
                content: [{ type: "text", text: output }]
            };

        } catch (error) {
            throw new Error(`Error creando arco: ${error.message}`);
        }
    }

    async crearTarea(args) {
        const { 
            nombre, 
            descripcion, 
            arco, 
            fecha_vencimiento, 
            importancia = "normal", 
            status = "Pendiente",
            completado = false,
            contenido_detallado 
        } = args;
        
        if (!nombre || nombre.trim() === '') {
            throw new Error('Nombre de la tarea es requerido');
        }

        try {
            let arcoId = null;
            let arcoInfo = "";

            // Lógica inteligente para manejo de arcos
            if (arco && arco.trim()) {
                // Se especificó un arco, buscarlo
                const arcoEncontrado = await this.buscarArcoPorNombre(arco.trim());
                if (arcoEncontrado) {
                    arcoId = arcoEncontrado.id;
                    arcoInfo = `🏷️ **Arco:** ${arcoEncontrado.name}\n`;
                } else {
                    throw new Error(`Arco "${arco}" no encontrado. Usa 'listar_arcos' para ver arcos disponibles o 'crear_evento' para crear uno nuevo.`);
                }
            } else {
                // No se especificó arco, sugerir arcos disponibles
                const arcosDisponibles = await this.obtenerArcos(false, 10);
                if (arcosDisponibles.length > 0) {
                    let sugerencia = `❓ **No se especificó un arco para esta tarea.**\n\n`;
                    sugerencia += `📋 **Arcos disponibles:**\n`;
                    arcosDisponibles.forEach((arco, index) => {
                        sugerencia += `${index + 1}. ${arco.name}\n`;
                    });
                    sugerencia += `\n💡 **Opciones:**\n`;
                    sugerencia += `• Usar 'crear_tarea' otra vez especificando el parámetro 'arco' con uno de los nombres de arriba\n`;
                    sugerencia += `• Usar 'crear_evento' primero para crear un nuevo arco\n`;
                    sugerencia += `• Continuar sin arco (no recomendado)\n`;
                    
                    return {
                        content: [{ type: "text", text: sugerencia }]
                    };
                }
            }

            // Preparar datos para la página
            const pageData = {
                parent: {
                    database_id: this.quest_db_id
                },
                properties: {
                    Name: {
                        title: [{ text: { content: nombre.trim() } }]
                    },
                    Status: {
                        select: { name: status }
                    },
                    importancia: {
                        multi_select: [{ name: importancia }]
                    },
                    "completed!": {
                        checkbox: completado
                    }
                }
            };

            // Añadir descripción si se proporcionó
            if (descripcion && descripcion.trim()) {
                pageData.properties.Description = {
                    rich_text: [{ text: { content: descripcion.trim() } }]
                };
            }

            // Añadir fecha de vencimiento si se proporcionó
            if (fecha_vencimiento) {
                pageData.properties["Due date"] = {
                    date: { start: fecha_vencimiento }
                };
            }

            // Añadir relación con arco si se encontró
            if (arcoId) {
                pageData.properties.arcos = {
                    relation: [{ id: arcoId }]
                };
            }

            // Crear la página
            const response = await this.makeRequest('https://api.notion.com/v1/pages', 'POST', pageData);
            
            let output = `✅ **Tarea creada exitosamente:**\n\n`;
            output += `📌 **Nombre:** ${response.properties.Name.title[0].plain_text}\n`;
            output += `🆔 **ID:** ${response.id}\n`;
            output += arcoInfo;
            output += `📊 **Estado:** ${status}\n`;
            output += `🎯 **Importancia:** ${importancia}\n`;
            if (fecha_vencimiento) output += `📅 **Fecha límite:** ${fecha_vencimiento}\n`;
            output += `✅ **Completada:** ${completado ? 'Sí' : 'No'}\n`;
            output += `📅 **Creada:** ${new Date(response.created_time).toLocaleString('es-ES')}\n`;
            output += `🔗 **Ver tarea:** ${response.url}\n`;

            // Si hay contenido detallado, añadirlo
            if (contenido_detallado && contenido_detallado.trim()) {
                await this.añadirContenidoAPagina(response.id, contenido_detallado);
                output += `📝 **Contenido detallado:** Añadido dentro de la página\n`;
            }

            return {
                content: [{ type: "text", text: output }]
            };

        } catch (error) {
            throw new Error(`Error creando tarea: ${error.message}`);
        }
    }

    async actualizarPagina(args) {
        const { 
            pagina_id, 
            buscar_por_nombre, 
            tipo_base,
            nombre,
            descripcion,
            status,
            importancia,
            fecha_vencimiento,
            completado
        } = args;

        try {
            let pageId = pagina_id;
            
            // Si no se proporcionó ID, buscar por nombre
            if (!pageId && buscar_por_nombre && tipo_base) {
                const pagina = await this.buscarPaginaPorNombre(buscar_por_nombre, tipo_base);
                if (!pagina) {
                    throw new Error(`No se encontró página con nombre "${buscar_por_nombre}" en base de datos "${tipo_base}"`);
                }
                pageId = pagina.id;
            }

            if (!pageId) {
                throw new Error('Se requiere pagina_id o buscar_por_nombre con tipo_base');
            }

            // Preparar datos de actualización
            const updateData = { properties: {} };

            if (nombre) {
                updateData.properties.Name = {
                    title: [{ text: { content: nombre } }]
                };
            }

            if (descripcion !== undefined) {
                updateData.properties.Description = {
                    rich_text: [{ text: { content: descripcion } }]
                };
            }

            if (status) {
                updateData.properties.Status = {
                    select: { name: status }
                };
            }

            if (importancia) {
                updateData.properties.importancia = {
                    multi_select: [{ name: importancia }]
                };
            }

            if (fecha_vencimiento) {
                updateData.properties["Due date"] = {
                    date: { start: fecha_vencimiento }
                };
            }

            if (completado !== undefined) {
                if (tipo_base === 'arcos') {
                    updateData.properties["clear!"] = { checkbox: completado };
                } else {
                    updateData.properties["completed!"] = { checkbox: completado };
                }
            }

            // Actualizar la página
            const response = await this.makeRequest(`https://api.notion.com/v1/pages/${pageId}`, 'PATCH', updateData);

            let output = `✅ **Página actualizada exitosamente:**\n\n`;
            output += `📌 **Nombre:** ${response.properties.Name.title[0].plain_text}\n`;
            output += `🆔 **ID:** ${response.id}\n`;
            output += `📅 **Última modificación:** ${new Date(response.last_edited_time).toLocaleString('es-ES')}\n`;
            output += `🔗 **Ver página:** ${response.url}\n`;

            return {
                content: [{ type: "text", text: output }]
            };

        } catch (error) {
            throw new Error(`Error actualizando página: ${error.message}`);
        }
    }

    async escribirContenido(args) {
        const { pagina_id, buscar_por_nombre, tipo_base, contenido, modo = "append" } = args;

        if (!contenido || contenido.trim() === '') {
            throw new Error('Contenido es requerido');
        }

        try {
            let pageId = pagina_id;
            
            // Si no se proporcionó ID, buscar por nombre
            if (!pageId && buscar_por_nombre && tipo_base) {
                const pagina = await this.buscarPaginaPorNombre(buscar_por_nombre, tipo_base);
                if (!pagina) {
                    throw new Error(`No se encontró página con nombre "${buscar_por_nombre}" en base de datos "${tipo_base}"`);
                }
                pageId = pagina.id;
            }

            if (!pageId) {
                throw new Error('Se requiere pagina_id o buscar_por_nombre con tipo_base');
            }

            // Si el modo es replace, primero eliminar contenido existente
            if (modo === "replace") {
                // Obtener bloques existentes y eliminarlos
                const existingBlocks = await this.makeRequest(`https://api.notion.com/v1/blocks/${pageId}/children`, 'GET');
                if (existingBlocks.results && existingBlocks.results.length > 0) {
                    for (const block of existingBlocks.results) {
                        await this.makeRequest(`https://api.notion.com/v1/blocks/${block.id}`, 'DELETE');
                    }
                }
            }

            // Añadir nuevo contenido
            await this.añadirContenidoAPagina(pageId, contenido);

            let output = `✅ **Contenido ${modo === 'replace' ? 'reemplazado' : 'añadido'} exitosamente:**\n\n`;
            output += `🆔 **Página ID:** ${pageId}\n`;
            output += `📝 **Modo:** ${modo === 'replace' ? 'Reemplazar todo' : 'Añadir al final'}\n`;
            output += `📏 **Contenido:** ${contenido.length} caracteres añadidos\n`;

            return {
                content: [{ type: "text", text: output }]
            };

        } catch (error) {
            throw new Error(`Error escribiendo contenido: ${error.message}`);
        }
    }

    async listarArcos(args) {
        const { incluir_completados = false, limite = 20 } = args;

        try {
            const arcos = await this.obtenerArcos(incluir_completados, limite);

            let output = `📋 **Arcos disponibles** (${arcos.length} encontrados):\n\n`;

            if (arcos.length === 0) {
                output += `❌ No se encontraron arcos. Usa 'crear_evento' para crear el primero.`;
            } else {
                arcos.forEach((arco, index) => {
                    output += `${index + 1}. **${arco.name}**\n`;
                    output += `   🆔 ID: ${arco.id}\n`;
                    output += `   ✅ Completado: ${arco.completado ? 'Sí' : 'No'}\n`;
                    if (arco.tareas > 0) {
                        output += `   📝 Tareas: ${arco.tareas}\n`;
                    }
                    output += `\n`;
                });
            }

            return {
                content: [{ type: "text", text: output }]
            };

        } catch (error) {
            throw new Error(`Error listando arcos: ${error.message}`);
        }
    }

    async buscarPaginas(args) {
        const { tipo_base = "ambas", termino, limite = 10 } = args;

        if (!termino || termino.trim() === '') {
            throw new Error('Término de búsqueda es requerido');
        }

        try {
            const resultados = [];

            // Buscar en arcos si se especifica
            if (tipo_base === 'arcos' || tipo_base === 'ambas') {
                const arcosEncontrados = await this.buscarEnBaseDatos(this.arcos_db_id, termino, Math.ceil(limite / 2));
                arcosEncontrados.forEach(arco => {
                    resultados.push({
                        ...arco,
                        tipo: 'arco'
                    });
                });
            }

            // Buscar en quest si se especifica
            if (tipo_base === 'quest' || tipo_base === 'ambas') {
                const questsEncontradas = await this.buscarEnBaseDatos(this.quest_db_id, termino, Math.ceil(limite / 2));
                questsEncontradas.forEach(quest => {
                    resultados.push({
                        ...quest,
                        tipo: 'quest'
                    });
                });
            }

            let output = `🔍 **Resultados de búsqueda para: "${termino}"** (${resultados.length} encontrados)\n\n`;

            if (resultados.length === 0) {
                output += `❌ No se encontraron páginas que contengan "${termino}".`;
            } else {
                resultados.slice(0, limite).forEach((resultado, index) => {
                    output += `${index + 1}. **${resultado.name}** (${resultado.tipo})\n`;
                    output += `   🆔 ID: ${resultado.id}\n`;
                    if (resultado.descripcion) {
                        output += `   📝 ${resultado.descripcion}\n`;
                    }
                    output += `\n`;
                });
            }

            return {
                content: [{ type: "text", text: output }]
            };

        } catch (error) {
            throw new Error(`Error en búsqueda: ${error.message}`);
        }
    }

    // === MÉTODOS HELPER ===

    async makeRequest(url, method = 'GET', data = null, retries = 2) {
        return new Promise((resolve, reject) => {
            const urlObj = new URL(url);
            
            const options = {
                method: method,
                headers: {
                    'Authorization': `Bearer ${this.api_key}`,
                    'Notion-Version': MCP_CONFIG.api_version,
                    'Content-Type': 'application/json',
                    'User-Agent': 'Aura-MCP-Notion/1.0.0'
                }
            };

            const req = https.request(urlObj, options, (res) => {
                let responseData = '';

                res.on('data', (chunk) => {
                    responseData += chunk;
                });

                res.on('end', () => {
                    try {
                        if (res.statusCode < 200 || res.statusCode >= 300) {
                            reject(new Error(`HTTP ${res.statusCode}: ${responseData}`));
                            return;
                        }

                        const jsonData = JSON.parse(responseData);
                        
                        if (jsonData.object === 'error') {
                            reject(new Error(jsonData.message || 'Error de Notion API'));
                            return;
                        }

                        resolve(jsonData);
                    } catch (error) {
                        reject(new Error(`Error parsing JSON: ${error.message}`));
                    }
                });
            });

            req.on('error', async (error) => {
                if (retries > 0) {
                    try {
                        const result = await this.makeRequest(url, method, data, retries - 1);
                        resolve(result);
                    } catch (retryError) {
                        reject(new Error(`Request error after retries: ${error.message}`));
                    }
                } else {
                    reject(new Error(`Request error: ${error.message}`));
                }
            });

            req.setTimeout(30000, () => {
                req.destroy();
                if (retries > 0) {
                    this.makeRequest(url, method, data, retries - 1).then(resolve).catch(reject);
                } else {
                    reject(new Error('Request timeout'));
                }
            });

            if (data) {
                req.write(JSON.stringify(data));
            }
            req.end();
        });
    }

    async buscarArcoPorNombre(nombre) {
        try {
            const response = await this.makeRequest(`https://api.notion.com/v1/databases/${this.arcos_db_id}/query`, 'POST', {
                filter: {
                    property: "Name",
                    title: {
                        equals: nombre
                    }
                },
                page_size: 1
            });

            if (response.results && response.results.length > 0) {
                const arco = response.results[0];
                return {
                    id: arco.id,
                    name: arco.properties.Name.title[0]?.plain_text || nombre
                };
            }
            return null;
        } catch (error) {
            throw new Error(`Error buscando arco: ${error.message}`);
        }
    }

    async buscarPaginaPorNombre(nombre, tipo) {
        const databaseId = tipo === 'arcos' ? this.arcos_db_id : this.quest_db_id;
        
        try {
            const response = await this.makeRequest(`https://api.notion.com/v1/databases/${databaseId}/query`, 'POST', {
                filter: {
                    property: "Name",
                    title: {
                        equals: nombre
                    }
                },
                page_size: 1
            });

            if (response.results && response.results.length > 0) {
                return response.results[0];
            }
            return null;
        } catch (error) {
            throw new Error(`Error buscando página: ${error.message}`);
        }
    }

    async obtenerArcos(incluirCompletados, limite) {
        try {
            const queryData = {
                page_size: Math.min(limite, 100),
                sorts: [
                    {
                        property: "Name",
                        direction: "ascending"
                    }
                ]
            };

            if (!incluirCompletados) {
                queryData.filter = {
                    property: "clear!",
                    checkbox: {
                        equals: false
                    }
                };
            }

            const response = await this.makeRequest(`https://api.notion.com/v1/databases/${this.arcos_db_id}/query`, 'POST', queryData);

            return response.results.map(arco => ({
                id: arco.id,
                name: arco.properties.Name.title[0]?.plain_text || 'Sin nombre',
                completado: arco.properties["clear!"]?.checkbox || false,
                tareas: arco.properties.quest?.relation?.length || 0
            }));

        } catch (error) {
            throw new Error(`Error obteniendo arcos: ${error.message}`);
        }
    }

    async buscarEnBaseDatos(databaseId, termino, limite) {
        try {
            const response = await this.makeRequest(`https://api.notion.com/v1/databases/${databaseId}/query`, 'POST', {
                filter: {
                    property: "Name",
                    title: {
                        contains: termino
                    }
                },
                page_size: Math.min(limite, 50)
            });

            return response.results.map(pagina => ({
                id: pagina.id,
                name: pagina.properties.Name.title[0]?.plain_text || 'Sin nombre',
                descripcion: pagina.properties.Description?.rich_text[0]?.plain_text || null
            }));

        } catch (error) {
            throw new Error(`Error buscando en base de datos: ${error.message}`);
        }
    }

    async añadirContenidoAPagina(pageId, contenido) {
        try {
            // Convertir contenido a bloques de Notion
            const blocks = this.convertirTextoABloques(contenido);
            
            // Añadir bloques a la página
            await this.makeRequest(`https://api.notion.com/v1/blocks/${pageId}/children`, 'PATCH', {
                children: blocks
            });

        } catch (error) {
            throw new Error(`Error añadiendo contenido: ${error.message}`);
        }
    }

    convertirTextoABloques(texto) {
        const lineas = texto.split('\n').filter(linea => linea.trim() !== '');
        const blocks = [];

        for (const linea of lineas) {
            const lineaTrimmed = linea.trim();
            
            if (lineaTrimmed.startsWith('# ')) {
                // Título nivel 1
                blocks.push({
                    object: "block",
                    type: "heading_1",
                    heading_1: {
                        rich_text: [{ type: "text", text: { content: lineaTrimmed.substring(2) } }]
                    }
                });
            } else if (lineaTrimmed.startsWith('## ')) {
                // Título nivel 2
                blocks.push({
                    object: "block",
                    type: "heading_2",
                    heading_2: {
                        rich_text: [{ type: "text", text: { content: lineaTrimmed.substring(3) } }]
                    }
                });
            } else if (lineaTrimmed.startsWith('- ') || lineaTrimmed.startsWith('* ')) {
                // Lista con viñetas
                blocks.push({
                    object: "block",
                    type: "bulleted_list_item",
                    bulleted_list_item: {
                        rich_text: [{ type: "text", text: { content: lineaTrimmed.substring(2) } }]
                    }
                });
            } else {
                // Párrafo normal
                blocks.push({
                    object: "block",
                    type: "paragraph",
                    paragraph: {
                        rich_text: [{ type: "text", text: { content: lineaTrimmed } }]
                    }
                });
            }
        }

        return blocks;
    }
}

// ======= CLI =======
async function main() {
    try {
        const server = new NotionServer();
        console.error(`🚀 Notion MCP Server iniciado exitosamente`);
        console.error(`📊 Bases de datos configuradas: arcos (${server.arcos_db_id}), quest (${server.quest_db_id})`);
    } catch (error) {
        console.error(`❌ Error: ${error.message}`);
        process.exit(1);
    }

    const server = new NotionServer();

    // Manejo de entrada por stdin
    process.stdin.setEncoding('utf8');
    let buffer = '';
    
    process.stdin.on('data', async (chunk) => {
        buffer += chunk;
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
            if (!line.trim()) continue;
            
            try {
                const request = JSON.parse(line);
                const response = await server.handleRequest(request);
                console.log(JSON.stringify(response));
            } catch (error) {
                console.log(JSON.stringify({ 
                    jsonrpc: "2.0", 
                    id: null, 
                    error: { 
                        code: -1, 
                        message: `Error de parsing: ${error.message}` 
                    } 
                }));
            }
        }
    });

    process.stdin.on('end', () => process.exit(0));
    
    process.on('SIGINT', () => {
        console.error('🛑 Notion MCP Server terminado');
        process.exit(0);
    });
}

if (require.main === module) {
    main().catch((err) => {
        console.error('❌ Error fatal:', err);
        process.exit(1);
    });
}

module.exports = NotionServer;

