import edge_tts
import pygame
import os
import tempfile
import asyncio
import threading

class TextToSpeech:
    def __init__(self, voice="en-US-EmmaMultilingualNeural"):
        self.voice = voice
        pygame.mixer.init()
        
    def get_voices(self):
        # Fixed Aura voice options - Emma (default) and Andrew
        return [
            ("en-US-EmmaMultilingualNeural", "Emma Multilingual (Female) - Default"),
            ("en-US-AndrewMultilingualNeural", "Andrew Multilingual (Male)")
        ]
    
    def set_voice(self, voice_id):
        self.voice = voice_id
            
    def speak(self, text, slow=False):
        if not text.strip():
            return
            
        try:
            rate = "-20%" if slow else "+0%"
            
            def run_edge_tts():
                async def _edge_speak():
                    communicate = edge_tts.Communicate(text, self.voice, rate=rate)
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                        await communicate.save(fp.name)
                        return fp.name
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                audio_file = loop.run_until_complete(_edge_speak())
                loop.close()
                
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
                
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(100)
                    
                os.unlink(audio_file)
            
            thread = threading.Thread(target=run_edge_tts)
            thread.start()
            thread.join()
            
        except Exception as e:
            print(f"Error in TTS: {e}")
            
    def speak_to_file(self, text, output_file, slow=False):
        if not text.strip():
            return False
            
        try:
            rate = "-20%" if slow else "+0%"
            
            async def _save_edge():
                communicate = edge_tts.Communicate(text, self.voice, rate=rate)
                await communicate.save(output_file)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_save_edge())
            loop.close()
            return True
        except Exception as e:
            print(f"Error saving to file: {e}")
            return False
    
    def get_supported_languages(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            voices = loop.run_until_complete(edge_tts.list_voices())
            loop.close()
            langs = {}
            for voice in voices:
                lang_code = voice['Locale'][:2]
                lang_name = voice['Locale']
                langs[lang_code] = lang_name
            return langs
        except:
            return {"en": "English"}
    
    def stop_playback(self):
        pygame.mixer.music.stop()
        
    def close(self):
        pygame.mixer.quit()