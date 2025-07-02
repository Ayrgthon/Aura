#!/usr/bin/env python3
import requests
import json
import sys
import os

# Importar módulos de voz
try:
    from engine.voice.hear import initialize_recognizer, listen_for_command
    from engine.voice.speak import (
        speak, stop_speaking, is_speaking,
        start_streaming_tts, add_text_to_stream, finish_streaming_tts
    )
    VOICE_AVAILABLE = True
    print("✅ Módulos de voz cargados correctamente")
    print("🔧 Funciones streaming TTS importadas:", 
          start_streaming_tts.__name__, add_text_to_stream.__name__, finish_streaming_tts.__name__)
except ImportError as e:
    VOICE_AVAILABLE = False
    print(f"⚠️ Módulos de voz no disponibles: {e}")
    print("💡 Instala las dependencias con: pip install -r requirements.txt")

class OllamaClient:
    def __init__(self, host="localhost", port=11434, context_size=100000, enable_voice=True):
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
    
    def generate_response(self, prompt, stream=False, use_history=True, voice_streaming=False):
        """
        Genera una respuesta usando el modelo especificado
        
        Args:
            prompt (str): El prompt/pregunta para el modelo
            stream (bool): Si True, transmite la respuesta en tiempo real
            use_history (bool): Si True, incluye el historial de conversación
            voice_streaming (bool): Si True, activa TTS en paralelo
            
        Returns:
            str: La respuesta del modelo
        """
        if not prompt.strip():
            return "Prompt vacío"
            
        url = f"{self.base_url}/api/generate"
        
        # Construir el prompt con historial si está habilitado
        if use_history and self.conversation_history:
            full_prompt = self._build_prompt_with_history(prompt)
        else:
            full_prompt = prompt
        
        # Configuración del modelo
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": stream,
            "options": {
                "num_ctx": self.context_size,
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40,
                "num_predict": 128,
                "stop": ["Usuario:", "Tú:", "Human:", "Assistant:"],
                "repeat_penalty": 1.1
            }
        }
        
        try:
            if stream:
                response_text = self._stream_response(url, payload, voice_streaming)
            else:
                response = requests.post(url, json=payload)
                if response.status_code != 200:
                    error_msg = f"Error: {response.status_code} - {response.text}"
                    print(error_msg)
                    return error_msg
                    
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    error_msg = f"Error decodificando respuesta: {e}"
                    print(error_msg)
                    return error_msg
                    
                if 'error' in data:
                    error_msg = f"Error del modelo: {data['error']}"
                    print(error_msg)
                    return error_msg
                    
                response_text = data.get('response', '')
                if not response_text.strip():
                    print("⚠️ La respuesta del modelo está vacía")
                    return "Sin respuesta"
            
            # Agregar al historial si está habilitado y hay respuesta válida
            if use_history and response_text and response_text != "Sin respuesta":
                self._add_to_history("user", prompt)
                self._add_to_history("assistant", response_text)
            
            return response_text
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error de conexión: {e}"
            print(error_msg)
            return error_msg
    
    def _build_prompt_with_history(self, current_prompt):
        """
        Construye un prompt que incluye el historial de conversación
        
        Args:
            current_prompt (str): El prompt actual del usuario
            
        Returns:
            str: Prompt completo con historial
        """
        # Limitar el número de mensajes en el historial para evitar sobrecargar el contexto
        max_history_messages = 10  # Ajustar según necesidad
        recent_history = self.conversation_history[-max_history_messages:] if len(self.conversation_history) > max_history_messages else self.conversation_history
        
        history_text = "A continuación hay una conversación entre un humano y un asistente de IA.\n\n"
        
        for entry in recent_history:
            if entry['role'] == 'user':
                history_text += f"Humano: {entry['content']}\n\n"
            else:
                history_text += f"Asistente: {entry['content']}\n\n"
        
        # Agregar el prompt actual
        history_text += f"Humano: {current_prompt}\n\nAsistente:"
        
        return history_text
    
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
    
    def _stream_response(self, url, payload, enable_voice_streaming=False):
        """
        Maneja las respuestas en streaming
        
        Args:
            url (str): URL del endpoint
            payload (dict): Datos a enviar
            enable_voice_streaming (bool): Si True, activa TTS en paralelo
            
        Returns:
            str: Respuesta completa
        """
        try:
            response = requests.post(url, json=payload, stream=True)
            if response.status_code != 200:
                error_msg = f"Error: {response.status_code} - {response.text}"
                print(error_msg)
                return error_msg
            
            full_response = ""
            streaming_tts = None
            
            # Inicializar TTS streaming si está habilitado
            if enable_voice_streaming and self.voice_enabled:
                try:
                    streaming_tts = start_streaming_tts()
                    print("🗣️ TTS en paralelo activado")
                except Exception as e:
                    print(f"❌ Error al inicializar TTS streaming: {e}")
                    streaming_tts = None
            
            print("Respuesta del modelo (streaming):")
            try:
                for line in response.iter_lines():
                    if not line:
                        continue
                        
                    try:
                        data = json.loads(line.decode('utf-8'))
                    except json.JSONDecodeError as e:
                        print(f"\n❌ Error decodificando respuesta: {e}")
                        continue
                    
                    if 'error' in data:
                        error_msg = f"\n❌ Error del modelo: {data['error']}"
                        print(error_msg)
                        return error_msg
                    
                    if 'response' in data:
                        chunk = data['response']
                        if chunk:  # Solo procesar si hay contenido
                            print(chunk, end='', flush=True)
                            full_response += chunk
                            
                            # Enviar chunk al TTS en paralelo
                            if streaming_tts:
                                try:
                                    add_text_to_stream(chunk)
                                except Exception as e:
                                    print(f"\n❌ Error en TTS chunk: {e}")
                    
                    if data.get('done', False):
                        break
                        
            except Exception as e:
                print(f"\n❌ Error procesando respuesta streaming: {e}")
                return f"Error en streaming: {e}"
            
            # Finalizar TTS streaming
            if streaming_tts:
                try:
                    finish_streaming_tts()
                except Exception as e:
                    print(f"\n❌ Error al finalizar TTS streaming: {e}")
            
            if not full_response.strip():
                print("\n⚠️ La respuesta del modelo está vacía")
                return "Sin respuesta"
                
            print()  # Nueva línea al final
            return full_response
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error de conexión: {e}"
            print(error_msg)
            return error_msg
    
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
            print("  • 'voz-streaming' - TTS en paralelo (recomendado)")
        
        print("-" * 60)
        
        use_stream = True  # Streaming activado por defecto
        use_voice_output = False  # Respuestas por voz
        use_voice_streaming = False  # TTS en paralelo
        
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
                    if use_voice_output:
                        print("💡 Usa 'voz-streaming' para TTS en paralelo (más fluido)")
                    continue
                
                if self.voice_enabled and user_input.lower() in ['voz-streaming', 'voice-streaming']:
                    use_voice_streaming = not use_voice_streaming
                    if use_voice_streaming:
                        use_voice_output = True  # Activar voz automáticamente
                        status = "🎬🗣️ ACTIVADO (TTS en paralelo)"
                    else:
                        status = "⏸️ DESACTIVADO"
                    print(f"✅ TTS Streaming: {status}")
                    continue
                
                if not user_input:
                    continue
                
                print(f"\n🤖 {self.model}:", end=" ")
                if use_stream:
                    # Si el streaming de voz está activado, no reproducir después
                    voice_after_stream = use_voice_output and not use_voice_streaming
                    response = self.generate_response(
                        user_input, 
                        stream=True, 
                        voice_streaming=use_voice_streaming
                    )
                    
                    # Solo reproducir voz después si no fue streaming
                    if voice_after_stream and response:
                        print("🗣️ Reproduciendo respuesta completa...")
                        self.speak_response(response)
                        
                else:
                    response = self.generate_response(user_input, stream=False)
                    print(response)
                    
                    # Síntesis de voz si está activada (modo no-stream)
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

 
