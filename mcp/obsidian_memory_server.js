#!/usr/bin/env node

/**
 * Servidor MCP para Memoria Centralizada con Baúl de Obsidian
 * Compatible con la arquitectura MCP existente de Aura
 */

const fs = require('fs').promises;
const path = require('path');
const { createReadStream, createWriteStream } = require('fs');
const { pipeline } = require('stream/promises');

// Configuración del servidor MCP
const MCP_CONFIG = {
    name: "obsidian-memory",
    version: "1.0.0",
    vault_path: process.env.OBSIDIAN_VAULT_PATH || "/home/ary/Documents/Ary Vault"
};

class ObsidianMemoryServer {
    constructor() {
        this.vault_path = MCP_CONFIG.vault_path;
        this.tools = [
            {
                name: "search_notes",
                description: "Busca notas en el Baúl de Obsidian por contenido, nombre, etiquetas o wikilinks. Soporta búsqueda semántica básica.",
                inputSchema: {
                    type: "object",
                    properties: {
                        query: {
                            type: "string",
                            description: "Término de búsqueda (texto, #etiqueta, [[wikilink]])"
                        },
                        search_type: {
                            type: "string",
                            enum: ["content", "filename", "tags", "wikilinks", "all"],
                            default: "all",
                            description: "Tipo de búsqueda: content (contenido), filename (nombre), tags (etiquetas), wikilinks (enlaces), all (todo)"
                        },
                        max_results: {
                            type: "integer",
                            default: 10,
                            description: "Máximo número de resultados"
                        }
                    },
                    required: ["query"]
                }
            },
            {
                name: "read_note",
                description: "Lee el contenido completo de una nota específica del Baúl de Obsidian.",
                inputSchema: {
                    type: "object",
                    properties: {
                        note_path: {
                            type: "string",
                            description: "Ruta relativa de la nota desde el vault (ej: 'Proyectos/Aura/MCPS.md')"
                        }
                    },
                    required: ["note_path"]
                }
            },
            {
                name: "create_note",
                description: "Crea una nueva nota en el Baúl de Obsidian con el contenido especificado.",
                inputSchema: {
                    type: "object",
                    properties: {
                        note_path: {
                            type: "string",
                            description: "Ruta donde crear la nota (ej: 'Proyectos/Nueva Nota.md')"
                        },
                        content: {
                            type: "string",
                            description: "Contenido de la nota en formato Markdown"
                        },
                        overwrite: {
                            type: "boolean",
                            default: false,
                            description: "Si sobrescribir la nota si ya existe"
                        }
                    },
                    required: ["note_path", "content"]
                }
            },
            {
                name: "update_note",
                description: "Actualiza una nota existente agregando contenido o reemplazándolo.",
                inputSchema: {
                    type: "object",
                    properties: {
                        note_path: {
                            type: "string",
                            description: "Ruta de la nota a actualizar"
                        },
                        content: {
                            type: "string",
                            description: "Nuevo contenido"
                        },
                        mode: {
                            type: "string",
                            enum: ["append", "prepend", "replace"],
                            default: "append",
                            description: "Modo de actualización: append (agregar al final), prepend (agregar al inicio), replace (reemplazar)"
                        }
                    },
                    required: ["note_path", "content"]
                }
            },
            {
                name: "list_vault_structure",
                description: "Lista la estructura completa del Baúl de Obsidian mostrando carpetas y archivos.",
                inputSchema: {
                    type: "object",
                    properties: {
                        max_depth: {
                            type: "integer",
                            default: 10,
                            description: "Profundidad máxima de listado"
                        }
                    }
                }
            },
            {
                name: "get_note_metadata",
                description: "Obtiene metadatos de una nota: tamaño, fecha de modificación, etiquetas encontradas, wikilinks.",
                inputSchema: {
                    type: "object",
                    properties: {
                        note_path: {
                            type: "string",
                            description: "Ruta de la nota"
                        }
                    },
                    required: ["note_path"]
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
                id,
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
            case 'search_notes':
                return await this.searchNotes(args);
            case 'read_note':
                return await this.readNote(args);
            case 'create_note':
                return await this.createNote(args);
            case 'update_note':
                return await this.updateNote(args);
            case 'list_vault_structure':
                return await this.listVaultStructure(args);
            case 'get_note_metadata':
                return await this.getNoteMetadata(args);
            default:
                throw new Error(`Herramienta desconocida: ${name}`);
        }
    }

    async searchNotes(args) {
        const { query, search_type = "all", max_results = 10 } = args;
        
        if (!query || query.trim() === '') {
            throw new Error('Query de búsqueda requerido');
        }

        const results = [];
        const searchTerm = query.toLowerCase();

        // Detectar tipo de búsqueda automáticamente
        const isTagSearch = query.startsWith('#');
        const isWikilinkSearch = query.includes('[[') || query.includes(']]');
        
        try {
            await this.searchInDirectory(this.vault_path, searchTerm, search_type, isTagSearch, isWikilinkSearch, results, max_results);
            
            // Ordenar resultados por relevancia
            results.sort((a, b) => b.relevance - a.relevance);
            
            return {
                content: [
                    {
                        type: "text",
                        text: this.formatSearchResults(results.slice(0, max_results), query)
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error en búsqueda: ${error.message}`);
        }
    }

    async searchInDirectory(dir, searchTerm, searchType, isTagSearch, isWikilinkSearch, results, maxResults) {
        if (results.length >= maxResults) return;

        try {
            const entries = await fs.readdir(dir, { withFileTypes: true });
            
            for (const entry of entries) {
                if (results.length >= maxResults) break;
                
                const fullPath = path.join(dir, entry.name);
                
                if (entry.isDirectory()) {
                    await this.searchInDirectory(fullPath, searchTerm, searchType, isTagSearch, isWikilinkSearch, results, maxResults);
                } else if (entry.isFile() && entry.name.endsWith('.md')) {
                    try {
                        const content = await fs.readFile(fullPath, 'utf8');
                        const relativePath = path.relative(this.vault_path, fullPath);
                        
                        let relevance = 0;
                        let matchDetails = [];
                        
                        // Búsqueda por nombre de archivo
                        if (searchType === 'filename' || searchType === 'all') {
                            if (entry.name.toLowerCase().includes(searchTerm)) {
                                relevance += 10;
                                matchDetails.push(`Nombre: ${entry.name}`);
                            }
                        }
                        
                        // Búsqueda por contenido
                        if (searchType === 'content' || searchType === 'all') {
                            const contentLower = content.toLowerCase();
                            if (contentLower.includes(searchTerm)) {
                                const matches = (contentLower.match(new RegExp(searchTerm, 'gi')) || []).length;
                                relevance += matches * 2;
                                matchDetails.push(`Contenido: ${matches} coincidencias`);
                            }
                        }
                        
                        // Búsqueda por etiquetas
                        if (searchType === 'tags' || searchType === 'all' || isTagSearch) {
                            const tags = this.extractTags(content);
                            const tagToSearch = isTagSearch ? searchTerm.substring(1) : searchTerm;
                            const matchingTags = tags.filter(tag => tag.toLowerCase().includes(tagToSearch));
                            if (matchingTags.length > 0) {
                                relevance += matchingTags.length * 5;
                                matchDetails.push(`Etiquetas: ${matchingTags.join(', ')}`);
                            }
                        }
                        
                        // Búsqueda por wikilinks
                        if (searchType === 'wikilinks' || searchType === 'all' || isWikilinkSearch) {
                            const wikilinks = this.extractWikilinks(content);
                            const linkToSearch = isWikilinkSearch ? searchTerm.replace(/\[\[|\]\]/g, '') : searchTerm;
                            const matchingLinks = wikilinks.filter(link => link.toLowerCase().includes(linkToSearch));
                            if (matchingLinks.length > 0) {
                                relevance += matchingLinks.length * 3;
                                matchDetails.push(`Wikilinks: ${matchingLinks.join(', ')}`);
                            }
                        }
                        
                        if (relevance > 0) {
                            results.push({
                                path: relativePath,
                                filename: entry.name,
                                relevance: relevance,
                                matchDetails: matchDetails,
                                preview: this.generatePreview(content, searchTerm)
                            });
                        }
                    } catch (error) {
                        // Continuar si hay error leyendo un archivo específico
                        console.error(`Error leyendo ${fullPath}:`, error.message);
                    }
                }
            }
        } catch (error) {
            throw new Error(`Error accediendo al directorio ${dir}: ${error.message}`);
        }
    }

    extractTags(content) {
        const tagRegex = /#[a-zA-Z0-9_-]+/g;
        const matches = content.match(tagRegex) || [];
        return matches.map(tag => tag.substring(1)); // Remover el #
    }

    extractWikilinks(content) {
        const wikilinkRegex = /\[\[([^\]]+)\]\]/g;
        const matches = [];
        let match;
        while ((match = wikilinkRegex.exec(content)) !== null) {
            matches.push(match[1]);
        }
        return matches;
    }

    generatePreview(content, searchTerm) {
        const lines = content.split('\n');
        const previewLines = [];
        
        for (let i = 0; i < lines.length && previewLines.length < 3; i++) {
            if (lines[i].toLowerCase().includes(searchTerm.toLowerCase())) {
                previewLines.push(lines[i].trim());
            }
        }
        
        if (previewLines.length === 0) {
            // Si no hay coincidencias, tomar las primeras líneas
            return lines.slice(0, 2).join('\n').substring(0, 200) + '...';
        }
        
        return previewLines.join('\n').substring(0, 200) + '...';
    }

    formatSearchResults(results, query) {
        if (results.length === 0) {
            return `No se encontraron resultados para: "${query}"`;
        }

        let output = `🔍 Resultados de búsqueda para: "${query}" (${results.length} encontrados)\n\n`;
        
        results.forEach((result, index) => {
            output += `${index + 1}. 📄 **${result.filename}**\n`;
            output += `   📂 Ruta: ${result.path}\n`;
            output += `   🎯 Relevancia: ${result.relevance}\n`;
            output += `   🔍 Coincidencias: ${result.matchDetails.join(', ')}\n`;
            output += `   📖 Vista previa:\n   ${result.preview}\n\n`;
        });

        return output;
    }

    async readNote(args) {
        const { note_path } = args;
        
        if (!note_path) {
            throw new Error('Ruta de nota requerida');
        }

        const fullPath = path.join(this.vault_path, note_path);
        
        try {
            const content = await fs.readFile(fullPath, 'utf8');
            const stats = await fs.stat(fullPath);
            
            return {
                content: [
                    {
                        type: "text",
                        text: `📄 **${path.basename(note_path)}**\n📂 Ruta: ${note_path}\n📅 Última modificación: ${stats.mtime.toLocaleString()}\n📏 Tamaño: ${stats.size} bytes\n\n---\n\n${content}`
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error leyendo la nota: ${error.message}`);
        }
    }

    async createNote(args) {
        const { note_path, content, overwrite = false } = args;
        
        if (!note_path || !content) {
            throw new Error('Ruta de nota y contenido requeridos');
        }

        const fullPath = path.join(this.vault_path, note_path);
        const dirPath = path.dirname(fullPath);

        try {
            // Crear directorio si no existe
            await fs.mkdir(dirPath, { recursive: true });
            
            // Verificar si existe y no se permite sobrescribir
            try {
                await fs.access(fullPath);
                if (!overwrite) {
                    throw new Error('La nota ya existe. Usa overwrite=true para sobrescribir');
                }
            } catch (error) {
                // El archivo no existe, está bien
            }

            // Agregar timestamp al contenido
            const timestamp = new Date().toISOString();
            const finalContent = `# ${path.basename(note_path, '.md')}\n\n*Creado: ${timestamp}*\n\n${content}`;
            
            await fs.writeFile(fullPath, finalContent, 'utf8');
            
            return {
                content: [
                    {
                        type: "text",
                        text: `✅ Nota creada exitosamente:\n📄 **${path.basename(note_path)}**\n📂 Ruta: ${note_path}\n📏 Tamaño: ${finalContent.length} caracteres`
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error creando la nota: ${error.message}`);
        }
    }

    async updateNote(args) {
        const { note_path, content, mode = 'append' } = args;
        
        if (!note_path || !content) {
            throw new Error('Ruta de nota y contenido requeridos');
        }

        const fullPath = path.join(this.vault_path, note_path);
        
        try {
            let existingContent = '';
            try {
                existingContent = await fs.readFile(fullPath, 'utf8');
            } catch (error) {
                throw new Error('La nota no existe. Usa create_note para crear una nueva nota');
            }

            let finalContent;
            const timestamp = new Date().toISOString();
            
            switch (mode) {
                case 'append':
                    finalContent = `${existingContent}\n\n---\n*Actualizado: ${timestamp}*\n\n${content}`;
                    break;
                case 'prepend':
                    finalContent = `*Actualizado: ${timestamp}*\n\n${content}\n\n---\n\n${existingContent}`;
                    break;
                case 'replace':
                    finalContent = `*Actualizado: ${timestamp}*\n\n${content}`;
                    break;
                default:
                    throw new Error(`Modo de actualización no válido: ${mode}`);
            }
            
            await fs.writeFile(fullPath, finalContent, 'utf8');
            
            return {
                content: [
                    {
                        type: "text",
                        text: `✅ Nota actualizada exitosamente:\n📄 **${path.basename(note_path)}**\n📂 Ruta: ${note_path}\n📅 Última modificación: ${timestamp}\n📏 Tamaño: ${finalContent.length} caracteres`
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error actualizando la nota: ${error.message}`);
        }
    }

    async listVaultStructure(args) {
        const { max_depth = 10 } = args;
        
        const results = [];
        
        try {
            await this.listDirectory(this.vault_path, results, max_depth);
            
            return {
                content: [
                    {
                        type: "text",
                        text: this.formatVaultStructure(results)
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error listando la estructura del Baúl: ${error.message}`);
        }
    }

    async listDirectory(dir, results, maxDepth) {
        if (maxDepth <= 0) return;

        try {
            const entries = await fs.readdir(dir, { withFileTypes: true });
            
            for (const entry of entries) {
                if (entry.isDirectory()) {
                    results.push({
                        type: "directory",
                        name: entry.name,
                        path: path.join(dir, entry.name)
                    });
                    await this.listDirectory(path.join(dir, entry.name), results, maxDepth - 1);
                } else if (entry.isFile() && entry.name.endsWith('.md')) {
                    results.push({
                        type: "file",
                        name: entry.name,
                        path: path.join(dir, entry.name)
                    });
                }
            }
        } catch (error) {
            throw new Error(`Error accediendo al directorio ${dir}: ${error.message}`);
        }
    }

    formatVaultStructure(results) {
        let output = '';
        
        results.forEach((item, index) => {
            output += `${index + 1}. ${item.type === 'directory' ? '📁' : '📄'} **${item.name}**\n`;
            output += `   📂 Ruta: ${item.path}\n`;
        });

        return output;
    }

    async getNoteMetadata(args) {
        const { note_path } = args;
        
        if (!note_path) {
            throw new Error('Ruta de nota requerida');
        }

        const fullPath = path.join(this.vault_path, note_path);
        
        try {
            const stats = await fs.stat(fullPath);
            const content = await fs.readFile(fullPath, 'utf8');
            
            const tags = this.extractTags(content);
            const wikilinks = this.extractWikilinks(content);
            
            return {
                content: [
                    {
                        type: "text",
                        text: `📄 **${path.basename(note_path)}**\n📂 Ruta: ${note_path}\n📅 Última modificación: ${stats.mtime.toLocaleString()}\n📏 Tamaño: ${stats.size} bytes\n📏 Tamaño: ${content.length} caracteres\n\n---\n\nEtiquetas: ${tags.join(', ')}\n\nWikilinks: ${wikilinks.join(', ')}`
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error obteniendo metadatos de la nota: ${error.message}`);
        }
    }
}

// ======= CLI =======
async function main() {
    const server = new ObsidianMemoryServer();
    // Comprobar que el vault existe
    try {
        await fs.access(server.vault_path);
        console.error(`🗃️ Obsidian Memory MCP Server iniciado para vault: ${server.vault_path}`);
    } catch (err) {
        console.error(`❌ Error: No se puede acceder al vault en ${server.vault_path}`);
        process.exit(1);
    }

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
                console.log(JSON.stringify({ jsonrpc: "2.0", id: null, error: { code: -1, message: `Error de parsing: ${error.message}` } }));
            }
        }
    });

    process.stdin.on('end', () => process.exit(0));
    process.on('SIGINT', () => {
        console.error('🛑 Servidor MCP terminado');
        process.exit(0);
    });
}

if (require.main === module) {
    main().catch((err) => {
        console.error('❌ Error fatal:', err);
        process.exit(1);
    });
}

module.exports = ObsidianMemoryServer;