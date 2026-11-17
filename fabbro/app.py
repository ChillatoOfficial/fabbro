import asyncio
import json
import os
import re
import time
from pathlib import Path

import httpx
from rich.markdown import Markdown
from rich.text import Text
from textual import work
from textual.widgets import Static

from agentecore import Agent, Anthropic, Google, OpenAI, SQLiteMemory
from fabbro import paths
from fabbro import config
from fabbro.config import DEFAULT_PROVIDERS, PROVIDER_DEFAULT, PROVIDERS
from fabbro.core import contesto, permessi, rag, runtime
from fabbro.tools import discover_tools
from fabbro.tools.skills import indice_skills
from fabbro.ui.logo import ACCENT, AMBRA, DIM, ROSSO, TESTO, VERDE, FabbroTUI
from fabbro.ui.benvenuto import Benvenuto
from fabbro.ui.selettore import Conferma, Domanda, Selettore

MAX_PASSI = 40
SESSIONE_DEFAULT = "main"
ESCI_SESSIONE = "↩ esci dalla sessione (torna a main)"
AGGIUNGI = "＋ aggiungi provider…"
URL_DEFAULT = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta",
}
MEMORIA_DB = paths.HOME / "memoria.db"


# ---------------------------------------------------------------- stato e provider
def carica_stato() -> tuple[str, str, str]:
    try:
        d = json.loads(paths.STATE_FILE.read_text(encoding="utf-8"))
        if d.get("provider") in PROVIDERS:
            return d["provider"], d.get("model") or PROVIDERS[d["provider"]]["model"], d.get("session") or "main"
    except (OSError, ValueError):
        pass
    return PROVIDER_DEFAULT, PROVIDERS[PROVIDER_DEFAULT]["model"], "main"


def salva_stato(provider: str, model: str, session: str) -> None:
    try:
        paths.STATE_FILE.write_text(json.dumps({"provider": provider, "model": model, "session": session}), encoding="utf-8")
    except OSError:
        pass


CLIENT = {"openai": OpenAI, "anthropic": Anthropic, "google": Google}


def crea_client(provider: str, model: str):
    p = PROVIDERS[provider]
    return CLIENT[p["tipo"]](model_name=model, api_key=p["api_key"] or None, base_url=p["base_url"])


async def elenca_modelli(provider: str) -> list[str]:
    """Chiede al provider i modelli disponibili. Solleva eccezione se non raggiungibile."""
    p = PROVIDERS[provider]
    url, params, headers = p["base_url"].rstrip("/") + "/models", {}, {}
    if p["tipo"] == "openai":
        headers["Authorization"] = f"Bearer {p['api_key']}"
    elif p["tipo"] == "anthropic":
        headers.update({"x-api-key": p["api_key"], "anthropic-version": "2023-06-01"})
        params["limit"] = 100
    else:
        params["key"] = p["api_key"]
        params["pageSize"] = 100
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(url, params=params, headers=headers)
        r.raise_for_status()
        d = r.json()
    voci = d.get("data") or d.get("models") or []
    return sorted({(v.get("id") or v.get("name", "")).removeprefix("models/") for v in voci} - {""})


# ---------------------------------------------------------------- prompt e agente
def prompt_base() -> str:
    try:
        return paths.PROMPT_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "Sei Fabbro, assistente di coding. Rispondi in modo conciso."


def costruisci_prompt() -> str:
    parti = [prompt_base(), "AMBIENTE\n" + contesto.info_ambiente()]
    progetto = contesto.file_contesto()
    if progetto:
        parti.append("ISTRUZIONI DEL PROGETTO (AGENTS.md)\n" + progetto)
    skills = indice_skills()
    if skills:
        parti.append(f"SKILL (usa load_skill per leggerle):\n{skills}")
    rag_idx = contesto.indice_rag()
    if rag_idx:
        parti.append(rag_idx)
    return "\n\n".join(parti)


def aggiorna_agente() -> None:
    """Ricarica tool, skill, contesto e RAG: quelli creati dall'agente valgono subito."""
    tools = permessi.avvolgi(discover_tools())
    agent.tools = {t.name: t for t in tools}
    agent._tool_specs = [t.to_dict() for t in tools]
    agent.system_prompt = costruisci_prompt()


