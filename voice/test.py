#!/usr/bin/env python3

import sys
import os
from hear import SpeechToText
from speak import TextToSpeech

def test_stt():
    print("=== Speech-to-Text Test ===")
    
    # Language selection
    print("Select STT language:")
    print("1. English (en)")
    print("2. Spanish (es)")
    
    try:
        lang_choice = int(input("\nEnter choice (1-2): ").strip())
        language = "en" if lang_choice == 1 else "es"
        lang_name = "English" if language == "en" else "Spanish"
        print(f"Selected: {lang_name}")
    except (ValueError, IndexError):
        print("Invalid choice, using English")
        language = "en"
        lang_name = "English"
    
    print(f"Initializing {lang_name} speech recognition...")
    
    try:
        stt = SpeechToText(language=language)
        print(f"✓ {lang_name} STT initialized successfully")
        
        print("\nChoose an option:")
        print("1. Listen once (5 seconds)")
        print("2. Continuous listening (Ctrl+C to stop)")
        print("3. Transcribe audio file")
        print("4. Switch language and continue")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            print("\nStarting to listen for 5 seconds...")
            stt.start_listening()
            
            for i in range(50):  # ~5 seconds
                text = stt.listen_once()
                if text:
                    print(f"You said: {text}")
                    break
            else:
                print("No speech detected")
                
        elif choice == "2":
            print("\nStarting continuous listening...")
            stt.listen_continuous()
            
        elif choice == "3":
            file_path = input("Enter path to WAV file: ").strip()
            if os.path.exists(file_path):
                print("Transcribing...")
                text = stt.transcribe_audio_file(file_path)
                if text:
                    print(f"Transcription: {text}")
                else:
                    print("Failed to transcribe")
            else:
                print("File not found")
                
        elif choice == "4":
            print("\nSwitch to:")
            print("1. English")
            print("2. Spanish")
            
            try:
                new_lang_choice = int(input("Enter choice (1-2): ").strip())
                new_language = "en" if new_lang_choice == 1 else "es"
                stt.switch_language(new_language)
                print("Language switched! You can now test again.")
                
                # Recursive call to continue testing
                return test_stt()
            except Exception as e:
                print(f"Error switching language: {e}")
        else:
            print("Invalid choice")
            
        stt.close()
        
    except Exception as e:
        print(f"Error: {e}")

def test_tts():
    print("=== Edge-TTS Test ===")
    print("Initializing Edge Text-to-Speech...")
    
    try:
        tts = TextToSpeech()
        print("✓ Edge-TTS initialized successfully")
        
        voices = tts.get_voices()
        print(f"\nAura's voices:")
        for i, (voice_id, voice_name) in enumerate(voices, 1):
            print(f"{i}. {voice_name}")
        
        try:
            voice_choice = int(input(f"\nSelect voice (1-{len(voices)}) or 0 for default: ").strip())
            if voice_choice > 0:
                tts.set_voice(voices[voice_choice - 1][0])
                print(f"✓ Voice set to: {voices[voice_choice - 1][1]}")
        except (ValueError, IndexError):
            print("Using default voice: Emma Multilingual (Female)")
        
        print("\nChoose test option:")
        print("1. Speak custom text")
        print("2. Speak predefined text")
        print("3. Save speech to file")
        print("4. Test different voices")
        print("5. Show supported languages")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == "1":
            text = input("Enter text to speak: ").strip()
            if text:
                slow = input("Speak slowly? (y/n): ").strip().lower() == 'y'
                print("Speaking...")
                tts.speak(text, slow=slow)
                print("Done!")
            else:
                print("No text provided")
                
        elif choice == "2":
            test_texts = [
                # English tests
                "Hello! This is a test of Microsoft Edge multilingual text to speech.",
                "The quick brown fox jumps over the lazy dog.",
                "Edge TTS provides high quality neural voices with multilingual support.",
                # Spanish tests
                "¡Hola! Soy Aura, tu asistente de inteligencia artificial multilingüe.",
                "El español es un idioma hermoso con más de quinientos millones de hablantes.",
                "Gracias por probar las capacidades multilingües de este sistema de síntesis de voz."
            ]
            
            for i, text in enumerate(test_texts, 1):
                lang = "Spanish" if i > 3 else "English"
                print(f"\nSpeaking test {i} ({lang}): {text}")
                tts.speak(text)
                input("Press Enter for next test...")
                
        elif choice == "3":
            text = input("Enter text to save: ").strip()
            filename = input("Enter filename (with .mp3 extension): ").strip()
            
            if text and filename:
                if tts.speak_to_file(text, filename):
                    print(f"✓ Speech saved to {filename}")
                else:
                    print("Failed to save speech")
            else:
                print("Text or filename not provided")
                
        elif choice == "4":
            test_texts = [
                "Hello, I am Aura, your multilingual AI assistant. I can speak multiple languages naturally.",
                "¡Hola! Soy Aura, tu asistente de inteligencia artificial multilingüe. Puedo hablar varios idiomas de forma natural."
            ]
            
            # Get Aura's fixed voices
            all_voices = tts.get_voices()
            print(f"\nTesting both of Aura's voices:")
            
            for voice_id, voice_name in all_voices:
                print(f"\n--- Testing {voice_name} ---")
                test_tts = TextToSpeech(voice=voice_id)
                
                for i, text in enumerate(test_texts, 1):
                    lang = "Spanish" if i == 2 else "English"
                    print(f"Speaking in {lang}...")
                    test_tts.speak(text)
                    
                test_tts.close()
                input("Press Enter for next voice...")
                
        elif choice == "5":
            langs = tts.get_supported_languages()
            print("\nSupported languages:")
            for code, name in list(langs.items())[:15]:  # Show first 15
                print(f"  {code}: {name}")
            if len(langs) > 15:
                print(f"... and {len(langs)-15} more")
        else:
            print("Invalid choice")
            
        tts.close()
        
    except Exception as e:
        print(f"Error: {e}")

def interactive_test():
    print("=== Interactive STT + TTS Test ===")
    print("This will listen to your speech and repeat it back")
    
    try:
        stt = SpeechToText()
        tts = TextToSpeech()
        
        print("✓ Both systems initialized")
        print("\nSay something, and I'll repeat it back to you!")
        print("Press Ctrl+C to stop\n")
        
        def on_speech(text):
            print(f"You said: {text}")
            print("Repeating back...")
            tts.speak(text)
            print("Ready for next input...\n")
            
        stt.listen_continuous(callback=on_speech)
        
        stt.close()
        tts.close()
        
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("Voice Processing Test Suite")
    print("=" * 30)
    
    while True:
        print("\nChoose a test:")
        print("1. Test Speech-to-Text (STT)")
        print("2. Test Text-to-Speech (TTS)")  
        print("3. Interactive test (STT + TTS)")
        print("4. Exit")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            test_stt()
        elif choice == "2":
            test_tts()
        elif choice == "3":
            interactive_test()
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")
            
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()