"""Provider: i default sono qui; ~/.fabbro/providers.json li estende o sovrascrive.

Per ogni provider: tipo (openai | anthropic | google), base_url, model e la chiave
in "api_key" oppure in "api_key_env" (nome di una variabile d'ambiente).
"""
import json
import os
import re

from fabbro import paths

DEFAULT_PROVIDERS = {
    "locale": {
        "tipo": "openai",
        "base_url": "http://localhost:11434/v1",   # es. Ollama; modificabile con /setup
        "api_key": "none",
        "model": "llama3.1",
    },
    "openai": {
        "tipo": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-4o-mini",
    },
    "anthropic": {
        "tipo": "anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "api_key_env": "ANTHROPIC_API_KEY",
        "model": "claude-sonnet-5-5",
    },
    "google": {
        "tipo": "google",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "api_key_env": "GOOGLE_API_KEY",
        "model": "gemini-2.5-flash",
    },
}
PROVIDER_DEFAULT = "locale"


def _scrivi(dati: dict) -> None:
    paths.PROVIDERS_FILE.write_text(json.dumps(dati, indent=2, ensure_ascii=False), encoding="utf-8")
    os.chmod(paths.PROVIDERS_FILE, 0o600)  # contiene chiavi API


def _leggi_file() -> dict:
    if not paths.PROVIDERS_FILE.exists():
        _scrivi(DEFAULT_PROVIDERS)
    try:
        d = json.loads(paths.PROVIDERS_FILE.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _carica() -> dict[str, dict]:
    utente = _leggi_file()
    prov = {k: dict(v) for k, v in DEFAULT_PROVIDERS.items()}
    for nome, cfg in utente.items():
        if isinstance(cfg, dict):
            prov[nome] = {**prov.get(nome, {}), **cfg}
    for cfg in prov.values():
        cfg["api_key"] = cfg.get("api_key") or os.environ.get(cfg.get("api_key_env", ""), "")
    return {k: v for k, v in prov.items() if {"tipo", "base_url", "model"} <= v.keys()}


PROVIDERS = _carica()
if PROVIDER_DEFAULT not in PROVIDERS:
    PROVIDER_DEFAULT = next(iter(PROVIDERS))


def ricarica() -> None:
    """Rilegge providers.json aggiornando PROVIDERS sul posto (chi lo ha importato lo vede)."""
    nuovi = _carica()
    PROVIDERS.clear()
    PROVIDERS.update(nuovi)


def salva_provider(nome: str, cfg: dict) -> None:
    dati = _leggi_file()
    dati[nome] = cfg
    _scrivi(dati)
    ricarica()


def rimuovi_provider(nome: str) -> bool:
    """Rimuove un provider aggiunto dall'utente. I default non si possono rimuovere."""
    dati = _leggi_file()
    if nome in DEFAULT_PROVIDERS or nome not in dati:
        return False
    del dati[nome]
    _scrivi(dati)
    ricarica()
    return True


def imposta_chiave(nome: str, valore: str) -> None:
    """Salva la chiave di un provider (anche predefinito). Un nome tipo OPENAI_API_KEY è una variabile d'ambiente."""
    dati = _leggi_file()
    voce = {**DEFAULT_PROVIDERS.get(nome, {}), **dati.get(nome, {})}
    if re.fullmatch(r"[A-Z][A-Z0-9_]*", valore):
        voce["api_key_env"], voce["api_key"] = valore, ""
    else:
        voce["api_key"] = valore
    dati[nome] = voce
    _scrivi(dati)
    ricarica()


def imposta_campo(nome: str, **campi: str) -> None:
    """Aggiorna alcuni campi di un provider (anche predefinito) senza toccare gli altri."""
    dati = _leggi_file()
    dati[nome] = {**DEFAULT_PROVIDERS.get(nome, {}), **dati.get(nome, {}), **campi}
    _scrivi(dati)
    ricarica()
