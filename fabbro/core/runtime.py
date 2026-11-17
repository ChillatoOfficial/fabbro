"""Stato condiviso tra i tool e la TUI. Vive fuori da tools/ perché quel pacchetto
viene ricaricato a caldo e perderebbe lo stato."""
import atexit
import os
import signal
import subprocess

LETTI: dict[str, float] = {}      # percorso -> mtime all'ultima lettura/scrittura
TODO: list[str] = []              # lista compiti corrente
DIFFS: dict[str, list] = {}       # nome tool -> coda di diff da mostrare nelle card
PROCESSI: dict[int, dict] = {}    # processi bash in background
FOREGROUND: list[subprocess.Popen] = []
_prossimo_id = [0]


def nuovo_id() -> int:
    _prossimo_id[0] += 1
    return _prossimo_id[0]


def uccidi(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.kill()
        except OSError:
            pass


def uccidi_foreground() -> None:
    for p in list(FOREGROUND):
        uccidi(p)


def uccidi_tutti() -> None:
    uccidi_foreground()
    for info in PROCESSI.values():
        if info["proc"].poll() is None:
            uccidi(info["proc"])


atexit.register(uccidi_tutti)
