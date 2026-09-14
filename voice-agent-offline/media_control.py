import keyboard

def media_play_pause():
    keyboard.send("play/pause media")
    return "Toggling playback."

def media_next():
    keyboard.send("next track")
    return "Skipping track."

def media_previous():
    keyboard.send("previous track")
    return "Going back a track."

def media_volume_up():
    keyboard.send("volume up")
    return "Turning it up."

def media_volume_down():
    keyboard.send("volume down")
    return "Turning it down."

def media_mute():
    keyboard.send("volume mute")
    return "Toggling mute."

def media_set_volume(level):
    try:
        level = max(0, min(100, int(level)))
        from pycaw.pycaw import AudioUtilities
        
        devices = AudioUtilities.GetSpeakers()
        volume = devices.EndpointVolume
        
        # Scalar volume takes a float from 0.0 to 1.0
        volume.SetMasterVolumeLevelScalar(level / 100.0, None)
        return f"Volume set to {level} percent."
    except Exception as e:
        return f"Couldn't set volume: {e}"

if __name__ == "__main__":
    print(media_play_pause())
