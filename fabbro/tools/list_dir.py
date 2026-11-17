import os

from agentecore import tool

from ._utils import resolve, truncate

IGNORA = {".git", "node_modules", "__pycache__", "venv", ".venv", ".mypy_cache"}


@tool
def list_dir(path: str = ".", depth: int = 1) -> str:
    """Elenca il contenuto di una cartella (ignora .git, venv, node_modules...).

    Args:
        path: cartella da elencare
        depth: profondità massima (1 = solo il primo livello)
    """
    base = resolve(path)
    if not os.path.isdir(base):
        return f"errore: cartella non trovata: {base}"
    out: list[str] = []

    def walk(d: str, livello: int) -> None:
        try:
            voci = sorted(os.scandir(d), key=lambda e: (not e.is_dir(), e.name))
        except OSError as e:
            out.append(f"{'  ' * livello}[{e.strerror}]")
            return
        for e in voci:
            if e.name in IGNORA:
                continue
            if e.is_dir():
                out.append(f"{'  ' * livello}{e.name}/")
                if livello + 1 < depth:
                    walk(e.path, livello + 1)
            else:
                out.append(f"{'  ' * livello}{e.name}")

    walk(base, 0)
    return truncate("\n".join(out)) or "(vuota)"
