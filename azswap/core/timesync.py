"""Trusted (non-local) time for expiration checks.

The local clock can be changed by whoever has the file, so the time comes from the HTTPS `Date`
header of well-known servers, over a *verified* TLS connection (a MITM can't fake it).
Once one server answers, later calls reuse that answer plus the monotonic clock (which can't be
changed by the user) for a while, instead of hitting the network every 20 seconds.
"""
import email.utils
import logging
import ssl
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

log = logging.getLogger(__name__)

TIME_SOURCES = ["https://www.google.com", "https://www.microsoft.com", "https://www.cloudflare.com"]
CACHE_SECONDS = 600

_ctx = ssl.create_default_context()  # certificate verification ON
_lock = threading.Lock()
_anchor: tuple[datetime, float] | None = None  # (trusted utc time, time.monotonic() when it was read)


def _fetch_date(url: str) -> datetime | None:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=4, context=_ctx) as r:
            header = r.headers.get("Date")
    except urllib.error.HTTPError as e:  # a 403/405 still carries a valid Date header
        header = e.headers.get("Date") if e.headers else None
    if not header:
        return None
    dt = email.utils.parsedate_to_datetime(header)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_trusted_now() -> datetime | None:
    """Current UTC time from the internet. None if no server could be reached."""
    global _anchor
    with _lock:
        if _anchor and time.monotonic() - _anchor[1] < CACHE_SECONDS:
            return _anchor[0] + timedelta(seconds=time.monotonic() - _anchor[1])
        for url in TIME_SOURCES:
            try:
                dt = _fetch_date(url)
            except Exception as e:  # noqa: BLE001
                log.debug("%s failed: %s: %s", url, type(e).__name__, e)
                continue
            if dt:
                _anchor = (dt, time.monotonic())
                return dt
        log.warning("no time source reachable")
        return None
