"""Registry of supported services. Order here = order of the tabs in the UI."""
from .base import Service
from .riot import RiotService

SERVICES: list[Service] = [
    RiotService(),
]

BY_ID: dict[str, Service] = {s.id: s for s in SERVICES}
