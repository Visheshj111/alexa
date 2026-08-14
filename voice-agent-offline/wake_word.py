import sounddevice as sd
import numpy as np
from openwakeword.model import Model

def listen_for_wake_word():
    model = Model(wakeword_models=["alexa"], inference_framework="onnx")
    print("Listening for wake word: alexa")
    
    with sd.InputStream(samplerate=16000, channels=1, dtype='int16', blocksize=1280) as stream:
        while True:
            audio_chunk, overflowed = stream.read(1280)
            if overflowed:
                pass # ignore overflow
            
            # sounddevice returns shape (frames, channels), openwakeword expects 1D array
            audio_data = audio_chunk.flatten()
            prediction = model.predict(audio_data)
            
            if prediction["alexa"] > 0.5:
                print("Wake word detected.")
                return True

if __name__ == "__main__":
    listen_for_wake_word()
