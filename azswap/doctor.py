"""`--doctor`: checks each part of the program on its own and prints OK / FAIL per part.

Required checks decide the exit code. Info checks (Riot installed? admin?) only describe the PC.
"""
import importlib
import sys
import tempfile

from . import APP_NAME, VERSION
from .core.paths import DATA_DIR, FROZEN

OK, FAIL, INFO = "[ OK ]", "[FAIL]", "[ -- ]"


class Doctor:
    def __init__(self):
        self.failed = 0

    def check(self, name: str, fn, required: bool = True):
        try:
            ok, detail = fn()
        except Exception as e:  # noqa: BLE001
            ok, detail = False, f"{type(e).__name__}: {e}"
        mark = OK if ok else (FAIL if required else INFO)
        if required and not ok:
            self.failed += 1
        print(f"  {mark} {name}" + (f"  ->  {detail}" if detail else ""))

    def section(self, title: str):
        print(f"\n{title}")


def _import(module: str):
    def fn():
        m = importlib.import_module(module)
        return True, getattr(m, "__version__", "")
    return fn


def _data_dir_writable():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=DATA_DIR, prefix=".write_test_", delete=True):
        pass
    return True, str(DATA_DIR)


def _crypto():
    from .core import auc
    return auc.HAVE_CRYPTO, "" if auc.HAVE_CRYPTO else "cryptography is not installed / not bundled"


def _admin():
    from .core.elevation import is_admin
    return is_admin(), "" if is_admin() else "not elevated (normal for --doctor)"


def _task():
    from .core.elevation import task_name, task_problems
    name = task_name()
    problems = task_problems(name)
    if problems:
        return False, f"{name}: {'; '.join(problems)} (fixed on next start, asks UAC once)"
    return True, name


def _time():
    from .core.timesync import get_trusted_now
    now = get_trusted_now()
    return now is not None, now.isoformat(timespec="seconds") if now else "no time server reachable"


def _ui_headless():
    from .ui.app import AccountSwap

    async def pilot(p):
        await p.pause()
        p.app.exit()

    app = AccountSwap(admin=True)
    app.run(headless=True, auto_pilot=pilot)
    return app.return_code in (0, None), f"return code {app.return_code}"


def run_doctor(ui_smoke: bool = False, pause: bool = False) -> int:
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:  # noqa: BLE001
        pass
    d = Doctor()
    print(f"{APP_NAME} v{VERSION} - doctor")
    print(f"  python {sys.version.split()[0]}, {'exe (frozen)' if FROZEN else 'dev (python)'}")

    d.section("Program")
    d.check("data folder writable", _data_dir_writable)
    d.check("textual", _import("textual"))
    d.check("rich", _import("rich"))
    d.check("cryptography (.auc export/import)", _crypto)
    d.check("tkinter (file picker)", _import("tkinter.filedialog"))
    d.check("core modules", lambda: (bool([importlib.import_module(f"azswap.core.{m}") for m in (
        "auc", "config", "elevation", "expiry", "filepicker", "processes", "state", "storage", "tasks", "timesync",
        "util",
    )]), ""))
    d.check("services", lambda: (bool(importlib.import_module("azswap.services").SERVICES), ""))
    d.check("UI modules", _import("azswap.ui.app"))
    if ui_smoke:
        d.check("UI starts (headless)", _ui_headless)

    d.section("This PC")
    d.check("admin rights", _admin, required=False)
    d.check("scheduled task", _task, required=False)
    d.check("internet time", _time, required=False)

    from .services import SERVICES
    for svc in SERVICES:
        d.section(f"Service: {svc.name}")
        for name, ok, detail in svc.diagnose():
            d.check(name, lambda ok=ok, detail=detail: (ok, detail), required=False)

    print(f"\n{'All required checks passed.' if not d.failed else f'{d.failed} required check(s) FAILED.'}")
    if pause:
        try:
            input("\nPress Enter to close...")
        except EOFError:
            pass
    return 1 if d.failed else 0
