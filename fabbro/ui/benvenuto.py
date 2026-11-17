"""Schermata di primo avvio: logo animato e 'installazione' dei componenti."""
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from fabbro.ui.logo import ACCENT, DIM, IDLE, TESTO, VERDE, WAVE_A, WAVE_B, disegna, scritta

SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


class Benvenuto(ModalScreen[None]):
    """Mostra i passi di preparazione (nome, dettaglio) con spinner e barra di avanzamento."""

    BINDINGS = [("escape", "salta", "Salta"), ("enter", "salta", "Continua")]
    DEFAULT_CSS = """
    Benvenuto { align: center middle; background: #0d1117; }
    #centro { width: 64; height: auto; }
    #logo, #titolo, #barra, #fine { width: 100%; content-align: center middle; }
    #logo { height: 6; }
    #titolo { height: 4; margin-bottom: 1; }
    #passi { margin: 1 4; height: auto; }
    #barra { margin-top: 1; }
    #fine { margin-top: 1; color: #6e7681; }
    """

    def __init__(self, passi: list[tuple[str, str]]) -> None:
        super().__init__()
        self.passi = passi
        self.fatti = 0
        self.t = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="centro"):
            yield Static(id="logo")
            yield Static(disegna(scritta()), id="titolo")
            yield Static(id="passi")
            yield Static(id="barra")
            yield Static("", id="fine")

    def on_mount(self) -> None:
        self._disegna()
        self.anima = self.set_interval(0.12, self._tick)
        self.avanza = self.set_interval(0.6, self._avanza)

    def _tick(self) -> None:
        self.t += 1
        if self.fatti < len(self.passi):
            frame = WAVE_A if (self.t // 2) % 2 == 0 else WAVE_B   # l'omino saluta mentre lavora
        else:
            frame = IDLE
        self.query_one("#logo", Static).update(disegna(frame))
        self._disegna()

    def _avanza(self) -> None:
        self.fatti += 1
        if self.fatti >= len(self.passi):
            self.avanza.stop()
            self.query_one("#fine", Static).update(Text("Pronto — Invio per configurare il provider", style=DIM))
            self.set_timer(1.8, self.action_salta)

    def _disegna(self) -> None:
        t = Text()
        for i, (nome, dett) in enumerate(self.passi):
            if i:
                t.append("\n")
            if i < self.fatti:
                t.append("✓ ", style=VERDE)
                t.append(nome, style=TESTO)
                t.append(f"  {dett}" if dett else "", style=DIM)
            elif i == self.fatti:
                t.append(f"{SPINNER[self.t % len(SPINNER)]} ", style=ACCENT)
                t.append(nome + "…", style=ACCENT)
            else:
                t.append(f"· {nome}", style=DIM)
        self.query_one("#passi", Static).update(t)
        larghezza = 40
        pieno = round(larghezza * self.fatti / max(len(self.passi), 1))
        barra = Text("█" * pieno, style=ACCENT)
        barra.append("░" * (larghezza - pieno), style="#30363d")
        barra.append(f"  {100 * self.fatti // max(len(self.passi), 1)}%", style=DIM)
        self.query_one("#barra", Static).update(barra)

    def action_salta(self) -> None:
        if self.is_current:
            self.dismiss(None)
