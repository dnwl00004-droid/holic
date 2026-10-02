"""Bounded provider jobs and safe refresh audit metadata."""
from __future__ import annotations

import re
import subprocess
import sys
import time
from datetime import datetime, timezone

from .reliability import now


class ProviderJobError(RuntimeError):
    """A public error code, never arbitrary provider output or credentials."""


def run_provider_job(label, command, *, cwd, timeout):
    started = time.monotonic()
    print(f"[refresh] {label}: started (limit {timeout}s)", flush=True)
    try:
        result = subprocess.run(
            [sys.executable, *command], cwd=cwd, capture_output=True,
            timeout=timeout, text=True, errors="replace",
        )
    except subprocess.TimeoutExpired:
        raise ProviderJobError(f"provider_timeout_{timeout}s") from None
    if result.returncode:
        # Classify known failures without publishing raw responses or headers.
        output = result.stderr + result.stdout
        if "YFRateLimitError" in output or "Too Many Requests" in output:
            code = "rate_limited_429"
        elif "Less than 90% universe price coverage" in output:
            code = "insufficient_universe_price_coverage"
        elif "SPY benchmark data unavailable" in output:
            code = "benchmark_prices_unavailable"
        else:
            code = f"provider_exit_{result.returncode}"
        raise ProviderJobError(code)
    elapsed = round(time.monotonic() - started, 2)
    print(f"[refresh] {label}: completed ({elapsed}s)", flush=True)
    return elapsed


def history_provider_health(source, items):
    available = [x for x in items if x.get("count", 0) > 0]
    successful = [x for x in items if x.get("status") == "ok"]
    status = "ok" if items and len(successful) == len(items) else "stale" if available else "unavailable"
    attempts = [x["last_attempt"] for x in items if x.get("last_attempt")]
    successes = [x["last_success"] for x in items if x.get("last_success")]
    errors = sorted({x["error"] for x in items if x.get("error")})
    return {
        "source": source, "status": status,
        "available_series": len(available), "total_series": len(items),
        "successful_series": len(successful),
        "last_attempt": max(attempts, default=None),
        # The oldest success describes how recently the entire group was verified.
        "last_success": min(successes, default=None),
        "error": "; ".join(errors) or None,
    }


def snapshot_stamp(snapshot):
    """Archive every completed build, including snapshots without equity prices."""
    meta = snapshot.get("meta", {})
    for key in ("last_refresh_completed", "generated_at", "as_of"):
        value = meta.get(key)
        if not isinstance(value, str):
            continue
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc)
        stamp = dt.strftime("%Y-%m-%dT%H%M%S")
        return stamp + (f"{dt.microsecond:06d}" if dt.microsecond else "") + "Z"
    return re.sub(r"[^0-9TZ-]", "", now())
