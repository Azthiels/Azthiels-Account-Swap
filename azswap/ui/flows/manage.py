"""Flows that only touch saved accounts: rename, delete, ban."""
import asyncio
from datetime import datetime, timedelta

from ...core import state, storage
from ...core.util import fmt_date

PERMA_WORDS = ("PERMA", "PERMANENT", "P")


class ManageFlows:
    def action_rename(self):
        self._start(self.do_rename)

    def action_delete(self):
        self._start(self.do_delete)

    def action_ban(self):
        self._start(self.do_ban)

    async def _remove(self, acc):
        await asyncio.to_thread(storage.delete_account, acc)
        if state.get_active(acc.service_id) == acc.folder:
            state.set_active(acc.service_id, None)

    async def do_rename(self):
        acc = self.current()
        if not acc:
            return
        new = await self.ask("New alias for this account:", acc.alias)
        if not new:
            self.set_status("Cancelled", "warn")
            return
        storage.update_meta(acc, {"alias": new})
        self.set_status(f'Renamed to "{new}"', "ok")

    async def do_delete(self):
        acc = self.current()
        if not acc:
            return
        if not await self.confirm(f'Delete "{acc.alias}" from this program?\n(does not log you out)'):
            self.set_status("Cancelled", "warn")
            return
        await self._remove(acc)
        self.set_status("Account deleted", "ok")

    async def do_ban(self):
        acc = self.current()
        if not acc:
            self.set_status("No account selected", "warn")
            return

        if acc.banned_until:
            if await self.confirm(f'"{acc.alias}" is marked banned.\nClear that mark?'):
                storage.update_meta(acc, remove=("banned_until",))
                self.set_status("Ban mark cleared", "ok")
            else:
                self.set_status("Cancelled", "warn")
            return

        txt = await self.ask(
            f'Mark "{acc.alias}" as banned.\n'
            "Type PERMA to remove it from the list, or a number of days for a temporary ban:"
        )
        if not txt:
            self.set_status("Cancelled", "warn")
            return
        if txt.strip().upper() in PERMA_WORDS:
            if not await self.confirm(f'Permanently remove "{acc.alias}" from the list?'):
                self.set_status("Cancelled", "warn")
                return
            await self._remove(acc)
            self.set_status("Account removed (permanent ban)", "ok")
            return
        try:
            days = float(txt)
            if days <= 0:
                raise ValueError
        except ValueError:
            self.set_status("Not a valid number of days - cancelled", "err")
            return
        until = (datetime.now() + timedelta(days=days)).isoformat()
        storage.update_meta(acc, {"banned_until": until})
        self.set_status(f"Marked banned until {fmt_date(until)}", "warn")
