# 🔨 Fabbro

### Your AI. Your Terminal. Your Rules.

**Fabbro** è un assistente di coding che vive nel terminale: legge il tuo progetto, modifica i file, esegue comandi e ricorda le conversazioni, con un'interfaccia pixel-art minimale. Funziona con modelli locali (Ollama, LM Studio, vLLM…) e con OpenAI, Anthropic e Google.

Non un semplice chatbot: un agente che lavora nel tuo ambiente, sotto il tuo controllo.

---

<div align="center">

<img src="./assets/logo.png" alt="Fabbro Logo" width="200">

**LOCAL AI • TERMINAL NATIVE • DEVELOPER FOCUSED**

</div>

## ✨ Features

- **Tool di coding** — legge, cerca, scrive e modifica file, esegue comandi (anche in background), scarica pagine web.
- **Conferme con diff** — prima di modificare file o lanciare comandi vedi un'anteprima e decidi; Esc interrompe l'agente in qualsiasi momento.
- **Più provider** — locale (compatibile OpenAI), OpenAI, Anthropic, Google, più quelli che aggiungi tu.
- **Sessioni e memoria** — le conversazioni sono salvate su disco, con riassunto automatico quando diventano lunghe.
- **RAG locale** — salvi i tuoi file `.md` e l'agente li consulta quando servono.
- **Si estende da solo** — può creare nuovi tool e skill, salvati globalmente e validi in ogni progetto.
- **Contesto del progetto** — legge `AGENTS.md`/`CLAUDE.md` e conosce ramo git e file modificati.
- **Configurazione guidata** — al primo avvio un'animazione di installazione e la scelta del provider.

## 📦 Installation

Requisiti: Python 3.10+.

```bash
pipx install git+https://github.com/ChillatoOfficial/fabbro.git    # consigliato
# oppure: pip install git+https://github.com/ChillatoOfficial/fabbro.git
```

Da sorgente, per sviluppare:

```bash
git clone https://github.com/ChillatoOfficial/fabbro.git && cd fabbro
pip install -e .
```

Aggiornare: `pipx upgrade fabbro` · Rimuovere: `pipx uninstall fabbro`

