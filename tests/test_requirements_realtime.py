from pathlib import Path

from packaging.requirements import Requirement


REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS_FILE = REPO_ROOT / "requirements_realtime.txt"

EXPECTED_REQUIREMENTS = {
    "pytdx": ">=1.72",
    "aiohttp": ">=3.8.0",
    "aiohttp-cors": ">=0.7.0",
    "websockets": "<14.0,>=10.0",
}


def _requirement_lines():
    raw_content = REQUIREMENTS_FILE.read_bytes()

    assert not raw_content.startswith(b"\xef\xbb\xbf")

    text = raw_content.decode("utf-8")
    requirement_lines = []

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith("#"):
            assert line.startswith("#")
            continue

        assert "#" not in stripped
        requirement_lines.append(stripped)

    return requirement_lines


def test_requirements_realtime_exists_at_repo_root():
    assert REQUIREMENTS_FILE.is_file()


def test_requirements_realtime_lists_runtime_dependencies():
    requirements = {}

    for line in _requirement_lines():
        requirement = Requirement(line)
        name = requirement.name.lower()

        assert name not in requirements
        requirements[name] = str(requirement.specifier)

    assert requirements == EXPECTED_REQUIREMENTS
