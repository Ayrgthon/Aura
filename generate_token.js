#!/usr/bin/env node

/**
 * Script para generar token.json para Google Workspace
 * Ejecutar: node generate_token.js
 */

const fs = require('fs').promises;
const path = require('path');
const { google } = require('googleapis');
const readline = require('readline');

const SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/spreadsheets.readonly'
];

const CREDENTIALS_PATH = './credentials.json';
const TOKEN_PATH = './token.json';

async function main() {
    try {
        console.log('🔑 Generando token de Google Workspace...\n');
        
        // Leer credenciales
        const credentials = JSON.parse(await fs.readFile(CREDENTIALS_PATH));
        const { client_secret, client_id, redirect_uris } = credentials.installed || credentials.web;
        
        const oAuth2Client = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0]);
        
        // Generar URL de autorización
        const authUrl = oAuth2Client.generateAuthUrl({
            access_type: 'offline',
            scope: SCOPES,
        });
        
        console.log('📋 Autoriza esta aplicación visitando esta URL:');
        console.log('\n' + authUrl + '\n');
        
        const rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout,
        });
        
        const code = await new Promise((resolve) => {
            rl.question('📝 Introduce el código de la página: ', resolve);
        });
        
        rl.close();
        
        // Obtener token
        const { tokens } = await oAuth2Client.getToken(code);
        
        // Guardar token
        await fs.writeFile(TOKEN_PATH, JSON.stringify(tokens));
        
        console.log('\n✅ Token guardado en:', TOKEN_PATH);
        console.log('🚀 Ahora puedes ejecutar el cliente: python client/main.py');
        
    } catch (error) {
        console.error('❌ Error:', error.message);
        process.exit(1);
    }
}

main();