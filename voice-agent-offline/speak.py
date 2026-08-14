from _soundfile import speak
import subprocess
import os
import sounddevice as sd
import soundfile as sf
import re
import sys

def clean_for_speech(text):
    # Convert smart apostrophes to standard straight apostrophes
    text = text.replace("’", "'").replace("‘", "'")
    
    # Remove all types of quotes except apostrophes to keep contractions like "don't" intact
    text = re.sub(r'["`“”]', '', text)
    
    # Remove bullet points and blockquotes at the start of lines
    text = re.sub(r'^\s*[-*+>]\s+', '', text, flags=re.MULTILINE)
    
    # Replace double dashes with a comma for a pause
    text = text.replace('--', ', ')
    
    # Keep only letters, numbers, whitespace, and basic punctuation (including apostrophes)
    # Everything else (emojis, math symbols, formatting characters) becomes a space
    text = re.sub(r'[^\w\s\.,!\?:;\(\)\[\]\{\}\']', ' ', text)
    
    # Collapse multiple spaces
    return re.sub(r'\s+', ' ', text).strip()

