from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def active_rules():
    return [
        line.strip()
        for line in (ROOT / '.gitignore').read_text(encoding='utf-8').splitlines()
        if line.strip() and not line.lstrip().startswith('#')
    ]


def test_csv_ignore_is_scoped_to_repository_root():
    rules = active_rules()

    assert '*.csv' not in rules
    assert '/*.csv' in rules


def test_gitignore_has_no_duplicate_active_rules():
    duplicates = {
        rule: count for rule, count in Counter(active_rules()).items() if count > 1
    }

    assert duplicates == {}