provider_attuale, modello_attuale, sessione_attuale = carica_stato()

agent = Agent(
    crea_client(provider_attuale, modello_attuale),
    tools=discover_tools(),
    system_prompt=costruisci_prompt(),
    max_steps=MAX_PASSI,
    memory=SQLiteMemory(MEMORIA_DB, session_id=sessione_attuale),
)


# ---------------------------------------------------------------- rendering delle card
def _breve(v, n: int = 60) -> str:
    """Valore compatto su una riga: i testi lunghi diventano 'N righe'."""
    if isinstance(v, str):
        righe = v.count("\n") + 1
        if righe > 1 or len(v) > n:
            return f"<{righe} righe, {len(v)} car>" if righe > 1 else v[: n - 1] + "…"
        return v
    if isinstance(v, list):
        return f"<{len(v)} voci>"
    return str(v)


def render_diff(righe: list[str], limite: int = 14) -> Text:
    t = Text()
    for i, r in enumerate(righe[:limite]):
        if i:
            t.append("\n")
        stile = VERDE if r.startswith("+") else ROSSO if r.startswith("-") else DIM
        t.append(r[:120], style=stile)
    if len(righe) > limite:
        t.append(f"\n… +{len(righe) - limite} righe", style=DIM)
    return t


def formatta_tool(c) -> Text:
    """Riga stile Claude Code: ● nome(args), sotto ⎿ esito (e diff per le modifiche)."""
    args = c.arguments
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            args = {"args": args}
    corpo = ", ".join(f"{k}={_breve(v)}" for k, v in args.items()) if isinstance(args, dict) else _breve(args)
    righe = str(c.result).strip().splitlines() or ["(nessun output)"]
    errore = righe[0].lower().startswith(("errore", "error", "interrotto")) or (
        "[exit " in righe[-1] and "[exit 0]" not in righe[-1])
    diff = runtime.DIFFS.get(c.name, []).pop(0) if runtime.DIFFS.get(c.name) else []
    t = Text()
    t.append("● ", style=ROSSO if errore else VERDE)
    t.append(c.name, style=f"bold {TESTO}")
    t.append(f"({corpo})", style=DIM)

    if c.name == "todo_write" and not errore:
        for i, r in enumerate(righe[:14]):
            t.append("\n  ⎿ " if i == 0 else "\n    ", style=DIM)
            stile = VERDE if r.startswith("[x]") else AMBRA if r.startswith("[~]") else TESTO
            t.append(r[:110], style=stile)
        return t

    for i, r in enumerate(righe[:4]):
        t.append("\n  ⎿ " if i == 0 else "\n    ", style=DIM)
        t.append(r[:110], style=ROSSO if errore and i == 0 else DIM)
    if len(righe) > 4:
        t.append(f"\n    … +{len(righe) - 4} righe", style=DIM)
    if diff and not errore:
        t.append("\n")
        t.append_text(render_diff(diff[1:] or diff))
    return t


class Spinner(Static):
    """Spinner animato con tempo trascorso."""
    FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, etichetta: str = "lavoro") -> None:
        super().__init__("", classes="spinner")
        self.etichetta, self.i, self.t0 = etichetta, 0, time.monotonic()

    def on_mount(self) -> None:
        self._tick()
        self.set_interval(0.08, self._tick)

    def _tick(self) -> None:
        self.i += 1
        s = time.monotonic() - self.t0
        self.update(Text(f"{self.FRAMES[self.i % 10]} {self.etichetta}… {s:.1f}s  (Esc per interrompere)", style=ACCENT))


