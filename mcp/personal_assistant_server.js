#!/usr/bin/env node

/**
 * Servidor MCP para Asistente Personal - Gestión de Tareas Diarias
 * Gestiona archivos semanales .md en formato YYYY-MM-DD_DD.md
 * Compatible con la arquitectura MCP existente de Aura
 */

const fs = require('fs').promises;
const path = require('path');

// Configuración del servidor MCP
const MCP_CONFIG = {
    name: "personal-assistant",
    version: "1.0.0",
    daily_path: process.env.DAILY_PATH || "/home/ary/Documents/Ary Vault/Daily"
};

class PersonalAssistantServer {
    constructor() {
        this.daily_path = MCP_CONFIG.daily_path;
        this.tools = [
            {
                name: "list_pending_tasks",
                description: "Lista todas las tareas pendientes filtradas por período (día, semana o mes).",
                inputSchema: {
                    type: "object",
                    properties: {
                        period: {
                            type: "string",
                            enum: ["day", "week", "month", "all"],
                            default: "week",
                            description: "Período: day (hoy), week (esta semana), month (este mes), all (todas)"
                        },
                        date: {
                            type: "string",
                            description: "Fecha específica en formato YYYY-MM-DD (opcional, usa fecha actual si no se especifica)"
                        }
                    }
                }
            },
            {
                name: "create_weekly_file",
                description: "Crea un nuevo archivo semanal .md con la estructura de template para gestión de tareas.",
                inputSchema: {
                    type: "object",
                    properties: {
                        start_date: {
                            type: "string",
                            description: "Fecha de inicio de la semana en formato YYYY-MM-DD (debe ser lunes)"
                        },
                        overwrite: {
                            type: "boolean",
                            default: false,
                            description: "Si sobrescribir el archivo si ya existe"
                        }
                    },
                    required: ["start_date"]
                }
            },
            {
                name: "delete_weekly_file",
                description: "Elimina un archivo semanal específico.",
                inputSchema: {
                    type: "object",
                    properties: {
                        start_date: {
                            type: "string",
                            description: "Fecha de inicio de la semana en formato YYYY-MM-DD"
                        },
                        confirm: {
                            type: "boolean",
                            default: false,
                            description: "Confirmación para eliminar (debe ser true)"
                        }
                    },
                    required: ["start_date", "confirm"]
                }
            },
            {
                name: "read_weekly_file",
                description: "Lee el contenido completo de un archivo semanal específico.",
                inputSchema: {
                    type: "object",
                    properties: {
                        start_date: {
                            type: "string",
                            description: "Fecha de inicio de la semana en formato YYYY-MM-DD"
                        }
                    },
                    required: ["start_date"]
                }
            },
            {
                name: "edit_task",
                description: "Edita tareas específicas: marcar como completada, eliminar tarea o agregar nueva tarea.",
                inputSchema: {
                    type: "object",
                    properties: {
                        start_date: {
                            type: "string",
                            description: "Fecha de inicio de la semana en formato YYYY-MM-DD"
                        },
                        day_of_week: {
                            type: "string",
                            enum: ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"],
                            description: "Día de la semana"
                        },
                        action: {
                            type: "string",
                            enum: ["complete", "add", "remove"],
                            description: "Acción: complete (marcar como hecha), add (agregar), remove (eliminar)"
                        },
                        task_text: {
                            type: "string",
                            description: "Texto de la tarea (para add) o texto a buscar (para complete/remove)"
                        },
                        time: {
                            type: "string",
                            description: "Hora de la tarea en formato HH:MM (opcional, solo para add)"
                        }
                    },
                    required: ["start_date", "day_of_week", "action", "task_text"]
                }
            },
            {
                name: "list_weekly_files",
                description: "Lista todos los archivos semanales disponibles en el directorio Daily.",
                inputSchema: {
                    type: "object",
                    properties: {
                        month: {
                            type: "string",
                            description: "Filtrar por mes en formato YYYY-MM (opcional)"
                        },
                        year: {
                            type: "string",
                            description: "Filtrar por año en formato YYYY (opcional)"
                        }
                    }
                }
            },
            {
                name: "get_week_summary",
                description: "Obtiene un resumen completo de la semana: tareas completadas, pendientes, porcentaje de progreso y estadísticas.",
                inputSchema: {
                    type: "object",
                    properties: {
                        start_date: {
                            type: "string",
                            description: "Fecha de inicio de la semana en formato YYYY-MM-DD"
                        },
                        include_details: {
                            type: "boolean",
                            default: true,
                            description: "Incluir detalles de las tareas en el resumen"
                        }
                    },
                    required: ["start_date"]
                }
            },
            {
                name: "search_tasks",
                description: "Busca tareas por texto en todos los archivos semanales o en un período específico.",
                inputSchema: {
                    type: "object",
                    properties: {
                        query: {
                            type: "string",
                            description: "Texto a buscar en las tareas"
                        },
                        status: {
                            type: "string",
                            enum: ["all", "pending", "completed"],
                            default: "all",
                            description: "Filtrar por estado: all (todas), pending (pendientes), completed (completadas)"
                        },
                        period: {
                            type: "string",
                            enum: ["week", "month", "all"],
                            default: "all",
                            description: "Período de búsqueda"
                        },
                        date: {
                            type: "string",
                            description: "Fecha de referencia en formato YYYY-MM-DD (opcional)"
                        }
                    },
                    required: ["query"]
                }
            },
            {
                name: "get_task_statistics",
                description: "Obtiene estadísticas de productividad: tareas por día, tendencias, días más productivos.",
                inputSchema: {
                    type: "object",
                    properties: {
                        period: {
                            type: "string",
                            enum: ["week", "month", "all"],
                            default: "month",
                            description: "Período para las estadísticas"
                        },
                        start_date: {
                            type: "string",
                            description: "Fecha de inicio del período en formato YYYY-MM-DD (opcional)"
                        }
                    }
                }
            },
            {
                name: "move_task",
                description: "Mueve una tarea de un día a otro dentro de la misma semana o entre semanas diferentes.",
                inputSchema: {
                    type: "object",
                    properties: {
                        from_start_date: {
                            type: "string",
                            description: "Fecha de inicio de la semana origen en formato YYYY-MM-DD"
                        },
                        from_day: {
                            type: "string",
                            enum: ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"],
                            description: "Día origen"
                        },
                        to_start_date: {
                            type: "string",
                            description: "Fecha de inicio de la semana destino en formato YYYY-MM-DD"
                        },
                        to_day: {
                            type: "string",
                            enum: ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"],
                            description: "Día destino"
                        },
                        task_text: {
                            type: "string",
                            description: "Texto de la tarea a mover"
                        }
                    },
                    required: ["from_start_date", "from_day", "to_start_date", "to_day", "task_text"]
                }
            },
            {
                name: "duplicate_week",
                description: "Copia la estructura y tareas de una semana a otra, útil para crear plantillas o repetir patrones semanales.",
                inputSchema: {
                    type: "object",
                    properties: {
                        source_start_date: {
                            type: "string",
                            description: "Fecha de inicio de la semana origen en formato YYYY-MM-DD"
                        },
                        target_start_date: {
                            type: "string",
                            description: "Fecha de inicio de la semana destino en formato YYYY-MM-DD"
                        },
                        copy_completed: {
                            type: "boolean",
                            default: false,
                            description: "Si copiar también las tareas marcadas como completadas"
                        },
                        overwrite: {
                            type: "boolean",
                            default: false,
                            description: "Si sobrescribir el archivo destino si ya existe"
                        }
                    },
                    required: ["source_start_date", "target_start_date"]
                }
            },
            {
                name: "set_recurring_tasks",
                description: "Configura tareas recurrentes que se pueden aplicar a múltiples semanas (plantillas de rutinas).",
                inputSchema: {
                    type: "object",
                    properties: {
                        template_name: {
                            type: "string",
                            description: "Nombre de la plantilla de tareas recurrentes"
                        },
                        tasks: {
                            type: "array",
                            items: {
                                type: "object",
                                properties: {
                                    day: {
                                        type: "string",
                                        enum: ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
                                    },
                                    time: {
                                        type: "string",
                                        description: "Hora en formato HH:MM (opcional)"
                                    },
                                    task: {
                                        type: "string",
                                        description: "Descripción de la tarea"
                                    }
                                },
                                required: ["day", "task"]
                            },
                            description: "Lista de tareas recurrentes"
                        },
                        apply_to_week: {
                            type: "string",
                            description: "Fecha de inicio de semana para aplicar plantilla inmediatamente (opcional)"
                        }
                    },
                    required: ["template_name", "tasks"]
                }
            },
            {
                name: "get_current_date",
                description: "Obtiene la fecha y hora actual del sistema con información estructurada para facilitar otras operaciones.",
                inputSchema: {
                    type: "object",
                    properties: {
                        format: {
                            type: "string",
                            enum: ["structured", "iso", "readable", "date_only", "time_only"],
                            default: "structured",
                            description: "Formato de salida: structured (información completa), iso (ISO 8601), readable (legible), date_only (solo fecha), time_only (solo hora)"
                        }
                    }
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
            case 'list_pending_tasks':
                return await this.listPendingTasks(args);
            case 'create_weekly_file':
                return await this.createWeeklyFile(args);
            case 'delete_weekly_file':
                return await this.deleteWeeklyFile(args);
            case 'read_weekly_file':
                return await this.readWeeklyFile(args);
            case 'edit_task':
                return await this.editTask(args);
            case 'list_weekly_files':
                return await this.listWeeklyFiles(args);
            case 'get_week_summary':
                return await this.getWeekSummary(args);
            case 'search_tasks':
                return await this.searchTasks(args);
            case 'get_task_statistics':
                return await this.getTaskStatistics(args);
            case 'move_task':
                return await this.moveTask(args);
            case 'duplicate_week':
                return await this.duplicateWeek(args);
            case 'set_recurring_tasks':
                return await this.setRecurringTasks(args);
            case 'get_current_date':
                return await this.getCurrentDate(args);
            default:
                throw new Error(`Herramienta desconocida: ${name}`);
        }
    }

    getWeekInfo(date = null) {
        // Usar fecha actual si no se proporciona o crear nueva fecha si es string
        let currentDate;
        if (!date) {
            // Usar fecha local en zona horaria America/Bogota
            const now = new Date();
            const localTime = new Date(now.toLocaleString('en-US', { timeZone: 'America/Bogota' }));
            currentDate = localTime;
        } else if (typeof date === 'string') {
            // Si es string, crear fecha local
            const parts = date.split('-');
            currentDate = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]), 12, 0, 0);
        } else {
            currentDate = new Date(date);
        }
        
