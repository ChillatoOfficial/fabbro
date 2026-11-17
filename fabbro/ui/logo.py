"""logo.py - tutto in un file: grafica del logo + interfaccia TUI di Fabbro.

Requisiti: pip install textual rich
Avvio:     python logo.py            (TUI completa)
           python logo.py --stampa   (solo logo statico)

Dentro la TUI: clicca l'omino per farlo salutare.
Per collegare il tuo agente vedi FabbroTUI.elabora().
"""
import asyncio
from pathlib import Path

from rich.console import Console
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Input, Static

# =====================================================================
# GRAFICA: omino a pixel + scritta FABBRO
# =====================================================================
VERDE = "#5ae0ad"
AMBRA = "#ffd166"
ROSSO = "#f47067"
ACCENT = "#d97757"      # colore del brand
TESTO = "#e6edf3"
DIM = "#6e7681"
COLORI = {"#": ACCENT, "o": AMBRA}

_TESTA = [
    ".######..",
    ".######..",
    ".#.##.#..",
    ".#.##.#..",
    ".######..",
]
_ANTENNA = ["....o....", "....#...."]

IDLE = _ANTENNA + _TESTA + [
    "########.",
    "#.####.#.",
    "#.####.#.",
    "..####...",
    ".##..##..",
]
_CORPO_SALUTO = ["#.####...", "#.####...", "..####...", ".##..##.."]
WAVE_A = _ANTENNA + [
    ".######.#",
    ".######.#",
    ".#.##.#.#",
    ".#.##.#.#",
    ".######.#",
    "#########",
] + _CORPO_SALUTO
WAVE_B = _ANTENNA + [
    ".######..",
    ".######.#",
    ".#.##.#.#",
    ".#.##.#.#",
    ".######.#",
    "#########",
] + _CORPO_SALUTO

