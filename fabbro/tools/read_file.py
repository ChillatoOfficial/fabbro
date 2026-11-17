import os

from agentecore import tool

from ._utils import is_binary, resolve, segna_letto, truncate


@tool
def read_file(path: str, offset: int = 1, limit: int = 500) -> str:
    """Legge un file di testo e lo restituisce con i numeri di riga.

    Args:
        path: percorso del file
        offset: riga da cui iniziare (parte da 1)
        limit: numero massimo di righe da leggere
    """
    p = resolve(path)
    if not os.path.isfile(p):
        return f"errore: file non trovato: {p}"
    if is_binary(p):
        return f"errore: file binario: {p}"
    with open(p, encoding="utf-8", errors="replace") as f:
        righe = f.read().splitlines()
    segna_letto(p)
    totale = len(righe)
    inizio = max(offset, 1) - 1
    fine = inizio + max(limit, 1)
    out = [f"{i + 1:>6}\t{r}" for i, r in enumerate(righe[inizio:fine], start=inizio)]
    if not out:
        return f"(nessuna riga: il file ha {totale} righe)"
    if fine < totale:
        out.append(f"... [{totale - fine} righe rimanenti, usa offset={fine + 1}]")
    return truncate("\n".join(out))
