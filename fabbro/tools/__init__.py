import importlib
import importlib.util
import os
import sys

import pkgutil

from fabbro import paths
from agentecore import Tool

_PACKAGE_DIR = os.path.dirname(__file__)
_USER_DIR = str(paths.TOOLS)
_USER_PREFIX = "fabbro_user_tools."

_TOOLS_CACHE: list[Tool] = []
_FILE_MTIMES: dict[str, float] = {}


def _file_mtimes() -> dict[str, float]:
    mtimes: dict[str, float] = {}
    for cartella in (_PACKAGE_DIR, _USER_DIR):
        try:
            nomi = os.listdir(cartella)
        except OSError:
            continue
        for nome_file in nomi:
            if nome_file.endswith(".py") and not nome_file.startswith("_"):
                percorso = os.path.join(cartella, nome_file)
                try:
                    mtimes[percorso] = os.path.getmtime(percorso)
                except OSError:
                    pass
    return mtimes


def carica_file(percorso: str):
    """Importa un singolo file .py come modulo (solleva se è rotto). Per i tool utente."""
    nome = _USER_PREFIX + os.path.splitext(os.path.basename(percorso))[0]
    spec = importlib.util.spec_from_file_location(nome, percorso)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(nome, None)
        raise
    return mod


def _tool_di(mod) -> list[Tool]:
    return [v for v in vars(mod).values() if isinstance(v, Tool)]


def discover_tools(force: bool = False) -> list[Tool]:
    global _TOOLS_CACHE, _FILE_MTIMES

    mtimes = _file_mtimes()
    if not force and mtimes == _FILE_MTIMES:
        return _TOOLS_CACHE

    importlib.invalidate_caches()
    prefisso = f"{__name__}."
    for nome_modulo in list(sys.modules):
        if nome_modulo.startswith((prefisso, _USER_PREFIX)):
            del sys.modules[nome_modulo]

    risultati: list[Tool] = []
    for modulo in pkgutil.iter_modules(__path__):
        if modulo.name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"{__name__}.{modulo.name}")
        except Exception:
            # Un tool rotto non deve bloccare il caricamento degli altri.
            continue
        risultati += _tool_di(mod)

    # Tool globali dell'utente (~/.fabbro/tools): con lo stesso nome vincono sui built-in.
    try:
        nomi_utente = sorted(n for n in os.listdir(_USER_DIR) if n.endswith(".py") and not n.startswith("_"))
    except OSError:
        nomi_utente = []
    for nome_file in nomi_utente:
        try:
            nuovi = _tool_di(carica_file(os.path.join(_USER_DIR, nome_file)))
        except Exception:
            continue
        nomi = {t.name for t in nuovi}
        risultati = [t for t in risultati if t.name not in nomi] + nuovi

    _TOOLS_CACHE = risultati
    _FILE_MTIMES = mtimes
    return risultati


# Mantiene la vecchia variabile TOOLS per chi l'importa direttamente.
TOOLS = discover_tools()


# Compatibilità: i tool globali scritti con "from tools._utils import ..." continuano a funzionare.
sys.modules.setdefault("tools", sys.modules[__name__])
