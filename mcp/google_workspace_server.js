#!/usr/bin/env node

/**
 * Servidor MCP para Google Workspace - Calendar, Gmail, Drive, Sheets, YouTube Music
 * Compatible con la arquitectura MCP existente de Aura
 * Integra todas las funcionalidades esenciales de Google Services
 */

const fs = require('fs').promises;
const path = require('path');
const { google } = require('googleapis');

// Configuración del servidor MCP
const MCP_CONFIG = {
    name: "google-workspace",
    version: "1.0.0",
    credentials_path: process.env.GOOGLE_CREDENTIALS_PATH || path.join(process.cwd(), 'credentials.json'),
    token_path: process.env.GOOGLE_TOKEN_PATH || path.join(process.cwd(), 'token.json'),
    user_email: "ayrgthon223@gmail.com" // Email principal configurado
};

const SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/spreadsheets.readonly'
];

class GoogleWorkspaceServer {
    constructor() {
        this.credentials_path = MCP_CONFIG.credentials_path;
        this.token_path = MCP_CONFIG.token_path;
        this.user_email = MCP_CONFIG.user_email;
        this.auth = null;
        
        this.tools = [
            {
                name: "list_calendar_events",
                description: "CUÁNDO USAR: Para consultar eventos próximos o buscar disponibilidad en el calendario. CÓMO USAR: Especifica el período (today, tomorrow, week, month) y opcionalmente el número de eventos. Útil para responder preguntas como '¿qué tengo hoy?', '¿estoy libre mañana?', '¿qué eventos tengo esta semana?'",
                inputSchema: {
                    type: "object",
                    properties: {
                        time_period: {
                            type: "string",
                            enum: ["today", "tomorrow", "week", "month", "custom"],
                            default: "today",
                            description: "Período de tiempo: today (hoy), tomorrow (mañana), week (próximos 7 días), month (próximo mes), custom (rango personalizado)"
                        },
                        max_results: {
                            type: "integer",
                            default: 10,
                            description: "Número máximo de eventos a mostrar (1-50)"
                        },
                        start_date: {
                            type: "string",
                            description: "Fecha de inicio para custom en formato YYYY-MM-DD"
                        },
                        end_date: {
                            type: "string",
                            description: "Fecha de fin para custom en formato YYYY-MM-DD"
                        },
                        search_query: {
                            type: "string",
                            description: "Buscar eventos que contengan este texto en título o descripción"
                        }
                    }
                }
            },
            {
                name: "create_calendar_event",
                description: "CUÁNDO USAR: Para crear nuevos eventos, reuniones, recordatorios o bloquear tiempo en el calendario. CÓMO USAR: Proporciona al menos título, fecha/hora de inicio y fin. Puedes agregar participantes, ubicación, descripción y recordatorios. Útil para comandos como 'agenda una reunión', 'bloquea 2 horas para trabajo', 'créame un recordatorio'",
                inputSchema: {
                    type: "object",
                    properties: {
                        title: {
                            type: "string",
                            description: "Título/resumen del evento (requerido)"
                        },
                        description: {
                            type: "string",
                            description: "Descripción detallada del evento"
                        },
                        start_datetime: {
                            type: "string",
                            description: "Fecha y hora de inicio en formato ISO: YYYY-MM-DDTHH:MM:SS (ej: 2025-08-11T14:00:00)"
                        },
                        end_datetime: {
                            type: "string",
                            description: "Fecha y hora de fin en formato ISO: YYYY-MM-DDTHH:MM:SS (ej: 2025-08-11T15:00:00). OPCIONAL: Si no se especifica, se asume duración de 1 hora"
                        },
                        all_day: {
                            type: "boolean",
                            default: false,
                            description: "Si es evento de todo el día (usa solo start_date si es true)"
                        },
                        start_date: {
                            type: "string",
                            description: "Solo fecha para eventos de todo el día en formato YYYY-MM-DD"
                        },
                        end_date: {
                            type: "string",
                            description: "Solo fecha de fin para eventos de todo el día en formato YYYY-MM-DD"
                        },
                        location: {
                            type: "string",
                            description: "Ubicación física o virtual del evento"
                        },
                        attendees: {
                            type: "array",
                            items: {
                                type: "string",
                                description: "Email del participante"
                            },
                            description: "Lista de emails de participantes a invitar"
                        },
                        timezone: {
                            type: "string",
                            default: "America/Bogota",
                            description: "Zona horaria del evento"
                        },
                        color: {
                            type: "string",
                            enum: ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"],
                            description: "Color del evento: 1=azul, 2=verde, 3=morado, 4=rojo, 5=amarillo, 6=naranja, 7=turquesa, 8=gris, 9=azul_oscuro, 10=verde_oscuro, 11=rojo_oscuro"
                        },
                        reminder_email_minutes: {
                            type: "integer",
                            default: 60,
                            description: "Recordatorio por email X minutos antes del evento (0 para desactivar)"
                        },
                        reminder_popup_minutes: {
                            type: "integer",
                            default: 10,
                            description: "Recordatorio popup X minutos antes del evento (0 para desactivar)"
                        },
                        visibility: {
                            type: "string",
                            enum: ["default", "public", "private"],
                            default: "default",
                            description: "Visibilidad del evento"
                        },
                        create_meet: {
                            type: "boolean",
                            default: false,
                            description: "Crear automáticamente una reunión de Google Meet"
                        }
                    },
                    required: ["title"]
                }
            },
            {
                name: "update_calendar_event",
                description: "CUÁNDO USAR: Para modificar eventos existentes, cambiar horarios, agregar participantes o actualizar detalles. CÓMO USAR: Busca primero el evento por título o ID, luego proporciona los campos a modificar. Útil para 'mueve la reunión a las 3pm', 'agrega a Juan a la reunión del viernes', 'cambia la ubicación del evento'",
                inputSchema: {
                    type: "object",
                    properties: {
                        event_id: {
                            type: "string",
                            description: "ID del evento a actualizar (obtener con list_calendar_events)"
                        },
                        search_title: {
                            type: "string",
                            description: "Buscar evento por título si no tienes el ID"
                        },
                        title: {
                            type: "string",
                            description: "Nuevo título del evento"
                        },
                        description: {
                            type: "string",
                            description: "Nueva descripción del evento"
                        },
                        start_datetime: {
                            type: "string",
                            description: "Nueva fecha/hora de inicio en formato ISO"
                        },
                        end_datetime: {
                            type: "string",
                            description: "Nueva fecha/hora de fin en formato ISO"
                        },
                        location: {
                            type: "string",
                            description: "Nueva ubicación"
                        },
                        attendees: {
                            type: "array",
                            items: {
                                type: "string"
                            },
                            description: "Nueva lista de participantes (reemplaza la existente)"
                        },
                        add_attendees: {
                            type: "array",
                            items: {
                                type: "string"
                            },
                            description: "Agregar estos participantes a los existentes"
                        }
                    }
                }
            },
            {
                name: "delete_calendar_event",
                description: "CUÁNDO USAR: Para cancelar eventos, reuniones o eliminar entradas del calendario. CÓMO USAR: Proporciona el ID del evento o busca por título. Útil para 'cancela la reunión de mañana', 'elimina el evento del viernes', 'borra mi cita médica'",
                inputSchema: {
                    type: "object",
                    properties: {
                        event_id: {
                            type: "string",
                            description: "ID del evento a eliminar"
                        },
                        search_title: {
                            type: "string",
                            description: "Buscar evento por título para eliminar"
                        },
                        confirm: {
                            type: "boolean",
                            default: false,
                            description: "Confirmación requerida para eliminar (debe ser true)"
                        }
                    }
                }
            },
            {
                name: "find_free_time",
                description: "CUÁNDO USAR: Para encontrar espacios libres en el calendario, programar reuniones o verificar disponibilidad. CÓMO USAR: Especifica el rango de fechas y duración deseada. Útil para '¿cuándo tengo tiempo libre esta semana?', 'encuentra 2 horas libres para mañana', 'busca un espacio para reunión de 1 hora'",
                inputSchema: {
                    type: "object",
                    properties: {
                        start_date: {
                            type: "string",
                            description: "Fecha de inicio de búsqueda en formato YYYY-MM-DD"
                        },
                        end_date: {
                            type: "string",
                            description: "Fecha de fin de búsqueda en formato YYYY-MM-DD"
                        },
                        duration_minutes: {
                            type: "integer",
                            default: 60,
                            description: "Duración mínima del tiempo libre en minutos"
                        },
                        working_hours_only: {
                            type: "boolean",
                            default: true,
                            description: "Solo buscar en horario laboral (9am-6pm)"
                        },
                        exclude_weekends: {
                            type: "boolean",
                            default: true,
                            description: "Excluir fines de semana"
                        }
                    },
                    required: ["start_date", "end_date"]
                }
            },
            {
                name: "send_calendar_reminder_email",
                description: "CUÁNDO USAR: Para enviar recordatorios manuales por email sobre eventos próximos o importantes. CÓMO USAR: Especifica el destinatario (por defecto tu email), asunto y mensaje. Útil para recordatorios personalizados, seguimiento de reuniones o notificaciones importantes",
                inputSchema: {
                    type: "object",
                    properties: {
                        recipient_email: {
                            type: "string",
                            default: "ayrgthon223@gmail.com",
                            description: "Email del destinatario"
                        },
                        subject: {
                            type: "string",
                            description: "Asunto del recordatorio"
                        },
                        message: {
                            type: "string",
                            description: "Mensaje del recordatorio"
                        },
                        event_title: {
                            type: "string",
                            description: "Título del evento relacionado (opcional)"
                        },
                        event_datetime: {
                            type: "string",
                            description: "Fecha/hora del evento en formato legible"
                        }
                    },
                    required: ["subject", "message"]
                }
            },
            {
                name: "get_calendar_summary",
                description: "CUÁNDO USAR: Para obtener resúmenes de productividad, estadísticas del calendario o análisis de tiempo. CÓMO USAR: Especifica el período a analizar. Útil para responder '¿qué tal estuvo mi semana?', 'resumen de mis reuniones del mes', 'estadísticas de mi calendario'",
                inputSchema: {
                    type: "object",
                    properties: {
                        period: {
                            type: "string",
                            enum: ["week", "month", "custom"],
                            default: "week",
                            description: "Período para el resumen"
                        },
                        start_date: {
                            type: "string",
                            description: "Fecha de inicio para período custom en formato YYYY-MM-DD"
                        },
                        end_date: {
                            type: "string",
                            description: "Fecha de fin para período custom en formato YYYY-MM-DD"
                        },
                        include_stats: {
                            type: "boolean",
                            default: true,
                            description: "Incluir estadísticas detalladas"
                        }
                    }
                }
            }
        ];
    }

