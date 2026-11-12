"""Flows that touch the game's live session: save, update, switch, new, logout."""
import asyncio
import logging

from ...core import state, storage
from ...core.processes import kill_processes
from ...core.util import fmt_date, safe_name

log = logging.getLogger(__name__)

KILL_FAILED = "Could not close every process (try running as admin)"


class SessionFlows:
    def action_save(self):
        self._start(self.do_save)

    def action_update(self):
        self._start(self.do_update)

    def action_new(self):
        self._start(self.do_new)

    def action_logout(self):
        self._start(self.do_logout)

    async def do_save(self):
        svc = self.service
        alias = await asyncio.to_thread(svc.get_active_id)
        if not alias:
            alias = await self.ask(f"Alias for this {svc.name} account (e.g. Name#TAG or a nickname):")
            if not alias:
                self.set_status("Cancelled", "warn")
                return
        if not await asyncio.to_thread(svc.has_session):
            self.set_status(f"No {svc.name} session found. Log in and retry (see debug.log).", "err")
            return
        blob = await asyncio.to_thread(svc.read_session)
        if not blob:
            self.set_status("Could not read the session data", "err")
            return
        folder = safe_name(alias)
        await asyncio.to_thread(storage.save_account, svc.id, folder, alias, blob)
        self.set_active(folder)
        self.set_status(f"Account saved: {alias}", "ok")
        self.refresh_list(select=folder)

    async def do_update(self):
        svc = self.service
        acc = self.current()
        if not acc:
            self.set_status("No account selected", "warn")
            return
        if not await asyncio.to_thread(svc.has_session):
            self.set_status(f"No live {svc.name} session to update from", "err")
            return
        blob = await asyncio.to_thread(svc.read_session)
        if not blob:
            self.set_status("Could not read the session data", "err")
            return
        await asyncio.to_thread(storage.save_account, svc.id, acc.folder, acc.alias, blob)
        self.set_status(f"Updated: {acc.alias}", "ok")

    @staticmethod
    def _refresh_active_if_verified(svc, active_folder):
        """Before switching away, re-save the active account's session (tokens get refreshed while
        you play) - but only if the service confirms it's really still that account."""
        if not active_folder:
            return
        try:
            alias = svc.get_active_id()
            if alias and safe_name(alias) == active_folder:
                blob = svc.read_session()
                acc = storage.get_account(svc.id, active_folder)
                if blob and acc:
                    storage.save_account(svc.id, active_folder, acc.alias, blob)
        except Exception:  # noqa: BLE001
            log.exception("could not refresh the active account before switching")

    async def do_switch(self):
        svc = self.service
        acc = self.current()
        if not acc:
            return
        if not acc.session_path.exists():
            self.set_status("That account's session data is missing", "err")
            return
        self.set_status(f"Closing {svc.name} and saving the current session…", "busy")
        await asyncio.to_thread(self._refresh_active_if_verified, svc, state.get_active(svc.id))
        if not await asyncio.to_thread(kill_processes, svc.processes):
            self.set_status(KILL_FAILED, "err")
            return
        await asyncio.to_thread(svc.write_session, acc.read_session())
        self.set_active(acc.folder)
        await asyncio.to_thread(svc.launch)
        if acc.banned_until:
            self.set_status(f"Active account: {acc.alias} - ⚠ marked banned until {fmt_date(acc.banned_until)}", "warn")
        else:
            self.set_status(f"Active account: {acc.alias}", "ok")

    async def do_new(self):
        svc = self.service
        self.set_status(f"Closing {svc.name} and clearing the current session…", "busy")
        if not await asyncio.to_thread(kill_processes, svc.processes):
            self.set_status(KILL_FAILED, "err")
            return
        await asyncio.to_thread(svc.clear_session)
        self.set_active(None)
        await asyncio.to_thread(svc.launch)
        self.set_status(f"{svc.name} opened logged out: sign in, then press S", "warn")

    async def do_logout(self):
        svc = self.service
        if not await self.confirm(f"Close {svc.name} and clear the current session?\n(saved accounts are not touched)"):
            self.set_status("Cancelled", "warn")
            return
        if not await asyncio.to_thread(kill_processes, svc.processes):
            self.set_status(KILL_FAILED, "err")
            return
        await asyncio.to_thread(svc.clear_session)
        self.set_active(None)
        self.set_status("Logged out", "ok")
