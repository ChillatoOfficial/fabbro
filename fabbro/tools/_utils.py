import os

MAX_OUTPUT = 20000


def resolve(path: str) -> str:
    """Espande ~ e risolve il percorso rispetto alla cartella di lavoro corrente."""
    return os.path.abspath(os.path.expanduser(path))


def truncate(testo: str, limite: int = MAX_OUTPUT) -> str:
    if len(testo) <= limite:
        return testo
    meta = limite // 2
    return f"{testo[:meta]}\n... [troncato: {len(testo) - limite} caratteri] ...\n{testo[-meta:]}"


def is_binary(percorso: str) -> bool:
    try:
        with open(percorso, "rb") as f:
            return b"\0" in f.read(4096)
    except OSError:
        return False


def segna_letto(percorso: str) -> None:
    from fabbro.core import runtime
    try:
        runtime.LETTI[percorso] = os.path.getmtime(percorso)
    except OSError:
        pass


def controlla_scrittura(percorso: str) -> str | None:
    """Errore (stringa) se il file esiste e non è stato letto, o è cambiato dopo la lettura."""
    from fabbro.core import runtime
    if not os.path.exists(percorso):
        return None
    if percorso not in runtime.LETTI:
        return "errore: leggi prima il file con read_file, poi modificalo"
    if os.path.getmtime(percorso) != runtime.LETTI[percorso]:
        return "errore: il file è cambiato dopo l'ultima lettura; rileggilo con read_file"
    return None
