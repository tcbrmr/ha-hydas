"""Tests for release metadata and translations."""

import json
import os
from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "hydas"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _key_tree(value):
    """Return a nested representation containing only dictionary keys."""
    if isinstance(value, dict):
        return {key: _key_tree(child) for key, child in value.items()}
    return None


def test_json_files_are_valid_and_translations_match():
    strings = _load_json(INTEGRATION / "strings.json")
    english = _load_json(INTEGRATION / "translations" / "en.json")
    german = _load_json(INTEGRATION / "translations" / "de.json")

    assert _key_tree(strings) == _key_tree(english) == _key_tree(german)


def test_release_tag_matches_manifest_version():
    """Prevent publishing a tag that disagrees with the integration version."""
    if os.environ.get("GITHUB_REF_TYPE") != "tag":
        return

    manifest = _load_json(INTEGRATION / "manifest.json")
    assert os.environ["GITHUB_REF_NAME"].removeprefix("v") == manifest["version"]
