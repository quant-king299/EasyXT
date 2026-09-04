"""Path-safety regression tests for the core data manager configuration."""

from pathlib import Path

from core.data_manager.config import DataManagerConfig


def test_default_duckdb_path_is_project_local():
    config = DataManagerConfig.__new__(DataManagerConfig)

    resolved = Path(config._detect_duckdb_path()).resolve()
    project_root = Path(__file__).resolve().parents[3]

    assert resolved == project_root / "data" / "stock_data.ddb"
