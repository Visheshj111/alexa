import mss
import mss.tools
from PIL import Image
import base64
import io

def capture_screen_base64():
    """Captures the primary monitor, resizes longest edge to 1280px, compresses JPEG to 75, returns base64."""
    with mss.mss() as sct:
        # Capture the primary monitor
        monitor = sct.monitors[1]  # 0 is the sum of all monitors, 1 is the primary
        sct_img = sct.grab(monitor)
        
        # Convert to PIL Image
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        
        # Resize if necessary (longest edge 1280)
        max_size = 1280
        width, height = img.size
        if max(width, height) > max_size:
            if width > height:
                new_width = max_size
                new_height = int((height / width) * max_size)
            else:
                new_height = max_size
                new_width = int((width / height) * max_size)
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save to memory buffer as JPEG with quality 75
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=75)
        
        # Encode to base64
        base64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return base64_str

if __name__ == "__main__":
    b64 = capture_screen_base64()
    print(f"Captured screenshot! Base64 length: {len(b64)}")
    print("Starts with:", b64[:50])
