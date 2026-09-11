from pathlib import Path

import pytest

from core.live_trading_config import load_live_trading_settings


def test_live_orders_are_disabled_by_default(tmp_path: Path):
    settings = load_live_trading_settings(environ={}, dotenv_path=tmp_path / ".env")

    assert settings.auto_confirm is False
    assert settings.account_id == ""
    assert settings.qmt_userdata_path == ""


def test_loads_standard_qmt_settings_from_dotenv(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "QMT_ACCOUNT_ID=12345678\n"
        "QMT_DATA_DIR=D:/Broker/userdata_mini\n"
        "QMT_SESSION_ID=small_cap_live\n"
        "EASYXT_LIVE_AUTO_CONFIRM=0\n",
        encoding="utf-8",
    )

    settings = load_live_trading_settings(environ={}, dotenv_path=env_file)

    assert settings.account_id == "12345678"
    assert settings.qmt_userdata_path == "D:/Broker/userdata_mini"
    assert settings.session_id == "small_cap_live"
    assert settings.auto_confirm is False


def test_process_environment_overrides_dotenv_and_can_explicitly_enable(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("EASYXT_LIVE_AUTO_CONFIRM=0\n", encoding="utf-8")

    settings = load_live_trading_settings(
        environ={
            "QMT_ACCOUNT_ID": "87654321",
            "QMT_USERDATA_PATH": "E:/QMT/userdata_mini",
            "EASYXT_LIVE_AUTO_CONFIRM": "true",
        },
        dotenv_path=env_file,
    )

    assert settings.account_id == "87654321"
    assert settings.qmt_userdata_path == "E:/QMT/userdata_mini"
    assert settings.auto_confirm is True


def test_invalid_live_switch_fails_closed():
    with pytest.raises(ValueError, match="EASYXT_LIVE_AUTO_CONFIRM"):
        load_live_trading_settings(
            environ={"EASYXT_LIVE_AUTO_CONFIRM": "enabled"}
        )
