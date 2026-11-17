import os
import subprocess
import tempfile

from fabbro.core import runtime
from agentecore import tool

from ._utils import resolve, truncate


@tool
def bash(command: str, timeout: int = 120, cwd: str = ".", background: bool = False) -> str:
    """Esegue un comando shell. Con background=true lo avvia e restituisce un id (server, watch).

    Args:
        command: comando da eseguire
        timeout: secondi massimi prima di interrompere il comando (ignorato in background)
        cwd: cartella in cui eseguirlo
        background: se vero non aspetta la fine; leggi l'output con bash_output
    """
    try:
        if background:
            fd, log = tempfile.mkstemp(prefix="fabbro-bg-", suffix=".log")
            proc = subprocess.Popen(
                command, shell=True, cwd=resolve(cwd), stdout=fd, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, start_new_session=True,
            )
            os.close(fd)
            pid = runtime.nuovo_id()
            runtime.PROCESSI[pid] = {"proc": proc, "log": log, "cmd": command}
            return f"avviato in background: id={pid}. Usa bash_output({pid}) per leggere, bash_kill({pid}) per fermarlo."
        proc = subprocess.Popen(
            command, shell=True, cwd=resolve(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL, text=True, errors="replace", start_new_session=True,
        )
    except OSError as e:
        return f"errore: {e}"
    runtime.FOREGROUND.append(proc)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        runtime.uccidi(proc)
        out, err = proc.communicate()
        return truncate(f"errore: timeout dopo {timeout}s\n{out or ''}{err or ''}")
    finally:
        if proc in runtime.FOREGROUND:
            runtime.FOREGROUND.remove(proc)
    if proc.returncode in (-9, -15):
        return "interrotto dall'utente"
    parti = []
    if out:
        parti.append(out)
    if err:
        parti.append(f"[stderr]\n{err}")
    parti.append(f"[exit {proc.returncode}]")
    return truncate("\n".join(parti))


@tool
def bash_output(id: int, tail: int = 60) -> str:
    """Legge le ultime righe di output di un processo avviato in background.

    Args:
        id: id restituito da bash con background=true
        tail: quante righe finali leggere
    """
    info = runtime.PROCESSI.get(id)
    if not info:
        return f"errore: nessun processo con id {id}"
    try:
        with open(info["log"], encoding="utf-8", errors="replace") as f:
            righe = f.read().splitlines()
    except OSError as e:
        return f"errore: {e}"
    code = info["proc"].poll()
    stato = "in esecuzione" if code is None else f"terminato (exit {code})"
    return truncate(f"[{stato}] {info['cmd']}\n" + "\n".join(righe[-max(tail, 1):]))


@tool
def bash_kill(id: int) -> str:
    """Ferma un processo avviato in background.

    Args:
        id: id restituito da bash con background=true
    """
    info = runtime.PROCESSI.get(id)
    if not info:
        return f"errore: nessun processo con id {id}"
    if info["proc"].poll() is None:
        runtime.uccidi(info["proc"])
        return f"processo {id} fermato"
    return f"processo {id} già terminato"
