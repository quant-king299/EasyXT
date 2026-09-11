from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

COMPATIBILITY_REQUIREMENTS = {
    'requirements.txt': '-e .[data,backtest,gui,automation,realtime]',
    'requirements_realtime.txt': '-e .[realtime]',
    'gui_app/requirements.txt': '-e ..[data,gui,automation]',
    'easyxt_backtest/requirements.txt': '-e ..[backtest,gui]',
    'easyxt_backtest/web_app/requirements.txt': '-e ../..[backtest,gui]',
    'strategies/xueqiu_follow/requirements.txt': '-e ../..[xueqiu,gui]',
}


def active_requirement_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding='utf-8').splitlines()
        if line.strip() and not line.lstrip().startswith('#')
    ]


def test_requirements_files_only_proxy_pyproject_extras():
    for relative_path, expected_proxy in COMPATIBILITY_REQUIREMENTS.items():
        path = ROOT / relative_path
        assert path.is_file(), relative_path
        assert active_requirement_lines(path) == [expected_proxy], relative_path


def test_lockfile_exists_and_matches_supported_python_range():
    lockfile = ROOT / 'uv.lock'
    text = lockfile.read_text(encoding='utf-8')

    assert text.startswith('version = 1\n')
    assert 'requires-python = ">=3.9"' in text
    assert 'name = "easyxt"' in text


def test_core_safety_ci_uses_locked_project_extras():
    workflow = (ROOT / '.github/workflows/core-safety-tests.yml').read_text(
        encoding='utf-8'
    )

    assert 'pip install pytest pandas numpy backtrader' not in workflow
    assert 'uv sync --locked --extra backtest --extra dev' in workflow
    assert 'uv run --no-sync python -m pytest' in workflow
