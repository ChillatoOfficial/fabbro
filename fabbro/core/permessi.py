"""Conferme prima delle azioni che modificano file o eseguono comandi, con anteprima del diff."""
import dataclasses
import difflib
import os
import re

from fabbro.core import runtime

CONFERMA = {"bash", "write_file", "edit_file", "create_tool"}
FILE_TOOLS = {"write_file", "edit_file", "create_tool"}
MODI = ("chiedi", "modifiche", "auto")   # modifiche = accetta in automatico le modifiche ai file

STATO = {"modo": "chiedi", "sempre": set(), "chiedi": None}   # chiedi(nome, args, righe) -> "si" | "sempre" | "no"

_SICURI = {
    "ls", "pwd", "cat", "head", "tail", "wc", "echo", "grep", "rg", "which", "date", "tree", "stat",
    "file", "du", "df", "whoami", "uname", "basename", "dirname", "sort", "uniq", "diff",
}
_GIT_SICURI = {"status", "diff", "log", "branch", "show", "remote", "rev-parse", "ls-files", "blame"}


def bash_sicuro(cmd: str) -> bool:
    """Solo lettura: comandi noti, niente redirect/sostituzioni; la pipe è ok tra comandi sicuri."""
    if re.search(r"[;&><`$\n(]", cmd):
        return False
    for seg in cmd.split("|"):
        parole = seg.split()
        if not parole:
            return False
        if parole[0] == "git":
            if len(parole) < 2 or parole[1] not in _GIT_SICURI:
                return False
        elif parole[0] == "find":
            if any(p in ("-exec", "-delete", "-ok", "-execdir", "-fprint") for p in parole):
                return False
        elif parole[0] not in _SICURI:
            return False
    return True


def _chiave(nome: str, args: dict) -> str:
    if nome == "bash":
        parole = str(args.get("command", "")).split()
        return f"bash:{parole[0] if parole else ''}"
    return nome


def richiede(nome: str, args: dict) -> bool:
    if nome not in CONFERMA or STATO["modo"] == "auto" or _chiave(nome, args) in STATO["sempre"]:
        return False
    if nome == "bash":
        return not bash_sicuro(str(args.get("command", "")))
    return not (nome in FILE_TOOLS and STATO["modo"] == "modifiche")


def _diff(vecchio: str, nuovo: str) -> list[str]:
    righe = list(difflib.unified_diff(vecchio.splitlines(), nuovo.splitlines(), lineterm="", n=2))
    return righe[2:]


def _leggi(p: str) -> str | None:
    try:
        with open(p, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def anteprima(nome: str, args: dict) -> list[str]:
    """Righe da mostrare: diff unificato per i file, comando per bash."""
    try:
        if nome == "bash":
            return [f"$ {args.get('command', '')}"] + ([f"(in background)"] if args.get("background") else [])
        if nome == "edit_file":
            p = os.path.abspath(os.path.expanduser(args["path"]))
            testo = _leggi(p)
            if testo is None:
                return [f"{p}: non leggibile"]
            old, new = args["old_string"], args["new_string"]
            if old not in testo:
                return [f"{p}: old_string non trovato"]
            nuovo = testo.replace(old, new) if args.get("replace_all") else testo.replace(old, new, 1)
            return [f"{p}"] + _diff(testo, nuovo)
        if nome == "write_file":
            p = os.path.abspath(os.path.expanduser(args["path"]))
            vecchio = _leggi(p)
            if vecchio is None:
                righe = args["content"].splitlines()
                return [f"{p} (nuovo, {len(righe)} righe)"] + [f"+{r}" for r in righe[:40]] + (
                    [f"… +{len(righe) - 40} righe"] if len(righe) > 40 else [])
            return [f"{p}"] + _diff(vecchio, args["content"])
        if nome == "create_tool":
            righe = args["code"].splitlines()
            return [f"nuovo tool globale: {args['name']}"] + [f"+{r}" for r in righe[:40]]
    except Exception as e:
        return [f"(anteprima non disponibile: {e})"]
    return []


def avvolgi(tools: list) -> list:
    """Restituisce i tool con controllo permessi e raccolta dei diff per le card."""
    def crea(t):
        orig = t.fn

        def fn(**kw):
            if t.name in ("edit_file", "write_file"):
                from fabbro.tools._utils import controlla_scrittura   # inutile chiedere se fallirebbe comunque
                errore = controlla_scrittura(os.path.abspath(os.path.expanduser(kw["path"])))
                if errore:
                    return errore
            righe = anteprima(t.name, kw) if t.name in CONFERMA else []
            if t.name in ("edit_file", "write_file"):
                runtime.DIFFS.setdefault(t.name, []).append(righe)
            if richiede(t.name, kw) and STATO["chiedi"]:
                risposta = STATO["chiedi"](t.name, kw, righe)
                if risposta == "no":
                    if t.name in runtime.DIFFS and runtime.DIFFS[t.name]:
                        runtime.DIFFS[t.name].pop()
                    return "errore: azione rifiutata dall'utente. Non riprovare uguale: chiedi cosa preferisce."
                if risposta == "sempre":
                    STATO["sempre"].add(_chiave(t.name, kw))
            return orig(**kw)

        return dataclasses.replace(t, fn=fn) if t.name in CONFERMA else t

    return [crea(t) for t in tools]
