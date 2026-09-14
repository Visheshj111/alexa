import sounddevice as sd
import numpy as np
from openwakeword.model import Model

# Keep wake word model permanently resident in RAM
_wake_model = Model(wakeword_models=["alexa"], inference_framework="onnx")

def listen_for_wake_word():
    print("Listening for wake word: alexa")
    _wake_model.reset()
    
    with sd.InputStream(samplerate=16000, channels=1, dtype='int16', blocksize=1280) as stream:
        # Flush the OS audio buffer to prevent residual audio from triggering the wake word
        for _ in range(5):
            stream.read(1280)
            
        while True:
            audio_chunk, overflowed = stream.read(1280)
            # sounddevice returns shape (frames, channels), openwakeword expects 1D array
            audio_data = audio_chunk.flatten()
            prediction = _wake_model.predict(audio_data)
            
            if prediction["alexa"] > 0.5:
                print("Wake word detected.")
                return True

if __name__ == "__main__":
    listen_for_wake_word()
