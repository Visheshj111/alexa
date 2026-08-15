import pyautogui
import mss

def get_actual_screen_size():
    # Computed fresh every call, not hardcoded, since monitor setup can change
    # if you dock to an external display or your resolution changes
    with mss.MSS() as sct:
        monitor = sct.monitors[1]  # primary monitor
        return monitor["width"], monitor["height"]

def scale_coordinates(x, y, actual_width, actual_height):
    # Qwen-VL outputs coordinates normalized from 0 to 1000.
    # 0,0 is top-left, 1000,1000 is bottom-right.
    real_x = (x / 1000.0) * actual_width
    real_y = (y / 1000.0) * actual_height
    return int(real_x), int(real_y)

def execute_click(x, y):
    # Move the mouse to the coordinates first, taking a fraction of a second.
    # This allows UI elements to register the 'hover' state before the click,
    # which is required by many modern applications.
    pyautogui.moveTo(x, y, duration=0.2)
    pyautogui.click(x, y)

if __name__ == "__main__":
    w, h = get_actual_screen_size()
    print(f"Primary monitor resolution: {w}x{h}")
