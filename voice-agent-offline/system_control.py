import subprocess

def set_brightness(level):
    """Set brightness to a specific percentage (0-100)"""
    level = max(0, min(100, int(level)))
    cmd = f'powershell -Command "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})"'
    subprocess.run(cmd, shell=True)
    return f"Brightness set to {level} percent."

def change_brightness(amount):
    """Increase or decrease brightness by amount (e.g. +10 or -10)"""
    try:
        # Get current brightness
        cmd_get = 'powershell -Command "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"'
        result = subprocess.run(cmd_get, shell=True, capture_output=True, text=True)
        current = int(result.stdout.strip())
        
        # Calculate new brightness
        new_level = max(0, min(100, current + amount))
        
        # Set new brightness
        cmd_set = f'powershell -Command "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{new_level})"'
        subprocess.run(cmd_set, shell=True)
        
        direction = "increased" if amount > 0 else "decreased"
        return f"Brightness {direction} to {new_level} percent."
    except Exception as e:
        return f"Couldn't change brightness: {e}"

def lock_screen():
    subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
    return "Locking screen."

def sleep_system():
    # Note: Requires hibernation to be disabled (powercfg -h off) to actually sleep, otherwise it hibernates
    subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
    return "Going to sleep."

if __name__ == "__main__":
    print(change_brightness(10))
