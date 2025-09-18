#!/usr/bin/env node

/**
 * Servidor MCP para Control de Hyprland - Simplificado y Funcional
 */

const { exec, execSync } = require('child_process');
const { promisify } = require('util');
const execAsync = promisify(exec);

// Configurar variables de entorno para Hyprland
process.env.PATH = process.env.PATH + ':/usr/bin:/usr/local/bin';

// Si no están configuradas, intentar obtenerlas del entorno
if (!process.env.HYPRLAND_INSTANCE_SIGNATURE || !process.env.WAYLAND_DISPLAY) {
    console.error(`⚠️ Variables de entorno Hyprland no configuradas.`);
    console.error(`Actual HYPRLAND_INSTANCE_SIGNATURE: ${process.env.HYPRLAND_INSTANCE_SIGNATURE || 'undefined'}`);
    console.error(`Actual WAYLAND_DISPLAY: ${process.env.WAYLAND_DISPLAY || 'undefined'}`);
}

const MCP_CONFIG = {
    name: "hyprland-control",
    version: "1.0.0"
};

class HyprlandControlServer {
    constructor() {
        this.tools = [
            {
                name: "open_app_in_workspace",
                description: "CUÁNDO USAR: Cuando el usuario quiera abrir una aplicación específica en un espacio de trabajo/workspace específico de Hyprland. Ejemplos de frases que activan esta herramienta: 'abre notion en el espacio de trabajo 3', 'abre firefox en workspace 2', 'abrir obsidian en el workspace 4', 'lanza spotify en espacio 5'. CÓMO USAR: Antes de ejecutar esta herramienta, SIEMPRE usa 'sequentialthinking' para planificar la acción y confirmar que entiendes correctamente qué aplicación y qué workspace solicita el usuario. La herramienta cambia automáticamente al workspace especificado y luego abre la aplicación deseada. Auto-detecta inteligentemente el comando ejecutable correcto para aplicaciones comunes como notion (notion-app), obsidian, firefox, chrome (google-chrome), code, spotify, discord, etc. Funciona con aplicaciones instaladas via paquetes normales, Flatpak, y Snap. IMPORTANTE: Los números de workspace van del 1 al 10. Si el usuario dice 'tres' convertir a 3, 'cuatro' a 4, etc.",
                inputSchema: {
                    type: "object",
                    properties: {
                        application: {
                            type: "string",
                            description: "Nombre de la aplicación a abrir. Puede ser el nombre común (notion, firefox, obsidian, code, spotify, discord, etc.) - el sistema auto-detectará el comando ejecutable correcto."
                        },
                        workspace: {
                            type: "integer",
                            description: "Número del workspace/espacio de trabajo de Hyprland donde abrir la aplicación (1-10). Si el usuario dice números en palabras ('tres', 'cuatro'), convertir a números (3, 4).",
                            minimum: 1,
                            maximum: 10
                        }
                    },
                    required: ["application", "workspace"]
                }
            }
        ];
    }

    async handleRequest(request) {
        try {
            console.error(`DEBUG: Request received:`, JSON.stringify(request));
            const { method, params, id } = request;
            console.error(`DEBUG: Method: ${method}, Params:`, params);
            let result;

            switch (method) {
                case 'initialize':
                    result = {
                        protocolVersion: "2024-11-05",
                        capabilities: { tools: { listChanged: false } },
                        serverInfo: { name: MCP_CONFIG.name, version: MCP_CONFIG.version }
                    };
                    break;
                case 'tools/list':
                    result = { tools: this.tools };
                    break;
                case 'tools/call':
                    result = await this.callTool(params);
                    break;
                default:
                    throw new Error(`Método desconocido: ${method}`);
            }

            return { jsonrpc: "2.0", id: id, result: result };
        } catch (error) {
            return {
                jsonrpc: "2.0",
                id: request.id || null,
                error: { code: -1, message: error.message }
            };
        }
    }

    async callTool(params) {
        console.error(`DEBUG: callTool called with params:`, params);
        const { name, arguments: args } = params;
        console.error(`DEBUG: Tool name: ${name}, Args:`, args);

        if (name === 'open_app_in_workspace') {
            console.error(`DEBUG: Calling openAppInWorkspace...`);
            const result = await this.openAppInWorkspace(args);
            console.error(`DEBUG: openAppInWorkspace result:`, result);
            return result;
        }
        throw new Error(`Herramienta desconocida: ${name}`);
    }

