import os

from agentecore import tool

from ._utils import controlla_scrittura, resolve, segna_letto


@tool
def edit_file(path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
    """Sostituisce testo esatto in un file. old_string deve essere unico, salvo replace_all.

    Args:
        path: percorso del file
        old_string: testo da sostituire (corrispondenza esatta, spazi inclusi)
        new_string: testo sostitutivo
        replace_all: se vero sostituisce tutte le occorrenze
    """
    p = resolve(path)
    if not os.path.isfile(p):
        return f"errore: file non trovato: {p}"
    errore = controlla_scrittura(p)
    if errore:
        return errore
    if old_string == new_string:
        return "errore: old_string e new_string sono uguali"
    with open(p, encoding="utf-8") as f:
        testo = f.read()
    n = testo.count(old_string)
    if n == 0:
        return "errore: old_string non trovato"
    if n > 1 and not replace_all:
        return f"errore: old_string compare {n} volte; aggiungi contesto o usa replace_all"
    nuovo = testo.replace(old_string, new_string) if replace_all else testo.replace(old_string, new_string, 1)
    with open(p, "w", encoding="utf-8") as f:
        f.write(nuovo)
    segna_letto(p)
    return f"modificato: {p} ({n if replace_all else 1} sostituzioni)"
