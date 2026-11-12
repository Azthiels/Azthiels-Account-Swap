"""Logging setup. Every module uses `logging.getLogger(__name__)`, so each line in debug.log
says which module wrote it (e.g. `azswap.services.riot`) - that's how you find what broke."""
import logging
from logging.handlers import RotatingFileHandler

from .paths import DEBUG_LOG

_configured = False


def setup_logging(level: int = logging.DEBUG) -> None:
    global _configured
    if _configured:
        return
    root = logging.getLogger("azswap")
    root.setLevel(level)
    root.propagate = False
    try:
        DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(DEBUG_LOG, maxBytes=512_000, backupCount=2, encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)-5s %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        ))
        root.addHandler(handler)
    except OSError:
        root.addHandler(logging.NullHandler())
    _configured = True
