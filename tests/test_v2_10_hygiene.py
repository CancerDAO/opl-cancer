"""v2.12.0 hygiene / packaging guards.

Locks in the patient-fidelity-review hygiene fixes so they cannot silently
regress:

  * The two operator scripts that imported the deleted ``opl_cancer.llm``
    module are gone (they crashed on run).
  * Version is bumped to 2.12.0 and consistent across pyproject / __init__ /
    plugin manifests / README badges.
  * Public-facing product docs carry no ``memory:*`` private anchors and do
    not name private internal skills.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]

_DELETED_SCRIPTS = [
    "scripts/verify_minimax_setup.py",
    "scripts/live_v2_e2e_minimax.py",
]

# Public-facing docs that must stay free of private-anchor / internal-skill leaks.
_PUBLIC_DOCS = [
    "README.md",
    "README.zh-CN.md",
    "SKILL.md",
    "TECHNICAL_REPORT.md",
    "docs/rfc/0001-compositional-paradigm.md",
]

_MEMORY_ANCHOR_RE = re.compile(r"memory:[A-Za-z0-9_]+")


@pytest.mark.parametrize("rel", _DELETED_SCRIPTS)
def test_crashing_minimax_scripts_deleted(rel: str) -> None:
    """These scripts imported the deleted ``opl_cancer.llm`` module — removed."""
    assert not (_REPO / rel).exists(), (
        f"{rel} imported the deleted opl_cancer.llm module and crashed on run; "
        "it must not be reintroduced as a live tool."
    )


def test_no_minimax_llm_module() -> None:
    """The llm module the dead scripts depended on is genuinely gone."""
    assert not (_REPO / "src" / "opl_cancer" / "llm").exists()


def test_version_is_2_10_0() -> None:
    from opl_cancer import __version__

    assert __version__ == "2.12.0"


def test_pyproject_version_matches() -> None:
    text = (_REPO / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "2.12.0"' in text


@pytest.mark.parametrize(
    "rel",
    [
        ".claude-plugin/plugin.json",
        ".codex-plugin/plugin.json",
        ".cursor-plugin/plugin.json",
    ],
)
def test_plugin_manifest_version(rel: str) -> None:
    data = json.loads((_REPO / rel).read_text(encoding="utf-8"))
    assert data["version"] == "2.12.0"


def test_marketplace_manifest_versions() -> None:
    data = json.loads((_REPO / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert data["version"] == "2.12.0"
    assert all(p["version"] == "2.12.0" for p in data["plugins"])


def test_readme_test_count_restamped() -> None:
    """README EN/ZH must report the real 1748 count, not the stale 1828."""
    for rel in ("README.md", "README.zh-CN.md"):
        text = (_REPO / rel).read_text(encoding="utf-8")
        assert "1828" not in text, f"{rel} still claims stale 1828 test count"
        assert "1748" in text, f"{rel} missing real 1748 test count"


@pytest.mark.parametrize("rel", _PUBLIC_DOCS)
def test_no_memory_anchor_leak_in_public_docs(rel: str) -> None:
    text = (_REPO / rel).read_text(encoding="utf-8")
    leaks = _MEMORY_ANCHOR_RE.findall(text)
    assert not leaks, f"{rel} leaks private memory anchors: {sorted(set(leaks))}"


def test_skill_md_no_private_skill_names() -> None:
    text = (_REPO / "SKILL.md").read_text(encoding="utf-8")
    for forbidden in ("vmtb-skill", "mtb-core"):
        assert forbidden not in text, (
            f"SKILL.md (public product doc) must not name private internal skill {forbidden!r}"
        )


def test_rfc_author_deidentified() -> None:
    text = (_REPO / "docs" / "rfc" / "0001-compositional-paradigm.md").read_text(encoding="utf-8")
    assert "Author**: CancerDAO Contributors" in text
    assert "zwbao" not in text
    # session UUID line removed
    assert "Origin session" not in text