> `fabbro` dipende da [`agentecore`](https://github.com/ChillatoOfficial/agentecore), scaricato da GitHub durante l'installazione.

## 🚀 Quick start

```bash
fabbro              # avvia nella cartella corrente
fabbro --version
fabbro --help
```

Al primo avvio parte la procedura guidata: scegli il provider, inserisci URL o chiave API, scegli il modello. Puoi rifarla quando vuoi con `/setup`.

Poi scrivi come a una persona:

```text
› spiegami come funziona il modulo di autenticazione
› aggiungi un test per la funzione parse_date e fallo girare
› crea una skill per fare code review
```

## 🖥️ Preview

```text
      ▄█▄
    ███████          Fabbro
    █ ▀ █            locale/llama3.1
    █   █            ~/progetti/mio-progetto
  ▄███████▄
                     /help comandi · /model · /provider
```

## 🎮 Commands

| Comando | Cosa fa |
|---|---|
| `/help` | Mostra l'elenco dei comandi |
| `/setup` | Configurazione guidata del provider (scelta, URL/chiave, modello) |
| `/provider` | Menu dei provider disponibili |
| `/provider <nome>` | Passa a quel provider (se manca la chiave, la chiede) |
| `/provider add` | Aggiunge un provider: nome → tipo → URL → chiave → modello |
| `/provider rm <nome>` | Rimuove un provider aggiunto da te (quelli predefiniti restano) |
| `/provider key [nome]` | Imposta o cambia la chiave API; senza nome, quella del provider attivo |
| `/model` | Menu dei modelli del provider attivo (filtro integrato) |
| `/model <nome>` | Imposta direttamente un modello, anche se non in elenco |
| `/session` | Menu delle sessioni; scrivendo un nome nuovo ne crea una |
| `/session <nome>` | Passa a una sessione, creandola se non esiste |
| `/session exit` | Esce dalla sessione e torna a `main` (resta salvata) |
| `/session rm [nome]` | Elimina una sessione, con conferma; senza nome, quella corrente |
| `/permessi` | Mostra il livello di conferma attuale |
| `/permessi chiedi` | Chiede conferma per comandi e modifiche (i comandi di sola lettura passano) |
| `/permessi modifiche` | Accetta in automatico le modifiche ai file, chiede per i comandi |
| `/permessi auto` | Nessuna conferma (da usare con cautela) |
| `/rag add <percorso>` | Salva un file `.md`/`.txt` o tutti quelli di una cartella |
| `/rag list` | Elenca i documenti salvati |
| `/rag rm <nome>` | Rimuove un documento dalla base di conoscenza |
| `/compact` | Riassume la conversazione per liberare contesto |
| `/clear` | Cancella la chat e azzera la memoria della sessione corrente |
| `/thinking basso\|medio\|alto` | Imposta l'etichetta mostrata nel footer (non cambia ancora il comportamento del modello) |
| `/quit` | Esce |

### Scorciatoie

| Tasto | Azione |
|---|---|
| `Esc` | Interrompe l'agente (ferma anche un comando in esecuzione) |
| `Ctrl+L` | Pulisce lo schermo, senza toccare la memoria |
| `Ctrl+C` | Esce |
| `↑` `↓` `Invio` | Navigano i menu; nei menu `y` `a` `n` rispondono alle conferme |
| Click sull'omino | Lo fa salutare 👋 |

## 🧰 Tools

Gli strumenti che l'agente può usare da solo:

| Tool | Descrizione |
|---|---|
| `read_file` | Legge un file con numeri di riga (`offset` e `limit`) |
| `write_file` | Crea o sovrascrive un file |
| `edit_file` | Sostituisce testo esatto in un file (richiede di averlo letto prima) |
| `list_dir` | Elenca una cartella, con profondità regolabile |
| `glob_files` | Trova file per pattern (`**/*.py`) |
| `grep` | Cerca una regex nel contenuto dei file |
| `bash` | Esegue comandi shell, anche in background |
| `bash_output` / `bash_kill` | Leggono l'output o fermano un processo in background |
| `web_fetch` | Scarica una pagina web e restituisce il testo |
| `todo_write` | Tiene la lista dei compiti di un lavoro a più passi |
| `rag_search` / `rag_add` / `rag_list` / `rag_remove` | Consultano e gestiscono i documenti del RAG |
| `create_tool` | Crea un nuovo tool Python globale |
| `create_skill` / `load_skill` | Salvano e leggono istruzioni riutilizzabili |

`bash`, `write_file`, `edit_file` e `create_tool` passano dalle conferme (vedi `/permessi`).

## 🧠 Provider

| Provider | Tipo | Chiave |
|---|---|---|
| `locale` | API compatibile OpenAI (Ollama, LM Studio, vLLM…) | non necessaria |
| `openai` | OpenAI | `OPENAI_API_KEY` o inserita con `/provider key` |
| `anthropic` | Anthropic | `ANTHROPIC_API_KEY` o inserita con `/provider key` |
| `google` | Google Gemini | `GOOGLE_API_KEY` o inserita con `/provider key` |

Con `/provider add` aggiungi qualsiasi altro servizio compatibile (OpenRouter, Groq…). La chiave può essere scritta direttamente oppure indicata come nome di una variabile d'ambiente.

## 📁 Dati e configurazione

Tutto sta in `~/.fabbro` (cambiabile con la variabile `FABBRO_HOME`):

```text
~/.fabbro/
  providers.json   provider, URL e chiavi (permessi 600)
  state.json       ultimo provider, modello e sessione
  prompt.txt       system prompt, modificabile
  AGENTS.md        istruzioni valide in ogni progetto (opzionale)
  memoria.db       sessioni e cronologia
  tools/           tool creati dall'agente o da te
  skills/          skill in markdown
  rag/             documenti salvati con /rag
```

In un progetto puoi aggiungere un `AGENTS.md` (o `CLAUDE.md`) con convenzioni e comandi di test: Fabbro lo legge a ogni messaggio.

### Aggiungere un tool a mano

Un file `.py` in `~/.fabbro/tools/` (o in `fabbro/tools/` per un tool integrato):

```python
from agentecore import tool

@tool
def saluta(nome: str) -> str:
    """Saluta una persona.

    Args:
        nome: chi salutare
    """
    return f"ciao {nome}"
```

I tool vengono ricaricati a ogni messaggio, senza riavviare.

## 🗂️ Project structure

```text
main.py                  punto di ingresso (python main.py)
fabbro/
  app.py                 TUI, comandi e ciclo dell'agente
  config.py              provider (default + providers.json)
  paths.py               cartella globale ~/.fabbro
  core/
    permessi.py          conferme e anteprima diff
    contesto.py          contesto nel prompt e compattazione
    rag.py               base di conoscenza locale (BM25)
    runtime.py           stato condiviso tra tool e UI
  tools/                 tool integrati
  ui/                    logo, schermata di benvenuto, menu
  prompts/system.txt     prompt di default
tests/                   python -m unittest discover -s tests -t .
```

## 🛣️ Roadmap

- [x] Tool system e integrazione con il filesystem
- [x] Esecuzione di comandi, anche in background
- [x] Gestione dei provider e dei modelli
- [x] Sessioni e memoria persistente
- [x] Conferme con anteprima del diff
- [x] RAG locale su file markdown
- [x] Tool e skill creati dall'agente
- [x] Interfaccia animata e configurazione guidata
- [ ] `/undo` per annullare le modifiche dell'ultimo turno
- [ ] Sandbox per i comandi
- [ ] RAG semantico (embedding)
- [ ] Sub-agenti e compiti in parallelo
- [ ] Browser automation
- [ ] Effetto reale di `/thinking` sul modello

## 🛠️ Philosophy

> The terminal is not just a place to execute commands. It's a place to build things.

Un agente AI dovrebbe essere accessibile, estensibile e sotto il controllo dello sviluppatore. Niente interfacce inutilmente complicate: solo terminale, intelligenza artificiale e strumenti.

## 🤝 Contributing

I contributi sono benvenuti!

1. Forka il repository.
2. Crea un branch per le tue modifiche.
3. Esegui i test: `python -m unittest discover -s tests -t .`
4. Apri una Pull Request.

## 📄 License

La licenza verrà definita prima della prima release pubblica.

---

<div align="center">

### 🔨 FABBRO

**Forged for developers. Built for intelligence.**

*Made with passion and code.*

</div>
