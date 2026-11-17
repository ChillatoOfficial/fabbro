import os
import py_compile
import re
import tempfile

from fabbro import paths
from agentecore import tool

from . import carica_file, discover_tools, _tool_di

NOME_RE = re.compile(r"^[a-z][a-z0-9_]{1,40}$")


@tool
def create_tool(name: str, code: str, overwrite: bool = False) -> str:
    """Crea un tool Python globale (salvato in ~/.fabbro/tools, valido in ogni progetto).

    Disponibile dal messaggio successivo dell'utente. Il codice deve importare
    `from agentecore import tool` e definire una funzione decorata con @tool con type
    hint e docstring stile Google (Args:). Può usare `from fabbro.tools._utils import resolve,
    truncate`. Il tool deve restituire una stringa.

    Args:
        name: nome del file e del tool, snake_case (es. 'run_tests')
        code: sorgente Python completo del modulo
        overwrite: se vero sostituisce un tool esistente con lo stesso nome
    """
    if not NOME_RE.match(name):
        return "errore: nome non valido (snake_case, 2-41 caratteri)"
    if os.path.exists(os.path.join(os.path.dirname(__file__), f"{name}.py")):
        return f"errore: '{name}' è un tool integrato e non si può sostituire; scegli un altro nome"
    dest = str(paths.TOOLS / f"{name}.py")
    if os.path.exists(dest) and not overwrite:
        return f"errore: il tool '{name}' esiste già; usa overwrite=true"
    if "@tool" not in code:
        return "errore: il codice deve contenere una funzione decorata con @tool"

    paths.TOOLS.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        tmp = f.name
    try:
        py_compile.compile(tmp, doraise=True)
        # Prova a importarlo davvero prima di salvarlo nella cartella definitiva.
        nomi = [t.name for t in _tool_di(carica_file(tmp))]
        if not nomi:
            return "errore: nessun Tool trovato nel modulo"
    except py_compile.PyCompileError as e:
        return f"errore di sintassi: {e.msg}"
    except Exception as e:
        return f"errore: il modulo non si carica ({type(e).__name__}: {e}); non salvato"
    finally:
        os.unlink(tmp)

    with open(dest, "w", encoding="utf-8") as f:
        f.write(code)
    discover_tools(force=True)
    return f"tool creato: {', '.join(nomi)} (file {dest}). Sarà usabile dal prossimo messaggio dell'utente."
