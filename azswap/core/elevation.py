"""Admin rights: one UAC prompt, then a scheduled task (run level highest) for every later launch.

Killing game processes and writing their files needs admin. Asking UAC every launch is annoying,
so the first elevated run creates a scheduled task, and later runs start themselves through it.

The task must point at *this* exe/script. If it points elsewhere (the exe was moved or renamed),
`schtasks /run` still reports success but nothing opens - so the task is always checked first and
recreated when it doesn't match. Dev runs (python) and the exe use separate tasks so they don't
keep overwriting each other.

Games are NOT started with our admin rights: `launch_as_user` starts them through a second,
non-elevated task, so they run exactly as if opened from the Start menu.
"""
import ctypes
import logging
import os
import subprocess
import sys
from pathlib import Path

from . import tasks
from .paths import APP_DIR, FROZEN
from .processes import launch_detached

log = logging.getLogger(__name__)

TASK_BASE = "AzthielsAccountSwap"
LAUNCHER_TASK = f"{TASK_BASE}-launcher"


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:  # noqa: BLE001
        return False


def task_name() -> str:
    return TASK_BASE if FROZEN else f"{TASK_BASE}-dev"


def launch_target() -> tuple[str, list[str]]:
    """(executable, args) that start this program."""
    if FROZEN:
        return sys.executable, []
    return sys.executable, [str(Path(sys.argv[0]).resolve())]


def task_problems(name: str) -> list[str]:
    """Why the program's task can't be used as-is (empty list = it's fine)."""
    info = tasks.read(name)
    if info is None:
        return ["does not exist"]
    exe, args = launch_target()
    problems = []
    if os.path.normcase(os.path.abspath(info["command"])) != os.path.normcase(os.path.abspath(exe)):
        problems.append(f"points to {info['command']}")
    elif not Path(info["command"]).exists():
        problems.append("target file is missing")
    if info["arguments"].lower() != subprocess.list2cmdline(args).lower():
        problems.append(f"arguments are {info['arguments']!r}")
    if info["priority"] != "4":
        problems.append(f"priority {info['priority']} (should be 4 = normal)")
    if info["time_limit"] != "PT0S":
        problems.append(f"time limit {info['time_limit']}")
    if info["run_level"] != "HighestAvailable":
        problems.append(f"run level {info['run_level']}")
    return problems


def task_is_current(name: str) -> bool:
    problems = task_problems(name)
    if problems:
        log.info("task %s can't be used: %s", name, "; ".join(problems))
    return not problems


def request_uac() -> bool:
    exe, args = launch_target()
    params = subprocess.list2cmdline([*args, *sys.argv[1:]])
    try:
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, str(APP_DIR), 1)
    except Exception as e:  # noqa: BLE001
        log.error("UAC request failed: %s", e)
        return False
    return rc > 32


def ensure_admin() -> str:
    """Returns one of:
    "admin"       - already elevated, keep running
    "relaunched"  - an elevated copy was started, this process should exit
    "unelevated"  - user refused UAC (or it failed), keep running without admin
    """
    name = task_name()
    if is_admin():
        if not task_is_current(name):
            exe, args = launch_target()
            tasks.create(name, exe, args, elevated=True, description="Azthiels Account Swap (admin, no UAC prompt)")
        return "admin"
    if task_is_current(name) and tasks.run(name):
        log.info("relaunched through task %s", name)
        return "relaunched"
    if request_uac():
        log.info("relaunched through UAC")
        return "relaunched"
    log.warning("running without admin rights")
    return "unelevated"


def launch_as_user(exe: str, args: list[str]) -> None:
    """Start a program WITHOUT our admin rights (as a normal user, normal priority)."""
    if not is_admin():
        launch_detached(exe, args)
        return
    ok = tasks.create(LAUNCHER_TASK, exe, args, elevated=False, description="Azthiels Account Swap game launcher")
    if ok and tasks.run(LAUNCHER_TASK):
        log.info("launched as normal user: %s %s", exe, args)
        return
    log.warning("launcher task failed - starting %s with admin rights instead", exe)
    launch_detached(exe, args)