_FONT = {
    "A": [".###.", "#...#", "#####", "#...#", "#...#"],
    "G": [".####", "#....", "#..##", "#...#", ".###."],
    "E": ["#####", "#....", "####.", "#....", "#####"],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#"],
    "T": ["#####", "..#..", "..#..", "..#..", "..#.."],
    "F": ["#####", "#....", "####.", "#....", "#...."],
    "B": ["####.", "#...#", "####.", "#...#", "####."],
    "R": ["####.", "#...#", "####.", "#..#.", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", ".###."],
}


def scritta(parola: str = "FABBRO") -> list[str]:
    righe = ["" for _ in range(5)]
    for i, ch in enumerate(parola):
        for r in range(5):
            righe[r] += _FONT[ch][r] + ("." if i < len(parola) - 1 else "")
    righe.append("." * len(righe[0]))  # riga vuota: numero pari di righe
    return righe


def disegna(griglia: list[str]) -> Text:
    """Griglia di pixel -> Text (due righe di pixel per riga di terminale)."""
    t = Text()
    if len(griglia) % 2:
        griglia = griglia + ["." * len(griglia[0])]
    for r in range(0, len(griglia), 2):
        for c in range(len(griglia[0])):
            su = COLORI.get(griglia[r][c])
            giu = COLORI.get(griglia[r + 1][c])
            if su and giu:
                t.append("▀", style=f"{su} on {giu}")
            elif su:
                t.append("▀", style=su)
            elif giu:
                t.append("▄", style=giu)
            else:
                t.append(" ")
        t.append("\n")
    return t


def logo_completo(frame: list[str] = IDLE) -> Text:
    """Omino sopra, scritta FABBRO sotto, centrati sulla stessa larghezza."""
    testo = scritta()
    larghezza = max(len(frame[0]), len(testo[0]))
    out = Text()
    for blocco, w in ((disegna(frame), len(frame[0])), (disegna(testo), len(testo[0]))):
        pad = " " * ((larghezza - w) // 2)
        for riga in blocco.split("\n", allow_blank=False):
            out.append(pad)
            out.append_text(riga)
            out.append("\n")
    return out


def stampa_logo(console: Console | None = None) -> None:
    (console or Console()).print(logo_completo(), justify="center")


# =====================================================================
# INTERFACCIA: TUI di Fabbro
# =====================================================================
AIUTO = (
    "[b]Comandi[/b]\n"
    "  /help               mostra questo aiuto\n"
    "  /clear              pulisce la chat\n"
    "  /thinking basso|medio|alto\n"
    "  /session            menu sessioni · <nome> cambia/crea · exit · rm [nome]\n"
    "  /provider [nome]    scegli il provider (menu); add, rm, key <nome>\n"
    "  /model [nome]       scegli il modello (menu)\n"
    "  /setup              configura il provider passo per passo\n"
    "  /permessi [modo]    chiedi | modifiche | auto\n"
    "  /rag add <percorso> salva file .md per la ricerca (anche list, rm)\n"
    "  /compact            riassumi la conversazione\n"
    "Esc interrompe l'agente.\n"
    "  /quit               esci (anche Ctrl+C)\n"
    "Clicca l'omino per farlo salutare."
)


class Omino(Static):
    """Logo cliccabile: al click l'omino alza il braccio e saluta."""

    def __init__(self) -> None:
        super().__init__(disegna(IDLE), classes="logo")
        self._saluta_ora = False
        self._n = 0

    def on_click(self) -> None:
        if self._saluta_ora:
            return
        self._saluta_ora, self._n = True, 0
        self._timer = self.set_interval(0.25, self._tick)

    def _tick(self) -> None:
        self.update(disegna(WAVE_A if self._n % 2 == 0 else WAVE_B))
        self._n += 1
        if self._n >= 8:
            self._timer.stop()
            self.update(disegna(IDLE))
            self._saluta_ora = False


class FabbroTUI(App):
    TITLE = "Fabbro"
    BINDINGS = [("ctrl+c", "quit", "Esci"), ("ctrl+l", "pulisci", "Pulisci")]
    CSS = """
    Screen { layout: vertical; background: #0d1117; color: #e6edf3; }
    #header { height: 1; padding: 0 2; background: #0d1117; }
    #chat { padding: 0 2; scrollbar-size-vertical: 1; scrollbar-color: #30363d; scrollbar-background: #0d1117; }
    #banner { height: auto; margin: 1 0 0 0; }
    .logo { width: auto; height: auto; margin-right: 3; }
    #info { width: 1fr; height: 6; content-align: left middle; }
    .utente { background: #161b22; color: #e6edf3; padding: 0 1; margin-top: 1; }
    .riga { height: auto; margin-top: 1; }
    .puntino { width: 2; color: #d97757; }
    .agente { width: 1fr; }
    .tool { margin-top: 1; color: #6e7681; }
    .sistema { color: #6e7681; margin-top: 1; padding-left: 2; }
    #input { border: round #30363d; margin: 1 1 0 1; background: #0d1117; }
    #input:focus { border: round #d97757; }
    #footer { height: 1; padding: 0 2; color: #6e7681; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.sessione = "main"
        self.thinking = "medio"
        self.modello = "modello-locale"
        self.token = 0
        self.occupato = False

    # ---------- layout ----------
    def compose(self) -> ComposeResult:
        yield Static(id="header")
        yield VerticalScroll(id="chat")
        yield Input(placeholder="Scrivi un messaggio…", id="input")
        yield Static(id="footer")

    def on_mount(self) -> None:
        self._benvenuto()
        self._aggiorna_header()
        self._aggiorna_footer()
        self.query_one("#input", Input).focus()

    def _benvenuto(self) -> None:
        chat = self.query_one("#chat", VerticalScroll)
        info = Text()
        info.append("Fabbro\n", style=f"bold {ACCENT}")
        info.append(f"{self.modello}\n", style=TESTO)
        info.append(f"{Path.cwd()}\n\n", style=DIM)
        info.append("/help", style=ACCENT)
        info.append(" comandi · ", style=DIM)
        info.append("/model", style=ACCENT)
        info.append(" · ", style=DIM)
        info.append("/provider", style=ACCENT)
        chat.mount(Horizontal(Omino(), Static(info, id="info"), id="banner"))

    def _aggiorna_header(self) -> None:
        t = Text()
        t.append("● ", style=AMBRA if self.occupato else VERDE)
        t.append("lavoro…" if self.occupato else "pronto", style=TESTO)
        t.append(f"  ·  sessione {self.sessione}", style=DIM)
        self.query_one("#header", Static).update(t)

    def _aggiorna_footer(self) -> None:
        cwd = Path.cwd().name or "/"
        t = Text()
        sep = (" · ", DIM)
        for i, (v, stile) in enumerate([
            (self.modello, TESTO), (f"ragionamento {self.thinking}", DIM),
            (f"ctx {self.token / 1000:.1f}k", DIM), (cwd, DIM),
        ]):
            if i:
                t.append(*sep)
            t.append(v, style=stile)
        self.query_one("#footer", Static).update(t)

    async def _aggiungi(self, testo: str, classe: str, markup: bool = True) -> Static:
        chat = self.query_one("#chat", VerticalScroll)
        w = Static(testo, classes=classe, markup=markup)
        if classe.startswith("agente"):
            await chat.mount(Horizontal(Static("●", classes="puntino"), w, classes="riga"))
        else:
            await chat.mount(w)
        chat.scroll_end(animate=False)
        return w

    # ---------- input ----------
    async def on_input_submitted(self, e: Input.Submitted) -> None:
        testo = e.value.strip()
        e.input.clear()
        if not testo or self.occupato:
            return
        if testo.startswith("/"):
            await self._comando(testo)
            return
        await self._aggiungi(f"› {testo}", "utente", markup=False)
        self.elabora(testo)

    async def _comando(self, riga: str) -> None:
        cmd, _, arg = riga.partition(" ")
        if cmd == "/help":
            await self._aggiungi(AIUTO, "sistema")
        elif cmd == "/clear":
            await self.action_pulisci()
        elif cmd == "/thinking" and arg in ("basso", "medio", "alto"):
            self.thinking = arg
            self._aggiorna_footer()
            await self._aggiungi(f"ragionamento impostato su {arg}", "sistema")
        elif cmd == "/session" and arg:
            self.sessione = arg
            self._aggiorna_header()
            await self._aggiungi(f"sessione: {arg}", "sistema")
        elif cmd == "/quit":
            self.exit()
        else:
            await self._aggiungi(f"comando non valido: {riga}", "sistema", markup=False)

    async def action_pulisci(self) -> None:
        # si aspetta la rimozione: altrimenti il nuovo banner collide con l'id del vecchio
        await self.query_one("#chat", VerticalScroll).remove_children()
        self._benvenuto()

    # ---------- agente (da sostituire con il tuo) ----------
    @work(exclusive=True)
    async def elabora(self, testo: str) -> None:
        """Collega qui il tuo agente (es. agentecore).

        Per ogni tool: crea una scheda con `_aggiungi(..., "tool")`, aggiornala con
        `scheda.update(...)` mentre arriva l'output e, a fine tool, `scheda.add_class("finito")`.
        Per la risposta scrivi un po' di testo alla volta. Questa è solo una simulazione.
        """
        self.occupato = True
        self._aggiorna_header()

        scheda = await self._aggiungi("⚙ read  README.md", "tool", markup=False)
        for i in range(1, 4):
            await asyncio.sleep(0.4)
            scheda.update(f"⚙ read  README.md\n{'.' * i} lettura in corso")
        scheda.update("⚙ read  README.md\n✓ 42 righe")
        scheda.add_class("finito")

        risposta = await self._aggiungi("", "agente", markup=False)
        parole = f"Ho ricevuto: «{testo}». Collega qui il tuo agente per risposte vere.".split()
        corrente = ""
        for p in parole:
            corrente += p + " "
            risposta.update(corrente)
            self.token += 1
            self._aggiorna_footer()
            self.query_one("#chat", VerticalScroll).scroll_end(animate=False)
            await asyncio.sleep(0.06)

        self.occupato = False
        self._aggiorna_header()


if __name__ == "__main__":
    import sys

    if "--stampa" in sys.argv:
        stampa_logo()
    else:
        FabbroTUI().run()