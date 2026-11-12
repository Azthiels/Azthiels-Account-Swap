"""Windows Task Scheduler helpers, used for two things:

  * the program's own elevated task (core/elevation.py) - skips the UAC prompt on later launches
  * a non-elevated "launcher" task - starts games as a normal user even when we run as admin

Tasks are created from XML instead of `schtasks /tr`, because the /tr defaults are bad for us:
priority 7 (BELOW NORMAL - inherited by everything the task starts, games included) and a 72 hour
limit after which Windows kills the process.
"""
import locale
import logging
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

from .processes import NO_WINDOW, run_hidden

log = logging.getLogger(__name__)

_NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}

_TEMPLATE = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>{description}</Description></RegistrationInfo>
  <Principals>
    <Principal id="Author">
      <UserId>{user}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>{run_level}</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>Parallel</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>false</StartWhenAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>4</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{command}</Command>
      <Arguments>{arguments}</Arguments>
      <WorkingDirectory>{workdir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""

_user_sid: str | None = None


def current_user_sid() -> str:
    global _user_sid
    if _user_sid is None:
        out = run_hidden(["whoami", "/user", "/fo", "csv", "/nh"]).stdout.strip()
        _user_sid = out.split(",")[-1].strip().strip('"')
    return _user_sid


def create(name: str, exe: str, args: list[str], elevated: bool, description: str = "") -> bool:
    xml = _TEMPLATE.format(
        description=escape(description or name),
        user=escape(current_user_sid()),
        run_level="HighestAvailable" if elevated else "LeastPrivilege",
        command=escape(exe),
        arguments=escape(subprocess.list2cmdline(args)),
        workdir=escape(str(Path(exe).parent)),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "task.xml"
        path.write_text(xml, encoding="utf-16")
        r = run_hidden(["schtasks", "/create", "/tn", name, "/xml", str(path), "/f"])
    if r.returncode != 0:
        log.error("could not create task %s: %s", name, (r.stderr or r.stdout).strip())
        return False
    log.info("created task %s (%s) -> %s %s", name, "elevated" if elevated else "normal user", exe, args)
    return True


def run(name: str) -> bool:
    r = run_hidden(["schtasks", "/run", "/tn", name])
    if r.returncode != 0:
        log.error("could not run task %s: %s", name, (r.stderr or r.stdout).strip())
    return r.returncode == 0


def read(name: str) -> dict | None:
    """Main settings of an existing task, or None if it doesn't exist."""
    r = subprocess.run(["schtasks", "/query", "/tn", name, "/xml"], capture_output=True, creationflags=NO_WINDOW)
    if r.returncode != 0:
        return None
    raw = r.stdout
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = raw.decode("utf-16")
    else:
        text = raw.decode(locale.getpreferredencoding(False), errors="ignore")
    text = re.sub(r"^\s*<\?xml[^>]*\?>", "", text)
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        log.warning("could not parse task %s: %s", name, e)
        return None

    def get(path: str) -> str:
        el = root.find(path, _NS)
        return (el.text or "").strip() if el is not None else ""

    return {
        "command": get(".//t:Exec/t:Command").strip('"'),
        "arguments": get(".//t:Exec/t:Arguments"),
        "run_level": get(".//t:Principal/t:RunLevel"),
        "priority": get(".//t:Settings/t:Priority") or "7",
        "time_limit": get(".//t:Settings/t:ExecutionTimeLimit") or "PT72H",
    }
