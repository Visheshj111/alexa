import pyautogui
import mss

def get_actual_screen_size():
    # Computed fresh every call, not hardcoded, since monitor setup can change
    # if you dock to an external display or your resolution changes
    with mss.MSS() as sct:
        monitor = sct.monitors[1]  # primary monitor
        return monitor["width"], monitor["height"]

def scale_coordinates(x, y, resized_max_edge, actual_width, actual_height):
    # This assumes exactly ONE resize step in the pipeline: screenshot.py resizes
    # the image so its longest edge equals resized_max_edge before sending to
    # LM Studio, and LM Studio's own "Never exceed" resize setting is OFF.
    # If that LM Studio setting ever gets turned on, this math breaks silently
    # and clicks will land in the wrong place. Check that setting first if
    # clicks stop lining up.
    longest_actual = max(actual_width, actual_height)
    scale = longest_actual / resized_max_edge
    return int(x * scale), int(y * scale)

def execute_click(x, y):
    pyautogui.click(x, y)

if __name__ == "__main__":
    w, h = get_actual_screen_size()
    print(f"Primary monitor resolution: {w}x{h}")
