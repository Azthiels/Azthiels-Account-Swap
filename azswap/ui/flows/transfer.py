"""Flows that move accounts in/out of the program: export .auc, import .auc, plain backup zip."""
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from ...core import auc, storage
from ...core.filepicker import pick_file
from ...core.paths import DATA_DIR
from ...core.timesync import get_trusted_now
from ...core.util import fmt_date, safe_name
from ...services import BY_ID

MIN_PASSWORD = 4
MISSING_CRYPTO = "Missing dependency: pip install cryptography"


class TransferFlows:
    def action_export(self):
        self._start(self.do_export)

    def action_export_all(self):
        self._start(self.do_export_all)

    def action_import(self):
        self._start(self.do_import)

    async def do_export_all(self):
        if not storage.has_any_account():
            self.set_status("Nothing to back up", "warn")
            return
        out = DATA_DIR / f"backup_all_{datetime.now():%Y%m%d_%H%M%S}.zip"
        await asyncio.to_thread(storage.backup_all, out)
        self.set_status(f"Backup created: {out.name} (NOT encrypted - do not share it)", "warn")

    async def do_export(self):
        if not auc.HAVE_CRYPTO:
            self.set_status(MISSING_CRYPTO, "err")
            return
        acc = self.current()
        if not acc:
            self.set_status("No account selected", "warn")
            return
        pw = await self.ask(f'Password to encrypt "{acc.alias}" (min {MIN_PASSWORD} chars):', password=True)
        if not pw:
            self.set_status("Cancelled", "warn")
            return
        if len(pw) < MIN_PASSWORD:
            self.set_status(f"Password too short - use at least {MIN_PASSWORD} characters", "err")
            return
        if await self.ask("Confirm the password:", password=True) != pw:
            self.set_status("Passwords did not match - cancelled", "err")
            return

        expires_at = None
        exp_txt = await self.ask("Expires after how many minutes? (blank = never expires):")
        if exp_txt:
            try:
                minutes = float(exp_txt)
                if minutes <= 0:
                    raise ValueError
            except ValueError:
                self.set_status("Not a valid number of minutes - cancelled", "err")
                return
            self.set_status("Checking the time online…", "busy")
            now = await asyncio.to_thread(get_trusted_now)
            if now is None:
                self.set_status("Could not reach the internet to timestamp the expiration - cancelled", "err")
                return
            expires_at = (now + timedelta(minutes=minutes)).isoformat()

        payload = {"service": acc.service_id, "alias": acc.alias, "blob_b64": auc.b64(acc.read_session())}
        if expires_at:
            payload["expires_at"] = expires_at
        out = DATA_DIR / f"{safe_name(acc.alias)}_{datetime.now():%Y%m%d_%H%M%S}{auc.AUC_EXT}"
        await asyncio.to_thread(auc.encrypt, payload, out, pw)
        suffix = f" (expires {fmt_date(expires_at)})" if expires_at else ""
        self.set_status(f"Exported: {out.name}{suffix}", "ok")

    async def do_import(self):
        if not auc.HAVE_CRYPTO:
            self.set_status(MISSING_CRYPTO, "err")
            return
        self.set_status("Opening file picker…", "busy")
        filetypes = [("Azthiels Universal Credentials", f"*{auc.AUC_EXT}"), ("All files", "*.*")]
        path = await asyncio.to_thread(pick_file, filetypes, f"Select a {auc.AUC_EXT} file to import")
        if not path:
            self.set_status("Cancelled", "warn")
            return
        src = Path(path)
        pw = await self.ask(f'Password for "{src.name}":', password=True)
        if not pw:
            self.set_status("Cancelled", "warn")
            return
        try:
            payload = await asyncio.to_thread(auc.decrypt, src, pw)
        except ValueError as e:
            self.set_status(str(e), "err")
            return

        svc = BY_ID.get(payload["service"])
        if svc is None:
            self.set_status(f"This program doesn't support that service yet: {payload['service']!r}", "err")
            return

        expires_at = payload.get("expires_at")
        if expires_at:
            self.set_status("Checking the time online…", "busy")
            now = await asyncio.to_thread(get_trusted_now)
            if now is None:
                self.set_status("Could not reach the internet to verify the expiration - import refused", "err")
                return
            if now >= datetime.fromisoformat(expires_at):
                self.set_status("This file has expired", "err")
                return

        alias = payload["alias"]
        folder = safe_name(alias)
        blob = auc.unb64(payload["blob_b64"])
        await asyncio.to_thread(storage.save_account, svc.id, folder, alias, blob, expires_at)
        self.set_status(f"Imported: {alias} ({svc.name})", "ok")
        self.refresh_list(select=folder if svc.id == self.service.id else None)
