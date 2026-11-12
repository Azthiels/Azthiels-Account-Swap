"""config.json: user options. Each service declares its own options as ConfigField entries
(see Service.config_fields); the Options screen lists them all automatically."""
from dataclasses import dataclass, field

from .paths import CONFIG_FILE
from .util import read_json, write_json


@dataclass(frozen=True)
class ConfigField:
    key: str
    label: str
    kind: str = "text"                      # "text" | "path" | "secret"
    filetypes: tuple = field(default=(("All files", "*.*"),))


def load() -> dict:
    return read_json(CONFIG_FILE, {})


def get(key: str, default=None):
    return load().get(key, default)


def set_value(key: str, value) -> None:
    cfg = load()
    cfg[key] = value
    write_json(CONFIG_FILE, cfg)