    async initialize() {
        try {
            // Verificar archivos de credenciales
            await fs.access(this.credentials_path);
            
            // Inicializar autenticación
            this.auth = await this.initializeAuth();
            
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
        } catch (error) {
            throw new Error(`Error inicializando Google Workspace: ${error.message}`);
        }
    }

    async initializeAuth() {
        try {
            // Cargar credenciales
            const credentials = JSON.parse(await fs.readFile(this.credentials_path));
            const { client_secret, client_id, redirect_uris } = credentials.web || credentials.installed;
            
            // Crear cliente OAuth2
            const oAuth2Client = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0]);

            try {
                // Intentar cargar token existente
                const token = await fs.readFile(this.token_path);
                oAuth2Client.setCredentials(JSON.parse(token));
                return oAuth2Client;
            } catch (err) {
                throw new Error('Token no encontrado. Ejecuta la autenticación primero con calendar-simple.js');
            }
        } catch (error) {
            throw new Error(`Error configurando autenticación: ${error.message}`);
        }
    }

    async handleRequest(request) {
        try {
            const { method, params, id } = request;
            let result;
            
            switch (method) {
                case 'initialize':
                    result = await this.initialize();
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

    async callTool(params) {
        const { name, arguments: args } = params;

        // Asegurar que la autenticación esté inicializada
        if (!this.auth) {
            this.auth = await this.initializeAuth();
        }

        switch (name) {
            case 'list_calendar_events':
                return await this.listCalendarEvents(args);
            case 'create_calendar_event':
                return await this.createCalendarEvent(args);
            case 'update_calendar_event':
                return await this.updateCalendarEvent(args);
            case 'delete_calendar_event':
                return await this.deleteCalendarEvent(args);
            case 'find_free_time':
                return await this.findFreeTime(args);
            case 'send_calendar_reminder_email':
                return await this.sendCalendarReminderEmail(args);
            case 'get_calendar_summary':
                return await this.getCalendarSummary(args);
            default:
                throw new Error(`Herramienta desconocida: ${name}`);
        }
    }

    async listCalendarEvents(args) {
        try {
            const { 
                time_period = "today", 
                max_results = 10, 
                start_date, 
                end_date, 
                search_query 
            } = args;

            const calendar = google.calendar({ version: 'v3', auth: this.auth });
            
            // Calcular fechas según el período
            let timeMin, timeMax;
            const now = new Date();
            
            switch (time_period) {
                case 'today':
                    timeMin = new Date(now);
                    timeMin.setHours(0, 0, 0, 0);
                    timeMax = new Date(now);
                    timeMax.setHours(23, 59, 59, 999);
                    break;
                case 'tomorrow':
                    timeMin = new Date(now);
                    timeMin.setDate(now.getDate() + 1);
                    timeMin.setHours(0, 0, 0, 0);
                    timeMax = new Date(timeMin);
                    timeMax.setHours(23, 59, 59, 999);
                    break;
                case 'week':
                    timeMin = new Date(now);
                    timeMax = new Date(now);
                    timeMax.setDate(now.getDate() + 7);
                    break;
                case 'month':
                    timeMin = new Date(now);
                    timeMax = new Date(now);
                    timeMax.setMonth(now.getMonth() + 1);
                    break;
                case 'custom':
                    if (!start_date || !end_date) {
                        throw new Error('start_date y end_date requeridos para período custom');
                    }
                    timeMin = new Date(start_date + 'T00:00:00');
                    timeMax = new Date(end_date + 'T23:59:59');
                    break;
            }

            const response = await calendar.events.list({
                calendarId: 'primary',
                timeMin: timeMin.toISOString(),
                timeMax: timeMax.toISOString(),
                maxResults: Math.min(max_results, 50),
                singleEvents: true,
                orderBy: 'startTime',
                q: search_query
            });

            const events = response.data.items || [];
            
            let output = `📅 **Eventos ${this.getPeriodLabel(time_period, start_date, end_date)}** (${events.length} encontrados)\n\n`;
            
            if (events.length === 0) {
                output += `✨ No tienes eventos programados ${this.getPeriodLabel(time_period, start_date, end_date)}`;
            } else {
                events.forEach((event, index) => {
                    const start = event.start.dateTime || event.start.date;
                    const end = event.end.dateTime || event.end.date;
                    const startTime = new Date(start);
                    const endTime = new Date(end);
                    
                    output += `${index + 1}. 📌 **${event.summary}**\n`;
                    output += `   🆔 ID: ${event.id}\n`;
                    
                    if (event.start.dateTime) {
                        output += `   📅 ${startTime.toLocaleDateString('es-ES', { weekday: 'long', month: 'long', day: 'numeric' })}\n`;
                        output += `   🕐 ${startTime.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })} - ${endTime.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}\n`;
                    } else {
                        output += `   📅 ${startTime.toLocaleDateString('es-ES', { weekday: 'long', month: 'long', day: 'numeric' })} (Todo el día)\n`;
                    }
                    
                    if (event.location) {
                        output += `   📍 ${event.location}\n`;
                    }
                    
                    if (event.description) {
                        const desc = event.description.length > 100 ? 
                            event.description.substring(0, 100) + '...' : 
                            event.description;
                        output += `   📝 ${desc}\n`;
                    }
                    
                    if (event.attendees && event.attendees.length > 0) {
                        output += `   👥 Participantes: ${event.attendees.length}\n`;
                    }
                    
                    output += `\n`;
                });
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
            throw new Error(`Error listando eventos: ${error.message}`);
        }
    }

    async createCalendarEvent(args) {
        try {
            const {
                title,
                description,
                start_datetime,
                end_datetime,
                all_day = false,
                start_date,
                end_date,
                location,
                attendees = [],
                timezone = "America/Bogota",
                color,
                reminder_email_minutes = 60,
                reminder_popup_minutes = 10,
                visibility = "default",
                create_meet = false
            } = args;

            if (!title) {
                throw new Error('Título del evento es requerido');
            }

            const calendar = google.calendar({ version: 'v3', auth: this.auth });

            // Construir objeto del evento
            const event = {
                summary: title,
                description: description,
                location: location,
                colorId: color,
                visibility: visibility
            };

            // Configurar fechas/horas
            if (all_day) {
                if (!start_date) {
                    throw new Error('start_date requerido para eventos de todo el día');
                }
                event.start = { date: start_date };
                event.end = { date: end_date || start_date };
            } else {
                if (!start_datetime) {
                    throw new Error('start_datetime requerido para eventos con hora');
                }
                
                // Si no se especifica end_datetime, usar duración de 1 hora por defecto
                let endDateTime = end_datetime;
                if (!endDateTime) {
                    const startDate = new Date(start_datetime);
                    startDate.setHours(startDate.getHours() + 1); // Agregar 1 hora
                    endDateTime = startDate.toISOString().slice(0, 19); // Formato YYYY-MM-DDTHH:MM:SS
                }
                
                event.start = {
                    dateTime: start_datetime,
                    timeZone: timezone
                };
                event.end = {
                    dateTime: endDateTime,
                    timeZone: timezone
                };
            }

            // Agregar participantes
            if (attendees.length > 0) {
                event.attendees = attendees.map(email => ({ email }));
            }

            // Configurar recordatorios
            const reminders = [];
            if (reminder_email_minutes > 0) {
                reminders.push({ method: 'email', minutes: reminder_email_minutes });
            }
            if (reminder_popup_minutes > 0) {
                reminders.push({ method: 'popup', minutes: reminder_popup_minutes });
            }
            
            if (reminders.length > 0) {
                event.reminders = {
                    useDefault: false,
                    overrides: reminders
                };
            }

            // Configurar Google Meet si se solicita
            if (create_meet) {
                event.conferenceData = {
                    createRequest: {
                        requestId: `meet-${Date.now()}`,
                        conferenceSolutionKey: { type: 'hangoutsMeet' }
                    }
                };
            }

            const response = await calendar.events.insert({
                calendarId: 'primary',
                resource: event,
                conferenceDataVersion: create_meet ? 1 : 0
            });

            const createdEvent = response.data;
            const eventStart = new Date(createdEvent.start.dateTime || createdEvent.start.date);

            let output = `✅ **Evento creado exitosamente:**\n\n`;
            output += `📌 **Título:** ${createdEvent.summary}\n`;
            output += `🆔 **ID:** ${createdEvent.id}\n`;
            
            if (all_day) {
                output += `📅 **Fecha:** ${eventStart.toLocaleDateString('es-ES', { weekday: 'long', month: 'long', day: 'numeric' })} (Todo el día)\n`;
            } else {
                const eventEnd = new Date(createdEvent.end.dateTime);
                output += `📅 **Fecha:** ${eventStart.toLocaleDateString('es-ES', { weekday: 'long', month: 'long', day: 'numeric' })}\n`;
                output += `🕐 **Hora:** ${eventStart.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })} - ${eventEnd.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}\n`;
            }
            
            if (location) output += `📍 **Ubicación:** ${location}\n`;
            if (attendees.length > 0) output += `👥 **Participantes:** ${attendees.join(', ')}\n`;
            if (create_meet && createdEvent.conferenceData) {
                output += `💻 **Google Meet:** ${createdEvent.conferenceData.entryPoints[0].uri}\n`;
            }
            
            output += `🔗 **Ver en Calendar:** ${createdEvent.htmlLink}`;

            return {
                content: [
                    {
                        type: "text",
                        text: output
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error creando evento: ${error.message}`);
        }
    }

    async updateCalendarEvent(args) {
        try {
            const {
                event_id,
                search_title,
                title,
                description,
                start_datetime,
                end_datetime,
                location,
                attendees,
                add_attendees
            } = args;

            const calendar = google.calendar({ version: 'v3', auth: this.auth });
            
            let eventId = event_id;
            
            // Si no tenemos ID, buscar por título
            if (!eventId && search_title) {
                const searchResponse = await calendar.events.list({
                    calendarId: 'primary',
                    q: search_title,
                    maxResults: 1,
                    singleEvents: true,
                    orderBy: 'startTime'
                });
                
                if (searchResponse.data.items.length === 0) {
                    throw new Error(`No se encontró evento con título "${search_title}"`);
                }
                
                eventId = searchResponse.data.items[0].id;
            }
            
            if (!eventId) {
                throw new Error('event_id o search_title requerido');
            }

            // Obtener evento actual
            const currentEvent = await calendar.events.get({
                calendarId: 'primary',
                eventId: eventId
            });

            // Construir objeto de actualización
            const updateData = { ...currentEvent.data };
            
            if (title) updateData.summary = title;
            if (description !== undefined) updateData.description = description;
            if (location !== undefined) updateData.location = location;
            
            if (start_datetime) {
                updateData.start = {
                    dateTime: start_datetime,
                    timeZone: updateData.start.timeZone || "America/Mexico_City"
                };
            }
            
            if (end_datetime) {
                updateData.end = {
                    dateTime: end_datetime,
                    timeZone: updateData.end.timeZone || "America/Mexico_City"
                };
            }
            
            if (attendees) {
                updateData.attendees = attendees.map(email => ({ email }));
            } else if (add_attendees && add_attendees.length > 0) {
                const currentAttendees = updateData.attendees || [];
                const existingEmails = currentAttendees.map(a => a.email);
                const newAttendees = add_attendees
                    .filter(email => !existingEmails.includes(email))
                    .map(email => ({ email }));
                updateData.attendees = [...currentAttendees, ...newAttendees];
            }

            const response = await calendar.events.update({
                calendarId: 'primary',
                eventId: eventId,
                resource: updateData
            });

            const updatedEvent = response.data;
            const eventStart = new Date(updatedEvent.start.dateTime || updatedEvent.start.date);

            let output = `✅ **Evento actualizado exitosamente:**\n\n`;
            output += `📌 **Título:** ${updatedEvent.summary}\n`;
            output += `🆔 **ID:** ${updatedEvent.id}\n`;
            output += `📅 **Nueva fecha:** ${eventStart.toLocaleDateString('es-ES', { weekday: 'long', month: 'long', day: 'numeric' })}\n`;
            
            if (updatedEvent.start.dateTime) {
                const eventEnd = new Date(updatedEvent.end.dateTime);
                output += `🕐 **Nueva hora:** ${eventStart.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })} - ${eventEnd.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}\n`;
            }
            
            if (updatedEvent.location) output += `📍 **Ubicación:** ${updatedEvent.location}\n`;
            if (updatedEvent.attendees && updatedEvent.attendees.length > 0) {
                output += `👥 **Participantes:** ${updatedEvent.attendees.map(a => a.email).join(', ')}\n`;
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
            throw new Error(`Error actualizando evento: ${error.message}`);
        }
    }

    async deleteCalendarEvent(args) {
        try {
            const { event_id, search_title, confirm = false } = args;

            if (!confirm) {
                throw new Error('Confirmación requerida. Establece confirm=true para eliminar el evento');
            }

            const calendar = google.calendar({ version: 'v3', auth: this.auth });
            
            let eventId = event_id;
            let eventTitle = '';
            
            // Si no tenemos ID, buscar por título
            if (!eventId && search_title) {
                const searchResponse = await calendar.events.list({
                    calendarId: 'primary',
                    q: search_title,
                    maxResults: 1,
                    singleEvents: true,
                    orderBy: 'startTime'
                });
                
                if (searchResponse.data.items.length === 0) {
                    throw new Error(`No se encontró evento con título "${search_title}"`);
                }
                
                eventId = searchResponse.data.items[0].id;
                eventTitle = searchResponse.data.items[0].summary;
            }
            
            if (!eventId) {
                throw new Error('event_id o search_title requerido');
            }

            // Obtener detalles del evento antes de eliminarlo
            if (!eventTitle) {
                const eventDetails = await calendar.events.get({
                    calendarId: 'primary',
                    eventId: eventId
                });
                eventTitle = eventDetails.data.summary;
            }

            await calendar.events.delete({
                calendarId: 'primary',
                eventId: eventId
            });

            return {
                content: [
                    {
                        type: "text",
                        text: `🗑️ **Evento eliminado exitosamente:**\n\n📌 **Título:** ${eventTitle}\n🆔 **ID:** ${eventId}\n\n✅ El evento ha sido cancelado y eliminado del calendario.`
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error eliminando evento: ${error.message}`);
        }
    }

    async findFreeTime(args) {
        try {
            const {
                start_date,
                end_date,
                duration_minutes = 60,
                working_hours_only = true,
                exclude_weekends = true
            } = args;

            const calendar = google.calendar({ version: 'v3', auth: this.auth });
            
            const timeMin = new Date(start_date + 'T00:00:00').toISOString();
            const timeMax = new Date(end_date + 'T23:59:59').toISOString();

            // Obtener eventos ocupados
            const response = await calendar.events.list({
                calendarId: 'primary',
                timeMin: timeMin,
                timeMax: timeMax,
                singleEvents: true,
                orderBy: 'startTime'
            });

            const busyEvents = response.data.items || [];
            const freeSlots = [];

            // Generar slots de tiempo libre
            let current = new Date(start_date + 'T00:00:00');
            const endDate = new Date(end_date + 'T23:59:59');

            while (current < endDate) {
                const dayOfWeek = current.getDay();
                
                // Saltar fines de semana si se especifica
                if (exclude_weekends && (dayOfWeek === 0 || dayOfWeek === 6)) {
                    current.setDate(current.getDate() + 1);
                    current.setHours(0, 0, 0, 0);
                    continue;
                }

                // Definir horario de trabajo
                const workStart = working_hours_only ? 9 : 0;
                const workEnd = working_hours_only ? 18 : 24;

                for (let hour = workStart; hour < workEnd; hour++) {
                    const slotStart = new Date(current);
                    slotStart.setHours(hour, 0, 0, 0);
                    
                    const slotEnd = new Date(slotStart);
                    slotEnd.setMinutes(slotEnd.getMinutes() + duration_minutes);

                    // Verificar si el slot no conflicta con eventos existentes
                    const hasConflict = busyEvents.some(event => {
                        const eventStart = new Date(event.start.dateTime || event.start.date);
                        const eventEnd = new Date(event.end.dateTime || event.end.date);
                        
                        return (slotStart < eventEnd && slotEnd > eventStart);
                    });

                    if (!hasConflict && slotEnd.getDate() === slotStart.getDate()) {
                        freeSlots.push({
                            start: slotStart,
                            end: slotEnd,
                            duration: duration_minutes
                        });
                    }
                }

                current.setDate(current.getDate() + 1);
                current.setHours(0, 0, 0, 0);
            }

            let output = `🔍 **Tiempo libre encontrado** (${freeSlots.length} slots disponibles)\n\n`;
            output += `📅 **Período:** ${start_date} - ${end_date}\n`;
            output += `⏱️ **Duración mínima:** ${duration_minutes} minutos\n`;
            output += `💼 **Solo horario laboral:** ${working_hours_only ? 'Sí (9am-6pm)' : 'No'}\n`;
            output += `📅 **Excluir fines de semana:** ${exclude_weekends ? 'Sí' : 'No'}\n\n`;

            if (freeSlots.length === 0) {
                output += `❌ No se encontraron espacios libres con los criterios especificados.`;
            } else {
                output += `✅ **Espacios disponibles:**\n\n`;
                
                freeSlots.slice(0, 20).forEach((slot, index) => { // Limitar a 20 resultados
                    output += `${index + 1}. 📅 ${slot.start.toLocaleDateString('es-ES', { weekday: 'long', month: 'short', day: 'numeric' })}\n`;
                    output += `   🕐 ${slot.start.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })} - ${slot.end.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}\n`;
                    output += `   ⏱️ Duración: ${slot.duration} minutos\n\n`;
                });

                if (freeSlots.length > 20) {
                    output += `... y ${freeSlots.length - 20} espacios más disponibles.`;
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
            throw new Error(`Error buscando tiempo libre: ${error.message}`);
        }
    }

    async sendCalendarReminderEmail(args) {
        try {
            const {
                recipient_email = this.user_email,
                subject,
                message,
                event_title,
                event_datetime
            } = args;

            const gmail = google.gmail({ version: 'v1', auth: this.auth });

            let emailBody = `Estimado usuario,\n\n${message}\n\n`;
            
            if (event_title) {
                emailBody += `📅 Evento: ${event_title}\n`;
            }
            
            if (event_datetime) {
                emailBody += `🕐 Fecha/Hora: ${event_datetime}\n`;
            }
            
            emailBody += `\nEste es un recordatorio automático enviado desde tu asistente Aura.\n\n`;
            emailBody += `Saludos,\nTu Asistente Personal Aura 🤖`;

            const email = [
                `To: ${recipient_email}`,
                `Subject: ${subject}`,
                '',
                emailBody
            ].join('\n');

            const encodedEmail = Buffer.from(email).toString('base64')
                .replace(/\+/g, '-')
                .replace(/\//g, '_')
                .replace(/=+$/, '');

            await gmail.users.messages.send({
                userId: 'me',
                resource: {
                    raw: encodedEmail
                }
            });

            return {
                content: [
                    {
                        type: "text",
                        text: `📧 **Recordatorio enviado exitosamente:**\n\n📨 **Para:** ${recipient_email}\n📋 **Asunto:** ${subject}\n✅ **Estado:** Enviado\n\n💡 El recordatorio ha sido entregado a la bandeja de entrada.`
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error enviando recordatorio: ${error.message}`);
        }
    }

    async getCalendarSummary(args) {
        try {
            const {
                period = "week",
                start_date,
                end_date,
                include_stats = true
            } = args;

            const calendar = google.calendar({ version: 'v3', auth: this.auth });

            // Calcular fechas del período
            let timeMin, timeMax;
            const now = new Date();

            switch (period) {
                case 'week':
                    const startOfWeek = new Date(now);
                    startOfWeek.setDate(now.getDate() - now.getDay());
                    startOfWeek.setHours(0, 0, 0, 0);
                    timeMin = startOfWeek;
                    timeMax = new Date(startOfWeek);
                    timeMax.setDate(startOfWeek.getDate() + 7);
                    break;
                case 'month':
                    timeMin = new Date(now.getFullYear(), now.getMonth(), 1);
                    timeMax = new Date(now.getFullYear(), now.getMonth() + 1, 0);
                    timeMax.setHours(23, 59, 59, 999);
                    break;
                case 'custom':
                    if (!start_date || !end_date) {
                        throw new Error('start_date y end_date requeridos para período custom');
                    }
                    timeMin = new Date(start_date + 'T00:00:00');
                    timeMax = new Date(end_date + 'T23:59:59');
                    break;
            }

            const response = await calendar.events.list({
                calendarId: 'primary',
                timeMin: timeMin.toISOString(),
                timeMax: timeMax.toISOString(),
                singleEvents: true,
                orderBy: 'startTime'
            });

            const events = response.data.items || [];

            // Calcular estadísticas
            const stats = {
                totalEvents: events.length,
                meetings: 0,
                allDayEvents: 0,
                eventsWithLocation: 0,
                eventsWithAttendees: 0,
                totalDuration: 0,
                byDay: {},
                upcomingEvents: []
            };

            const dayNames = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];

            events.forEach(event => {
                const start = new Date(event.start.dateTime || event.start.date);
                const dayName = dayNames[start.getDay()];
                
                stats.byDay[dayName] = (stats.byDay[dayName] || 0) + 1;

                if (event.start.dateTime && event.end.dateTime) {
                    const end = new Date(event.end.dateTime);
                    const duration = (end - start) / (1000 * 60); // minutos
                    stats.totalDuration += duration;
                } else {
                    stats.allDayEvents++;
                }

                if (event.attendees && event.attendees.length > 1) {
                    stats.meetings++;
                    stats.eventsWithAttendees++;
                }

                if (event.location) {
                    stats.eventsWithLocation++;
                }

                // Eventos próximos (próximos 7 días desde hoy)
                const weekFromNow = new Date();
                weekFromNow.setDate(weekFromNow.getDate() + 7);
                if (start > now && start <= weekFromNow) {
                    stats.upcomingEvents.push(event);
                }
            });

            let output = `📊 **Resumen del Calendar** (${this.getPeriodLabel(period, start_date, end_date)})\n\n`;
            
            output += `📈 **Estadísticas generales:**\n`;
            output += `• Total de eventos: ${stats.totalEvents}\n`;
            output += `• Reuniones/Citas: ${stats.meetings}\n`;
            output += `• Eventos de todo el día: ${stats.allDayEvents}\n`;
            output += `• Con ubicación: ${stats.eventsWithLocation}\n`;
            output += `• Con participantes: ${stats.eventsWithAttendees}\n`;
            
            if (stats.totalDuration > 0) {
                const hours = Math.floor(stats.totalDuration / 60);
                const minutes = Math.floor(stats.totalDuration % 60);
                output += `• Tiempo total en eventos: ${hours}h ${minutes}min\n`;
            }

            if (include_stats && Object.keys(stats.byDay).length > 0) {
                output += `\n📅 **Distribución por día:**\n`;
                Object.entries(stats.byDay).forEach(([day, count]) => {
                    output += `• ${day.charAt(0).toUpperCase() + day.slice(1)}: ${count} eventos\n`;
                });
            }

            if (stats.upcomingEvents.length > 0) {
                output += `\n🔮 **Próximos eventos (7 días):**\n`;
                stats.upcomingEvents.slice(0, 5).forEach(event => {
                    const start = new Date(event.start.dateTime || event.start.date);
                    output += `• ${event.summary} - ${start.toLocaleDateString('es-ES', { month: 'short', day: 'numeric' })}\n`;
                });
            }

            // Análisis de productividad
            if (include_stats) {
                output += `\n💡 **Insights:**\n`;
                
                const busyDays = Object.entries(stats.byDay)
                    .sort(([,a], [,b]) => b - a)
                    .slice(0, 2);
                
                if (busyDays.length > 0) {
                    output += `• Días más ocupados: ${busyDays.map(([day, count]) => `${day} (${count})`).join(', ')}\n`;
                }
                
                const meetingRatio = stats.totalEvents > 0 ? Math.round((stats.meetings / stats.totalEvents) * 100) : 0;
                output += `• ${meetingRatio}% de tus eventos involucran a otras personas\n`;
                
                if (stats.totalDuration > 0) {
                    const avgDuration = Math.round(stats.totalDuration / (stats.totalEvents - stats.allDayEvents));
                    output += `• Duración promedio por evento: ${avgDuration} minutos\n`;
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
            throw new Error(`Error generando resumen: ${error.message}`);
        }
    }

    getPeriodLabel(period, startDate, endDate) {
        switch (period) {
            case 'today': return 'hoy';
            case 'tomorrow': return 'mañana';
            case 'week': return 'esta semana';
            case 'month': return 'este mes';
            case 'custom': return `${startDate} - ${endDate}`;
            default: return period;
        }
    }
}

// ======= CLI =======
async function main() {
    try {
        const server = new GoogleWorkspaceServer();
        await server.initialize();
        console.error(`🔧 Google Workspace MCP Server iniciado exitosamente`);
        console.error(`📧 Configurado para usuario: ${server.user_email}`);
    } catch (error) {
        console.error(`❌ Error: ${error.message}`);
        process.exit(1);
    }

    const server = new GoogleWorkspaceServer();

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
        console.error('🛑 Google Workspace MCP Server terminado');
        process.exit(0);
    });
}

if (require.main === module) {
    main().catch((err) => {
        console.error('❌ Error fatal:', err);
        process.exit(1);
    });
}

module.exports = GoogleWorkspaceServer;