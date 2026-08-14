import os
import subprocess
import sys
import asyncio
from speaker_verify import verify_speaker

def test_speaker_verify():
    print("--- Testing Speaker Verification ---")
    
    # 1. Generate enrolled voice using Piper (simulating the user)
    print("Generating enrolled voice using Piper...")
    subprocess.run([
        sys.executable, "-m", "piper",
        "--model", r"c:\Vishesh\Docs\Repos\alexa\en_US-lessac-medium.onnx",
        "--output_file", "enrolled_voice.wav"
    ], input="Hello, my name is Vishesh. This is my enrolled voice sample.".encode('utf-8'), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 2. Generate another voice using Piper with different text (simulating the user again)
    print("Generating another voice for the SAME user using Piper...")
    subprocess.run([
        sys.executable, "-m", "piper",
        "--model", r"c:\Vishesh\Docs\Repos\alexa\en_US-lessac-medium.onnx",
        "--output_file", "same_user.wav"
    ], input="Remind me to buy groceries tomorrow. Open my email.".encode('utf-8'), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 3. Test verification for the same user
    print("Testing same user...")
    try:
        is_me, score = verify_speaker("same_user.wav", reference_path="enrolled_voice.wav")
        print(f"Result for SAME user: {'PASSED (Correct)' if is_me else 'FAILED (Incorrectly rejected)'} - Score: {score:.4f}")
    except Exception as e:
        print(f"Error testing same user: {e}")

    # 4. We cannot easily convert mp3 from edge-tts to wav without ffmpeg, 
    # but we can try another Piper model or ask the user to test with their voice.
    print("\n--- Next Steps for You ---")
    print("1. To properly test Speaker Verification with a stranger's voice, you should manually speak into the mic using another person's voice or play a video of someone else talking.")
    print("2. To test the Wake Word, please run `python wake_word.py` and say 'alexa' to confirm it triggers reliably.")
    
if __name__ == "__main__":
    test_speaker_verify()
