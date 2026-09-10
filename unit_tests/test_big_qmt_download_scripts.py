import importlib.util
from pathlib import Path


TOOLS = Path(__file__).resolve().parents[1] / "tools"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_precise_updater_does_not_fallback_to_full_market(monkeypatch, tmp_path):
    module = _load("big_qmt_daily_dat_update")
    module.MANIFEST_PATH = str(tmp_path / "missing.json")
    called = []
    monkeypatch.setattr(module, "download_history_data", lambda *args: called.append(args),
                        raising=False)
    module._run_downloads(object())
    assert called == []


def test_full_market_range_uses_configured_dates(monkeypatch):
    module = _load("big_qmt_full_market_range_download")
    module.START_DATE = "20260820"
    module.END_DATE = "20260910"
    module.PAUSE_SECONDS = 0
    monkeypatch.setattr(module, "get_stock_list_in_sector",
                        lambda _name: ["000002.SZ", "000001.SZ", "000001.SZ"],
                        raising=False)
    called = []
    monkeypatch.setattr(module, "download_history_data", lambda *args: called.append(args),
                        raising=False)
    module._run_downloads(object())
    assert called == [
        ("000001.SZ", "1d", "20260820", "20260910"),
        ("000002.SZ", "1d", "20260820", "20260910"),
    ]
