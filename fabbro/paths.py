"""Cartella globale di Fabbro: ~/.fabbro (cambiabile con la variabile FABBRO_HOME).

~/.fabbro/
  providers.json   provider e chiavi API
  state.json       ultimo provider/modello scelto
  prompt.txt       system prompt (copiato dal default al primo avvio)
  tools/           tool creati dall'agente o da te (validi in ogni progetto)
  skills/          skill in markdown
"""
import os
import shutil
from pathlib import Path

_VECCHIA = Path.home() / ".agente"      # nome precedente del progetto
HOME = Path(os.environ.get("FABBRO_HOME") or Path.home() / ".fabbro").expanduser()
if not os.environ.get("FABBRO_HOME") and not HOME.exists() and _VECCHIA.is_dir():
    shutil.move(str(_VECCHIA), str(HOME))  # migra provider, memoria, tool, skill e RAG
TOOLS = HOME / "tools"
SKILLS = HOME / "skills"
PROVIDERS_FILE = HOME / "providers.json"
STATE_FILE = HOME / "state.json"
PROMPT_FILE = HOME / "prompt.txt"

PROMPT_DEFAULT = Path(__file__).parent / "prompts" / "system.txt"


def ensure() -> None:
    """Crea la cartella globale; al primo avvio copia il prompt di default."""
    for d in (HOME, TOOLS, SKILLS):
        d.mkdir(parents=True, exist_ok=True)
    if not PROMPT_FILE.exists() and PROMPT_DEFAULT.exists():
        shutil.copy(PROMPT_DEFAULT, PROMPT_FILE)


# Primo avvio: nessuno stato salvato (chi viene da una versione precedente ce l'ha già).
PRIMO_AVVIO = not STATE_FILE.exists()

ensure()
