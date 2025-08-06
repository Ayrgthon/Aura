import json
import wave
import pyaudio
import vosk
import os

class SpeechToText:
    def __init__(self, language="en"):
        # Available models
        self.models = {
            "en": "vosk-model-en-us-0.42-gigaspeech",
            "es": "vosk-model-es-0.42"
        }
        
        self.language = language
        self.model_path = os.path.join(os.path.dirname(__file__), self.models[language])
        
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Vosk model not found at {self.model_path}")
        
        print(f"Loading {language.upper()} model: {self.models[language]}")
        self.model = vosk.Model(self.model_path)
        self.rec = vosk.KaldiRecognizer(self.model, 16000)
        
        self.p = pyaudio.PyAudio()
        self.stream = None
        
    def get_available_languages(self):
        return list(self.models.keys())
        
    def switch_language(self, language):
        if language not in self.models:
            raise ValueError(f"Language {language} not supported. Available: {list(self.models.keys())}")
        
        # Close current streams
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            
        # Load new model
        self.language = language
        self.model_path = os.path.join(os.path.dirname(__file__), self.models[language])
        
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Vosk model not found at {self.model_path}")
            
        print(f"Switching to {language.upper()} model: {self.models[language]}")
        self.model = vosk.Model(self.model_path)
        self.rec = vosk.KaldiRecognizer(self.model, 16000)
        
    def start_listening(self):
        self.stream = self.p.open(format=pyaudio.paInt16,
                                  channels=1,
                                  rate=16000,
                                  input=True,
                                  frames_per_buffer=8000)
        self.stream.start_stream()
        
    def stop_listening(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            
    def listen_once(self, timeout=5):
        if not self.stream or not self.stream.is_active():
            self.start_listening()
            
        data = self.stream.read(4000)
        if len(data) == 0:
            return None
            
        if self.rec.AcceptWaveform(data):
            result = json.loads(self.rec.Result())
            return result.get('text', '')
        else:
            partial = json.loads(self.rec.PartialResult())
            return partial.get('partial', '')
    
    def listen_continuous(self, callback=None):
        if not self.stream or not self.stream.is_active():
            self.start_listening()
            
        print("Listening... Press Ctrl+C to stop")
        try:
            while True:
                data = self.stream.read(4000)
                if len(data) == 0:
                    break
                    
                if self.rec.AcceptWaveform(data):
                    result = json.loads(self.rec.Result())
                    text = result.get('text', '')
                    if text and callback:
                        callback(text)
                    elif text:
                        print(f"Recognized: {text}")
                else:
                    partial = json.loads(self.rec.PartialResult())
                    partial_text = partial.get('partial', '')
                    if partial_text:
                        print(f"Partial: {partial_text}", end='\r')
        except KeyboardInterrupt:
            print("\nStopping...")
            
    def transcribe_audio_file(self, file_path):
        wf = wave.open(file_path, 'rb')
        
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != 'NONE':
            print("Audio file must be WAV format mono PCM.")
            return None
            
        rec = vosk.KaldiRecognizer(self.model, wf.getframerate())
        
        transcription = ""
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                transcription += result.get('text', '') + " "
                
        final_result = json.loads(rec.FinalResult())
        transcription += final_result.get('text', '')
        
        wf.close()
        return transcription.strip()
    
    def close(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()