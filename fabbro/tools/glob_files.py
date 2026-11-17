import glob
import os

from agentecore import tool

from ._utils import resolve, truncate

IGNORA = ("/.git/", "/node_modules/", "/__pycache__/", "/venv/", "/.venv/")


@tool
def glob_files(pattern: str, path: str = ".") -> str:
    """Trova file tramite pattern glob (es. '**/*.py'), ordinati per modifica recente.

    Args:
        pattern: pattern glob, relativo a path
        path: cartella base della ricerca
    """
    base = resolve(path)
    trovati = [
        f for f in glob.glob(os.path.join(base, pattern), recursive=True)
        if os.path.isfile(f) and not any(i in f + "/" for i in IGNORA)
    ]
    trovati.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    if not trovati:
        return "nessun file trovato"
    return truncate("\n".join(os.path.relpath(f, base) for f in trovati[:500]))
