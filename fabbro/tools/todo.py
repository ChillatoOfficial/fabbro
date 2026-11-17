from fabbro.core import runtime
from agentecore import tool


@tool
def todo_write(todos: list[str]) -> str:
    """Aggiorna la lista dei compiti del lavoro in corso (sostituisce quella precedente).

    Usala per compiti a più passi: scrivi il piano all'inizio e aggiornala man mano.
    Ogni voce inizia con lo stato: '[ ] ' da fare, '[~] ' in corso, '[x] ' fatto.

    Args:
        todos: elenco completo e aggiornato delle voci
    """
    runtime.TODO[:] = [t.strip() for t in todos if t.strip()]
    if not runtime.TODO:
        return "lista vuota"
    return "\n".join(runtime.TODO)