# ---------------------------------------------------------------- app
class Fabbro(FabbroTUI):
    BINDINGS = [("escape", "interrompi", "Interrompi")]
    CSS = FabbroTUI.CSS + """
    .spinner { margin-top: 1; padding-left: 2; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.provider, self.model = provider_attuale, modello_attuale
        self.sessione = sessione_attuale
        self.modello = f"{self.provider}/{self.model}"

    def on_mount(self) -> None:
        permessi.STATO["chiedi"] = lambda n, a, r: self.call_from_thread(self._chiedi, n, a, r)
        self.token = contesto.stima_token(agent.memory)
        self._aggiorna_footer()
        n = len(agent.memory.turns)
        if paths.PRIMO_AVVIO:
            self.run_worker(self._onboarding(), group="wizard")
        elif n:
            self.call_later(self._aggiungi, f"sessione «{self.sessione}» ripresa ({n} messaggi). /clear per ricominciare.", "sistema", False)

    # ---------- permessi ----------
    async def _chiedi(self, nome: str, args: dict, righe: list[str]) -> str:
        titoli = {"bash": "Eseguire questo comando?", "edit_file": "Applicare questa modifica?",
                  "write_file": "Scrivere questo file?", "create_tool": "Creare questo tool?"}
        sempre = f"«{str(args.get('command', '')).split()[0] if str(args.get('command', '')).split() else ''}»" if nome == "bash" else nome
        fut = asyncio.get_running_loop().create_future()
        self.push_screen(Conferma(titoli.get(nome, nome), render_diff(righe, 40), sempre), lambda v: fut.done() or fut.set_result(v or "no"))
        return await fut

    # ---------- interruzione ----------
    def action_interrompi(self) -> None:
        if not self.occupato:
            return
        runtime.uccidi_foreground()
        self.workers.cancel_all()

    # ---------- comandi ----------
    async def _comando(self, riga: str) -> None:
        cmd, _, arg = riga.partition(" ")
        arg = arg.strip()
        if cmd == "/clear":
            agent.memory.clear()
            runtime.TODO.clear()
            self.token = 0
            self._aggiorna_footer()
            return await super()._comando(riga)
        if cmd == "/setup":
            if self.occupato:
                return await self._msg("attendi la fine della risposta")
            self.run_worker(self._setup_provider(), group="wizard")
            return
        if cmd == "/permessi":
            return await self._permessi(arg)
        if cmd == "/rag":
            return await self._rag(arg)
        if cmd == "/compact":
            return await self._compatta_ora()
        if cmd == "/session":
            return await self._sessione_cmd(arg)
        if cmd not in ("/provider", "/model"):
            return await super()._comando(riga)
        if self.occupato:
            await self._aggiungi("attendi la fine della risposta", "sistema", markup=False)
            return
        if cmd == "/provider":
            sub, _, resto = arg.partition(" ")
            if sub == "key":
                await self._chiedi_chiave(resto.strip() or self.provider)
            elif sub == "add":
                self.run_worker(self._nuovo_provider(), group="wizard")
            elif sub in ("rm", "remove"):
                await self._rimuovi_provider(resto.strip())
            elif arg:
                await self._scegli_provider(arg)
            else:
                self.push_screen(
                    Selettore("Provider", list(PROVIDERS) + [AGGIUNGI], self.provider,
                              "/provider rm <nome> rimuove uno aggiunto da te"),
                    self._dopo_menu_provider,
                )
        elif arg:
            await self._scegli_modello(arg)
        else:
            try:
                voci = await elenca_modelli(self.provider)
                nota = ""
            except Exception as e:
                voci, nota = [], f"elenco non disponibile ({type(e).__name__}): scrivi il nome a mano"
            self.push_screen(
                Selettore(f"Modello · {self.provider}", voci, self.model, nota),
                lambda v: self.run_worker(self._scegli_modello(v)) if v else None,
            )

    async def _msg(self, testo: str) -> None:
        await self._aggiungi(testo, "sistema", markup=False)

    async def _permessi(self, arg: str) -> None:
        if arg in permessi.MODI:
            permessi.STATO["modo"] = arg
            permessi.STATO["sempre"].clear()
        elif arg:
            return await self._msg(f"modi: {', '.join(permessi.MODI)}")
        spiega = {"chiedi": "chiede conferma per comandi e modifiche (i comandi di sola lettura passano)",
                  "modifiche": "accetta in automatico le modifiche ai file, chiede per i comandi",
                  "auto": "nessuna conferma (usa con cautela)"}
        m = permessi.STATO["modo"]
        await self._msg(f"permessi: {m} — {spiega[m]}\nusa /permessi chiedi|modifiche|auto")

    async def _rag(self, arg: str) -> None:
        sub, _, resto = arg.partition(" ")
        resto = resto.strip().strip("'\"")
        try:
            if sub == "add" and resto:
                nomi = rag.aggiungi(resto)
                await self._msg(f"RAG: salvati {len(nomi)} documenti ({', '.join(nomi[:6])}{'…' if len(nomi) > 6 else ''})")
            elif sub in ("rm", "remove") and resto:
                await self._msg("RAG: rimosso" if rag.rimuovi(resto) else "RAG: documento non trovato")
            elif sub == "list" or not arg:
                docs = rag.lista()
                await self._msg("RAG: " + (", ".join(f"{d['nome']} ({d['byte'] // 1024 or 1}K)" for d in docs) or "nessun documento") +
                                "\n/rag add <file|cartella> · /rag rm <nome> · /rag list")
            else:
                await self._msg("uso: /rag add <file|cartella> · /rag rm <nome> · /rag list")
        except (OSError, ValueError) as e:
            await self._msg(f"RAG: {e}")

    async def _compatta_ora(self) -> None:
        if self.occupato:
            return await self._msg("attendi la fine della risposta")
        try:
            msg = await contesto.compatta(agent, forza=True)
        except Exception as e:
            msg = f"compattazione fallita: {e}"
        self.token = contesto.stima_token(agent.memory)
        self._aggiorna_footer()
        await self._msg(msg or "niente da compattare")

    async def _sessione_cmd(self, arg: str) -> None:
        sub, _, resto = arg.partition(" ")
        resto = resto.strip()
        if not arg:
            return self._menu_sessioni()
        if sub in ("exit", "leave", "esci"):
            return await self._esci_sessione()
        if sub in ("rm", "delete", "del", "elimina"):
            return await self._chiedi_eliminazione(resto or self.sessione)
        if not re.fullmatch(r"[\w-]{1,30}", arg):
            return await self._msg("nome sessione non valido (lettere, cifre, - e _, max 30)")
        await self._cambia_sessione(arg)

    def _menu_sessioni(self) -> None:
        if self.occupato:
            self.run_worker(self._msg("attendi la fine della risposta"))
            return
        conteggi = {s["session_id"]: s["turns"] for s in agent.memory.list_sessions()}
        conteggi.setdefault(self.sessione, len(agent.memory.turns))
        mappa = {f"{n}  ·  {c} messaggi": n for n, c in sorted(conteggi.items())}
        voci = list(mappa)
        if self.sessione != SESSIONE_DEFAULT:
            voci.append(ESCI_SESSIONE)
        attuale = next((v for v, n in mappa.items() if n == self.sessione), "")

        def scelto(v: str | None) -> None:
            if not v:
                return
            if v == ESCI_SESSIONE:
                self.run_worker(self._esci_sessione())
            elif v in mappa:
                if mappa[v] != self.sessione:
                    self.run_worker(self._cambia_sessione(mappa[v]))
            elif re.fullmatch(r"[\w-]{1,30}", v):          # testo libero = nuova sessione
                self.run_worker(self._cambia_sessione(v))
            else:
                self.run_worker(self._msg("nome sessione non valido"))

        self.push_screen(Selettore(
            "Sessioni", voci, attuale,
            "scrivi un nome nuovo + Invio per crearne una · /session rm [nome] elimina"), scelto)

    async def _esci_sessione(self) -> None:
        if self.sessione == SESSIONE_DEFAULT:
            return await self._msg("sei già nella sessione principale (main)")
        vecchia = self.sessione
        await self._cambia_sessione(SESSIONE_DEFAULT)
        await self._msg(f"uscito da «{vecchia}» (resta salvata: /session {vecchia} per tornarci)")

    async def _chiedi_eliminazione(self, nome: str) -> None:
        if self.occupato:
            return await self._msg("attendi la fine della risposta")
        conteggi = {s["session_id"]: s["turns"] for s in agent.memory.list_sessions()}
        conteggi.setdefault(self.sessione, len(agent.memory.turns))
        if nome not in conteggi:
            return await self._msg(f"sessione «{nome}» non trovata")
        si = "Sì, elimina"
        self.push_screen(
            Selettore(f"Eliminare «{nome}» ({conteggi[nome]} messaggi)? Non si può annullare.", ["No, annulla", si]),
            lambda v: self.run_worker(self._elimina_sessione(nome)) if v == si else None,
        )

    async def _elimina_sessione(self, nome: str) -> None:
        if nome == self.sessione:
            agent.memory.clear()
            runtime.TODO.clear()
            if nome != SESSIONE_DEFAULT:
                await self._cambia_sessione(SESSIONE_DEFAULT)
                return await self._msg(f"sessione «{nome}» eliminata")
            self.token = 0
            await self.action_pulisci()
            self._aggiorna_footer()
            return await self._msg("sessione main svuotata")
        agent.memory.delete_session(nome)
        await self._msg(f"sessione «{nome}» eliminata")

    async def _cambia_sessione(self, nome: str) -> None:
        if self.occupato:
            return await self._msg("attendi la fine della risposta")
        agent.memory = SQLiteMemory(MEMORIA_DB, session_id=nome)
        self.sessione = nome
        salva_stato(self.provider, self.model, nome)
        self.token = contesto.stima_token(agent.memory)
        await self.action_pulisci()
        self._aggiorna_header()
        self._aggiorna_footer()
        await self._msg(f"sessione: {nome} ({len(agent.memory.turns)} messaggi)")

    def _dopo_menu_provider(self, v: str | None) -> None:
        if v == AGGIUNGI:
            self.run_worker(self._nuovo_provider(), group="wizard")
        elif v:
            self.run_worker(self._scegli_provider(v))

    async def _nuovo_provider(self) -> None:
        """Procedura guidata: nome → tipo → URL → chiave → modello. Esc annulla in ogni passo."""
        nome = await self.push_screen_wait(Domanda("Nuovo provider · nome", "es. openrouter, ollama, groq"))
        if nome is None:
            return
        nome = nome.lower()
        if not re.fullmatch(r"[a-z][a-z0-9_-]{1,30}", nome):
            return await self._msg("nome non valido: usa lettere minuscole, cifre, - e _ (2-31 caratteri)")
        if nome in PROVIDERS:
            return await self._msg(f"«{nome}» esiste già (rimuovilo con /provider rm {nome})")
        tipo = await self.push_screen_wait(Selettore(
            "Tipo di API", list(URL_DEFAULT), "openai",
            "openai = qualsiasi servizio compatibile (OpenRouter, Ollama, LM Studio, vLLM, Groq…)"))
        if tipo not in URL_DEFAULT:
            return
        url = await self.push_screen_wait(Domanda(
            "URL base dell'API", "es. http://localhost:11434/v1 per Ollama", default=URL_DEFAULT[tipo]))
        if not url:
            return
        chiave = await self.push_screen_wait(Domanda(
            "Chiave API", "oppure il nome di una variabile d'ambiente (es. GROQ_API_KEY). Vuoto = nessuna chiave",
            segreto=False))
        if chiave is None:
            return
        cfg = {"tipo": tipo, "base_url": url.rstrip("/"), "model": ""}
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", chiave):
            cfg["api_key_env"] = chiave
        else:
            cfg["api_key"] = chiave or "none"
        # registrazione temporanea per interrogare l'elenco dei modelli
        PROVIDERS[nome] = {**cfg, "api_key": cfg.get("api_key") or os.environ.get(cfg.get("api_key_env", ""), "")}
        try:
            try:
                voci, nota = await elenca_modelli(nome), ""
            except Exception as e:
                voci, nota = [], f"elenco non disponibile ({type(e).__name__}): scrivi il nome a mano"
            modello = await self.push_screen_wait(Selettore(f"Modello · {nome}", voci, "", nota))
        finally:
            PROVIDERS.pop(nome, None)
        if not modello:
            return await self._msg("provider non aggiunto")
        cfg["model"] = modello
        config.salva_provider(nome, cfg)
        await self._msg(f"provider «{nome}» salvato in providers.json")
        await self._scegli_provider(nome)

    async def _chiedi_chiave(self, nome: str) -> None:
        """Chiede (e salva) la chiave API di un provider; poi lo attiva."""
        if nome not in PROVIDERS:
            return await self._msg(f"provider sconosciuto: {nome} ({', '.join(PROVIDERS)})")
        env = PROVIDERS[nome].get("api_key_env")
        nota = f"Incolla la chiave" + (f" oppure il nome di una variabile d'ambiente (es. {env})." if env else ".")
        self.push_screen(
            Domanda(f"Chiave API · {nome}", nota, segreto=True),
            lambda v: self.run_worker(self._salva_chiave(nome, v)) if v else None,
        )

    async def _salva_chiave(self, nome: str, valore: str) -> None:
        config.imposta_chiave(nome, valore)
        await self._msg(f"chiave di «{nome}» salvata in providers.json")
        if PROVIDERS[nome]["api_key"]:
            await self._scegli_provider(nome)
        else:
            await self._msg(f"la variabile d'ambiente indicata per «{nome}» non è impostata")

    # ---------- primo avvio / /setup ----------
    async def _onboarding(self) -> None:
        """Animazione di installazione, poi configurazione guidata del provider."""
        passi = [
            ("Creo la cartella globale", str(paths.HOME).replace(str(paths.Path.home()), "~")),
            ("Carico i tool", f"{len(discover_tools())} disponibili"),
            ("Preparo memoria e sessioni", "memoria.db"),
            ("Predispongo skill e RAG", "~/.fabbro/skills · rag"),
            ("Leggo i provider", ", ".join(PROVIDERS)),
        ]
        await self.push_screen_wait(Benvenuto(passi))
        await self._setup_provider(primo=True)

    async def _setup_provider(self, primo: bool = False) -> None:
        """Sceglie e configura un provider (URL/chiave/modello) in modo guidato."""
        descr = {
            "locale": "server locale compatibile OpenAI (Ollama, LM Studio, vLLM…)",
            "openai": "OpenAI", "anthropic": "Anthropic (Claude)", "google": "Google (Gemini)",
        }
        mappa = {f"{n} · {descr.get(n, PROVIDERS[n]['tipo'])}": n for n in PROVIDERS}
        voci = list(mappa) + [AGGIUNGI]
        titolo = "Benvenuto! Scegli il provider da usare" if primo else "Configura un provider"
        scelta = await self.push_screen_wait(Selettore(titolo, voci, "", "Potrai cambiarlo in qualsiasi momento con /provider"))
        if scelta is None:
            if primo:
                salva_stato(self.provider, self.model, self.sessione)
                await self._msg("configurazione rimandata: usa /setup quando vuoi")
            return
        if scelta == AGGIUNGI:
            await self._nuovo_provider()
            salva_stato(self.provider, self.model, self.sessione)
            return
        nome = mappa.get(scelta)
        if nome is None:
            return await self._msg("scelta non valida")
        cfg = PROVIDERS[nome]
        if cfg["tipo"] == "openai" and nome == "locale":
            url = await self.push_screen_wait(Domanda("URL del server", "es. http://localhost:11434/v1", default=cfg["base_url"]))
            if not url:
                return
            config.imposta_campo(nome, base_url=url.rstrip("/"))
        elif not cfg["api_key"]:
            env = cfg.get("api_key_env")
            chiave = await self.push_screen_wait(Domanda(
                f"Chiave API · {nome}",
                "Incolla la chiave" + (f" oppure il nome di una variabile (es. {env})." if env else "."), segreto=True))
            if not chiave:
                return await self._msg("configurazione annullata")
            config.imposta_chiave(nome, chiave)
            if not PROVIDERS[nome]["api_key"]:
                return await self._msg(f"la variabile d'ambiente per «{nome}» non è impostata")
        try:
            voci_m, nota = await elenca_modelli(nome), ""
        except Exception as e:
            voci_m, nota = [], f"elenco non disponibile ({type(e).__name__}): scrivi il nome a mano"
        modello = await self.push_screen_wait(Selettore(f"Modello · {nome}", voci_m, PROVIDERS[nome]["model"], nota))
        self.provider = nome
        self.model = modello or PROVIDERS[nome]["model"]
        await self._applica()
        await self._msg(f"Tutto pronto: {nome}/{self.model}. Scrivi un messaggio o usa /help (puoi rifare questa procedura con /setup).")

    async def _rimuovi_provider(self, nome: str) -> None:
        if not nome:
            return await self._msg("uso: /provider rm <nome>")
        if nome in DEFAULT_PROVIDERS:
            return await self._msg(f"«{nome}» è un provider predefinito e non si rimuove")
        if not config.rimuovi_provider(nome):
            return await self._msg(f"provider «{nome}» non trovato")
        await self._msg(f"provider «{nome}» rimosso")
        if nome == self.provider:
            await self._scegli_provider(PROVIDER_DEFAULT)

    async def _scegli_provider(self, nome: str) -> None:
        if nome not in PROVIDERS:
            await self._msg(f"provider sconosciuto: {nome} ({', '.join(PROVIDERS)})")
            return
        p = PROVIDERS[nome]
        if not p["api_key"]:
            return await self._chiedi_chiave(nome)
        self.provider, self.model = nome, p["model"]
        await self._applica()
        await self._msg(f"provider: {nome} · modello: {self.model} (cambia con /model)")

    async def _scegli_modello(self, nome: str) -> None:
        self.model = nome
        await self._applica()
        await self._msg(f"modello: {nome}")

    async def _applica(self) -> None:
        vecchio = agent.client
        agent.client = crea_client(self.provider, self.model)
        try:
            await vecchio.aclose()
        except Exception:
            pass
        salva_stato(self.provider, self.model, self.sessione)
        self.modello = f"{self.provider}/{self.model}"
        self._aggiorna_footer()

    # ---------- turno dell'agente ----------
    @work(exclusive=True)
    async def elabora(self, testo: str) -> None:
        self.occupato = True
        self._aggiorna_header()
        chat = self.query_one("#chat")
        spin = None

        async def spinner_on(etichetta: str = "lavoro") -> None:
            nonlocal spin
            if spin:
                await spin.remove()
            spin = Spinner(etichetta)
            await chat.mount(spin)
            chat.scroll_end(animate=False)

        async def spinner_off() -> None:
            nonlocal spin
            if spin:
                await spin.remove()
                spin = None

        risposta, buffer = None, ""
        try:
            aggiorna_agente()
            soglia = PROVIDERS[self.provider].get("contesto", contesto.SOGLIA_DEFAULT)
            if contesto.stima_token(agent.memory) >= soglia:
                await spinner_on("compatto la conversazione")
                try:
                    msg = await contesto.compatta(agent, soglia)
                    if msg:
                        await self._msg(msg)
                except Exception as e:
                    await self._msg(f"compattazione fallita: {e}")
            await spinner_on()
            async for ev in agent.astream(testo):
                if ev.type == "tool":
                    await spinner_off()
                    await self._aggiungi(formatta_tool(ev.call), "tool finito", markup=False)
                    risposta, buffer = None, ""
                    await spinner_on()          # riparte per il passo successivo
                elif ev.type == "text":
                    if risposta is None:
                        await spinner_off()
                        risposta = await self._aggiungi("", "agente", markup=False)
                    buffer += ev.text
                    risposta.update(Markdown(buffer))
                    chat.scroll_end(animate=False)
        except asyncio.CancelledError:
            await spinner_off()
            await self._msg("interrotto")
            raise
        except RuntimeError as e:
            extra = " Scrivi «continua» per riprendere." if "passi" in str(e) else ""
            await self._msg(f"errore: {e}.{extra}")
        except Exception as e:
            await self._msg(f"errore: {e}")
        finally:
            await spinner_off()
            self.token = contesto.stima_token(agent.memory)
            self.occupato = False
            self._aggiorna_header()
            self._aggiorna_footer()


def main() -> None:
    import sys
    from fabbro import __version__
    if any(a in ("-v", "--version") for a in sys.argv[1:]):
        print(f"fabbro {__version__}")
        return
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print("fabbro — assistente di coding da terminale\n\nUso: fabbro   (poi /help)\nDati in ~/.fabbro (cambiabile con FABBRO_HOME)")
        return
    Fabbro().run()


if __name__ == "__main__":
    main()
