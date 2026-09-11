"""Fail-closed configuration helpers for live-trading entry points."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Mapping, Optional


_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"", "0", "false", "no", "off"}


@dataclass(frozen=True)
class LiveTradingSettings:
    account_id: str
    qmt_userdata_path: str
    session_id: str
    auto_confirm: bool


def _read_dotenv(path: Optional[Path]) -> dict[str, str]:
    if path is None or not path.is_file():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _parse_bool(value: str, name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ValueError(
        f"{name} 必须是 1/0、true/false、yes/no 或 on/off，当前值无效"
    )


def load_live_trading_settings(
    *,
    environ: Optional[Mapping[str, str]] = None,
    dotenv_path: Optional[Path] = None,
    configured_qmt_path: str = "",
    configured_account_id: str = "",
    configured_session_id: str = "mini_qmt",
) -> LiveTradingSettings:
    """Load settings with process environment taking precedence over ``.env``.

    ``EASYXT_LIVE_AUTO_CONFIRM`` deliberately defaults to false.  Invalid values
    raise instead of accidentally enabling live order submission.
    """

    env = os.environ if environ is None else environ
    file_values = _read_dotenv(dotenv_path)

    def get(name: str, default: str = "") -> str:
        if name in env:
            return str(env[name]).strip()
        return file_values.get(name, default).strip()

    qmt_path = (
        get("QMT_DATA_DIR")
        or get("QMT_USERDATA_PATH")
        or configured_qmt_path.strip()
    )
    account_id = get("QMT_ACCOUNT_ID") or configured_account_id.strip()
    session_id = get("QMT_SESSION_ID") or configured_session_id.strip() or "mini_qmt"
    auto_confirm = _parse_bool(
        get("EASYXT_LIVE_AUTO_CONFIRM", "0"),
        "EASYXT_LIVE_AUTO_CONFIRM",
    )

    return LiveTradingSettings(
        account_id=account_id,
        qmt_userdata_path=qmt_path,
        session_id=session_id,
        auto_confirm=auto_confirm,
    )
