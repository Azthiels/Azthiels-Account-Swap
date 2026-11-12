"""Running, finding, killing and launching Windows processes."""
import logging
import subprocess
import time

log = logging.getLogger(__name__)

NO_WINDOW = 0x08000000                      # CREATE_NO_WINDOW
DETACHED = 0x00000008 | 0x00000200          # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP


def run_hidden(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, errors="ignore", creationflags=NO_WINDOW)


def running(names: list[str]) -> list[str]:
    out = run_hidden(["tasklist", "/FO", "CSV", "/NH"]).stdout.lower()
    return [p for p in names if f'"{p.lower()}"' in out]


def kill_processes(names: list[str], timeout: float = 25.0) -> bool:
    """Force-close every process in `names`. True once none are left."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        alive = running(names)
        if not alive:
            time.sleep(1.0)  # let Windows release file/registry handles
            return True
        for p in alive:
            run_hidden(["taskkill", "/F", "/T", "/IM", p])
        time.sleep(0.6)
    left = running(names)
    if left:
        log.error("could not close: %s", ", ".join(left))
    return not left


def launch_detached(exe: str, args: list[str]) -> None:
    log.info("launching %s %s", exe, args)
    subprocess.Popen(
        [exe, *args], creationflags=DETACHED, close_fds=True,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
