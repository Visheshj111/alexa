import json
import os
from datetime import datetime

FILE = "reminders.json"

def add_reminder(text, when=None):
    data = []
    if os.path.exists(FILE):
        with open(FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    data.append({"text": text, "created": str(datetime.now()), "when": when})
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def list_reminders():
    if not os.path.exists(FILE):
        return []
    with open(FILE, "r", encoding="utf-8") as f:
        return json.load(f)
