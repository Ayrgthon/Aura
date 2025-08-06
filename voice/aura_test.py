#!/usr/bin/env python3

import time
from speak import TextToSpeech
from hear import SpeechToText

def test_aura_recognition():
    print("=== Aura Recognition Test ===")
    print("Testing if Emma's pronunciation of 'Aura' is recognized correctly by STT")
    
    # Initialize TTS with Emma (default)
    tts = TextToSpeech()
    print("✓ Emma TTS initialized")
    
    # Initialize STT
    try:
        stt = SpeechToText()
        print("✓ STT initialized")
    except Exception as e:
        print(f"Error initializing STT: {e}")
        return
    
    # Test phrases with "Aura"
    test_phrases = [
        "Aura",
        "Hello Aura",
        "Hi Aura",
        "Hey Aura",
        "Good morning Aura",
        "Aura assistant",
        "My name is Aura",
        "I am Aura, your AI assistant"
    ]
    
    print("\nStarting recognition test...")
    print("Emma will speak each phrase, then we'll listen for recognition\n")
    
    stt.start_listening()
    
    for i, phrase in enumerate(test_phrases, 1):
        print(f"Test {i}: Emma will say: '{phrase}'")
        print("Starting to listen FIRST...")
        
        # Start listening before Emma speaks
        recognized_text = ""
        recognition_started = False
        
        # Use threading to speak while listening
        import threading
        
        def speak_phrase():
            time.sleep(0.5)  # Small delay to ensure listening is active
            print("  → Emma speaking...")
            tts.speak(phrase)
        
        # Start Emma speaking in background
        speak_thread = threading.Thread(target=speak_phrase)
        speak_thread.start()
        
        # Listen while Emma is speaking
        print("Listening for recognition...")
        for attempt in range(100):  # ~10 seconds total
            result = stt.listen_once()
            if result and result.strip():
                recognized_text = result.strip()
                break
            time.sleep(0.1)
        
        # Wait for speaking to finish
        speak_thread.join()
        
        # Show results
        if recognized_text:
            print(f"✓ Recognized: '{recognized_text}'")
            if "aura" in recognized_text.lower():
                print("  → SUCCESS: 'Aura' detected correctly!")
            else:
                print("  → ISSUE: 'Aura' not detected properly")
        else:
            print("  → No speech recognized")
        
        print("-" * 50)
        input("Press Enter to continue to next test...")
    
    stt.close()
    tts.close()
    
    print("\n=== Test Summary ===")
    print("This test helps identify:")
    print("1. How well Emma pronounces 'Aura'")
    print("2. Which phrases work best for recognition")
    print("3. If context helps recognition accuracy")

def quick_test():
    print("=== Quick Aura Test ===")
    
    tts = TextToSpeech()
    stt = SpeechToText()
    
    phrase = "Hello, I am Aura"
    print(f"Emma will say: '{phrase}'")
    print("Starting listening first...")
    
    stt.start_listening()
    
    import threading
    def speak_delayed():
        time.sleep(0.5)
        print("  → Emma speaking...")
        tts.speak(phrase)
    
    # Start speaking in background
    speak_thread = threading.Thread(target=speak_delayed)
    speak_thread.start()
    
    print("Listening for recognition...")
    recognized = False
    for i in range(80):  # 8 seconds
        result = stt.listen_once()
        if result and result.strip():
            print(f"✓ Recognized: '{result.strip()}'")
            if "aura" in result.lower():
                print("  → SUCCESS: 'Aura' detected!")
            recognized = True
            break
        time.sleep(0.1)
    
    if not recognized:
        print("  → No recognition detected")
    
    speak_thread.join()
    stt.close()
    tts.close()

def main():
    print("Aura Recognition Test")
    print("=" * 30)
    print("1. Full test (8 phrases)")
    print("2. Quick test (1 phrase)")
    print("3. Exit")
    
    choice = input("\nChoose test (1-3): ").strip()
    
    if choice == "1":
        test_aura_recognition()
    elif choice == "2":
        quick_test()
    elif choice == "3":
        print("Goodbye!")
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()