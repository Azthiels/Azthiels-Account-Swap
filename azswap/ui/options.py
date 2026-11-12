"""Options screen. The list of settings comes from each service's `config_fields`."""
import asyncio
import os

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList
from textual.widgets.option_list import Option

from ..core import config
from ..core.filepicker import pick_file
from ..core.paths import DATA_DIR
from ..services import SERVICES


def all_fields():
    return [f for svc in SERVICES for f in svc.config_fields]


class OptionsScreen(ModalScreen):
    BINDINGS = [
        Binding("escape", "close", ""),
        Binding("b", "browse", ""),
        Binding("o", "open_data_dir", ""),
    ]

    def __init__(self):
        super().__init__()
        self.fields = all_fields()

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Options")
            yield OptionList(id="opt_list")
            yield Label(
                "⏎ Edit value   ·   B Browse for a file (paths only)   ·   O Open data folder   ·   Esc Close",
                classes="hint",
            )

    def on_mount(self):
        self.refresh_rows()
        self.query_one(OptionList).focus()

    def refresh_rows(self):
        cfg = config.load()
        ol = self.query_one("#opt_list", OptionList)
        prev = ol.highlighted or 0
        ol.clear_options()
        for f in self.fields:
            raw = cfg.get(f.key)
            if f.kind == "secret" and raw:
                val = f"{'•' * max(len(raw) - 4, 0)}{raw[-4:]}"
            else:
                val = raw or "(not set)"
            ol.add_option(Option(f"{f.label}:  {val}", id=f.key))
        if self.fields:
            ol.highlighted = min(prev, len(self.fields) - 1)

    def _selected_field(self):
        i = self.query_one("#opt_list", OptionList).highlighted
        if i is None or i >= len(self.fields):
            return None
        return self.fields[i]

    def _save(self, key: str, value):
        config.set_value(key, value)
        self.refresh_rows()
        self.query_one(OptionList).focus()

    def on_option_list_option_selected(self, event):
        event.stop()
        field = self._selected_field()
        if field:
            self.run_worker(self._edit(field))

    async def _edit(self, field):
        current = config.get(field.key, "")
        new = await self.app.ask(f"{field.label}:", str(current or ""), password=(field.kind == "secret"))
        if new is not None:
            self._save(field.key, new)
        else:
            self.query_one(OptionList).focus()

    def action_browse(self):
        field = self._selected_field()
        if field and field.kind == "path":
            self.run_worker(self._browse(field))

    async def _browse(self, field):
        path = await asyncio.to_thread(pick_file, field.filetypes, f"Select: {field.label}")
        if path:
            self._save(field.key, path)
        else:
            self.query_one(OptionList).focus()

    def action_open_data_dir(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(str(DATA_DIR))  # noqa: S606

    def action_close(self):
        self.dismiss(None)
