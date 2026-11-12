"""What every game/service has to provide. To add a new game: subclass Service in its own file
(see riot.py) and add an instance to SERVICES in services/__init__.py. Nothing else changes."""
from ..core.config import ConfigField
from ..core.storage import Account


class Service:
    id: str = ""                              # folder name under Accounts/, stored in .auc files
    name: str = ""                            # shown in the tab bar
    processes: list[str] = []                 # closed before swapping sessions
    config_fields: list[ConfigField] = []     # shown in the Options screen

    def get_active_id(self) -> str | None:
        """Alias of the account that's logged in right now (e.g. "Name#TAG"), or None if the
        service can't tell. When None, the user types the alias by hand on Save."""
        return None

    def has_session(self) -> bool:
        raise NotImplementedError

    def read_session(self) -> bytes | None:
        raise NotImplementedError

    def write_session(self, blob: bytes) -> None:
        raise NotImplementedError

    def clear_session(self) -> None:
        raise NotImplementedError

    def launch(self) -> None:
        raise NotImplementedError

    def is_busy(self, account: Account) -> bool:
        """True = don't interrupt now (e.g. a match in progress). Used by the expiry sweep."""
        return False

    def diagnose(self) -> list[tuple[str, bool, str]]:
        """Checks for `--doctor`: (what, ok, detail)."""
        return []
