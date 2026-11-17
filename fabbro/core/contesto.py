"""Contesto aggiunto al system prompt (progetto, git, RAG) e compattazione della conversazione."""
import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path

from fabbro import paths
from fabbro.core import rag
from agentecore import Memory, Role, TextBlock, Turn
from agentecore.type.type import FunctionCallBlock, FunctionCallResultBlock

NOMI_CONTESTO = ("AGENTS.md", "CLAUDE.md")
MAX_CONTESTO = 4000
SOGLIA_DEFAULT = 24000   # token stimati oltre i quali la conversazione viene riassunta


def _git(*args: str) -> str:
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True, timeout=2, cwd=os.getcwd())
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def file_contesto() -> str:
    """AGENTS.md/CLAUDE.md dalla cartella corrente risalendo fino alla radice git (o a ~)."""
    trovati = []
    cartella = Path.cwd()
    home = Path.home()
    for d in [cartella, *cartella.parents]:
        for nome in NOMI_CONTESTO:
            f = d / nome
            if f.is_file():
                trovati.append(f)
                break
        if (d / ".git").exists() or d == home:
            break
    globale = paths.HOME / "AGENTS.md"
    if globale.is_file():
        trovati.append(globale)
    testo = ""
    for f in trovati:
        try:
            testo += f"\n[{f}]\n{f.read_text(encoding='utf-8').strip()}\n"
        except OSError:
            pass
    return testo[:MAX_CONTESTO] + ("\n…[troncato]" if len(testo) > MAX_CONTESTO else "")


def info_ambiente() -> str:
    righe = [f"cwd: {os.getcwd()}", f"data: {datetime.now():%Y-%m-%d}", f"sistema: {platform.system()}"]
    ramo = _git("rev-parse", "--abbrev-ref", "HEAD")
    if ramo:
        modificati = len(_git("status", "--porcelain").splitlines())
        righe.append(f"git: ramo {ramo}, {modificati} file modificati")
    else:
        righe.append("git: non è un repository")
    return "\n".join(righe)


def indice_rag() -> str:
    docs = [d["nome"] for d in rag.lista()]
    if not docs:
        return ""
    extra = f" (+{len(docs) - 15})" if len(docs) > 15 else ""
    return f"RAG: documenti salvati dall'utente, consultali con rag_search quando servono: {', '.join(docs[:15])}{extra}"


# ---------------------------------------------------------------- compattazione
def stima_token(memory: Memory) -> int:
    n = 0
    for t in memory.turns:
        for b in t.blocks:
            n += len(str(b.to_dict()))
    return n // 4


def _testo_turno(t: Turn) -> str:
    out = []
    for b in t.blocks:
        if isinstance(b, TextBlock):
            out.append(f"{t.role.value}: {b.content[:1500]}")
        elif isinstance(b, FunctionCallBlock):
            out.append(f"tool {b.name}({str(b.arguments)[:200]})")
        elif isinstance(b, FunctionCallResultBlock):
            out.append(f"  -> {b.result[:300]}")
    return "\n".join(out)


def _inizi_utente(memory: Memory) -> list[int]:
    return [i for i, t in enumerate(memory.turns)
            if t.role == Role.USER and any(isinstance(b, TextBlock) for b in t.blocks)]


async def compatta(agent, soglia: int = SOGLIA_DEFAULT, tieni: int = 3, forza: bool = False) -> str | None:
    """Riassume i turni vecchi se il contesto supera la soglia. Restituisce un messaggio o None."""
    mem = agent.memory
    if not forza and stima_token(mem) < soglia:
        return None
    inizi = _inizi_utente(mem)
    if len(inizi) <= tieni:
        return None
    taglio = inizi[-tieni]
    vecchi = mem.turns[:taglio]
    testo = "\n".join(_testo_turno(t) for t in vecchi)[-60000:]
    riassunto = ""
    async for ev in agent.client.a_stream_invoke(
        "Riassumi questa conversazione tra utente e assistente di coding. Conserva: obiettivo, "
        "decisioni, file toccati (percorsi), comandi importanti, errori incontrati, cose ancora da fare. "
        "Sii denso e conciso (max 400 parole).\n\n" + testo,
        memory=Memory(),
        system_prompt="Sei un assistente che riassume conversazioni tecniche senza perdere i dettagli utili.",
    ):
        if ev.type == "text":
            riassunto += ev.text
    riassunto = riassunto.strip()
    if not riassunto:
        return None
    recenti = mem.turns[taglio:]
    prima = stima_token(mem)
    mem.clear()
    mem.add(Role.USER, [TextBlock(f"[Riassunto della conversazione precedente]\n{riassunto}")])
    for t in recenti:
        mem.add(t.role, t.blocks)
    return f"conversazione compattata: ~{prima // 1000}k → ~{stima_token(mem) // 1000}k token"
