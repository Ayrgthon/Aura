#!/usr/bin/env node

/**
 * Servidor MCP para SerpAPI - Búsquedas de Google
 * Compatible con la arquitectura MCP existente de Aura
 */

const https = require('https');
const { URL } = require('url');

// Configuración del servidor MCP
const MCP_CONFIG = {
    name: "serpapi",
    version: "1.0.0",
    api_key: process.env.SERPAPI_API_KEY
};

class SerpApiServer {
    constructor() {
        this.api_key = MCP_CONFIG.api_key;
        
        if (!this.api_key) {
            throw new Error('SERPAPI_API_KEY es requerida en las variables de entorno');
        }
        
        this.tools = [
            {
                name: "google_search",
                description: "Realiza búsquedas en Google usando SerpAPI. Devuelve resultados orgánicos, anuncios, snippets destacados y más.",
                inputSchema: {
                    type: "object",
                    properties: {
                        query: {
                            type: "string",
                            description: "Término de búsqueda en Google"
                        },
                        location: {
                            type: "string",
                            description: "Ubicación para la búsqueda (ej: 'Colombia', 'New York, NY')",
                            default: "Colombia"
                        },
                        language: {
                            type: "string",
                            description: "Idioma de los resultados (ej: 'es', 'en')",
                            default: "es"
                        },
                        num_results: {
                            type: "integer",
                            description: "Número de resultados a obtener (1-100)",
                            default: 10
                        },
                        safe_search: {
                            type: "string",
                            enum: ["active", "off"],
                            description: "Filtro de búsqueda segura",
                            default: "active"
                        }
                    },
                    required: ["query"]
                }
            },
            {
                name: "google_news_search",
                description: "Busca noticias recientes en Google News usando SerpAPI.",
                inputSchema: {
                    type: "object",
                    properties: {
                        query: {
                            type: "string",
                            description: "Término de búsqueda para noticias"
                        },
                        location: {
                            type: "string",
                            description: "Ubicación para las noticias",
                            default: "Colombia"
                        },
                        language: {
                            type: "string",
                            description: "Idioma de las noticias",
                            default: "es"
                        },
                        time_period: {
                            type: "string",
                            enum: ["qdr:h", "qdr:d", "qdr:w", "qdr:m", "qdr:y"],
                            description: "Período de tiempo: qdr:h (1 hora), qdr:d (1 día), qdr:w (1 semana), qdr:m (1 mes), qdr:y (1 año)",
                            default: "qdr:d"
                        }
                    },
                    required: ["query"]
                }
            },
            {
                name: "google_images_search",
                description: "Busca imágenes en Google usando SerpAPI.",
                inputSchema: {
                    type: "object",
                    properties: {
                        query: {
                            type: "string",
                            description: "Término de búsqueda para imágenes"
                        },
                        image_size: {
                            type: "string",
                            enum: ["large", "medium", "icon"],
                            description: "Tamaño de las imágenes",
                            default: "medium"
                        },
                        image_type: {
                            type: "string",
                            enum: ["photo", "clipart", "lineart", "face", "news"],
                            description: "Tipo de imagen"
                        },
                        num_results: {
                            type: "integer",
                            description: "Número de imágenes a obtener (1-50)",
                            default: 10
                        }
                    },
                    required: ["query"]
                }
            },
            {
                name: "google_hotels_search",
                description: "Busca hoteles en Google Hotels con filtros avanzados. Ideal para encontrar hoteles más populares/valorados por ciudad.",
                inputSchema: {
                    type: "object",
                    properties: {
                        query: {
                            type: "string",
                            description: "Ciudad o ubicación para buscar hoteles (ej: 'Bogotá', 'Medellín', 'Cartagena')"
                        },
                        check_in_date: {
                            type: "string",
                            description: "Fecha de check-in en formato YYYY-MM-DD (opcional)"
                        },
                        check_out_date: {
                            type: "string", 
                            description: "Fecha de check-out en formato YYYY-MM-DD (opcional)"
                        },
                        sort_by: {
                            type: "integer",
                            description: "Ordenar por: 3=Precio más bajo, 8=Rating más alto, 13=Más reseñas. Default: 8"
                        },
                        adults: {
                            type: "integer",
                            description: "Número de adultos (default: 2)"
                        },
                        children: {
                            type: "integer",
                            description: "Número de niños (default: 0)"
                        },
                        min_price: {
                            type: "integer",
                            description: "Precio mínimo por noche"
                        },
                        max_price: {
                            type: "integer",
                            description: "Precio máximo por noche"
                        },
                        currency: {
                            type: "string",
                            description: "Moneda para precios (ej: 'USD', 'COP'). Default: USD"
                        }
                    },
                    required: ["query"]
                }
            },
            {
                name: "google_hotels_property_details",
                description: "Obtiene detalles específicos de un hotel usando su property_token de Google Hotels.",
                inputSchema: {
                    type: "object",
                    properties: {
                        property_token: {
                            type: "string",
                            description: "Token único del hotel obtenido de google_hotels_search"
                        },
                        check_in_date: {
                            type: "string",
                            description: "Fecha de check-in en formato YYYY-MM-DD (opcional)"
                        },
                        check_out_date: {
                            type: "string",
                            description: "Fecha de check-out en formato YYYY-MM-DD (opcional)"
                        },
                        adults: {
                            type: "integer",
                            description: "Número de adultos (default: 2)"
                        },
                        currency: {
                            type: "string",
                            description: "Moneda para precios (default: USD)"
                        }
                    },
                    required: ["property_token"]
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
            case 'google_search':
                return await this.googleSearch(args);
            case 'google_news_search':
                return await this.googleNewsSearch(args);
            case 'google_images_search':
                return await this.googleImagesSearch(args);
            case 'google_hotels_search':
                return await this.googleHotelsSearch(args);
            case 'google_hotels_property_details':
                return await this.googleHotelsPropertyDetails(args);
            default:
                throw new Error(`Herramienta desconocida: ${name}`);
        }
    }

    async googleSearch(args) {
        const { 
            query, 
            location = "Colombia", 
            language = "es", 
            num_results = 10,
            safe_search = "active"
        } = args;

        if (!query || query.trim() === '') {
            throw new Error('Query de búsqueda requerido');
        }

        const searchParams = {
            engine: 'google',
            q: query,
            location: location,
            hl: language,
            gl: language === 'es' ? 'co' : 'us',
            num: Math.min(num_results, 100),
            safe: safe_search,
            api_key: this.api_key
        };

        try {
            const data = await this.makeRequest(searchParams);
            return {
                content: [
                    {
                        type: "text",
                        text: this.formatGoogleResults(data, query)
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error en búsqueda de Google: ${error.message}`);
        }
    }

    async googleNewsSearch(args) {
        const { 
            query, 
            location = "Colombia", 
            language = "es",
            time_period = "qdr:d"
        } = args;

        if (!query || query.trim() === '') {
            throw new Error('Query de búsqueda requerido');
        }

        const searchParams = {
            engine: 'google',
            q: query,
            location: location,
            hl: language,
            gl: language === 'es' ? 'co' : 'us',
            tbm: 'nws',
            tbs: time_period,
            api_key: this.api_key
        };

        try {
            const data = await this.makeRequest(searchParams);
            return {
                content: [
                    {
                        type: "text",
                        text: this.formatNewsResults(data, query)
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error en búsqueda de noticias: ${error.message}`);
        }
    }

    async googleImagesSearch(args) {
        const { 
            query, 
            image_size = "medium", 
            image_type,
            num_results = 10
        } = args;

        if (!query || query.trim() === '') {
            throw new Error('Query de búsqueda requerido');
        }

        const searchParams = {
            engine: 'google',
            q: query,
            tbm: 'isch',
            imgsz: image_size,
            num: Math.min(num_results, 50),
            api_key: this.api_key
        };

        if (image_type) {
            searchParams.imgtype = image_type;
        }

        try {
            const data = await this.makeRequest(searchParams);
            return {
                content: [
                    {
                        type: "text",
                        text: this.formatImageResults(data, query)
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error en búsqueda de imágenes: ${error.message}`);
        }
    }

    async googleHotelsSearch(args) {
        const { 
            query, 
            check_in_date,
            check_out_date,
            sort_by = 8,
            adults = 2,
            children = 0,
            min_price,
            max_price,
            currency = "USD"
        } = args;

        if (!query || query.trim() === '') {
            throw new Error('Query de búsqueda requerido');
        }

        const searchParams = {
            engine: 'google_hotels',
            q: query,
            gl: 'co', // Colombia
            hl: 'es', // Español
            currency: currency,
            adults: adults,
            sort_by: sort_by,
            api_key: this.api_key
        };

        // Agregar parámetros opcionales solo si están definidos
        if (check_in_date) searchParams.check_in_date = check_in_date;
        if (check_out_date) searchParams.check_out_date = check_out_date;
        if (children > 0) searchParams.children = children;
        if (min_price) searchParams.min_price = min_price;
        if (max_price) searchParams.max_price = max_price;

        try {
            const data = await this.makeRequest(searchParams);
            return {
                content: [
                    {
                        type: "text",
                        text: this.formatHotelsResults(data, query)
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error en búsqueda de hoteles: ${error.message}`);
        }
    }

    async googleHotelsPropertyDetails(args) {
        const { 
            property_token,
            check_in_date,
            check_out_date,
            adults = 2,
            currency = "USD"
        } = args;

        if (!property_token || property_token.trim() === '') {
            throw new Error('Property token requerido');
        }

        const searchParams = {
            engine: 'google_hotels_property_details',
            property_token: property_token,
            gl: 'co',
            hl: 'es', 
            currency: currency,
            adults: adults,
            api_key: this.api_key
        };

        // Agregar fechas si están definidas
        if (check_in_date) searchParams.check_in_date = check_in_date;
        if (check_out_date) searchParams.check_out_date = check_out_date;

        try {
            const data = await this.makeRequest(searchParams);
            return {
                content: [
                    {
                        type: "text", 
                        text: this.formatHotelDetailsResults(data)
                    }
                ]
            };
        } catch (error) {
            throw new Error(`Error obteniendo detalles del hotel: ${error.message}`);
        }
    }

    async makeRequest(params) {
        return new Promise((resolve, reject) => {
            const url = new URL('https://serpapi.com/search.json');
            
            // Agregar parámetros a la URL
            Object.entries(params).forEach(([key, value]) => {
                if (value !== undefined && value !== null) {
                    url.searchParams.append(key, value.toString());
                }
            });

            const options = {
                method: 'GET',
                headers: {
                    'User-Agent': 'Aura-MCP-SerpAPI/1.0.0',
                    'Accept': 'application/json'
                }
            };

            const req = https.request(url, options, (res) => {
                let data = '';

                res.on('data', (chunk) => {
                    data += chunk;
                });

                res.on('end', () => {
                    try {
                        if (res.statusCode !== 200) {
                            console.error(`❌ Error HTTP ${res.statusCode}: ${data}`);
                            reject(new Error(`HTTP ${res.statusCode}: ${data}`));
                            return;
                        }

                        const jsonData = JSON.parse(data);
                        
                        if (jsonData.error) {
                            console.error(`❌ Error de SerpAPI: ${jsonData.error}`);
                            reject(new Error(jsonData.error));
                            return;
                        }

                        resolve(jsonData);
                    } catch (error) {
                        console.error(`❌ Error parsing JSON: ${error.message}`);
                        reject(new Error(`Error parsing JSON: ${error.message}`));
                    }
                });
            });

            req.on('error', (error) => {
                console.error(`❌ Error de conexión: ${error.message}`);
                reject(new Error(`Request error: ${error.message}`));
            });

            req.setTimeout(30000, () => {
                console.error(`❌ Timeout de petición`);
                req.destroy();
                reject(new Error('Request timeout'));
            });

            req.end();
        });
    }

    formatGoogleResults(data, query) {
        let output = `🔍 **Resultados de Google para: "${query}"**\n\n`;

        // Snippet destacado si existe
        if (data.answer_box) {
            output += `📌 **Respuesta destacada:**\n${data.answer_box.answer || data.answer_box.snippet}\n`;
            if (data.answer_box.link) {
                output += `🔗 Fuente: ${data.answer_box.link}\n`;
            }
            output += `\n---\n\n`;
        }

        // Knowledge Graph si existe
        if (data.knowledge_graph) {
            const kg = data.knowledge_graph;
            output += `📊 **Panel de conocimiento:**\n`;
            output += `**${kg.title}** - ${kg.type || 'Información'}\n`;
            if (kg.description) {
                output += `${kg.description}\n`;
            }
            output += `\n---\n\n`;
        }

        // Resultados orgánicos
        if (data.organic_results && data.organic_results.length > 0) {
            output += `📋 **Resultados orgánicos:**\n\n`;
            
            data.organic_results.forEach((result, index) => {
                output += `${index + 1}. **${result.title}**\n`;
                output += `🔗 ${result.link}\n`;
                if (result.snippet) {
                    output += `📝 ${result.snippet}\n`;
                }
                if (result.date) {
                    output += `📅 ${result.date}\n`;
                }
                output += `\n`;
            });
        }

        // Búsquedas relacionadas
        if (data.related_searches && data.related_searches.length > 0) {
            output += `\n🔍 **Búsquedas relacionadas:**\n`;
            data.related_searches.slice(0, 5).forEach(search => {
                output += `• ${search.query}\n`;
            });
        }

        return output || `No se encontraron resultados para: "${query}"`;
    }

    formatNewsResults(data, query) {
        let output = `📰 **Noticias para: "${query}"**\n\n`;

        if (data.news_results && data.news_results.length > 0) {
            data.news_results.forEach((news, index) => {
                output += `${index + 1}. **${news.title}**\n`;
                output += `📰 ${news.source}\n`;
                output += `🔗 ${news.link}\n`;
                if (news.snippet) {
                    output += `📝 ${news.snippet}\n`;
                }
                if (news.date) {
                    output += `📅 ${news.date}\n`;
                }
                output += `\n`;
            });
        } else {
            output += `No se encontraron noticias recientes para: "${query}"`;
        }

        return output;
    }

    formatImageResults(data, query) {
        let output = `🖼️ **Imágenes para: "${query}"**\n\n`;

        if (data.images_results && data.images_results.length > 0) {
            data.images_results.forEach((image, index) => {
                output += `${index + 1}. **${image.title || 'Imagen'}**\n`;
                output += `🔗 URL de imagen: ${image.original}\n`;
                output += `📐 Dimensiones: ${image.original_width}x${image.original_height}\n`;
                if (image.source) {
                    output += `🌐 Fuente: ${image.source}\n`;
                }
                output += `\n`;
            });
        } else {
            output += `No se encontraron imágenes para: "${query}"`;
        }

        return output;
    }

    formatHotelsResults(data, query) {
        let output = `🏨 **Hoteles en: "${query}"**\n\n`;

        if (data && data.properties && Array.isArray(data.properties) && data.properties.length > 0) {
            output += `🔍 **Se encontraron ${data.properties.length} hoteles**\n\n`;
            
            data.properties.forEach((hotel, index) => {
                if (!hotel) return; // Skip null/undefined hotels
                output += `**${index + 1}. ${hotel.name || 'Hotel sin nombre'}**\n`;
                
                if (hotel.overall_rating) {
                    output += `⭐ Rating: ${hotel.overall_rating}`;
                    if (hotel.reviews) {
                        output += ` (${hotel.reviews} reseñas)`;
                    }
                    output += `\n`;
                }
                
                if (hotel.rate_per_night && hotel.rate_per_night.lowest) {
                    output += `💰 Precio: ${hotel.rate_per_night.lowest} por noche\n`;
                }
                
                if (hotel.nearby_places && hotel.nearby_places.length > 0 && hotel.nearby_places[0] && hotel.nearby_places[0].name) {
                    output += `📍 Ubicación: ${hotel.nearby_places[0].name}\n`;
                }
                
                if (hotel.amenities && hotel.amenities.length > 0) {
                    const topAmenities = hotel.amenities.slice(0, 3).map(a => a && a.name ? a.name : 'Servicio').join(', ');
                    output += `🛎️ Servicios: ${topAmenities}\n`;
                }
                
                if (hotel.property_token) {
                    output += `🔗 Property Token: ${hotel.property_token}\n`;
                }
                
                if (hotel.link) {
                    output += `🌐 Ver más: ${hotel.link}\n`;
                }
                
                output += `\n`;
            });
            
            // Información adicional si está disponible
            if (data.search_metadata && data.search_metadata.total_results) {
                output += `\n📊 **Total de resultados disponibles:** ${data.search_metadata.total_results}`;
            }
            
        } else {
            output += `No se encontraron hoteles para: "${query}"\n`;
            if (data && data.error) {
                output += `Error de SerpAPI: ${data.error}\n`;
            }
        }

        return output;
    }

    formatHotelDetailsResults(data) {
        let output = `🏨 **Detalles del Hotel**\n\n`;

        if (data.property_details) {
            const hotel = data.property_details;
            
            output += `**${hotel.name || 'Hotel'}**\n`;
            
            if (hotel.overall_rating) {
                output += `⭐ Rating General: ${hotel.overall_rating}`;
                if (hotel.reviews_breakdown && hotel.reviews_breakdown.mentions) {
                    output += ` (${hotel.reviews_breakdown.mentions} reseñas)`;
                }
                output += `\n`;
            }
            
            if (hotel.address) {
                output += `📍 Dirección: ${hotel.address}\n`;
            }
            
            if (hotel.phone) {
                output += `📞 Teléfono: ${hotel.phone}\n`;
            }
            
            if (hotel.check_in_time || hotel.check_out_time) {
                output += `🕐 Check-in: ${hotel.check_in_time || 'N/A'} | Check-out: ${hotel.check_out_time || 'N/A'}\n`;
            }
            
            if (hotel.price && hotel.price.offers && hotel.price.offers.length > 0) {
                output += `\n💰 **Precios:**\n`;
                hotel.price.offers.slice(0, 3).forEach(offer => {
                    output += `• ${offer.rate_per_night || offer.total_rate} - ${offer.booking_option || 'Oferta'}\n`;
                });
            }
            
            if (hotel.amenities && Array.isArray(hotel.amenities) && hotel.amenities.length > 0) {
                output += `\n🛎️ **Servicios y Amenidades:**\n`;
                hotel.amenities.forEach(amenity => {
                    if (amenity && amenity.name) {
                        output += `• ${amenity.name}\n`;
                    }
                });
            }
            
            if (hotel.about && Array.isArray(hotel.about) && hotel.about.length > 0) {
                output += `\n📝 **Sobre el hotel:**\n`;
                hotel.about.slice(0, 3).forEach(info => {
                    if (info && info.title && info.description) {
                        output += `• **${info.title}**: ${info.description}\n`;
                    }
                });
            }
            
            if (hotel.reviews_breakdown) {
                output += `\n📊 **Desglose de Reviews:**\n`;
                if (hotel.reviews_breakdown.location) {
                    output += `• Ubicación: ${hotel.reviews_breakdown.location}\n`;
                }
                if (hotel.reviews_breakdown.cleanliness) {
                    output += `• Limpieza: ${hotel.reviews_breakdown.cleanliness}\n`;
                }
                if (hotel.reviews_breakdown.service) {
                    output += `• Servicio: ${hotel.reviews_breakdown.service}\n`;
                }
                if (hotel.reviews_breakdown.value) {
                    output += `• Relación calidad-precio: ${hotel.reviews_breakdown.value}\n`;
                }
            }
            
        } else {
            output += `No se pudieron obtener los detalles del hotel.`;
        }

        return output;
    }
}

// ======= CLI =======
async function main() {
    try {
        const server = new SerpApiServer();
        console.error(`🔍 SerpAPI MCP Server iniciado con API key configurada`);
    } catch (error) {
        console.error(`❌ Error: ${error.message}`);
        process.exit(1);
    }

    const server = new SerpApiServer();

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
        console.error('🛑 SerpAPI MCP Server terminado');
        process.exit(0);
    });
}

if (require.main === module) {
    main().catch((err) => {
        console.error('❌ Error fatal:', err);
        process.exit(1);
    });
}

module.exports = SerpApiServer;