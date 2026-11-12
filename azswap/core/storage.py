"""Saved accounts on disk: Accounts/<service_id>/<folder>/{session.bin, meta.json}.

meta.json keys: alias, saved_at, updated_at, and optionally banned_until / expires_at.
"""
import logging
import shutil
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .paths import ACCOUNTS_DIR
from .util import now_iso, read_json, write_json

log = logging.getLogger(__name__)

SESSION_FILE = "session.bin"
META_FILE = "meta.json"


@dataclass
class Account:
    service_id: str
    folder: str
    meta: dict = field(default_factory=dict)

    @property
    def dir(self) -> Path:
        return ACCOUNTS_DIR / self.service_id / self.folder

    @property
    def session_path(self) -> Path:
        return self.dir / SESSION_FILE

    @property
    def meta_path(self) -> Path:
        return self.dir / META_FILE

    @property
    def alias(self) -> str:
        return self.meta.get("alias") or self.folder

    @property
    def banned_until(self) -> str | None:
        return self.meta.get("banned_until")

    @property
    def expires_at(self) -> str | None:
        return self.meta.get("expires_at")

    def read_session(self) -> bytes:
        return self.session_path.read_bytes()


def service_dir(service_id: str) -> Path:
    return ACCOUNTS_DIR / service_id


def _clear_finished_ban(acc: Account) -> None:
    until = acc.banned_until
    if not until:
        return
    try:
        if datetime.fromisoformat(until) <= datetime.now():
            update_meta(acc, remove=("banned_until",))
            log.info("ban ended for %s/%s", acc.service_id, acc.folder)
    except ValueError:
        pass


def list_accounts(service_id: str) -> list[Account]:
    """Saved accounts for a service; banned ones last, then by alias."""
    out = []
    d = service_dir(service_id)
    if d.exists():
        for f in d.iterdir():
            if f.is_dir() and (f / SESSION_FILE).exists():
                acc = Account(service_id, f.name, read_json(f / META_FILE, {}))
                _clear_finished_ban(acc)
                out.append(acc)
    out.sort(key=lambda a: (bool(a.banned_until), a.alias.lower()))
    return out


def get_account(service_id: str, folder: str) -> Account | None:
    d = service_dir(service_id) / folder
    if not (d / SESSION_FILE).exists():
        return None
    return Account(service_id, folder, read_json(d / META_FILE, {}))


def save_account(service_id: str, folder: str, alias: str, blob: bytes, expires_at: str | None = None) -> Account:
    acc = Account(service_id, folder)
    acc.dir.mkdir(parents=True, exist_ok=True)
    acc.session_path.write_bytes(blob)
    meta = read_json(acc.meta_path, {})
    meta.setdefault("saved_at", now_iso())
    meta["alias"] = alias
    meta["updated_at"] = now_iso()
    if expires_at is not None:
        meta["expires_at"] = expires_at
    write_json(acc.meta_path, meta)
    acc.meta = meta
    log.info("saved %s/%s (%d bytes)", service_id, folder, len(blob))
    return acc


def update_meta(acc: Account, set_: dict | None = None, remove: tuple = ()) -> None:
    meta = read_json(acc.meta_path, {})
    meta.update(set_ or {})
    for key in remove:
        meta.pop(key, None)
    write_json(acc.meta_path, meta)
    acc.meta = meta


def delete_account(acc: Account) -> None:
    shutil.rmtree(acc.dir, ignore_errors=True)
    log.info("deleted %s/%s", acc.service_id, acc.folder)


def has_any_account() -> bool:
    return ACCOUNTS_DIR.exists() and any(ACCOUNTS_DIR.rglob(SESSION_FILE))


def backup_all(out: Path) -> None:
    """Plain (NOT encrypted) zip of every saved account."""
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in ACCOUNTS_DIR.rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(ACCOUNTS_DIR))
