import os
import re

from fabbro import paths
from agentecore import tool

from ._utils import truncate

DIR = str(paths.SKILLS)
NOME_RE = re.compile(r"^[a-z][a-z0-9-]{1,40}$")


def indice_skills() -> str:
    """Una riga per skill ('nome: descrizione'), per il system prompt."""
    if not os.path.isdir(DIR):
        return ""
    righe = []
    for n in sorted(os.listdir(DIR)):
        if not n.endswith(".md"):
            continue
        with open(os.path.join(DIR, n), encoding="utf-8") as f:
            m = re.search(r"^description:\s*(.+)$", f.read(1000), re.M)
        righe.append(f"- {n[:-3]}: {m.group(1).strip() if m else ''}")
    return "\n".join(righe)


@tool
def create_skill(name: str, description: str, content: str, overwrite: bool = False) -> str:
    """Salva una skill: istruzioni riutilizzabili in markdown per un tipo di compito.

    Args:
        name: identificatore con trattini (es. 'code-review')
        description: una riga che dice quando usarla (finisce nell'indice del prompt)
        content: istruzioni complete in markdown, concise
        overwrite: se vero sostituisce una skill esistente
    """
    if not NOME_RE.match(name):
        return "errore: nome non valido (minuscolo, cifre e trattini)"
    os.makedirs(DIR, exist_ok=True)
    p = os.path.join(DIR, f"{name}.md")
    if os.path.exists(p) and not overwrite:
        return f"errore: la skill '{name}' esiste già; usa overwrite=true"
    desc = " ".join(description.split())
    with open(p, "w", encoding="utf-8") as f:
        f.write(f"---\nname: {name}\ndescription: {desc}\n---\n\n{content.strip()}\n")
    return f"skill salvata: {name}. Sarà nell'indice dal prossimo messaggio."


@tool
def load_skill(name: str) -> str:
    """Carica il testo completo di una skill dall'indice, prima di usarla.

    Args:
        name: nome della skill
    """
    p = os.path.join(DIR, f"{name}.md")
    if not NOME_RE.match(name) or not os.path.isfile(p):
        return f"errore: skill non trovata. Disponibili:\n{indice_skills() or '(nessuna)'}"
    with open(p, encoding="utf-8") as f:
        return truncate(f.read())
