import os
import re

from agentecore import tool

from ._utils import is_binary, resolve, truncate

IGNORA = {".git", "node_modules", "__pycache__", "venv", ".venv"}


@tool
def grep(pattern: str, path: str = ".", include: str = "", ignore_case: bool = False, max_results: int = 200) -> str:
    """Cerca una regex nel contenuto dei file. Restituisce file:riga:testo.

    Args:
        pattern: espressione regolare Python
        path: file o cartella in cui cercare
        include: estensione o suffisso da filtrare (es. '.py')
        ignore_case: ignora maiuscole/minuscole
        max_results: numero massimo di corrispondenze
    """
    try:
        rx = re.compile(pattern, re.IGNORECASE if ignore_case else 0)
    except re.error as e:
        return f"errore: regex non valida: {e}"
    base = resolve(path)
    if os.path.isfile(base):
        files = [base]
    else:
        files = []
        for root, dirs, nomi in os.walk(base):
            dirs[:] = [d for d in dirs if d not in IGNORA]
            files += [os.path.join(root, n) for n in nomi if n.endswith(include)]
    out: list[str] = []
    for f in sorted(files):
        if is_binary(f):
            continue
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                for i, riga in enumerate(fh, 1):
                    if rx.search(riga):
                        out.append(f"{os.path.relpath(f, base if os.path.isdir(base) else os.path.dirname(base))}:{i}:{riga.rstrip()[:300]}")
                        if len(out) >= max_results:
                            return truncate("\n".join(out)) + "\n... [limite raggiunto]"
        except OSError:
            continue
    return truncate("\n".join(out)) if out else "nessuna corrispondenza"
