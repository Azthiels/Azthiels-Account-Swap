"""Entry point. Startup runs in named stages so a crash report says exactly where it broke.

    run.py                 normal start (asks for admin once, then opens the TUI)
    run.py --doctor        check every part of the program and print OK/FAIL for each
    run.py --self-test     --doctor + start the TUI headless; exit code 1 on failure (build.bat uses it)
    run.py --no-elevate    skip the admin/UAC step (same as env var RS_NO_ELEVATE=1)
"""
import argparse
import logging
import os
import sys
import traceback
from datetime import datetime

from . import APP_NAME, VERSION
from .core.paths import CRASH_LOG, FROZEN

log = logging.getLogger(__name__)

_stage = "startup"


def _set_stage(name: str) -> None:
    global _stage
    _stage = name
    log.debug("stage: %s", name)


def _parse_args(argv):
    p = argparse.ArgumentParser(prog="Azthiels-Account-Swap", description=f"{APP_NAME} v{VERSION}")
    p.add_argument("--doctor", action="store_true", help="check every part of the program and exit")
    p.add_argument("--self-test", action="store_true", help="doctor + headless UI start, no pause, exit code 0/1")
    p.add_argument("--no-elevate", action="store_true", help="don't ask for admin rights")
    return p.parse_args(argv)


def _main(argv) -> int:
    _set_stage("reading arguments")
    args = _parse_args(argv)

    if sys.platform != "win32":
        print("This program is Windows only.")
        return 1

    _set_stage("logging setup")
    from .core.logs import setup_logging
    setup_logging()
    log.info("%s v%s starting (frozen=%s, python %s)", APP_NAME, VERSION, FROZEN, sys.version.split()[0])

    if args.doctor or args.self_test:
        _set_stage("doctor")
        from .doctor import run_doctor
        return run_doctor(ui_smoke=args.self_test, pause=FROZEN and not args.self_test)

    _set_stage("admin elevation")
    from .core.elevation import ensure_admin, is_admin
    if args.no_elevate or os.environ.get("RS_NO_ELEVATE"):
        admin = is_admin()
    else:
        result = ensure_admin()
        if result == "relaunched":
            return 0
        admin = result == "admin"

    _set_stage("loading the UI modules")
    from .ui.app import AccountSwap

    _set_stage("running the UI")
    AccountSwap(admin=admin).run(mouse=False)
    log.info("closed normally")
    return 0


def _report_crash() -> None:
    text = traceback.format_exc()
    report = (
        f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {APP_NAME} v{VERSION} (frozen={FROZEN})\n"
        f"Crashed while: {_stage}\n\n{text}\n"
    )
    try:
        log.critical("crashed while %s\n%s", _stage, text)
        CRASH_LOG.parent.mkdir(parents=True, exist_ok=True)
        CRASH_LOG.write_text(report, encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass  # the console output below is the fallback
    print(f"\n--- {APP_NAME} crashed while: {_stage} ---\n")
    print(text)
    print(f"This was also saved to: {CRASH_LOG}")
    try:
        input("\nPress Enter to close...")
    except EOFError:
        pass


def run() -> None:
    try:
        code = _main(sys.argv[1:])
    except SystemExit:
        raise
    except KeyboardInterrupt:
        code = 130
    except BaseException:  # noqa: BLE001
        _report_crash()
        code = 1
    sys.exit(code)
