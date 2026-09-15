"""
Screen typing and prompt refinement engine for Alexa.

Allows typing text directly into active windows, AI prompt boxes (e.g. AntiGravity, Cursor),
browsers, or text fields. Supports refining rough spoken requests into detailed, high-quality
prompts before typing.
"""

import time
import pyperclip
import pyautogui
from ask_local import ask
from ask_vision import ask_with_image
from screenshot import capture_screen_base64
from screen_click import scale_coordinates, execute_click, get_actual_screen_size

pyautogui.PAUSE = 0.05


def refine_prompt_for_ai(raw_request: str, repo_path: str = None) -> str:
    """Refine a rough spoken prompt request into a detailed, structured prompt for AI coding tools."""
    prompt_builder = [
        "You are an expert prompt engineer.",
        f"The user wants to write an AI prompt for: '{raw_request}'.",
    ]
    if repo_path:
        prompt_builder.append(f"Target repository path: {repo_path}.")
    
    prompt_builder.append(
        "Refine this into a clear, professional, actionable prompt for an AI coding assistant. "
        "Output ONLY the final refined prompt text. Do NOT include quotes, intros, or explanations."
    )
    
    system_prompt = "\n".join(prompt_builder)
    refined = ask(raw_request, system_override=system_prompt)
    return refined.strip().strip('"').strip("'")


def type_text(text: str, press_enter: bool = False, delay: float = 0.1):
    """Paste text into the active window instantly via system clipboard.
    
    Using clipboard paste (ctrl+v) prevents dropped characters, handles multi-line
    prompts, and is ~100x faster than simulated keypresses.
    """
    if not text:
        return False
        
    pyperclip.copy(text)
    time.sleep(delay)
    pyautogui.hotkey('ctrl', 'v')
    
    if press_enter:
        time.sleep(0.1)
        pyautogui.press('enter')
    return True


def click_and_type(target_element: str, text: str, press_enter: bool = False):
    """Locate a text input field visually, click it to focus, and type the text."""
    image_b64 = capture_screen_base64()
    click_prompt = f"Find the text input box, search field, or button for: '{target_element}'."
    response = ask_with_image(click_prompt, image_b64, mode="click")
    
    try:
        x_str, y_str, desc = response.split(",", 2)
        x, y = int(x_str.strip()), int(y_str.strip())
        actual_width, actual_height = get_actual_screen_size()
        real_x, real_y = scale_coordinates(x, y, actual_width, actual_height)
        execute_click(real_x, real_y)
        time.sleep(0.1)
    except Exception as e:
        print(f"Could not locate element '{target_element}' visually: {e}. Typing into active window.")

    return type_text(text, press_enter=press_enter)


if __name__ == "__main__":
    print("Testing screen_type module...")
    sample_raw = "enhance my dashboard page by looking at the repo"
    print(f"Raw spoken: {sample_raw}")
    refined = refine_prompt_for_ai(sample_raw)
    print(f"Refined prompt:\n{refined}")
