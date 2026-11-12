"""Every filesystem location the program uses, in one place."""
import os
import sys
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))

# Folder of the exe (frozen) or of the project (dev). Not used for user data.
APP_DIR = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parents[2]

APPDATA = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
PROGRAMDATA = Path(os.environ.get("ProgramData", r"C:\ProgramData"))

DATA_DIR = APPDATA / "Azthiels Account Swap"
ACCOUNTS_DIR = DATA_DIR / "Accounts"      # Accounts/<service_id>/<account_folder>/{session.bin, meta.json}
STATE_FILE = DATA_DIR / "state.json"      # active account per service, last service shown
CONFIG_FILE = DATA_DIR / "config.json"    # user options (see core/config.py)
DEBUG_LOG = DATA_DIR / "debug.log"
CRASH_LOG = DATA_DIR / "crash.log"
