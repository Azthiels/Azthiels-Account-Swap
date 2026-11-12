"""Riot Games (LoL / Valorant): the session is RiotGamesPrivateSettings.yaml.
The active Riot ID is read from the Riot Client's local API (port + password in its lockfile)."""
import base64
import json
import logging
import shlex
import ssl
import time
import urllib.request
from pathlib import Path

from ..core import config
from ..core.config import ConfigField
from ..core.paths import LOCALAPPDATA, PROGRAMDATA
from ..core.elevation import launch_as_user
from ..core.processes import kill_processes
from ..core.util import read_json
from .base import Service

log = logging.getLogger(__name__)

RIOT_DIR = LOCALAPPDATA / "Riot Games" / "Riot Client"
LIVE_YAML = RIOT_DIR / "Data" / "RiotGamesPrivateSettings.yaml"
LOCKFILE = RIOT_DIR / "Config" / "lockfile"
INSTALLS_JSON = PROGRAMDATA / "Riot Games" / "RiotClientInstalls.json"
DEFAULT_CLIENT = r"C:\Riot Games\Riot Client\RiotClientServices.exe"

ID_ENDPOINTS = [
    "/riot-client-auth/v1/userinfo",
    "/player-account/aliases/v1/active",
    "/rso-auth/v1/authorization/userinfo",
]
SESSION_MARKERS = ("ssid", "cookies", "token", "session", "riot-login", "rso-auth")

# The Riot Client's local API (127.0.0.1) uses its own self-signed certificate, so verification
# is off - but ONLY for this context, which is never used for anything except localhost.
_LOCAL_CTX = ssl.create_default_context()
_LOCAL_CTX.check_hostname = False
_LOCAL_CTX.verify_mode = ssl.CERT_NONE


def _local_api_get(endpoint: str):
    parts = LOCKFILE.read_text().strip().split(":")
    port, password = parts[2], parts[3]
    token = base64.b64encode(f"riot:{password}".encode()).decode()
    req = urllib.request.Request(f"https://127.0.0.1:{port}{endpoint}", headers={"Authorization": f"Basic {token}"})
    with urllib.request.urlopen(req, timeout=4, context=_LOCAL_CTX) as r:
        return json.loads(r.read().decode())


def _find_riot_id(obj) -> tuple[str, str] | None:
    """Search a JSON response (any shape) for game_name/tag_line."""
    if isinstance(obj, str):
        try:
            obj = json.loads(obj)
        except Exception:  # noqa: BLE001
            return None
    if isinstance(obj, dict):
        name = obj.get("game_name") or obj.get("gameName")
        tag = obj.get("tag_line") or obj.get("tagLine")
        if name and tag:
            return str(name), str(tag)
        children = obj.values()
    elif isinstance(obj, list):
        children = obj
    else:
        return None
    for v in children:
        found = _find_riot_id(v)
        if found:
            return found
    return None


def client_path() -> str:
    data = read_json(INSTALLS_JSON, {})
    for key in ("rc_default", "rc_live", "rc_beta"):
        p = data.get(key)
        if p and Path(p).exists():
            return p
    return DEFAULT_CLIENT


def launch_args() -> list[str]:
    raw = config.get("riot_launch_args", "")
    if isinstance(raw, list):
        return [str(a) for a in raw]
    return shlex.split(str(raw), posix=False) if raw else []


class RiotService(Service):
    id = "riot"
    name = "Riot Account"
    processes = [
        "RiotClientServices.exe", "RiotClientUx.exe", "RiotClientUxRender.exe", "RiotClientCrashHandler.exe",
        "Riot Client.exe", "VALORANT.exe", "VALORANT-Win64-Shipping.exe",
        "LeagueClient.exe", "LeagueClientUx.exe", "LeagueClientUxRender.exe", "League of Legends.exe",
    ]
    config_fields = [
        ConfigField("riot_launch_args", "Riot - extra launch arguments (space-separated)"),
    ]

    def get_active_id(self):
        if not LOCKFILE.exists():
            return None
        for ep in ID_ENDPOINTS:
            try:
                found = _find_riot_id(_local_api_get(ep))
            except Exception as e:  # noqa: BLE001
                log.debug("%s -> %s: %s", ep, type(e).__name__, e)
                continue
            if found:
                return f"{found[0]}#{found[1]}"
        log.info("Riot Client is running but no Riot ID was found")
        return None

    def has_session(self):
        try:
            if not LIVE_YAML.exists() or LIVE_YAML.stat().st_size < 64:
                return False
            text = LIVE_YAML.read_text(encoding="utf-8", errors="ignore").lower()
            return any(m in text for m in SESSION_MARKERS)
        except OSError as e:
            log.warning("could not read session file: %s", e)
            return False

    def read_session(self):
        try:
            return LIVE_YAML.read_bytes()
        except OSError as e:
            log.warning("could not read session file: %s", e)
            return None

    def write_session(self, blob):
        LIVE_YAML.parent.mkdir(parents=True, exist_ok=True)
        try:
            LIVE_YAML.write_bytes(blob)
        except PermissionError:
            kill_processes(self.processes)
            LIVE_YAML.write_bytes(blob)

    def clear_session(self):
        try:
            LIVE_YAML.unlink(missing_ok=True)
        except OSError:
            time.sleep(1.5)
            LIVE_YAML.unlink(missing_ok=True)

    def launch(self):
        launch_as_user(client_path(), launch_args())

    # is_busy: not implemented (always False) - see "Pendientes" in CLAUDE.md.

    def diagnose(self):
        exe = client_path()
        return [
            ("Riot Client exe", Path(exe).exists(), exe),
            ("Riot data folder", LIVE_YAML.parent.exists(), str(LIVE_YAML.parent)),
            ("Riot Client running (lockfile)", LOCKFILE.exists(), str(LOCKFILE)),
            ("Riot session present", self.has_session(), "log in to the Riot Client if this is NO"),
        ]
