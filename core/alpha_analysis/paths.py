"""Portable filesystem paths for the alpha-analysis command-line tools."""

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_DIR = PROJECT_ROOT / '101因子' / '101因子分析平台' / 'reports'


def get_alpha_report_dir() -> Path:
    """Return the configured report directory without assuming a user profile."""
    configured = os.getenv('EASYXT_ALPHA_REPORT_DIR', '').strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return DEFAULT_REPORT_DIR
