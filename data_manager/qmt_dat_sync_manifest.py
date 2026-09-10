"""Build exact Big QMT DAT download manifests after a GUI import pass."""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime
import json
from pathlib import Path
from typing import Iterable, Mapping, Optional


MANIFEST_FILENAME = "easyxt_qmt_dat_update_manifest.json"


def classify_security(code: str) -> str:
    pure, _, market = code.partition(".")
    if market == "BJ" or pure.startswith(("8", "92")):
        return "bse"
    if pure.startswith(("15", "16", "18", "50", "51", "56", "58")):
        return "etf"
    if market == "SH" and pure.startswith(("600", "601", "603", "605", "688", "689")):
        return "a_share"
    if market == "SZ" and pure.startswith(("000", "001", "002", "003", "300", "301")):
        return "a_share"
    return "other"


def is_a_share(code: str) -> bool:
    """Whether a symbol belongs to the Big QMT default ``沪深A股`` task."""
    return classify_security(code) == "a_share"


def _as_date_string(value) -> str:
    return value.strftime("%Y-%m-%d") if hasattr(value, "strftime") else str(value)[:10]


def _next_day(value) -> str:
    parsed = datetime.strptime(_as_date_string(value), "%Y-%m-%d").date()
    return date.fromordinal(parsed.toordinal() + 1).strftime("%Y%m%d")


def default_manifest_path(datadir: Optional[Path]) -> Path:
    if datadir:
        python_dir = Path(datadir).parent / "python"
        if python_dir.is_dir():
            return python_dir / MANIFEST_FILENAME
    return Path(__file__).resolve().parent.parent / ".easyxt" / MANIFEST_FILENAME


def write_manifest(stale_rows: Iterable[Mapping[str, object]], *, datadir: Optional[Path],
                   target_date: Optional[date] = None) -> tuple[Path, dict]:
    """Write one exact download job per stale symbol."""
    target = (target_date or date.today()).strftime("%Y%m%d")
    jobs_by_code = {}
    for row in stale_rows:
        code = str(row["stock_code"])
        start = _next_day(row["latest_date"])
        old = jobs_by_code.get(code)
        if old is None or start < old["start_date"]:
            jobs_by_code[code] = {
                "stock_code": code, "start_date": start, "end_date": target,
                "security_type": classify_security(code),
                "reason": "duckdb_not_advanced_by_local_dat",
            }
    all_jobs = sorted((job for job in jobs_by_code.values() if job["start_date"] <= target),
                      key=lambda job: (job["security_type"], job["stock_code"]))
    # The embedded updater's default universe is exactly Big QMT's 沪深A股.
    # Non-A-share instruments remain visible for routing, but must not make a
    # QMT DAT task silently attempt ETF/BJ/index/bond downloads.
    jobs = [job for job in all_jobs if job["security_type"] == "a_share"]
    deferred_jobs = [job for job in all_jobs if job["security_type"] != "a_share"]
    counts = Counter(job["security_type"] for job in all_jobs)
    summary = {"total": len(all_jobs), "qmt_a_share": counts["a_share"],
               "etf": counts["etf"], "bse": counts["bse"], "other": counts["other"]}
    payload = {"version": 1, "generated_at": datetime.now().isoformat(timespec="seconds"),
               "target_date": target, "summary": summary, "jobs": jobs,
               "deferred_jobs": deferred_jobs}
    path = default_manifest_path(datadir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path, summary
