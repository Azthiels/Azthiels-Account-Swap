"""Small pure helpers: JSON files, dates, file-name sanitising."""
import json
import logging
import os
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)


def read_json(path: Path, default):
    """Read JSON; on a missing/corrupt file or an unexpected top-level type, return a copy of `default`."""
    fallback = default.copy() if isinstance(default, (dict, list)) else default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return fallback
    except Exception as e:  # noqa: BLE001
        log.warning("could not read %s: %s: %s", path, type(e).__name__, e)
        return fallback
    if isinstance(default, dict) and not isinstance(data, dict):
        log.warning("%s contained %s, expected an object; using defaults", path, type(data).__name__)
        return fallback
    if isinstance(default, list) and not isinstance(data, list):
        log.warning("%s contained %s, expected a list; using defaults", path, type(data).__name__)
        return fallback
    return data


def write_json(path: Path, data) -> None:
    """Write atomically (temp file + replace) so a crash never leaves half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def fmt_date(iso: str | None) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%Y-%m-%d %H:%M")
    except Exception:  # noqa: BLE001
        return "-"


def safe_name(name: str) -> str:
    """Turn an alias into a valid Windows folder name."""
    bad = '<>:"/\\|?*'
    return "".join("_" if c in bad else c for c in (name or "")).strip().rstrip(".") or "account"
