import re
import urllib.request

from agentecore import tool

from ._utils import truncate


@tool
def web_fetch(url: str, timeout: int = 20) -> str:
    """Scarica una pagina web e restituisce il testo (HTML ripulito dai tag).

    Args:
        url: indirizzo http/https
        timeout: secondi massimi di attesa
    """
    if not url.startswith(("http://", "https://")):
        return "errore: l'URL deve iniziare con http:// o https://"
    req = urllib.request.Request(url, headers={"User-Agent": "fabbro/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            tipo = r.headers.get("Content-Type", "")
            corpo = r.read(2_000_000).decode(r.headers.get_content_charset() or "utf-8", errors="replace")
    except Exception as e:
        return f"errore: {e}"
    if "html" in tipo:
        corpo = re.sub(r"(?is)<(script|style|noscript).*?</\1>", "", corpo)
        corpo = re.sub(r"(?s)<[^>]+>", " ", corpo)
        corpo = re.sub(r"[ \t]+", " ", corpo)
        corpo = re.sub(r"\n\s*\n+", "\n\n", corpo)
    return truncate(corpo.strip())
