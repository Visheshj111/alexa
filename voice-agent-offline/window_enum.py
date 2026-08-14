import win32gui

def get_open_windows():
    """Returns a list of visible, non-empty window titles."""
    def enum_window_callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                # Filter out some common invisible or generic Windows background tasks if needed
                if title not in ["Program Manager", "Settings", "Microsoft Text Input Application"]:
                    windows.append(title)
    
    windows = []
    win32gui.EnumWindows(enum_window_callback, windows)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_windows = [x for x in windows if not (x in seen or seen.add(x))]
    
    return unique_windows

if __name__ == "__main__":
    print("Testing window enumeration...")
    apps = get_open_windows()
    print("Open Windows:")
    for app in apps:
        print(f"- {app}")
