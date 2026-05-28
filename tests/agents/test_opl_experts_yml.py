"""v2.1 P0-#3: opl-* subagent types declared with file-write contract."""
from __future__ import annotations

from pathlib import Path

import yaml


_AGENTS_YML = Path("agents/opl-experts.yml")


def test_all_21_opl_experts_declared():
    expected = {
        "opl-rosa", "opl-bert", "opl-vince", "opl-rick", "opl-heddy", "opl-mary",
        "opl-aviv", "opl-tyler", "opl-iain", "opl-ted", "opl-riad", "opl-jen",
        "opl-kieren", "opl-mark", "opl-hong", "opl-frances", "opl-dennis",
        "opl-steve", "opl-maya", "opl-julius", "opl-henry",
    }
    data = yaml.safe_load(_AGENTS_YML.read_text())
    names = {a["name"] for a in data["agents"]}
    assert names == expected


def test_all_grant_write_scoped():
    data = yaml.safe_load(_AGENTS_YML.read_text())
    for a in data["agents"]:
        write_scope = a.get("tool_scopes", {}).get("Write", "")
        # Henry writes to triggers/<run>/audit/; experts write to tasks/.
        assert "patients/" in write_scope, (a["name"], write_scope)
        assert ("tasks/" in write_scope) or ("audit/" in write_scope), (a["name"], write_scope)
