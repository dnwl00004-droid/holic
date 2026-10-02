from pathlib import Path

import pytest

from src.refresh_support import (
    ProviderJobError, history_provider_health, run_provider_job, snapshot_stamp,
)
from src.reliability import atomic_json, blank_snapshot, read_json


def test_provider_timeout_is_bounded(tmp_path):
    script = tmp_path / "blocked.py"
    script.write_text("import time\ntime.sleep(5)\n")
    with pytest.raises(ProviderJobError, match="provider_timeout"):
        run_provider_job("blocked test provider", [str(script)], cwd=tmp_path, timeout=0.05)


def test_rate_limit_error_does_not_publish_raw_provider_output(tmp_path, capsys):
    script = tmp_path / "failed.py"
    script.write_text("import sys\nprint('YFRateLimitError: Too Many Requests, private-test-marker', file=sys.stderr)\nsys.exit(1)\n")
    with pytest.raises(ProviderJobError) as raised:
        run_provider_job("test provider", [str(script)], cwd=tmp_path, timeout=2)
    assert str(raised.value) == "rate_limited_429"
    assert "private-test-marker" not in capsys.readouterr().out


def test_partial_provider_is_not_reported_fully_verified():
    status = history_provider_health("test", [
        {"count": 100, "status": "ok", "last_success": "2026-10-02", "last_attempt": "2026-10-02"},
        {"count": 200, "status": "stale", "last_success": "2026-10-01", "last_attempt": "2026-10-02", "error": "ReadTimeout"},
    ])
    assert status["status"] == "stale"
    assert status["available_series"] == 2 and status["successful_series"] == 1
    assert status["last_success"] == "2026-10-01"


def test_macro_snapshot_archives_do_not_overwrite_same_equity_date():
    first = {"meta": {"as_of": "2026-09-30", "last_refresh_completed": "2026-10-01T08:00:00Z"}}
    second = {"meta": {"as_of": "2026-09-30", "last_refresh_completed": "2026-10-01T09:00:00Z"}}
    assert snapshot_stamp(first) != snapshot_stamp(second)
    assert snapshot_stamp({"meta": {"generated_at": "2026-10-02T18:30:00+09:00"}}) == "2026-10-02T093000Z"


def test_failed_child_restores_snapshot_and_still_completes_macro_refresh(tmp_path, monkeypatch):
    import scripts.refresh as runner
    from src.providers import calendar_live, eia_live

    original = blank_snapshot()
    original["meta"].update(as_of="2026-09-30", generated_at="2026-10-01T08:00:00Z")
    original["tickers"] = [{"ticker": "TEST", "price": {"close": 100.0}}]
    original["data_health"] = {"providers": [{"source": "Yahoo Finance / equity universe", "last_success": "2026-10-01T08:00:00Z"}]}
    atomic_json(tmp_path / "latest.json", original)

    def failed(label, command, **kwargs):
        output = Path(command[command.index("--output") + 1])
        atomic_json(output, {"tickers": [], "market": {}})
        raise ProviderJobError("rate_limited_429")

    monkeypatch.setattr(runner, "run_provider_job", failed)
    monkeypatch.setattr(runner, "build_official_history", lambda *a, **k: [])
    monkeypatch.setattr(runner, "nyfed_reference_rates", lambda: {})
    monkeypatch.setattr(calendar_live, "official_calendar", lambda: {"events": [], "providers": []})
    monkeypatch.setattr(eia_live, "build_eia", lambda *a: [])
    updated = runner.refresh(tmp_path)
    assert len(updated["tickers"]) == 1
    assert updated["tickers"][0]["ticker"] == "TEST"
    assert updated["tickers"][0]["price"] == original["tickers"][0]["price"]
    assert updated["meta"]["last_refresh_completed"]
    assert updated["data_health"]["providers"][0]["error"] == "ProviderJobError:rate_limited_429"
    archived = list((tmp_path / "snapshots").glob("*.json"))
    assert len(archived) == 1 and archived[0].stem != "unknown"
    assert read_json(archived[0])["tickers"] == original["tickers"]
