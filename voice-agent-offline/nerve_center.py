"""
The Nerve Center - Ultra-Fast Hybrid Indexer

A standalone, deeply optimized module designed to instantly locate files and symbols 
within a codebase. It uses a background daemon thread to parse Abstract Syntax Trees (AST) 
for O(1) memory lookups, and provides a robust sequential raw-text fallback for files 
with syntax errors.

Designed to be completely decoupled so it can be exported to other AI agents.
"""

import os
import ast
import threading
import subprocess
from pathlib import Path

class ProjectIndexer:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir).resolve()
        self.index = {}  # Format: {"symbol_name": [ {"file": "path", "line": int, "type": "function|class"} ] }
        self.broken_files = set()
        self.all_files = set()
        self._is_ready = False
        self._lock = threading.Lock()

    def start_background_indexing(self):
        """Spawns a daemon thread to map the project silently without blocking."""
        t = threading.Thread(target=self._build_index, daemon=True)
        t.start()
        return t

    def _get_all_files(self):
        """Uses git ls-files if available (fastest), else falls back to os.walk."""
        files = []
        try:
            # Try git ls-files (Instant, respects .gitignore natively)
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run(
                ["git", "ls-files"], 
                cwd=self.root_dir, 
                capture_output=True, 
                text=True, 
                check=True,
                creationflags=creationflags
            )
            for line in result.stdout.splitlines():
                if line.strip():
                    files.append(self.root_dir / line.strip())
        except Exception:
            # Fallback to standard os.walk if git fails or isn't a repo
            for root, dirs, filenames in os.walk(self.root_dir):
                if '.git' in dirs: dirs.remove('.git')
                if 'node_modules' in dirs: dirs.remove('node_modules')
                if '__pycache__' in dirs: dirs.remove('__pycache__')
                if '.venv' in dirs: dirs.remove('.venv')
                for f in filenames:
                    files.append(Path(root) / f)
        return files

    def _build_index(self):
        """The core mapping logic. Populates the RAM index."""
        files = self._get_all_files()
        
        with self._lock:
            self.all_files = set(files)
            self.index.clear()
            self.broken_files.clear()
            
        for file_path in files:
            if file_path.suffix == '.py':
                self._parse_python_file(file_path)
                
        with self._lock:
            self._is_ready = True
            
        print(f"[Nerve Center] Background mapping complete. Found {len(self.all_files)} files. {len(self.broken_files)} broken files bypassed.")

    def _parse_python_file(self, file_path: Path):
        """Parses a python file into an AST to extract functions and classes."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            
            # Walk the tree to find definitions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    self._add_to_index(node.name, file_path, node.lineno, "function")
                elif isinstance(node, ast.ClassDef):
                    self._add_to_index(node.name, file_path, node.lineno, "class")
                    
        except SyntaxError:
            # File has broken syntax, AST cannot parse it. Flag it for sequential fallback.
            with self._lock:
                self.broken_files.add(file_path)
        except Exception:
            # Ignore encoding or read errors
            pass 

    def _add_to_index(self, name: str, file_path: Path, line: int, sym_type: str):
        with self._lock:
            name_lower = name.lower()
            if name_lower not in self.index:
                self.index[name_lower] = []
            
            # Store relative path for cleaner output to LLM
            try:
                rel_path = str(file_path.relative_to(self.root_dir))
            except ValueError:
                rel_path = str(file_path)
                
            self.index[name_lower].append({
                "file": rel_path.replace("\\", "/"),  # Normalize for cross-platform
                "line": line,
                "type": sym_type,
                "absolute_path": str(file_path)
            })

    def find_target(self, target_name: str) -> list[dict]:
        """
        The hybrid resolver.
        1. Checks AST RAM index (O(1)).
        2. Falls back to sequential text search in broken files.
        3. Falls back to sequential text search across all files.
        """
        target_lower = target_name.lower().strip()
        
        # 1. Fast O(1) Ram Lookup
        with self._lock:
            if target_lower in self.index:
                return self.index[target_lower]
                
        # 2. Sequential fallback on broken files
        with self._lock:
            broken = list(self.broken_files)
            
        broken_results = self._sequential_text_search(target_lower, broken)
        if broken_results:
            return broken_results
            
        # 3. Deep Sequential fallback across all files
        with self._lock:
            all_fs = list(self.all_files)
            
        return self._sequential_text_search(target_lower, all_fs)

    def _sequential_text_search(self, target: str, files_to_search: list) -> list[dict]:
        """Raw text scanner. Extremely robust, but slower."""
        results = []
        for file_path in files_to_search:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line_content in enumerate(f, 1):
                        if target in line_content.lower():
                            try:
                                rel_path = str(file_path.relative_to(self.root_dir))
                            except ValueError:
                                rel_path = str(file_path)
                                
                            results.append({
                                "file": rel_path.replace("\\", "/"),
                                "line": line_num,
                                "type": "raw_text_match",
                                "absolute_path": str(file_path)
                            })
                            # Just grab the first match per file to keep it snappy
                            break
            except Exception:
                pass
        return results

# ── Singleton Wrapper ────────────────────────────────────────────────────────

_global_indexer = None

def init_indexer(root_dir: str):
    """Call this exactly once at application boot."""
    global _global_indexer
    if _global_indexer is None:
        _global_indexer = ProjectIndexer(root_dir)
        _global_indexer.start_background_indexing()

def get_indexer() -> ProjectIndexer:
    """Returns the initialized global indexer, or None if not initialized."""
    return _global_indexer

