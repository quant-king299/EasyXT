from datetime import date, datetime
import json
from pathlib import Path
import tempfile
import os

from data_manager import qmt_dat_sync_manifest as manifest


def test_classifies_stock_etf_and_bse():
    assert manifest.classify_security("000001.SZ") == "a_share"
    assert manifest.classify_security("510300.SH") == "etf"
    assert manifest.classify_security("920001.BJ") == "bse"


def test_manifest_uses_first_missing_date_and_groups_symbols(monkeypatch):
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / manifest.MANIFEST_FILENAME
        monkeypatch.setattr(manifest, "default_manifest_path", lambda _: output)
        path, summary = manifest.write_manifest([
            {"stock_code": "000001.SZ", "latest_date": "2026-08-17"},
            {"stock_code": "510300.SH", "latest_date": "2026-08-18"},
            {"stock_code": "920001.BJ", "latest_date": "2026-08-19"},
        ], datadir=None, target_date=date(2026, 9, 10))
        saved = json.loads(path.read_text(encoding="utf-8"))
        assert summary == {"total": 3, "qmt_a_share": 1, "etf": 1, "bse": 1, "other": 0}
        assert [job["stock_code"] for job in saved["jobs"]] == ["000001.SZ"]
        assert {job["stock_code"] for job in saved["deferred_jobs"]} == {"510300.SH", "920001.BJ"}
        by_code = {job["stock_code"]: job for job in saved["jobs"]}
        assert by_code["000001.SZ"]["start_date"] == "20260818"
        assert by_code["000001.SZ"]["end_date"] == "20260910"


def test_detects_dat_rebuilt_after_same_day_manifest():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        datadir = root / "datadir"
        python_dir = root / "python"
        dat_path = datadir / "SZ" / "86400" / "000001.DAT"
        dat_path.parent.mkdir(parents=True)
        python_dir.mkdir()
        dat_path.write_bytes(b"rebuilt")
        (python_dir / manifest.MANIFEST_FILENAME).write_text(json.dumps({
            "generated_at": "2026-09-10T10:00:00",
            "target_date": "20260910",
            "jobs": [{"stock_code": "000001.SZ"}],
        }), encoding="utf-8")
        rebuilt_time = datetime(2026, 9, 10, 11, 0).timestamp()
        os.utime(dat_path, (rebuilt_time, rebuilt_time))

        assert manifest.rebuilt_without_new_bar_codes(
            datadir=datadir, target_date=date(2026, 9, 10)) == {"000001.SZ"}
        assert manifest.rebuilt_without_new_bar_codes(
            datadir=datadir, target_date=date(2026, 9, 11)) == set()
