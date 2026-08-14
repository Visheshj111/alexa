import sounddevice as sd
import soundfile as sf

def enroll(seconds=15, filename="enrolled_voice.wav"):
    samplerate = 16000
    print(f"Speak naturally for {seconds} seconds. Read a paragraph out loud.")
    
    # Record audio
    recording = sd.rec(int(seconds * samplerate), samplerate=samplerate, channels=1, dtype='int16')
    sd.wait()  # Wait until recording is finished
    
    # Save as WAV file
    sf.write(filename, recording, samplerate)
    print(f"Saved reference voice sample to {filename}")

if __name__ == "__main__":
    enroll()