    async openAppInWorkspace(args) {
        console.error(`DEBUG: openAppInWorkspace called with:`, args);
        const { application, workspace } = args;

        try {
            console.error(`DEBUG: Starting execution for ${application} in workspace ${workspace}`);
            // 1. Detectar comando real
            console.error(`DEBUG: Finding command for ${application}...`);
            const realCommand = await this.findCommand(application);
            console.error(`DEBUG: Found command: ${realCommand}`);

            // 2. Verificar que hyprctl esté disponible con ruta completa
            const HYPRCTL_PATH = '/usr/bin/hyprctl';
            console.error(`DEBUG: Checking hyprctl availability...`);
            try {
                const env = {
                    ...process.env,
                    HYPRLAND_INSTANCE_SIGNATURE: process.env.HYPRLAND_INSTANCE_SIGNATURE,
                    WAYLAND_DISPLAY: process.env.WAYLAND_DISPLAY,
                    XDG_CURRENT_DESKTOP: process.env.XDG_CURRENT_DESKTOP
                };
                console.error(`DEBUG: Using env vars - HYPRLAND_INSTANCE_SIGNATURE: ${env.HYPRLAND_INSTANCE_SIGNATURE}, WAYLAND_DISPLAY: ${env.WAYLAND_DISPLAY}`);

                // Usar execSync para evitar problemas de timeout
                const stdout = execSync(`${HYPRCTL_PATH} version`, {
                    encoding: 'utf8',
                    env,
                    timeout: 5000
                });
                console.error(`DEBUG: hyprctl is available - ${stdout.split('\n')[0]}`);
            } catch (error) {
                console.error(`DEBUG: hyprctl not available: ${error.message}`);
                throw new Error(`Hyprctl no disponible en ${HYPRCTL_PATH}. ¿Estás ejecutando Hyprland? Error: ${error.message}`);
            }

            // 3. Cambiar workspace con manejo robusto de errores
            console.error(`DEBUG: Executing workspace command: ${HYPRCTL_PATH} dispatch workspace ${workspace}`);
            let workspaceResult;
            try {
                const env = {
                    ...process.env,
                    HYPRLAND_INSTANCE_SIGNATURE: process.env.HYPRLAND_INSTANCE_SIGNATURE,
                    WAYLAND_DISPLAY: process.env.WAYLAND_DISPLAY,
                    XDG_CURRENT_DESKTOP: process.env.XDG_CURRENT_DESKTOP
                };
                const stdout = execSync(`${HYPRCTL_PATH} dispatch workspace ${workspace}`, {
                    encoding: 'utf8',
                    env,
                    timeout: 5000
                });
                workspaceResult = { stdout, stderr: '' };
                console.error(`DEBUG: Workspace command result: ${stdout || 'ok'}`);

                // hyprctl no siempre devuelve error en stderr para comandos válidos
                if (workspaceResult.stderr && workspaceResult.stderr.includes('error')) {
                    console.error(`DEBUG: Workspace command stderr: ${workspaceResult.stderr}`);
                    throw new Error(`Error en hyprctl: ${workspaceResult.stderr}`);
                }
            } catch (error) {
                console.error(`DEBUG: Workspace command failed: ${error.message}`);
                throw new Error(`Error ejecutando hyprctl dispatch workspace ${workspace}: ${error.message}`);
            }

            // 4. Continuar sin pausa - hyprctl es lo suficientemente rápido
            console.error(`DEBUG: Continuing without pause...`);

            // 5. Verificar workspace actual (opcional - puede fallar si workspace no tiene ventanas)
            console.error(`DEBUG: Verifying workspace change...`);
            try {
                const env = {
                    ...process.env,
                    HYPRLAND_INSTANCE_SIGNATURE: process.env.HYPRLAND_INSTANCE_SIGNATURE,
                    WAYLAND_DISPLAY: process.env.WAYLAND_DISPLAY,
                    XDG_CURRENT_DESKTOP: process.env.XDG_CURRENT_DESKTOP
                };
                const stdout = execSync(`${HYPRCTL_PATH} activeworkspace`, {
                    encoding: 'utf8',
                    env,
                    timeout: 3000
                });
                console.error(`DEBUG: Current workspace: ${stdout.trim()}`);
                if (!stdout.includes(`workspace ID ${workspace}`)) {
                    // No lanzar error, solo advertencia
                    console.error(`DEBUG: Workspace verification failed, but continuing...`);
                }
            } catch (verifyError) {
                // Ignorar errores de verificación
                console.error(`DEBUG: Workspace verification error: ${verifyError.message}`);
            }

            // 6. Abrir aplicación
            console.error(`DEBUG: Executing app command: ${HYPRCTL_PATH} dispatch exec ${realCommand}`);
            let execResult;
            try {
                const env = {
                    ...process.env,
                    HYPRLAND_INSTANCE_SIGNATURE: process.env.HYPRLAND_INSTANCE_SIGNATURE,
                    WAYLAND_DISPLAY: process.env.WAYLAND_DISPLAY,
                    XDG_CURRENT_DESKTOP: process.env.XDG_CURRENT_DESKTOP
                };
                const stdout = execSync(`${HYPRCTL_PATH} dispatch exec ${realCommand}`, {
                    encoding: 'utf8',
                    env,
                    timeout: 5000
                });
                execResult = { stdout, stderr: '' };
                console.error(`DEBUG: App command result: ${stdout || 'ok'}`);

                if (execResult.stderr && execResult.stderr.includes('error')) {
                    console.error(`DEBUG: App command stderr: ${execResult.stderr}`);
                    throw new Error(`Error ejecutando aplicación: ${execResult.stderr}`);
                }
            } catch (error) {
                console.error(`DEBUG: App command failed: ${error.message}`);
                throw new Error(`Error abriendo ${realCommand}: ${error.message}`);
            }

            console.error(`DEBUG: Creating success response...`);
            const response = {
                content: [{
                    type: "text",
                    text: `✅ **${application} abierto en workspace ${workspace}**\n\n🔍 Comando detectado: \`${realCommand}\`\n🎯 Ejecutado exitosamente con hyprctl\n📋 Resultado workspace: ${workspaceResult.stdout || 'ok'}\n📋 Resultado exec: ${execResult.stdout || 'ok'}`
                }]
            };
            console.error(`DEBUG: Returning response:`, JSON.stringify(response));
            return response;
        } catch (error) {
            return {
                content: [{
                    type: "text",
                    text: `❌ **Error abriendo ${application} en workspace ${workspace}**\n\n🔍 Error: ${error.message}\n\n💡 **Sugerencias:**\n• Verifica que Hyprland esté ejecutándose\n• Confirma que la aplicación esté instalada\n• Intenta con workspace números 1-10`
                }]
            };
        }
    }

