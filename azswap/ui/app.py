"""Main window: banner, service tabs, account list, details, status bar.

The key actions themselves live in ui/flows/ (one file per group); this file only has the layout,
the list/details rendering and the shared plumbing the flows use (ask, confirm, set_status...).
"""
import asyncio
import logging

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from .. import APP_NAME
from ..core import expiry, state, storage
from ..core.paths import ACCOUNTS_DIR
from ..core.storage import Account
from ..core.timesync import get_trusted_now
from ..core.util import fmt_date
from ..services import BY_ID, SERVICES
from ..services.base import Service
from . import theme
from .banner import build_banner
from .dialogs import Ask, Confirm
from .flows.manage import ManageFlows
from .flows.session import SessionFlows
from .flows.transfer import TransferFlows
from .options import OptionsScreen

log = logging.getLogger(__name__)

SWEEP_SECONDS = 20.0


class AccountSwap(SessionFlows, ManageFlows, TransferFlows, App):
    TITLE = APP_NAME
    CSS = theme.APP_CSS

    BINDINGS = [
        Binding("tab", "next_service", "Next game", priority=True),
        Binding("shift+tab", "prev_service", "Prev game", priority=True),
        Binding("slash", "search", "Search"),
        Binding("s", "save", "Save"),
        Binding("u", "update", "Update"),
        Binding("n", "new", "New"),
        Binding("r", "rename", "Rename"),
        Binding("d", "delete", "Delete"),
        Binding("b", "ban", "Ban"),
        Binding("e", "export", "Export"),
        Binding("a", "export_all", "Backup all"),
        Binding("i", "import", "Import"),
        Binding("l", "logout", "Logout"),
        Binding("o", "options", "Options"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, admin: bool = True):
        super().__init__()
        self.admin = admin
        last = state.get_last_service()
        ids = [s.id for s in SERVICES]
        self.service_idx = ids.index(last) if last in ids else 0
        self.accounts: list[Account] = []
        self.search_query = ""
        self.busy = False
        self._sweeping = False

    @property
    def service(self) -> Service:
        return SERVICES[self.service_idx]

    # ---- layout --------------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Static(build_banner(), id="banner")
        yield Static(id="tabs")
        yield Input(placeholder="Search accounts…", id="search")
        with Horizontal(id="main"):
            yield OptionList(id="accounts")
            with Vertical(id="details"):
                yield Static(id="details_text")
        with Vertical(id="statusbox"):
            yield Static(id="status")
            yield Static(Text(theme.KEY_HELP, style=theme.MUTED))

    def on_mount(self):
        self.query_one("#accounts").border_title = "Accounts"
        self.query_one("#details").border_title = "Details"
        ACCOUNTS_DIR.mkdir(parents=True, exist_ok=True)
        if self.admin:
            self.set_status("Ready", "ok")
        else:
            self.set_status("Running without admin rights - closing sessions may fail", "warn")
        self.render_tabs()
        self.refresh_list()
        self.account_list.focus()
        self.set_interval(SWEEP_SECONDS, self.run_expiry_sweep)

    @property
    def account_list(self) -> OptionList:
        return self.query_one("#accounts", OptionList)

    def render_tabs(self):
        t = Text()
        for i, svc in enumerate(SERVICES):
            style = f"bold {theme.BG} on {theme.ACCENT}" if i == self.service_idx else theme.MUTED
            t.append(f" {svc.name} ", style=style)
            t.append(" ")
        self.query_one("#tabs", Static).update(t)

    def set_status(self, msg: str, kind: str = "ok"):
        color = theme.STATUS_COLORS[kind]
        self.query_one("#status", Static).update(Text.assemble(("● ", color), (msg, color)))
        log.info("status[%s]: %s", kind, msg)

    # ---- list + details ---------------------------------------------------------
    def current(self) -> Account | None:
        i = self.account_list.highlighted
        if i is None or i >= len(self.accounts):
            return None
        return self.accounts[i]

    def refresh_list(self, select: str | None = None):
        all_accounts = storage.list_accounts(self.service.id)
        q = self.search_query.strip().lower()
        self.accounts = [a for a in all_accounts if q in a.alias.lower()] if q else all_accounts
        active = state.get_active(self.service.id)
        ol = self.account_list
        prev = select or getattr(self.current(), "folder", None)
        ol.clear_options()
        idx = 0
        for n, acc in enumerate(self.accounts):
            if acc.banned_until:
                label = Text.assemble(
                    ("🚫 ", theme.BANNED), (acc.alias, f"{theme.BANNED} dim"),
                    (f"  (banned until {fmt_date(acc.banned_until)})", f"dim {theme.BANNED}"),
                )
            else:
                mark = "● " if acc.folder == active else "  "
                label = Text.assemble((mark, theme.ACTIVE), acc.alias)
            ol.add_option(Option(label, id=acc.folder))
            if acc.folder == prev:
                idx = n
        if self.accounts:
            ol.highlighted = idx
        self.render_details()

    def render_details(self):
        box = self.query_one("#details_text", Static)
        acc = self.current()
        if not acc:
            box.update(Text.assemble(
                ("*  ", theme.MUTED), (f"No {self.service.name} accounts saved yet.\n\n", "bold"),
                ("Log into it, then press [S] to save.", theme.FAINT),
            ))
            return
        t = Text()
        if acc.banned_until:
            t.append(f"⚠ BANNED until {fmt_date(acc.banned_until)}\n\n", style=f"bold {theme.BANNED}")
        is_active = acc.folder == state.get_active(self.service.id)
        size = acc.session_path.stat().st_size if acc.session_path.exists() else None
        rows = [
            ("Alias", acc.alias),
            ("Saved", fmt_date(acc.meta.get("saved_at"))),
            ("Updated", fmt_date(acc.meta.get("updated_at"))),
            ("Session", f"{size} bytes" if size is not None else "missing"),
            ("Expires", fmt_date(acc.expires_at) if acc.expires_at else "never"),
            ("Status", "ACTIVE" if is_active else "saved"),
        ]
        for k, v in rows:
            t.append(f"{k:<10}", style=theme.MUTED)
            t.append(f"{v}\n", style=f"bold {theme.ACTIVE}" if (k == "Status" and is_active) else "")
        box.update(t)

    def on_option_list_option_highlighted(self, event):
        self.render_details()

    def on_option_list_option_selected(self, event):
        self._start(self.do_switch)

    # ---- plumbing shared by the flows ------------------------------------------
    def _blocked(self) -> bool:
        return self.busy or isinstance(self.screen, ModalScreen)

    def _start(self, fn):
        if self._blocked():
            return
        self.run_worker(self._guard(fn), exclusive=False)

    async def _guard(self, fn):
        self.busy = True
        try:
            await fn()
        except Exception as e:  # noqa: BLE001
            log.exception("%s failed", fn.__name__)
            self.set_status(f"Error: {e}", "err")
        finally:
            self.busy = False
            self.refresh_list()
            self.account_list.focus()

    async def ask(self, title: str, value: str = "", password: bool = False):
        fut = asyncio.get_running_loop().create_future()
        self.push_screen(Ask(title, value, password), lambda r: fut.done() or fut.set_result(r))
        return await fut

    async def confirm(self, message: str) -> bool:
        fut = asyncio.get_running_loop().create_future()
        self.push_screen(Confirm(message), lambda r: fut.done() or fut.set_result(r))
        return bool(await fut)

    def set_active(self, folder: str | None):
        state.set_active(self.service.id, folder)

    # ---- tabs + search --------------------------------------------------------
    def _switch_service(self, delta: int):
        if self._blocked():
            return
        self.service_idx = (self.service_idx + delta) % len(SERVICES)
        state.set_last_service(self.service.id)
        self.render_tabs()
        self.refresh_list()

    def action_next_service(self):
        self._switch_service(1)

    def action_prev_service(self):
        self._switch_service(-1)

    def action_search(self):
        if self._blocked():
            return
        box = self.query_one("#search", Input)
        box.styles.display = "block"
        box.value = self.search_query
        box.focus()

    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "search":
            self.search_query = event.value
            self.refresh_list()

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "search":
            self._close_search(keep_filter=True)

    def _close_search(self, keep_filter: bool):
        box = self.query_one("#search", Input)
        box.styles.display = "none"
        if not keep_filter:
            self.search_query = ""
            box.value = ""
            self.refresh_list()
        self.account_list.focus()

    def on_key(self, event):
        if event.key == "escape" and self.query_one("#search", Input).has_focus:
            self._close_search(keep_filter=False)
            event.stop()

    def action_options(self):
        if not self._blocked():
            self.push_screen(OptionsScreen())

    # ---- background expiry sweep ---------------------------------------------
    async def run_expiry_sweep(self):
        if self._sweeping:
            return
        self._sweeping = True
        try:
            now = await asyncio.to_thread(get_trusted_now)
            if now is None:
                return  # offline; try again next tick
            deleted = await asyncio.to_thread(expiry.sweep, SERVICES, now)
            if deleted:
                names = ", ".join(f"{BY_ID[s].name}: {f}" for s, f in deleted)
                self.set_status(f"Expired accounts removed ({names})", "warn")
                if not self.busy:
                    self.refresh_list()
        except Exception:  # noqa: BLE001
            log.exception("expiry sweep failed")
        finally:
            self._sweeping = False
