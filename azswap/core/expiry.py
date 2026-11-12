"""Deletes imported accounts whose expiration has passed (checked against internet time)."""
import logging
from datetime import datetime

from . import state, storage
from .processes import kill_processes

log = logging.getLogger(__name__)


def sweep(services, trusted_now: datetime) -> list[tuple[str, str]]:
    """Delete every expired account. If it's the active one, close the game and clear its session
    first - unless the service says it's busy right now (then wait for the next sweep).
    Returns the (service_id, folder) pairs that were deleted."""
    deleted = []
    for svc in services:
        for acc in storage.list_accounts(svc.id):
            if not acc.expires_at:
                continue
            try:
                if trusted_now < datetime.fromisoformat(acc.expires_at):
                    continue
            except ValueError:
                log.warning("bad expires_at in %s/%s: %r", svc.id, acc.folder, acc.expires_at)
                continue
            if state.get_active(svc.id) == acc.folder:
                if svc.is_busy(acc):
                    log.info("%s/%s expired but service is busy - deferring", svc.id, acc.folder)
                    continue
                kill_processes(svc.processes)
                svc.clear_session()
                state.set_active(svc.id, None)
            storage.delete_account(acc)
            log.info("deleted expired %s/%s", svc.id, acc.folder)
            deleted.append((svc.id, acc.folder))
    return deleted
