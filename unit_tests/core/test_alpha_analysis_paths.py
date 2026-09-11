import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATHS_FILE = ROOT / 'core' / 'alpha_analysis' / 'paths.py'
SPEC = importlib.util.spec_from_file_location('easyxt_alpha_paths', PATHS_FILE)
PATHS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATHS)
DEFAULT_REPORT_DIR = PATHS.DEFAULT_REPORT_DIR
get_alpha_report_dir = PATHS.get_alpha_report_dir


def test_default_report_dir_is_inside_project(monkeypatch):
    monkeypatch.delenv('EASYXT_ALPHA_REPORT_DIR', raising=False)

    report_dir = get_alpha_report_dir()

    assert report_dir == ROOT / '101因子' / '101因子分析平台' / 'reports'
    assert 'Administrator' not in str(report_dir)


def test_report_dir_can_be_overridden(monkeypatch, tmp_path):
    configured = tmp_path / 'custom-alpha-reports'
    monkeypatch.setenv('EASYXT_ALPHA_REPORT_DIR', str(configured))

    assert get_alpha_report_dir() == configured.resolve()


def test_alpha_launchers_do_not_contain_machine_specific_paths():
    launchers = [
        ROOT / 'core' / 'alpha_analysis' / 'start_platform.py',
        ROOT / 'core' / 'alpha_analysis' / 'start_platform_with_qmt.py',
    ]

    for launcher in launchers:
        text = launcher.read_text(encoding='utf-8')
        assert r'C:\Users\Administrator' not in text
        assert 'get_alpha_report_dir()' in text


def test_exported_default_is_absolute():
    assert DEFAULT_REPORT_DIR.is_absolute()
