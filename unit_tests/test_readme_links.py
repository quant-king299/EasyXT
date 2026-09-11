from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
LOCAL_LINK = re.compile(r"\]\((?!https?://|mailto:)([^)#]*)(?:#[^)]*)?\)")


def test_root_readme_local_links_exist():
    readme = ROOT / 'README.md'
    missing = []

    for target in LOCAL_LINK.findall(readme.read_text(encoding='utf-8')):
        if target and not (readme.parent / target).exists():
            missing.append(target)

    assert missing == []


def test_documented_backtest_layout_uses_current_module_names():
    text = (ROOT / 'easyxt_backtest' / 'README.md').read_text(encoding='utf-8')

    assert '├── engine.py' not in text
    assert '├── data_manager.py' not in text
    assert 'enhanced_backtest_engine.py' in text
    assert 'core/data_manager/' in text


def test_public_setup_docs_do_not_embed_developer_machine_paths():
    files = [
        ROOT / 'README.md',
        ROOT / '.env.example',
        ROOT / 'core' / 'auto_login' / 'README.md',
        ROOT / 'core' / 'qmt_connection' / 'README.md',
    ]

    for path in files:
        text = path.read_text(encoding='utf-8')
        assert r'C:\Users\Administrator' not in text, path
        assert '国金QMT' not in text, path
        assert '国金证券QMT' not in text, path
