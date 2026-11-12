"""Modal dialogs: text input (Ask) and yes/no (Confirm)."""
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label


class Ask(ModalScreen):
    BINDINGS = [("escape", "cancel", "")]

    def __init__(self, title: str, value: str = "", password: bool = False):
        super().__init__()
        self._title, self._value, self._password = title, value, password

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self._title)
            yield Input(value=self._value, password=self._password)
            yield Label("Enter: accept  ·  Esc: cancel", classes="hint")

    def on_mount(self):
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted):
        event.stop()
        self.dismiss(event.value.strip() or None)

    def action_cancel(self):
        self.dismiss(None)


class Confirm(ModalScreen):
    BINDINGS = [("y,enter", "yes", ""), ("n,escape", "no", "")]

    def __init__(self, message: str):
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self._message)
            yield Label("[Y/Enter] Yes   ·   [N/Esc] No", classes="hint")

    def action_yes(self):
        self.dismiss(True)

    def action_no(self):
        self.dismiss(False)
