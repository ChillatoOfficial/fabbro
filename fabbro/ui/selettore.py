from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, OptionList
from textual.widgets.option_list import Option


class Selettore(ModalScreen[str | None]):
    """Menu a tendina con filtro. Restituisce la voce scelta o None (Esc).

    Se scrivi un testo che non è in elenco e premi Invio, viene restituito il testo
    così com'è (utile per inserire a mano un modello non elencato).
    """

    BINDINGS = [("escape", "annulla", "Annulla"), ("down", "giu", "Giù")]
    DEFAULT_CSS = """
    Selettore { align: center middle; background: #0d1117 60%; }
    #box { width: 60; max-width: 90%; height: auto; max-height: 80%;
           border: round #d97757; background: #161b22; padding: 0 1; }
    #titolo { color: #d97757; text-style: bold; margin-bottom: 1; }
    #filtro { border: round #30363d; }
    #filtro:focus { border: round #d97757; }
    #lista { height: auto; max-height: 18; background: #161b22; border: none; }
    #aiuto { color: #6e7681; margin-top: 1; }
    #nota { color: #6e7681; margin-bottom: 1; }
    """

    def __init__(self, titolo: str, voci: list[str], corrente: str = "", nota: str = "") -> None:
        super().__init__()
        self.titolo, self.voci, self.corrente, self.nota = titolo, voci, corrente, nota

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Label(self.titolo, id="titolo")
            if self.nota:
                yield Label(self.nota, id="nota")
            yield Input(placeholder="filtra o scrivi un nome…", id="filtro")
            yield OptionList(id="lista")
            yield Label("↑↓ scegli · Invio conferma · Esc annulla", id="aiuto")

    def on_mount(self) -> None:
        self._riempi("")
        self.query_one("#filtro", Input).focus()

    def _riempi(self, filtro: str) -> None:
        lista = self.query_one("#lista", OptionList)
        lista.clear_options()
        f = filtro.lower()
        for v in self.voci:
            if f in v.lower():
                lista.add_option(Option(f"{'● ' if v == self.corrente else '  '}{v}", id=v))
        if lista.option_count:
            lista.highlighted = 0

    @on(Input.Changed, "#filtro")
    def _filtra(self, e: Input.Changed) -> None:
        self._riempi(e.value)

    @on(Input.Submitted, "#filtro")
    def _invio(self, e: Input.Submitted) -> None:
        lista = self.query_one("#lista", OptionList)
        if lista.highlighted is not None and lista.option_count:
            self.dismiss(lista.get_option_at_index(lista.highlighted).id)
        elif e.value.strip():
            self.dismiss(e.value.strip())

    @on(OptionList.OptionSelected)
    def _scelta(self, e: OptionList.OptionSelected) -> None:
        self.dismiss(e.option.id)

    def action_giu(self) -> None:
        self.query_one("#lista", OptionList).focus()

    def action_annulla(self) -> None:
        self.dismiss(None)


class Conferma(ModalScreen[str]):
    """Chiede il permesso per un'azione, con anteprima. Restituisce 'si', 'sempre' o 'no'."""

    BINDINGS = [("escape", "no", "No"), ("n", "no", "No"), ("y", "si", "Sì"), ("a", "sempre", "Sempre")]
    DEFAULT_CSS = """
    Conferma { align: center middle; background: #0d1117 60%; }
    #cbox { width: 90%; max-width: 110; height: auto; max-height: 90%;
            border: round #d97757; background: #161b22; padding: 0 1; }
    #ctitolo { color: #d97757; text-style: bold; margin-bottom: 1; }
    #canteprima { height: auto; max-height: 20; background: #0d1117; padding: 0 1; margin-bottom: 1; }
    #copzioni { height: auto; background: #161b22; border: none; }
    OptionList > .option-list--option-highlighted { background: #d97757; color: #0d1117; text-style: bold; }
    """

    def __init__(self, titolo: str, anteprima, sempre: str) -> None:
        super().__init__()
        self.titolo, self.anteprima, self.sempre = titolo, anteprima, sempre

    def compose(self) -> ComposeResult:
        from textual.containers import VerticalScroll
        from textual.widgets import Static
        with Vertical(id="cbox"):
            yield Label(self.titolo, id="ctitolo")
            with VerticalScroll(id="canteprima"):
                yield Static(self.anteprima)
            yield OptionList(
                Option("Sì  (y)", id="si"),
                Option(f"Sì, e non chiedere più per {self.sempre}  (a)", id="sempre"),
                Option("No  (n / Esc)", id="no"),
                id="copzioni",
            )

    def on_mount(self) -> None:
        self.query_one("#copzioni", OptionList).focus()

    @on(OptionList.OptionSelected)
    def _scelta(self, e: OptionList.OptionSelected) -> None:
        self.dismiss(e.option.id)

    def action_si(self) -> None:
        self.dismiss("si")

    def action_sempre(self) -> None:
        self.dismiss("sempre")

    def action_no(self) -> None:
        self.dismiss("no")


class Domanda(ModalScreen[str | None]):
    """Chiede una riga di testo. Restituisce il testo (anche vuoto) oppure None con Esc."""

    BINDINGS = [("escape", "annulla", "Annulla")]
    DEFAULT_CSS = """
    Domanda { align: center middle; background: #0d1117 60%; }
    #dbox { width: 70; max-width: 90%; height: auto; border: round #d97757;
            background: #161b22; padding: 0 1; }
    #dtitolo { color: #d97757; text-style: bold; }
    #dnota { color: #6e7681; margin-bottom: 1; }
    #dinput { border: round #30363d; }
    #dinput:focus { border: round #d97757; }
    """

    def __init__(self, titolo: str, nota: str = "", default: str = "", segreto: bool = False) -> None:
        super().__init__()
        self.titolo, self.nota, self.default, self.segreto = titolo, nota, default, segreto

    def compose(self) -> ComposeResult:
        with Vertical(id="dbox"):
            yield Label(self.titolo, id="dtitolo")
            yield Label(self.nota + ("  " if self.nota else "") + "Invio conferma · Esc annulla", id="dnota")
            yield Input(value=self.default, password=self.segreto, id="dinput")

    def on_mount(self) -> None:
        self.query_one("#dinput", Input).focus()

    @on(Input.Submitted)
    def _invio(self, e: Input.Submitted) -> None:
        self.dismiss(e.value.strip())

    def action_annulla(self) -> None:
        self.dismiss(None)
