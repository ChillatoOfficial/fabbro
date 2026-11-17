from fabbro.core import rag
from agentecore import tool

from ._utils import truncate


@tool
def rag_search(query: str, k: int = 4) -> str:
    """Cerca nei documenti salvati dall'utente (RAG) e restituisce i passaggi più pertinenti.

    Usala quando la domanda può dipendere da documentazione, note o specifiche dell'utente.

    Args:
        query: parole chiave della ricerca (meglio termini specifici che frasi lunghe)
        k: numero di passaggi da restituire
    """
    ris = rag.cerca(query, k)
    if not ris:
        return "nessun risultato nei documenti salvati"
    return truncate("\n\n".join(
        f"[{r['doc']}{' › ' + r['titolo'] if r['titolo'] else ''}]\n{r['testo']}" for r in ris
    ), 8000)


@tool
def rag_add(path: str) -> str:
    """Salva un file .md/.txt, o tutti quelli di una cartella, nella base di conoscenza (RAG).

    Args:
        path: file o cartella da salvare
    """
    try:
        nomi = rag.aggiungi(path)
    except (OSError, ValueError) as e:
        return f"errore: {e}"
    return f"salvati {len(nomi)} documenti: {', '.join(nomi[:20])}"


@tool
def rag_list() -> str:
    """Elenca i documenti salvati nella base di conoscenza (RAG)."""
    docs = rag.lista()
    return "\n".join(f"{d['nome']} ({d['byte']} B)" for d in docs) or "nessun documento salvato"


@tool
def rag_remove(name: str) -> str:
    """Rimuove un documento dalla base di conoscenza (RAG).

    Args:
        name: nome del documento come in rag_list
    """
    return "rimosso" if rag.rimuovi(name) else "errore: documento non trovato"
