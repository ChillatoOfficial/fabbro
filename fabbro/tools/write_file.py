import os

from agentecore import tool

from ._utils import controlla_scrittura, resolve, segna_letto


@tool
def write_file(path: str, content: str) -> str:
    """Crea o sovrascrive un file con il contenuto dato. Crea le cartelle mancanti.

    Args:
        path: percorso del file
        content: contenuto completo del file
    """
    p = resolve(path)
    errore = controlla_scrittura(p)
    if errore:
        return errore
    esisteva = os.path.exists(p)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    segna_letto(p)
    return f"{'sovrascritto' if esisteva else 'creato'}: {p} ({len(content.splitlines())} righe)"
