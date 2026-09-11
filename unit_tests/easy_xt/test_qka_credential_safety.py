from pathlib import Path
import re

import pytest

from strategies.jq2qmt.qmt_signal_client import QMTSignalClient
from strategies.jq2qmt.test_qmt_trading import (
    LIVE_TEST_CONFIRMATION,
    load_live_test_config,
)


ROOT = Path(__file__).resolve().parents[2]


def test_live_qka_test_is_disabled_by_default():
    with pytest.raises(RuntimeError, match="真实买卖委托"):
        load_live_test_config({})


def test_live_qka_test_requires_external_token_after_confirmation():
    with pytest.raises(RuntimeError, match="QKA_TOKEN"):
        load_live_test_config({"QKA_ALLOW_LIVE_TEST": LIVE_TEST_CONFIRMATION})


def test_live_qka_test_loads_external_configuration():
    config = load_live_test_config(
        {
            "QKA_ALLOW_LIVE_TEST": LIVE_TEST_CONFIRMATION,
            "QKA_TOKEN": "runtime-secret",
            "QKA_BASE_URL": "http://127.0.0.1:9000",
        }
    )

    assert config == ("http://127.0.0.1:9000", "runtime-secret")


def test_signal_client_rejects_missing_token_before_network_use():
    with pytest.raises(ValueError, match="QKA_TOKEN"):
        QMTSignalClient(token=None)


def test_tracked_python_does_not_embed_or_log_qka_tokens():
    long_hex_token = re.compile(r"token\s*=\s*['\"][0-9a-fA-F]{40,}['\"]")
    unsafe_log_fragment = "访问令牌: {" + "self.token}"
    offenders = []

    for path in ROOT.rglob("*.py"):
        if any(part in {'.git', '.venv'} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if long_hex_token.search(text) or unsafe_log_fragment in text:
            offenders.append(str(path.relative_to(ROOT)))

    assert offenders == []
