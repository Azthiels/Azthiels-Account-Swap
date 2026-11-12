"""state.json: {"active": {"<service_id>": "<folder>"}, "last_service": "<service_id>"}.

Always read from disk, so the UI and the background expiry sweep never hold stale copies.
"""
from .paths import STATE_FILE
from .util import read_json, write_json


def _load() -> dict:
    state = read_json(STATE_FILE, {})
    active = state.get("active")
    if not isinstance(active, dict):
        active = {}
    state["active"] = {str(k): v for k, v in active.items() if isinstance(v, str)}
    return state


def get_active(service_id: str) -> str | None:
    return _load()["active"].get(service_id)


def set_active(service_id: str, folder: str | None) -> None:
    state = _load()
    if folder is None:
        state["active"].pop(service_id, None)
    else:
        state["active"][service_id] = folder
    write_json(STATE_FILE, state)


def get_last_service() -> str | None:
    value = _load().get("last_service")
    return value if isinstance(value, str) else None


def set_last_service(service_id: str) -> None:
    state = _load()
    state["last_service"] = service_id
    write_json(STATE_FILE, state)