    async findCommand(app) {
        console.error(`DEBUG: findCommand called with: ${app}`);
        const name = app.toLowerCase();
        console.error(`DEBUG: Normalized name: ${name}`);

        // Mapeo común
        const commonApps = {
            'obsidian': ['obsidian', 'Obsidian'],
            'notion': ['notion-app', 'notion'],
            'firefox': ['firefox'],
            'chrome': ['google-chrome', 'chromium'],
            'code': ['code', 'codium'],
            'spotify': ['spotify'],
            'discord': ['discord'],
            'telegram': ['telegram-desktop'],
            'vlc': ['vlc']
        };

        // 1. Verificar mapeo común
        if (commonApps[name]) {
            console.error(`DEBUG: Found in commonApps: ${JSON.stringify(commonApps[name])}`);
            for (const cmd of commonApps[name]) {
                console.error(`DEBUG: Testing command: ${cmd}`);
                const exists = this.commandExists(cmd);
                console.error(`DEBUG: Command ${cmd} exists: ${exists}`);
                if (exists) {
                    console.error(`DEBUG: Returning command: ${cmd}`);
                    return cmd;
                }
            }
        } else {
            console.error(`DEBUG: ${name} not found in commonApps`);
        }

        // 2. Verificar nombre directo
        console.error(`DEBUG: Testing direct name: ${name}`);
        if (this.commandExists(name)) {
            console.error(`DEBUG: Direct name works, returning: ${name}`);
            return name;
        }

        // 3. Si no encuentra nada
        console.error(`DEBUG: No command found for ${app}`);
        throw new Error(`No se encontró comando para "${app}"`);
    }

    commandExists(command) {
        try {
            console.error(`DEBUG: Checking if command exists: ${command}`);
            const result = execSync(`command -v ${command}`, { encoding: 'utf8' });
            console.error(`DEBUG: Command ${command} found at: ${result.trim()}`);
            return true;
        } catch (error) {
            console.error(`DEBUG: Command ${command} not found: ${error.message}`);
            return false;
        }
    }
}

// CLI
async function main() {
    const server = new HyprlandControlServer();
    console.error(`🖥️ Hyprland Control MCP (Simplificado) iniciado`);

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
                    jsonrpc: "2.0", id: null,
                    error: { code: -1, message: error.message }
                }));
            }
        }
    });

    process.stdin.on('end', () => process.exit(0));
    process.on('SIGINT', () => process.exit(0));
}

if (require.main === module) {
    main().catch(err => {
        console.error('Error:', err);
        process.exit(1);
    });
}

module.exports = HyprlandControlServer;