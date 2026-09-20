"""Small shared HTTP helper: polite User-Agent, rate limiting, robots.txt
check, one retry. Shared by every source so we only write this once.
"""
from __future__ import annotations

import logging
import time
import urllib.robotparser
from urllib.parse import urlparse

import requests

logger = logging.getLogger("tracker.http")

USER_AGENT = "DegreeApprenticeshipTracker/1.0 (+personal, non-commercial research tool; contact via github)"

_robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}
_last_request_at: dict[str, float] = {}


def _robots_for(url: str) -> urllib.robotparser.RobotFileParser:
    origin = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    if origin not in _robots_cache:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(origin + "/robots.txt")
        try:
            rp.read()
        except Exception:  # robots.txt missing/unreachable -> assume allowed
            rp.allow_all = True
        _robots_cache[origin] = rp
    return _robots_cache[origin]


def allowed_by_robots(url: str) -> bool:
    try:
        return _robots_for(url).can_fetch(USER_AGENT, url)
    except Exception:
        return True  # fail open on robots.txt parsing errors; don't block a real scan over that


def get(url: str, *, params: dict | None = None, timeout: int = 20, delay_seconds: float = 2.0) -> requests.Response | None:
    """GET with a per-host rate limit and a robots.txt check. Returns None
    (and logs) instead of raising, so one bad request never kills a source.
    """
    if not allowed_by_robots(url):
        logger.warning("robots.txt disallows fetching %s - skipping", url)
        return None

    host = urlparse(url).netloc
    last = _last_request_at.get(host, 0.0)
    wait = delay_seconds - (time.time() - last)
    if wait > 0:
        time.sleep(wait)

    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-GB,en;q=0.9"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        _last_request_at[host] = time.time()
        if resp.status_code == 429:
            logger.warning("429 rate-limited by %s, backing off", host)
            time.sleep(delay_seconds * 3)
            return None
        resp.raise_for_status()
        return resp
    except requests.RequestException as exc:
        logger.warning("request to %s failed: %s", url, exc)
        return None
