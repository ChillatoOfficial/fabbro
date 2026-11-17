"""RAG locale senza dipendenze: documenti markdown/testo copiati in ~/.fabbro/rag/docs
e ricerca per parole chiave con BM25 sui paragrafi (spezzati per titolo)."""
import json
import math
import re
import shutil
import time
import unicodedata
from pathlib import Path

from fabbro import paths

DIR = paths.HOME / "rag"
DOCS = DIR / "docs"
META = DIR / "meta.json"
ESTENSIONI = {".md", ".markdown", ".txt", ".rst"}
MAX_CHUNK = 1200
_STOP = set("""il lo la i gli le un uno una di a da in con su per tra fra e o ma che non si e'
the a an of to in on for and or is are be it this that with as by at from""".split())

_cache: dict = {"chiave": None, "chunks": [], "df": {}, "avg": 0.0}


def _meta() -> dict:
    try:
        return json.loads(META.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def lista() -> list[dict]:
    DOCS.mkdir(parents=True, exist_ok=True)
    meta = _meta()
    out = []
    for f in sorted(DOCS.glob("*")):
        if f.is_file():
            out.append({"nome": f.name, "byte": f.stat().st_size, "origine": meta.get(f.name, {}).get("origine", "")})
    return out


def aggiungi(percorso: str) -> list[str]:
    """Copia un file o tutti i .md di una cartella. Restituisce i nomi salvati."""
    src = Path(percorso).expanduser()
    if not src.exists():
        raise FileNotFoundError(f"non trovato: {src}")
    files = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.is_file())
    files = [f for f in files if f.suffix.lower() in ESTENSIONI and not any(x.startswith(".") for x in f.parts)]
    if not files:
        raise ValueError("nessun file .md/.txt trovato")
    DOCS.mkdir(parents=True, exist_ok=True)
    meta, salvati = _meta(), []
    for f in files:
        nome = f.name
        gia = meta.get(nome, {}).get("origine")
        if (DOCS / nome).exists() and gia != str(f.resolve()):   # stesso nome, file diverso
            nome = f"{f.parent.name}-{f.name}"
        shutil.copy(f, DOCS / nome)
        meta[nome] = {"origine": str(f.resolve()), "aggiunto": time.time()}
        salvati.append(nome)
    META.write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    return salvati


def rimuovi(nome: str) -> bool:
    f = DOCS / Path(nome).name
    if not f.is_file():
        return False
    f.unlink()
    meta = _meta()
    meta.pop(f.name, None)
    META.write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    return True


def _token(testo: str) -> list[str]:
    t = unicodedata.normalize("NFKD", testo.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    out = []
    for w in re.findall(r"[a-z0-9_]+", t):
        if len(w) < 2 or w in _STOP:
            continue
        out.append(w[:6] if len(w) > 6 else w)       # stemming grezzo: varianti della stessa radice
    return out


def _spezza(nome: str, testo: str) -> list[dict]:
    """Un chunk per sezione (titolo > sottotitolo), sezioni lunghe divise per paragrafi."""
    sezioni, percorso, corrente, in_codice = [], [], [], False
    def chiudi():
        if "".join(corrente).strip():
            sezioni.append((" › ".join(percorso), "".join(corrente).strip()))
        corrente.clear()
    for riga in testo.splitlines(keepends=True):
        if riga.lstrip().startswith("```"):
            in_codice = not in_codice
        m = None if in_codice else re.match(r"^(#{1,6})\s+(.*)", riga)
        if m:
            chiudi()
            livello = len(m.group(1))
            percorso[:] = percorso[: livello - 1] + [m.group(2).strip()]
        else:
            corrente.append(riga)
    chiudi()
    chunks = []
    for titolo, corpo in sezioni:
        blocchi, attuale = [], ""
        for par in re.split(r"\n\s*\n", corpo):
            if attuale and len(attuale) + len(par) > MAX_CHUNK:
                blocchi.append(attuale)
                attuale = ""
            attuale += ("\n\n" if attuale else "") + par
        blocchi.append(attuale)
        for b in blocchi:
            chunks.append({"doc": nome, "titolo": titolo, "testo": b, "tok": _token(f"{titolo} {titolo} {b}")})
    return chunks


def _indice() -> dict:
    DOCS.mkdir(parents=True, exist_ok=True)
    files = sorted(f for f in DOCS.glob("*") if f.is_file())
    chiave = tuple((f.name, f.stat().st_mtime) for f in files)
    if _cache["chiave"] == chiave:
        return _cache
    chunks = []
    for f in files:
        chunks += _spezza(f.name, f.read_text(encoding="utf-8", errors="replace"))
    df: dict[str, int] = {}
    for c in chunks:
        for t in set(c["tok"]):
            df[t] = df.get(t, 0) + 1
    _cache.update(chiave=chiave, chunks=chunks, df=df,
                  avg=(sum(len(c["tok"]) for c in chunks) / len(chunks)) if chunks else 0.0)
    return _cache


def cerca(query: str, k: int = 4) -> list[dict]:
    idx = _indice()
    chunks, df, avg = idx["chunks"], idx["df"], idx["avg"]
    q = _token(query)
    if not chunks or not q:
        return []
    n, k1, b = len(chunks), 1.5, 0.75
    risultati = []
    for c in chunks:
        tf: dict[str, int] = {}
        for t in c["tok"]:
            tf[t] = tf.get(t, 0) + 1
        score = 0.0
        for t in set(q):
            if t in tf:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                score += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * len(c["tok"]) / (avg or 1)))
        if score > 0:
            risultati.append({**c, "score": score})
    risultati.sort(key=lambda c: c["score"], reverse=True)
    return risultati[: max(k, 1)]
