import subprocess

APP_PATHS = {
    # Browsers
    "chrome": "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "brave": "C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe",
    "edge": "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "firefox": "C:/Program Files/Mozilla Firefox/firefox.exe",
    "zen": "C:/Vishesh/Apps/zen.exe",
    
    # Dev Tools & Editors
    "vscode": "C:/Users/vishe/AppData/Local/Programs/Microsoft VS Code/Code.exe",
    "code": "C:/Users/vishe/AppData/Local/Programs/Microsoft VS Code/Code.exe",
    "notepad": "notepad.exe",
    "command prompt": "cmd.exe",
    "terminal": "cmd.exe",
    "powershell": "powershell.exe",
    "github desktop": "C:/Users/vishe/AppData/Local/GitHubDesktop/GitHubDesktop.exe",
    "unity": "C:/Vishesh/Apps/6000.3.19f1/Editor/Unity.exe",
    "mongodb": "C:/Users/vishe/AppData/Local/MongoDBCompass/MongoDBCompass.exe",
    
    # Office & Productivity
    "word": "C:/Program Files/Microsoft Office/Root/Office16/WINWORD.EXE",
    "excel": "C:/Program Files/Microsoft Office/Root/Office16/EXCEL.EXE",
    "powerpoint": "C:/Program Files/Microsoft Office/Root/Office16/POWERPNT.EXE",
    "onenote": "C:/Program Files/Microsoft Office/Root/Office16/ONENOTE.EXE",
    "outlook": "C:/Program Files/Microsoft Office/Root/Office16/OUTLOOK.EXE",
    "access": "C:/Program Files/Microsoft Office/Root/Office16/MSACCESS.EXE",
    "publisher": "C:/Program Files/Microsoft Office/Root/Office16/MSPUB.EXE",
    "notion": "C:/Users/vishe/AppData/Local/Programs/Notion/Notion.exe",
    
    # Media & Creativity
    "spotify": "spotify:",
    "youtube music": "C:/Users/vishe/AppData/Local/youtube_music_desktop_app/youtube-music-desktop-app.exe",
    "vlc": "C:/Program Files/VideoLAN/VLC/vlc.exe",
    "gimp": "C:/Users/vishe/AppData/Local/Programs/GIMP 3/bin/gimp-3.exe",
    "zenbeats": "C:/Program Files/Zenbeats/Zenbeats.exe",
    
    # Gaming & Social
    "discord": "C:/Users/vishe/AppData/Local/Discord/Update.exe --processStart Discord.exe",
    "steam": "C:/Vishesh/Games/Steam/Steam.exe",
    
    # Utilities
    "lm studio": "C:/Vishesh/Apps/LM Studio/LM Studio.exe",
    "winrar": "C:/Program Files/WinRAR/WinRAR.exe",
    "afterburner": "C:/Games/MSI Afterburner/MSIAfterburner.exe",
    "nvidia": "C:/Program Files/NVIDIA Corporation/NVIDIA app/CEF/NVIDIA App.exe",
    "revo": "C:/Program Files/VS Revo Group/Revo Uninstaller/RevoUnin.exe",
    "bittorrent": "C:/Users/vishe/AppData/Roaming/BitTorrent Web/btweb.exe",
    
    # System Apps
    "explorer": "explorer.exe",
    "calculator": "calc.exe",
    "task manager": "taskmgr.exe",
    "control panel": "control.exe",
    
    # Settings URIs
    "settings": "ms-settings:",
    "wifi": "ms-settings:network-wifi",
    "bluetooth": "ms-settings:bluetooth",
    "display": "ms-settings:display",
    "sound": "ms-settings:sound",
    "apps": "ms-settings:appsfeatures",
    "update": "ms-settings:windowsupdate",
}

def open_app(name):
    name = name.lower().strip()
    for key, path in APP_PATHS.items():
        if key in name:
            try:
                subprocess.Popen(path, shell=True)
                return f"Opening {key}."
            except Exception as e:
                return f"Couldn't open {key}: {e}"
    return f"I don't have a path saved for that. Add it to APP_PATHS in app_control.py."

if __name__ == "__main__":
    print(open_app("calculator"))