        // Obtener el lunes de la semana actual
        const dayOfWeek = currentDate.getDay();
        const diffToMonday = (dayOfWeek === 0 ? -6 : 1 - dayOfWeek);
        
        const monday = new Date(currentDate);
        monday.setDate(currentDate.getDate() + diffToMonday);
        
        const sunday = new Date(monday);
        sunday.setDate(monday.getDate() + 6);
        
        // Formato YYYY-MM-DD_DD usando fechas locales
        const mondayStr = `${monday.getFullYear()}-${(monday.getMonth() + 1).toString().padStart(2, '0')}-${monday.getDate().toString().padStart(2, '0')}`;
        const sundayDay = sunday.getDate().toString().padStart(2, '0');
        const filename = `${mondayStr}_${sundayDay}.md`;
        
        // Número de semana del año
        const startOfYear = new Date(monday.getFullYear(), 0, 1);
        const weekNumber = Math.ceil(((monday - startOfYear) / 86400000 + startOfYear.getDay() + 1) / 7);
        
        return {
            monday,
            sunday,
            filename,
            weekNumber,
            year: monday.getFullYear(),
            mondayFormatted: monday.toLocaleDateString('es-CO', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', timeZone: 'America/Bogota' }),
            sundayFormatted: sunday.toLocaleDateString('es-CO', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', timeZone: 'America/Bogota' })
        };
    }

    async listPendingTasks(args) {
        const { period = "week", date } = args;
        
        try {
            const targetDate = date ? new Date(date + 'T12:00:00') : new Date();
            const pendingTasks = [];
            
            let filesToCheck = [];
            
            switch (period) {
                case 'day':
                    // Solo el archivo de la semana actual
                    const weekInfo = this.getWeekInfo(targetDate);
                    filesToCheck = [weekInfo.filename];
                    break;
                case 'week':
                    // Solo el archivo de la semana especificada
                    const currentWeekInfo = this.getWeekInfo(targetDate);
                    filesToCheck = [currentWeekInfo.filename];
                    break;
                case 'month':
                    // Todos los archivos del mes
                    const year = targetDate.getFullYear();
                    const month = (targetDate.getMonth() + 1).toString().padStart(2, '0');
                    const files = await fs.readdir(this.daily_path);
                    filesToCheck = files.filter(file => 
                        file.endsWith('.md') && file.startsWith(`${year}-${month}`)
                    );
                    break;
                case 'all':
                    // Todos los archivos
                    const allFiles = await fs.readdir(this.daily_path);
                    filesToCheck = allFiles.filter(file => file.endsWith('.md'));
                    break;
            }
            
            for (const filename of filesToCheck) {
                const filePath = path.join(this.daily_path, filename);
                
                try {
                    const content = await fs.readFile(filePath, 'utf8');
                    const tasks = this.extractPendingTasks(content, filename, period === 'day' ? targetDate : null);
                    pendingTasks.push(...tasks);
                } catch (error) {
                    // Continuar si no se puede leer un archivo - no mostrar error si es archivo esperado pero no existe
                    if (error.code !== 'ENOENT') {
                        console.error(`Error leyendo ${filename}: ${error.message}`);
                    }
                }
            }
            
            // Ordenar por fecha
            pendingTasks.sort((a, b) => new Date(a.date) - new Date(b.date));
            
            return {
                content: [
                    {
                        type: "text",
                        text: this.formatPendingTasks(pendingTasks, period, targetDate)
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error listando tareas pendientes: ${error.message}`);
        }
    }

    extractPendingTasks(content, filename, filterDate = null) {
        const tasks = [];
        const lines = content.split('\n');
        let currentDay = null;
        let currentDate = null;
        
        // Extraer fechas del nombre del archivo
        const dateMatch = filename.match(/(\d{4}-\d{2}-\d{2})_(\d{2})\.md/);
        if (!dateMatch) return tasks;
        
        const [, startDateStr, endDay] = dateMatch;
        const startDate = new Date(startDateStr + 'T12:00:00');
        
        for (const line of lines) {
            // Detectar días de la semana
            const dayMatch = line.match(/^## (Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo) (\d+) de (\w+)/);
            if (dayMatch) {
                const [, dayName, day] = dayMatch;
                
                // Calcular la fecha exacta
                const dayIndex = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'].indexOf(dayName.toLowerCase());
                currentDate = new Date(startDate);
                currentDate.setDate(startDate.getDate() + dayIndex);
                currentDay = dayName.toLowerCase();
                continue;
            }
            
            // Detectar tareas pendientes (- [ ]) - incluyendo las vacías
            const taskMatch = line.match(/^- \[ \] (.*)$/);
            if (taskMatch && currentDay && currentDate && taskMatch[1].trim()) {
                const taskText = taskMatch[1];
                
                // Si se filtra por día específico, verificar que coincida
                if (filterDate) {
                    const currentDateStr = currentDate.toISOString().split('T')[0];
                    const filterDateStr = filterDate.toISOString().split('T')[0];
                    if (currentDateStr !== filterDateStr) continue;
                }
                
                // Extraer hora si existe
                const timeMatch = taskText.match(/^(\d{2}:\d{2})\s+(.+)$/);
                const time = timeMatch ? timeMatch[1] : null;
                const description = timeMatch ? timeMatch[2] : taskText;
                
                tasks.push({
                    file: filename,
                    day: currentDay,
                    date: currentDate.toISOString().split('T')[0],
                    time: time,
                    description: description,
                    fullText: taskText
                });
            }
        }
        
        return tasks;
    }

    formatPendingTasks(tasks, period, targetDate) {
        if (tasks.length === 0) {
            return `📋 **No hay tareas pendientes para ${period === 'day' ? 'hoy' : period === 'week' ? 'esta semana' : period === 'month' ? 'este mes' : 'ningún período'}**`;
        }
        
        let output = `📋 **Tareas pendientes (${tasks.length} encontradas)**\n\n`;
        
        let currentFile = null;
        
        for (const task of tasks) {
            if (task.file !== currentFile) {
                currentFile = task.file;
                output += `📁 **Archivo:** ${task.file}\n\n`;
            }
            
            output += `📅 **${task.day}** (${task.date})\n`;
            output += `  ${task.time ? `🕐 ${task.time} - ` : '📝 '}${task.description}\n\n`;
        }
        
        return output;
    }

    async createWeeklyFile(args) {
        const { start_date, overwrite = false } = args;
        
        if (!start_date) {
            throw new Error('Fecha de inicio requerida');
        }
        
        try {
            const startDate = new Date(start_date + 'T12:00:00');
            
            // Verificar que sea lunes
            if (startDate.getDay() !== 1) {
                throw new Error('La fecha de inicio debe ser un lunes');
            }
            
            const weekInfo = this.getWeekInfo(startDate);
            const filePath = path.join(this.daily_path, weekInfo.filename);
            
            // Verificar si existe y no se permite sobrescribir
            try {
                await fs.access(filePath);
                if (!overwrite) {
                    throw new Error(`El archivo ${weekInfo.filename} ya existe. Usa overwrite=true para sobrescribir`);
                }
            } catch (error) {
                // El archivo no existe, está bien
            }
            
            // Crear directorio si no existe
            await fs.mkdir(this.daily_path, { recursive: true });
            
            // Generar contenido del template
            const content = this.generateWeeklyTemplate(weekInfo);
            
            await fs.writeFile(filePath, content, 'utf8');
            
            return {
                content: [
                    {
                        type: "text",
                        text: `✅ **Archivo semanal creado exitosamente:**\n📁 **Archivo:** ${weekInfo.filename}\n📅 **Semana:** ${weekInfo.mondayFormatted} - ${weekInfo.sundayFormatted}\n📏 **Tamaño:** ${content.length} caracteres`
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error creando archivo semanal: ${error.message}`);
        }
    }

    generateWeeklyTemplate(weekInfo) {
        const { monday, sunday } = weekInfo;
        const days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
        const months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
        
        let content = `# Semana ${monday.getDate().toString().padStart(2, '0')}-${sunday.getDate().toString().padStart(2, '0')} ${months[monday.getMonth()]} ${monday.getFullYear()}\n\n`;
        
        for (let i = 0; i < 7; i++) {
            const currentDate = new Date(monday);
            currentDate.setDate(monday.getDate() + i);
            
            const dayName = days[i];
            const day = currentDate.getDate();
            const month = months[currentDate.getMonth()];
            
            content += `## ${dayName} ${day} de ${month}\n`;
            content += `- [ ] \n\n`;
        }
        
        return content;
    }

    async deleteWeeklyFile(args) {
        const { start_date, confirm } = args;
        
        if (!start_date) {
            throw new Error('Fecha de inicio requerida');
        }
        
        if (!confirm) {
            throw new Error('Debes confirmar la eliminación estableciendo confirm=true');
        }
        
        try {
            const startDate = new Date(start_date + 'T12:00:00');
            const weekInfo = this.getWeekInfo(startDate);
            const filePath = path.join(this.daily_path, weekInfo.filename);
            
            // Verificar que existe
            await fs.access(filePath);
            
            // Eliminar archivo
            await fs.unlink(filePath);
            
            return {
                content: [
                    {
                        type: "text",
                        text: `🗑️ **Archivo semanal eliminado exitosamente:**\n📁 **Archivo:** ${weekInfo.filename}\n📅 **Semana:** ${weekInfo.mondayFormatted} - ${weekInfo.sundayFormatted}`
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error eliminando archivo semanal: ${error.message}`);
        }
    }

    async readWeeklyFile(args) {
        const { start_date } = args;
        
        if (!start_date) {
            throw new Error('Fecha de inicio requerida');
        }
        
        try {
            const startDate = new Date(start_date + 'T12:00:00');
            const weekInfo = this.getWeekInfo(startDate);
            const filePath = path.join(this.daily_path, weekInfo.filename);
            
            const content = await fs.readFile(filePath, 'utf8');
            const stats = await fs.stat(filePath);
            
            return {
                content: [
                    {
                        type: "text",
                        text: `📄 **${weekInfo.filename}**\n📂 Ruta: ${filePath}\n📅 Última modificación: ${stats.mtime.toLocaleString()}\n📏 Tamaño: ${stats.size} bytes\n\n---\n\n${content}`
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error leyendo archivo semanal: ${error.message}`);
        }
    }

    async editTask(args) {
        const { start_date, day_of_week, action, task_text, time } = args;
        
        if (!start_date || !day_of_week || !action || !task_text) {
            throw new Error('Todos los parámetros son requeridos: start_date, day_of_week, action, task_text');
        }
        
        try {
            const startDate = new Date(start_date + 'T12:00:00');
            const weekInfo = this.getWeekInfo(startDate);
            const filePath = path.join(this.daily_path, weekInfo.filename);
            
            let content = await fs.readFile(filePath, 'utf8');
            const lines = content.split('\n');
            
            const dayCapitalized = day_of_week.charAt(0).toUpperCase() + day_of_week.slice(1);
            const dayPattern = new RegExp(`^## ${dayCapitalized}`);
            
            let dayLineIndex = -1;
            let nextDayIndex = -1;
            
            // Encontrar el día específico
            for (let i = 0; i < lines.length; i++) {
                if (dayPattern.test(lines[i])) {
                    dayLineIndex = i;
                }
                if (dayLineIndex > -1 && i > dayLineIndex && lines[i].match(/^## (Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo)/)) {
                    nextDayIndex = i;
                    break;
                }
            }
            
            if (dayLineIndex === -1) {
                throw new Error(`No se encontró el día ${day_of_week} en el archivo`);
            }
            
            const endIndex = nextDayIndex === -1 ? lines.length : nextDayIndex;
            
            switch (action) {
                case 'complete':
                    // Buscar la tarea y marcarla como completada
                    for (let i = dayLineIndex + 1; i < endIndex; i++) {
                        if (lines[i].includes(task_text) && lines[i].match(/^- \[ \]/)) {
                            lines[i] = lines[i].replace(/^- \[ \]/, '- [x]');
                            break;
                        }
                    }
                    break;
                    
                case 'add':
                    // Agregar nueva tarea
                    const newTask = time ? `- [ ] ${time} ${task_text}` : `- [ ] ${task_text}`;
                    
                    // Encontrar dónde insertar (después de la línea del día)
                    let insertIndex = dayLineIndex + 1;
                    
                    // Si ya hay tareas, insertar al final de las tareas existentes
                    for (let i = dayLineIndex + 1; i < endIndex; i++) {
                        if (lines[i].match(/^- \[/)) {
                            insertIndex = i + 1;
                        } else if (lines[i].trim() === '') {
                            continue;
                        } else {
                            break;
                        }
                    }
                    
                    lines.splice(insertIndex, 0, newTask);
                    break;
                    
                case 'remove':
                    // Eliminar tarea
                    for (let i = dayLineIndex + 1; i < endIndex; i++) {
                        if (lines[i].includes(task_text) && lines[i].match(/^- \[/)) {
                            lines.splice(i, 1);
                            break;
                        }
                    }
                    break;
                    
                default:
                    throw new Error(`Acción no válida: ${action}`);
            }
            
            // Escribir el archivo modificado
            const newContent = lines.join('\n');
            await fs.writeFile(filePath, newContent, 'utf8');
            
            return {
                content: [
                    {
                        type: "text",
                        text: `✅ **Tarea editada exitosamente:**\n📁 **Archivo:** ${weekInfo.filename}\n📅 **Día:** ${dayCapitalized}\n🔧 **Acción:** ${action}\n📝 **Tarea:** ${task_text}${time ? `\n🕐 **Hora:** ${time}` : ''}`
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error editando tarea: ${error.message}`);
        }
    }

    async listWeeklyFiles(args) {
        const { month, year } = args;
        
        try {
            const files = await fs.readdir(this.daily_path);
            let weeklyFiles = files.filter(file => file.endsWith('.md') && file.match(/^\d{4}-\d{2}-\d{2}_\d{2}\.md$/));
            
            // Filtrar por año si se especifica
            if (year) {
                weeklyFiles = weeklyFiles.filter(file => file.startsWith(year));
            }
            
            // Filtrar por mes si se especifica
            if (month) {
                weeklyFiles = weeklyFiles.filter(file => file.startsWith(month));
            }
            
            // Ordenar por fecha
            weeklyFiles.sort();
            
            let output = `📁 **Archivos semanales disponibles** (${weeklyFiles.length} encontrados)\n\n`;
            
            for (const file of weeklyFiles) {
                const filePath = path.join(this.daily_path, file);
                
                try {
                    const stats = await fs.stat(filePath);
                    const dateMatch = file.match(/(\d{4}-\d{2}-\d{2})_(\d{2})\.md/);
                    
                    if (dateMatch) {
                        const startDate = new Date(dateMatch[1] + 'T12:00:00');
                        const weekInfo = this.getWeekInfo(startDate);
                        
                        output += `📄 **${file}**\n`;
                        output += `   📅 Semana: ${weekInfo.mondayFormatted} - ${weekInfo.sundayFormatted}\n`;
                        output += `   📏 Tamaño: ${stats.size} bytes\n`;
                        output += `   📅 Modificado: ${stats.mtime.toLocaleDateString()}\n\n`;
                    }
                } catch (error) {
                    output += `📄 **${file}** (Error accediendo: ${error.message})\n\n`;
                }
            }
            
            if (weeklyFiles.length === 0) {
                output = `📁 **No se encontraron archivos semanales**${month ? ` para ${month}` : ''}${year ? ` del año ${year}` : ''}`;
            }
            
            return {
                content: [
                    {
                        type: "text",
                        text: output
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error listando archivos semanales: ${error.message}`);
        }
    }

    async getWeekSummary(args) {
        const { start_date, include_details = true } = args;
        
        if (!start_date) {
            throw new Error('Fecha de inicio requerida');
        }
        
        try {
            const startDate = new Date(start_date + 'T12:00:00');
            const weekInfo = this.getWeekInfo(startDate);
            const filePath = path.join(this.daily_path, weekInfo.filename);
            
            const content = await fs.readFile(filePath, 'utf8');
            const lines = content.split('\n');
            
            let totalTasks = 0;
            let completedTasks = 0;
            let pendingTasks = 0;
            const dayStats = {};
            const taskDetails = [];
            
            let currentDay = null;
            
            for (const line of lines) {
                // Detectar días
                const dayMatch = line.match(/^## (Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo)/);
                if (dayMatch) {
                    currentDay = dayMatch[1].toLowerCase();
                    dayStats[currentDay] = { total: 0, completed: 0, pending: 0, tasks: [] };
                    continue;
                }
                
                // Detectar tareas
                const taskMatch = line.match(/^- \[([x ])\] (.+)$/);
                if (taskMatch && currentDay) {
                    const [, status, taskText] = taskMatch;
                    const isCompleted = status === 'x';
                    
                    totalTasks++;
                    dayStats[currentDay].total++;
                    
                    if (isCompleted) {
                        completedTasks++;
                        dayStats[currentDay].completed++;
                    } else {
                        pendingTasks++;
                        dayStats[currentDay].pending++;
                    }
                    
                    if (include_details) {
                        taskDetails.push({
                            day: currentDay,
                            status: isCompleted ? 'completada' : 'pendiente',
                            text: taskText
                        });
                    }
                    
                    dayStats[currentDay].tasks.push({
                        text: taskText,
                        completed: isCompleted
                    });
                }
            }
            
            const completionPercentage = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;
            
            let output = `📊 **Resumen de la semana ${weekInfo.filename}**\n\n`;
            output += `📈 **Estadísticas generales:**\n`;
            output += `• Total de tareas: ${totalTasks}\n`;
            output += `• Completadas: ${completedTasks} (${completionPercentage}%)\n`;
            output += `• Pendientes: ${pendingTasks}\n\n`;
            
            output += `📅 **Por día:**\n`;
            const days = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'];
            for (const day of days) {
                if (dayStats[day]) {
                    const dayPercentage = dayStats[day].total > 0 ? Math.round((dayStats[day].completed / dayStats[day].total) * 100) : 0;
                    output += `• ${day.charAt(0).toUpperCase() + day.slice(1)}: ${dayStats[day].completed}/${dayStats[day].total} (${dayPercentage}%)\n`;
                }
            }
            
            if (include_details && taskDetails.length > 0) {
                output += `\n📋 **Detalles de tareas:**\n`;
                for (const task of taskDetails) {
                    const icon = task.status === 'completada' ? '✅' : '⏳';
                    output += `${icon} ${task.day.charAt(0).toUpperCase() + task.day.slice(1)}: ${task.text}\n`;
                }
            }
            
            return {
                content: [
                    {
                        type: "text",
                        text: output
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error obteniendo resumen semanal: ${error.message}`);
        }
    }

    async searchTasks(args) {
        const { query, status = "all", period = "all", date } = args;
        
        if (!query || query.trim() === '') {
            throw new Error('Query de búsqueda requerido');
        }
        
        try {
            const searchTerm = query.toLowerCase();
            const results = [];
            let filesToSearch = [];
            
            // Determinar archivos a buscar según el período
            if (period === 'week' && date) {
                const targetDate = new Date(date + 'T12:00:00');
                const weekInfo = this.getWeekInfo(targetDate);
                filesToSearch = [weekInfo.filename];
            } else if (period === 'month' && date) {
                const targetDate = new Date(date + 'T12:00:00');
                const year = targetDate.getFullYear();
                const month = (targetDate.getMonth() + 1).toString().padStart(2, '0');
                const files = await fs.readdir(this.daily_path);
                filesToSearch = files.filter(file => 
                    file.endsWith('.md') && file.startsWith(`${year}-${month}`)
                );
            } else {
                const files = await fs.readdir(this.daily_path);
                filesToSearch = files.filter(file => file.endsWith('.md'));
            }
            
            for (const filename of filesToSearch) {
                const filePath = path.join(this.daily_path, filename);
                
                try {
                    const content = await fs.readFile(filePath, 'utf8');
                    const lines = content.split('\n');
                    let currentDay = null;
                    
                    for (const line of lines) {
                        const dayMatch = line.match(/^## (Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo)/);
                        if (dayMatch) {
                            currentDay = dayMatch[1].toLowerCase();
                            continue;
                        }
                        
                        const taskMatch = line.match(/^- \[([x ])\] (.+)$/);
                        if (taskMatch && currentDay) {
                            const [, taskStatus, taskText] = taskMatch;
                            const isCompleted = taskStatus === 'x';
                            
                            // Filtrar por estado si se especifica
                            if (status === 'pending' && isCompleted) continue;
                            if (status === 'completed' && !isCompleted) continue;
                            
                            // Buscar el término en el texto de la tarea
                            if (taskText.toLowerCase().includes(searchTerm)) {
                                results.push({
                                    file: filename,
                                    day: currentDay,
                                    status: isCompleted ? 'completada' : 'pendiente',
                                    text: taskText
                                });
                            }
                        }
                    }
                } catch (error) {
                    console.error(`Error leyendo ${filename}: ${error.message}`);
                }
            }
            
            let output = `🔍 **Resultados de búsqueda para: "${query}"** (${results.length} encontrados)\n\n`;
            
            if (results.length === 0) {
                output = `🔍 **No se encontraron tareas que contengan: "${query}"**`;
            } else {
                let currentFile = null;
                
                for (const result of results) {
                    if (result.file !== currentFile) {
                        currentFile = result.file;
                        output += `📁 **${result.file}**\n`;
                    }
                    
                    const icon = result.status === 'completada' ? '✅' : '⏳';
                    output += `${icon} ${result.day.charAt(0).toUpperCase() + result.day.slice(1)}: ${result.text}\n`;
                }
            }
            
            return {
                content: [
                    {
                        type: "text",
                        text: output
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error buscando tareas: ${error.message}`);
        }
    }

    async getTaskStatistics(args) {
        const { period = "month", start_date } = args;
        
        try {
            let filesToAnalyze = [];
            const targetDate = start_date ? new Date(start_date + 'T12:00:00') : new Date();
            
            // Determinar archivos según el período
            if (period === 'week') {
                const weekInfo = this.getWeekInfo(targetDate);
                filesToAnalyze = [weekInfo.filename];
            } else if (period === 'month') {
                const year = targetDate.getFullYear();
                const month = (targetDate.getMonth() + 1).toString().padStart(2, '0');
                const files = await fs.readdir(this.daily_path);
                filesToAnalyze = files.filter(file => 
                    file.endsWith('.md') && file.startsWith(`${year}-${month}`)
                );
            } else {
                const files = await fs.readdir(this.daily_path);
                filesToAnalyze = files.filter(file => file.endsWith('.md'));
            }
            
            const stats = {
                totalTasks: 0,
                completedTasks: 0,
                pendingTasks: 0,
                byDay: { lunes: 0, martes: 0, miércoles: 0, jueves: 0, viernes: 0, sábado: 0, domingo: 0 },
                byWeek: {},
                completionRate: 0,
                mostProductiveDay: '',
                leastProductiveDay: ''
            };
            
            for (const filename of filesToAnalyze) {
                const filePath = path.join(this.daily_path, filename);
                
                try {
                    const content = await fs.readFile(filePath, 'utf8');
                    const lines = content.split('\n');
                    let currentDay = null;
                    let weekTasks = { total: 0, completed: 0 };
                    
                    for (const line of lines) {
                        const dayMatch = line.match(/^## (Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo)/);
                        if (dayMatch) {
                            currentDay = dayMatch[1].toLowerCase();
                            continue;
                        }
                        
                        const taskMatch = line.match(/^- \[([x ])\] (.+)$/);
                        if (taskMatch && currentDay) {
                            const [, status] = taskMatch;
                            const isCompleted = status === 'x';
                            
                            stats.totalTasks++;
                            weekTasks.total++;
                            stats.byDay[currentDay]++;
                            
                            if (isCompleted) {
                                stats.completedTasks++;
                                weekTasks.completed++;
                            } else {
                                stats.pendingTasks++;
                            }
                        }
                    }
                    
                    stats.byWeek[filename] = weekTasks;
                } catch (error) {
                    console.error(`Error leyendo ${filename}: ${error.message}`);
                }
            }
            
            // Calcular estadísticas adicionales
            stats.completionRate = stats.totalTasks > 0 ? Math.round((stats.completedTasks / stats.totalTasks) * 100) : 0;
            
            // Día más y menos productivo
            let maxTasks = 0;
            let minTasks = Infinity;
            for (const [day, taskCount] of Object.entries(stats.byDay)) {
                if (taskCount > maxTasks) {
                    maxTasks = taskCount;
                    stats.mostProductiveDay = day;
                }
                if (taskCount < minTasks && taskCount > 0) {
                    minTasks = taskCount;
                    stats.leastProductiveDay = day;
                }
            }
            
            let output = `📊 **Estadísticas de productividad (${period})**\n\n`;
            output += `📈 **Resumen general:**\n`;
            output += `• Total de tareas: ${stats.totalTasks}\n`;
            output += `• Completadas: ${stats.completedTasks} (${stats.completionRate}%)\n`;
            output += `• Pendientes: ${stats.pendingTasks}\n\n`;
            
            output += `📅 **Distribución por día:**\n`;
            for (const [day, count] of Object.entries(stats.byDay)) {
                if (count > 0) {
                    output += `• ${day.charAt(0).toUpperCase() + day.slice(1)}: ${count} tareas\n`;
                }
            }
            
            if (stats.mostProductiveDay) {
                output += `\n🏆 **Día más productivo:** ${stats.mostProductiveDay.charAt(0).toUpperCase() + stats.mostProductiveDay.slice(1)} (${stats.byDay[stats.mostProductiveDay]} tareas)\n`;
            }
            
            if (stats.leastProductiveDay && stats.leastProductiveDay !== stats.mostProductiveDay) {
                output += `📉 **Día menos productivo:** ${stats.leastProductiveDay.charAt(0).toUpperCase() + stats.leastProductiveDay.slice(1)} (${stats.byDay[stats.leastProductiveDay]} tareas)\n`;
            }
            
            if (Object.keys(stats.byWeek).length > 1) {
                output += `\n📊 **Por semana:**\n`;
                for (const [week, data] of Object.entries(stats.byWeek)) {
                    const weekCompletion = data.total > 0 ? Math.round((data.completed / data.total) * 100) : 0;
                    output += `• ${week}: ${data.completed}/${data.total} (${weekCompletion}%)\n`;
                }
            }
            
            return {
                content: [
                    {
                        type: "text",
                        text: output
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error obteniendo estadísticas: ${error.message}`);
        }
    }

    async moveTask(args) {
        const { from_start_date, from_day, to_start_date, to_day, task_text } = args;
        
        if (!from_start_date || !from_day || !to_start_date || !to_day || !task_text) {
            throw new Error('Todos los parámetros son requeridos');
        }
        
        try {
            // Obtener información de ambas semanas
            const fromStartDate = new Date(from_start_date + 'T12:00:00');  
            const toStartDate = new Date(to_start_date + 'T12:00:00');
            const fromWeekInfo = this.getWeekInfo(fromStartDate);
            const toWeekInfo = this.getWeekInfo(toStartDate);
            
            const fromFilePath = path.join(this.daily_path, fromWeekInfo.filename);
            const toFilePath = path.join(this.daily_path, toWeekInfo.filename);
            
            // Leer archivo origen
            let fromContent = await fs.readFile(fromFilePath, 'utf8');
            let fromLines = fromContent.split('\n');
            
            // Buscar y eliminar la tarea del archivo origen
            let taskFound = false;
            let taskLine = null;
            const fromDayCapitalized = from_day.charAt(0).toUpperCase() + from_day.slice(1);
            const fromDayPattern = new RegExp(`^## ${fromDayCapitalized}`);
            
            let fromDayLineIndex = -1;
            let fromNextDayIndex = -1;
            
            for (let i = 0; i < fromLines.length; i++) {
                if (fromDayPattern.test(fromLines[i])) {
                    fromDayLineIndex = i;
                }
                if (fromDayLineIndex > -1 && i > fromDayLineIndex && fromLines[i].match(/^## (Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo)/)) {
                    fromNextDayIndex = i;
                    break;
                }
            }
            
            const fromEndIndex = fromNextDayIndex === -1 ? fromLines.length : fromNextDayIndex;
            
            for (let i = fromDayLineIndex + 1; i < fromEndIndex; i++) {
                if (fromLines[i].includes(task_text) && fromLines[i].match(/^- \[/)) {
                    taskLine = fromLines[i];
                    fromLines.splice(i, 1);
                    taskFound = true;
                    break;
                }
            }
            
            if (!taskFound) {
                throw new Error(`No se encontró la tarea "${task_text}" en ${from_day} del archivo ${fromWeekInfo.filename}`);
            }
            
            // Escribir archivo origen modificado
            await fs.writeFile(fromFilePath, fromLines.join('\n'), 'utf8');
            
            // Agregar tarea al archivo destino
            let toContent;
            let toLines;
            
            if (fromFilePath === toFilePath) {
                // Misma semana, usar el contenido ya modificado
                toContent = fromLines.join('\n');
                toLines = fromLines;
            } else {
                // Diferente semana, leer archivo destino
                toContent = await fs.readFile(toFilePath, 'utf8');
                toLines = toContent.split('\n');
            }
            
            const toDayCapitalized = to_day.charAt(0).toUpperCase() + to_day.slice(1);
            const toDayPattern = new RegExp(`^## ${toDayCapitalized}`);
            
            let toDayLineIndex = -1;
            let toNextDayIndex = -1;
            
            for (let i = 0; i < toLines.length; i++) {
                if (toDayPattern.test(toLines[i])) {
                    toDayLineIndex = i;
                }
                if (toDayLineIndex > -1 && i > toDayLineIndex && toLines[i].match(/^## (Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo)/)) {
                    toNextDayIndex = i;
                    break;
                }
            }
            
            const toEndIndex = toNextDayIndex === -1 ? toLines.length : toNextDayIndex;
            
            // Encontrar dónde insertar la tarea
            let insertIndex = toDayLineIndex + 1;
            for (let i = toDayLineIndex + 1; i < toEndIndex; i++) {
                if (toLines[i].match(/^- \[/)) {
                    insertIndex = i + 1;
                } else if (toLines[i].trim() === '') {
                    continue;
                } else {
                    break;
                }
            }
            
            toLines.splice(insertIndex, 0, taskLine);
            
            // Escribir archivo destino
            await fs.writeFile(toFilePath, toLines.join('\n'), 'utf8');
            
            return {
                content: [
                    {
                        type: "text",
                        text: `✅ **Tarea movida exitosamente:**\n📝 **Tarea:** ${task_text}\n📤 **Desde:** ${fromDayCapitalized} (${fromWeekInfo.filename})\n📥 **Hacia:** ${toDayCapitalized} (${toWeekInfo.filename})`
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error moviendo tarea: ${error.message}`);
        }
    }

    async duplicateWeek(args) {
        const { source_start_date, target_start_date, copy_completed = false, overwrite = false } = args;
        
        if (!source_start_date || !target_start_date) {
            throw new Error('Fechas de inicio de origen y destino requeridas');
        }
        
        try {
            const sourceStartDate = new Date(source_start_date + 'T12:00:00');
            const targetStartDate = new Date(target_start_date + 'T12:00:00');
            
            // Verificar que ambas fechas sean lunes
            if (sourceStartDate.getDay() !== 1 || targetStartDate.getDay() !== 1) {
                throw new Error('Ambas fechas deben ser lunes');
            }
            
            const sourceWeekInfo = this.getWeekInfo(sourceStartDate);
            const targetWeekInfo = this.getWeekInfo(targetStartDate);
            
            const sourceFilePath = path.join(this.daily_path, sourceWeekInfo.filename);
            const targetFilePath = path.join(this.daily_path, targetWeekInfo.filename);
            
            // Verificar que archivo origen existe
            const sourceContent = await fs.readFile(sourceFilePath, 'utf8');
            
            // Verificar si archivo destino existe
            try {
                await fs.access(targetFilePath);
                if (!overwrite) {
                    throw new Error(`El archivo ${targetWeekInfo.filename} ya existe. Usa overwrite=true para sobrescribir`);
                }
            } catch (error) {
                // El archivo no existe, está bien
            }
            
            // Procesar contenido del archivo origen
            const sourceLines = sourceContent.split('\n');
            let processedLines = [];
            
            // Actualizar el título con las nuevas fechas
            const months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
            const newTitle = `# Semana ${targetStartDate.getDate().toString().padStart(2, '0')}-${targetWeekInfo.sunday.getDate().toString().padStart(2, '0')} ${months[targetStartDate.getMonth()]} ${targetStartDate.getFullYear()}`;
            
            let currentDay = null;
            let dayIndex = 0;
            
            for (const line of sourceLines) {
                if (line.startsWith('# Semana')) {
                    processedLines.push(newTitle);
                    continue;
                }
                
                // Detectar días y actualizar fechas
                const dayMatch = line.match(/^## (Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo)/);
                if (dayMatch) {
                    const dayName = dayMatch[1];
                    currentDay = dayName.toLowerCase();
                    
                    // Calcular la nueva fecha para este día
                    const newDate = new Date(targetStartDate);
                    newDate.setDate(targetStartDate.getDate() + dayIndex);
                    
                    const newDayLine = `## ${dayName} ${newDate.getDate()} de ${months[newDate.getMonth()]}`;
                    processedLines.push(newDayLine);
                    dayIndex++;
                    continue;
                }
                
                // Procesar tareas
                const taskMatch = line.match(/^- \[([x ])\] (.+)$/);
                if (taskMatch) {
                    const [, status, taskText] = taskMatch;
                    const isCompleted = status === 'x';
                    
                    // Decidir si copiar la tarea
                    if (copy_completed || !isCompleted) {
                        // Resetear tareas a pendiente si no se copian completadas
                        const newStatus = copy_completed && isCompleted ? 'x' : ' ';
                        processedLines.push(`- [${newStatus}] ${taskText}`);
                    }
                    continue;
                }
                
                // Copiar otras líneas tal como están
                processedLines.push(line);
            }
            
            // Escribir archivo destino
            await fs.writeFile(targetFilePath, processedLines.join('\n'), 'utf8');
            
            return {
                content: [
                    {
                        type: "text",
                        text: `✅ **Semana duplicada exitosamente:**\n📁 **Origen:** ${sourceWeekInfo.filename}\n📁 **Destino:** ${targetWeekInfo.filename}\n📅 **Nueva semana:** ${targetWeekInfo.mondayFormatted} - ${targetWeekInfo.sundayFormatted}\n${copy_completed ? '✅ Tareas completadas copiadas' : '⏳ Solo tareas pendientes copiadas'}`
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error duplicando semana: ${error.message}`);
        }
    }

    async setRecurringTasks(args) {
        const { template_name, tasks, apply_to_week } = args;
        
        if (!template_name || !tasks || tasks.length === 0) {
            throw new Error('Nombre de plantilla y lista de tareas requeridos');
        }
        
        try {
            // Crear directorio para plantillas si no existe
            const templatesPath = path.join(this.daily_path, '.templates');
            await fs.mkdir(templatesPath, { recursive: true });
            
            // Guardar plantilla
            const templateData = {
                name: template_name,
                created: new Date().toISOString(),
                tasks: tasks
            };
            
            const templateFilePath = path.join(templatesPath, `${template_name}.json`);
            await fs.writeFile(templateFilePath, JSON.stringify(templateData, null, 2), 'utf8');
            
            let output = `✅ **Plantilla de tareas recurrentes creada:**\n📝 **Nombre:** ${template_name}\n📊 **Tareas:** ${tasks.length}\n\n`;
            
            output += `📋 **Detalles de la plantilla:**\n`;
            for (const task of tasks) {
                const timeStr = task.time ? `${task.time} ` : '';
                output += `• ${task.day.charAt(0).toUpperCase() + task.day.slice(1)}: ${timeStr}${task.task}\n`;
            }
            
            // Aplicar inmediatamente a una semana si se especifica
            if (apply_to_week) {
                try {
                    const applyResult = await this.applyRecurringTemplate(template_name, apply_to_week);
                    output += `\n🎯 **Aplicado a la semana ${apply_to_week}:**\n${applyResult}`;
                } catch (error) {
                    output += `\n⚠️ **Error aplicando a la semana:** ${error.message}`;
                }
            }
            
            return {
                content: [
                    {
                        type: "text",
                        text: output
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error configurando tareas recurrentes: ${error.message}`);
        }
    }

    async applyRecurringTemplate(templateName, startDate) {
        try {
            const templatesPath = path.join(this.daily_path, '.templates');
            const templateFilePath = path.join(templatesPath, `${templateName}.json`);
            
            const templateContent = await fs.readFile(templateFilePath, 'utf8');
            const templateData = JSON.parse(templateContent);
            
            const startDateObj = new Date(startDate + 'T12:00:00');
            const weekInfo = this.getWeekInfo(startDateObj);
            const filePath = path.join(this.daily_path, weekInfo.filename);
            
            // Leer archivo de la semana
            let content = await fs.readFile(filePath, 'utf8');
            let lines = content.split('\n');
            
            let tasksAdded = 0;
            
            // Aplicar cada tarea de la plantilla
            for (const task of templateData.tasks) {
                const dayCapitalized = task.day.charAt(0).toUpperCase() + task.day.slice(1);
                const dayPattern = new RegExp(`^## ${dayCapitalized}`);
                
                let dayLineIndex = -1;
                let nextDayIndex = -1;
                
                // Encontrar el día específico
                for (let i = 0; i < lines.length; i++) {
                    if (dayPattern.test(lines[i])) {
                        dayLineIndex = i;
                    }
                    if (dayLineIndex > -1 && i > dayLineIndex && lines[i].match(/^## (Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo)/)) {
                        nextDayIndex = i;
                        break;
                    }
                }
                
                if (dayLineIndex > -1) {
                    const endIndex = nextDayIndex === -1 ? lines.length : nextDayIndex;
                    
                    // Crear la nueva tarea
                    const newTask = task.time ? `- [ ] ${task.time} ${task.task}` : `- [ ] ${task.task}`;
                    
                    // Encontrar dónde insertar
                    let insertIndex = dayLineIndex + 1;
                    for (let i = dayLineIndex + 1; i < endIndex; i++) {
                        if (lines[i].match(/^- \[/)) {
                            insertIndex = i + 1;
                        } else if (lines[i].trim() === '') {
                            continue;
                        } else {
                            break;
                        }
                    }
                    
                    lines.splice(insertIndex, 0, newTask);
                    tasksAdded++;
                }
            }
            
            // Escribir archivo actualizado
            await fs.writeFile(filePath, lines.join('\n'), 'utf8');
            
            return `${tasksAdded} tareas agregadas de la plantilla "${templateName}"`;
        } catch (error) {
            throw new Error(`Error aplicando plantilla: ${error.message}`);
        }
    }

    async getCurrentDate(args) {
        const { format = "structured" } = args;
        
        try {
            const now = new Date();
            
            // Configurar zona horaria America/Bogotá
            const options = {
                timeZone: 'America/Bogota',
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            };
            
            const dayNames = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
            const monthNames = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
            
            // Obtener fecha local en zona horaria
            const localDate = new Date(now.toLocaleString('en-US', { timeZone: 'America/Bogota' }));
            const dayOfWeek = dayNames[localDate.getDay()];
            const dayNumber = localDate.getDate();
            const monthName = monthNames[localDate.getMonth()];
            const year = localDate.getFullYear();
            const dateString = localDate.toISOString().split('T')[0]; // YYYY-MM-DD
            const timeString = localDate.toTimeString().split(' ')[0]; // HH:MM:SS
            
            let formattedDateTime;
            
            switch (format) {
                case 'structured':
                    const weekInfo = this.getWeekInfo(dateString);
                    formattedDateTime = {
                        dayOfWeek: dayOfWeek,
                        dayNumber: dayNumber,
                        fullDate: dateString,
                        currentTime: timeString.substring(0, 5), // HH:MM
                        readableDate: `${dayOfWeek} ${dayNumber} de ${monthName} ${year}`,
                        weeklyFilename: weekInfo.filename,
                        isWeekend: dayOfWeek === 'sábado' || dayOfWeek === 'domingo'
                    };
                    break;
                case 'iso':
                    formattedDateTime = now.toLocaleString('sv-SE', options).replace(' ', 'T') + '-05:00';
                    break;
                case 'readable':
                    formattedDateTime = `${dayOfWeek} ${dayNumber} de ${monthName} ${year}, ${timeString.substring(0, 5)}`;
                    break;
                case 'date_only':
                    formattedDateTime = dateString;
                    break;
                case 'time_only':
                    formattedDateTime = timeString.substring(0, 5);
                    break;
                default:
                    formattedDateTime = `${dayOfWeek} ${dayNumber} de ${monthName} ${year}, ${timeString.substring(0, 5)}`;
            }
            
            return {
                content: [
                    {
                        type: "text",
                        text: format === 'structured' 
                            ? `🕐 **Información de fecha actual (America/Bogotá):**\n\n📅 **Día:** ${formattedDateTime.dayOfWeek}\n📊 **Fecha completa:** ${formattedDateTime.fullDate}\n🕐 **Hora actual:** ${formattedDateTime.currentTime}\n📖 **Legible:** ${formattedDateTime.readableDate}\n📁 **Archivo semanal:** ${formattedDateTime.weeklyFilename}\n${formattedDateTime.isWeekend ? '🏖️ **Es fin de semana**' : '💼 **Es día laborable**'}`
                            : `🕐 **Fecha y hora actual (America/Bogotá):**\n${typeof formattedDateTime === 'object' ? JSON.stringify(formattedDateTime, null, 2) : formattedDateTime}`
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error obteniendo la fecha/hora: ${error.message}`);
        }
    }
}

// ======= CLI =======
async function main() {
    try {
        const server = new PersonalAssistantServer();
        // Comprobar que el directorio Daily existe
        await fs.access(server.daily_path);
        console.error(`📋 Personal Assistant MCP Server iniciado para directorio: ${server.daily_path}`);
    } catch (err) {
        console.error(`❌ Error: No se puede acceder al directorio Daily en ${MCP_CONFIG.daily_path}`);
        process.exit(1);
    }

    const server = new PersonalAssistantServer();

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
        console.error('🛑 Personal Assistant MCP Server terminado');
        process.exit(0);
    });
}

if (require.main === module) {
    main().catch((err) => {
        console.error('❌ Error fatal:', err);
        process.exit(1);
    });
}

module.exports = PersonalAssistantServer;