#!/usr/bin/env python3
import requests
import json
import sys
import os

# Importar módulos de voz
try:
    from engine.voice.hear import initialize_recognizer, listen_for_command
    from engine.voice.speak import speak, stop_speaking, is_speaking
    VOICE_AVAILABLE = True
    print("✅ Módulos de voz cargados correctamente")
except ImportError as e:
    VOICE_AVAILABLE = False
    print(f"⚠️ Módulos de voz no disponibles: {e}")
    print("💡 Instala las dependencias con: pip install -r requirements.txt")

class OllamaClient:
    def __init__(self, host="localhost", port=11434, context_size=130000, enable_voice=True):
        """
        Inicializa el cliente de Ollama
        
        Args:
            host (str): Dirección del servidor de Ollama (por defecto localhost)
            port (int): Puerto del servidor de Ollama (por defecto 11434)
            context_size (int): Tamaño del contexto en tokens (por defecto 130000 para gemma3:4b)
            enable_voice (bool): Si True, habilita funcionalidades de voz
        """
        self.base_url = f"http://{host}:{port}"
        self.model = "gemma3:4b"
        self.context_size = context_size
        self.conversation_history = []  # Para mantener historial como en terminal
        
        # Configuración de voz
        self.voice_enabled = enable_voice and VOICE_AVAILABLE
        self.voice_recognizer = None
        
        if self.voice_enabled:
            self._initialize_voice()
    
    def _initialize_voice(self):
        """
        Inicializa los componentes de voz
        """
        try:
            self.voice_recognizer = initialize_recognizer()
            if self.voice_recognizer:
                print("🎤 Sistema de voz activado")
            else:
                print("❌ Error al inicializar reconocimiento de voz")
                self.voice_enabled = False
        except Exception as e:
            print(f"❌ Error al inicializar voz: {e}")
            self.voice_enabled = False
    
    def listen_to_voice(self, timeout=5):
        """
        Escucha entrada de voz del usuario
        
        Args:
            timeout (int): Tiempo límite de escucha
            
        Returns:
            str: Texto reconocido de la voz
        """
        if not self.voice_enabled or not self.voice_recognizer:
            print("❌ Funcionalidad de voz no disponible")
            return ""
        
        return listen_for_command(self.voice_recognizer, timeout)
    
    def speak_response(self, text):
        """
        Convierte respuesta a voz
        
        Args:
            text (str): Texto a convertir en voz
        """
        if not self.voice_enabled:
            return
        
        speak(text)

    def is_server_running(self):
        """
        Verifica si el servidor de Ollama está ejecutándose
        
        Returns:
            bool: True si el servidor está activo, False en caso contrario
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def list_models(self):
        """
        Lista todos los modelos disponibles en Ollama
        
        Returns:
            list: Lista de modelos disponibles
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            else:
                print(f"Error al obtener modelos: {response.status_code}")
                return []
        except requests.exceptions.RequestException as e:
            print(f"Error de conexión: {e}")
            return []
    
    def generate_response(self, prompt, stream=False, use_history=True):
        """
        Genera una respuesta usando el modelo especificado
        
        Args:
            prompt (str): El prompt/pregunta para el modelo
            stream (bool): Si True, transmite la respuesta en tiempo real
            use_history (bool): Si True, incluye el historial de conversación
            
        Returns:
            str: La respuesta del modelo
        """
        url = f"{self.base_url}/api/generate"
        
        # Construir el prompt con historial si está habilitado
        if use_history and self.conversation_history:
            full_prompt = self._build_prompt_with_history(prompt)
        else:
            full_prompt = prompt
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": stream,
            "options": {
                "num_ctx": self.context_size,  # Configurar contexto completo
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
        
        try:
            if stream:
                response_text = self._stream_response(url, payload)
            else:
                response = requests.post(url, json=payload)
                if response.status_code == 200:
                    response_text = response.json().get('response', '')
                else:
                    return f"Error: {response.status_code} - {response.text}"
            
            # Agregar al historial si está habilitado
            if use_history:
                self._add_to_history("user", prompt)
                self._add_to_history("assistant", response_text)
            
            return response_text
            
        except requests.exceptions.RequestException as e:
            return f"Error de conexión: {e}"
    
    def _build_prompt_with_history(self, current_prompt):
        """
        Construye un prompt que incluye el historial de conversación
        
        Args:
            current_prompt (str): El prompt actual del usuario
            
        Returns:
            str: Prompt completo con historial
        """
        history_text = ""
        for entry in self.conversation_history:
            if entry['role'] == 'user':
                history_text += f"Usuario: {entry['content']}\n"
            else:
                history_text += f"Asistente: {entry['content']}\n"
        
        return f"{history_text}Usuario: {current_prompt}\nAsistente:"
    
    def _add_to_history(self, role, content):
        """
        Agrega una entrada al historial de conversación
        
        Args:
            role (str): 'user' o 'assistant'
            content (str): El contenido del mensaje
        """
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        
        # Mantener el historial dentro del límite de contexto
        self._trim_history_if_needed()
    
    def _trim_history_if_needed(self):
        """
        Recorta el historial si excede el límite de contexto
        """
        # Estimación aproximada: 1 token ≈ 4 caracteres
        total_chars = sum(len(entry['content']) for entry in self.conversation_history)
        max_chars = self.context_size * 3  # Dejar espacio para la respuesta
        
        while total_chars > max_chars and len(self.conversation_history) > 2:
            # Remover las entradas más antiguas (pero mantener al menos 1 par)
            removed = self.conversation_history.pop(0)
            total_chars -= len(removed['content'])
    
    def clear_history(self):
        """
        Limpia el historial de conversación
        """
        self.conversation_history = []
        print("🗑️ Historial de conversación limpiado")
    
    def show_context_info(self):
        """
        Muestra información sobre el contexto configurado
        """
        print(f"📊 Información de Contexto:")
        print(f"   • Modelo: {self.model}")
        print(f"   • Contexto configurado: {self.context_size:,} tokens")
        print(f"   • Historial: {len(self.conversation_history)} mensajes")
        
        if self.conversation_history:
            total_chars = sum(len(entry['content']) for entry in self.conversation_history)
            estimated_tokens = total_chars // 4
            print(f"   • Tokens estimados en historial: {estimated_tokens:,}")
            usage_percent = (estimated_tokens / self.context_size) * 100
            print(f"   • Uso del contexto: {usage_percent:.1f}%")
    
    def _stream_response(self, url, payload):
        """
        Maneja las respuestas en streaming
        
        Args:
            url (str): URL del endpoint
            payload (dict): Datos a enviar
            
        Returns:
            str: Respuesta completa
        """
        try:
            response = requests.post(url, json=payload, stream=True)
            if response.status_code == 200:
                full_response = ""
                print("Respuesta del modelo (streaming):")
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line.decode('utf-8'))
                        if 'response' in data:
                            print(data['response'], end='', flush=True)
                            full_response += data['response']
                        if data.get('done', False):
                            break
                print()  # Nueva línea al final
                return full_response
            else:
                return f"Error: {response.status_code} - {response.text}"
        except requests.exceptions.RequestException as e:
            return f"Error de conexión: {e}"
    
    def chat(self):
        """
        Inicia una sesión de chat interactiva
        """
        print(f"🤖 Cliente de Ollama - Modelo: {self.model}")
        print(f"🧠 Contexto: {self.context_size:,} tokens (como en terminal)")
        print("🎬 Streaming: ACTIVADO por defecto")
        
        if self.voice_enabled:
            print("🎤🗣️ Modo VOZ: ACTIVADO")
        else:
            print("⚠️ Modo voz: NO disponible")
        
        print("Comandos disponibles:")
        print("  • 'salir' o 'exit' - Terminar sesión")
        print("  • 'stream' - Alternar modo streaming")
        print("  • 'historial' - Mostrar historial de conversación")
        print("  • 'limpiar' - Limpiar historial")
        print("  • 'info' - Mostrar información de contexto")
        
        if self.voice_enabled:
            print("  • 'escuchar' - Activar entrada por voz")
            print("  • 'voz' - Alternar respuestas por voz")
        
        print("-" * 60)
        
        use_stream = True  # Streaming activado por defecto
        use_voice_output = False  # Respuestas por voz
        
        while True:
            try:
                user_input = input("\n👤 Tú: ").strip()
                
                if user_input.lower() in ['salir', 'exit', 'quit']:
                    print("👋 ¡Hasta luego!")
                    break
                
                if user_input.lower() == 'stream':
                    use_stream = not use_stream
                    status = "🎬 ACTIVADO" if use_stream else "⏸️ DESACTIVADO"
                    print(f"✅ Modo streaming: {status}")
                    continue
                
                if user_input.lower() in ['historial', 'history']:
                    self._show_history()
                    continue
                
                if user_input.lower() in ['limpiar', 'clear']:
                    self.clear_history()
                    continue
                
                if user_input.lower() == 'info':
                    self.show_context_info()
                    continue
                
                # Comandos de voz
                if self.voice_enabled and user_input.lower() in ['escuchar', 'listen']:
                    print("🎤 Modo escucha activado...")
                    voice_text = self.listen_to_voice()
                    if voice_text:
                        user_input = voice_text
                        print(f"👤 Tú (por voz): {user_input}")
                    else:
                        print("🔇 No se detectó entrada de voz")
                        continue
                
                if self.voice_enabled and user_input.lower() in ['voz', 'voice']:
                    use_voice_output = not use_voice_output
                    status = "🗣️ ACTIVADA" if use_voice_output else "🔇 DESACTIVADA"
                    print(f"✅ Respuesta por voz: {status}")
                    continue
                
                if not user_input:
                    continue
                
                print(f"\n🤖 {self.model}:", end=" ")
                if use_stream:
                    response = self.generate_response(user_input, stream=True)
                else:
                    response = self.generate_response(user_input, stream=False)
                    print(response)
                
                # Síntesis de voz si está activada
                if use_voice_output and response and self.voice_enabled:
                    print("🗣️ Reproduciendo respuesta...")
                    self.speak_response(response)
                
            except KeyboardInterrupt:
                print("\n👋 ¡Hasta luego!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def _show_history(self):
        """
        Muestra el historial de conversación
        """
        if not self.conversation_history:
            print("📝 No hay historial de conversación")
            return
        
        print("📝 Historial de conversación:")
        print("-" * 40)
        for i, entry in enumerate(self.conversation_history, 1):
            role_icon = "👤" if entry['role'] == 'user' else "🤖"
            role_name = "Tú" if entry['role'] == 'user' else self.model
            content = entry['content'][:100] + "..." if len(entry['content']) > 100 else entry['content']
            print(f"{i}. {role_icon} {role_name}: {content}")

def main():
    """
    Función principal del script
    """
    # Permitir configurar el contexto desde argumentos
    context_size = 130000  # Máximo para gemma3:4b
    
    # Verificar si se debe deshabilitar la voz
    disable_voice = '--no-voice' in sys.argv
    if disable_voice:
        sys.argv.remove('--no-voice')
    
    client = OllamaClient(context_size=context_size, enable_voice=not disable_voice)
    
    # Verificar si el servidor está ejecutándose
    if not client.is_server_running():
        print("❌ Error: El servidor de Ollama no está ejecutándose")
        print("💡 Asegúrate de que Ollama esté iniciado con: ollama serve")
        sys.exit(1)
    
    print("✅ Conectado al servidor de Ollama")
    
    # Listar modelos disponibles
    models = client.list_models()
    if models:
        print(f"📋 Modelos disponibles: {', '.join(models)}")
    
    # Verificar si el modelo está disponible
    if client.model not in models:
        print(f"⚠️  Advertencia: El modelo '{client.model}' no se encuentra en la lista")
        print(f"💡 Puedes descargarlo con: ollama pull {client.model}")
    
    # Mostrar información de contexto
    client.show_context_info()
    
    # Modo de uso
    if len(sys.argv) > 1:
        # Modo prompt único con streaming por defecto
        prompt = " ".join(sys.argv[1:])
        print(f"🤖 Respuesta para: '{prompt}'")
        print("🎬 Streaming activado:")
        client.generate_response(prompt, stream=True)
    else:
        # Modo chat interactivo
        client.chat()

if __name__ == "__main__":
    main() 