import os
import glob

# Map spoken folder aliases to absolute paths on disk.
# The AI will try to match words you say against these keys.
FOLDER_MAP = {
    "downloads": "C:/Users/vishe/Downloads",
    "desktop": "C:/Users/vishe/Desktop",
    "documents": "C:/Users/vishe/Documents",
    "pictures": "C:/Users/vishe/Pictures",
    "videos": "C:/Users/vishe/Videos",
    "music": "C:/Users/vishe/Music",
    "onedrive": "C:/Users/vishe/OneDrive",
    "repos": "C:/Vishesh/Docs/Repos",
    "vishesh": "C:/Vishesh",
    "apps": "C:/Vishesh/Apps",
    "c drive": "C:/",
    "users": "C:/Users/vishe",
}

# File extensions we know how to read
SUPPORTED_EXTENSIONS = [".txt", ".log", ".csv", ".py", ".json", ".md", ".pdf", ".docx", ".html"]

def find_file(folder_alias, search_terms, recursive=True):
    """
    Given a spoken folder alias and search terms (list of words from the user's query),
    return the path to the best matching file, or None if not found.
    """
    folder_alias = folder_alias.lower().strip()
    folder_path = FOLDER_MAP.get(folder_alias)
    if not folder_path:
        return None, f"I don't know which folder '{folder_alias}' refers to."

    if not os.path.isdir(folder_path):
        return None, f"The folder '{folder_path}' doesn't exist on your drive."

    # Build all candidate files
    found_files = []
    pattern = "**/*" if recursive else "*"
    for ext in SUPPORTED_EXTENSIONS:
        matches = glob.glob(os.path.join(folder_path, pattern + ext), recursive=recursive)
        found_files.extend(matches)

    if not found_files:
        return None, f"No readable files found in {folder_path}."

    # Score each file: count how many search terms appear in the filename (case-insensitive)
    scored = []
    for f in found_files:
        basename = os.path.basename(f).lower()
        score = sum(1 for term in search_terms if term.lower() in basename)
        if score > 0:
            scored.append((score, f))

    if not scored:
        return None, f"Couldn't find any file matching '{' '.join(search_terms)}' in {folder_path}."

    # Return highest-scoring match
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1], None

def extract_text(filepath, max_chars=4000):
    """
    Extract text content from a file. Caps at max_chars to avoid blowing
    the local model's context window (LM Studio on 4B model has ~2048-4096 token limit).
    """
    ext = os.path.splitext(filepath)[1].lower()

    try:
        if ext in [".txt", ".log", ".csv", ".py", ".json", ".md", ".html"]:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(max_chars)

        elif ext == ".pdf":
            try:
                import PyPDF2
                text = []
                with open(filepath, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text.append(page.extract_text() or "")
                        if sum(len(t) for t in text) > max_chars:
                            break
                return "\n".join(text)[:max_chars]
            except ImportError:
                return "[PyPDF2 not installed. Run: pip install PyPDF2]"

        elif ext == ".docx":
            try:
                import docx
                doc = docx.Document(filepath)
                text = "\n".join(para.text for para in doc.paragraphs)
                return text[:max_chars]
            except ImportError:
                return "[python-docx not installed. Run: pip install python-docx]"

        else:
            return f"[Unsupported file type: {ext}]"

    except Exception as e:
        return f"[Error reading file: {e}]"


def detect_folder_from_text(text):
    """
    Given a transcribed user query, return the first FOLDER_MAP key found in the text,
    or None if no known folder is mentioned.
    """
    text_lower = text.lower()
    for alias in FOLDER_MAP:
        if alias in text_lower:
            return alias
    return None


if __name__ == "__main__":
    # Quick test — search Downloads for anything with "invoice" in the name
    path, err = find_file("downloads", ["invoice"])
    if err:
        print(f"Error: {err}")
    else:
        print(f"Found: {path}")
        text = extract_text(path)
        print(f"Content preview:\n{text[:500]}")
