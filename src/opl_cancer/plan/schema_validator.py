"""v2.1 P0-#5: profile schema validation + trigger field alignment.

``validate_profile(profile_dict, strict_triggers=False)``:

* JSON-Schema validate against ``schemas/profile.schema.json``.
* If ``strict_triggers`` is True, additionally assert every profile key is
  either present in the schema ``properties`` map OR in
  ``comorbid_planner.TRIGGER_KEYS``. This catches typo bugs like
  ``active_irrae`` → ``active_irae`` where the comorbid expansion silently
  fails to fire.

ADR-0021 invariant: plan emission CALLS this hard. A run that would have
fired Mark for active irAE but didn't because of a profile typo must blow
up at plan time, not deliver a silently-incomplete brief.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

from opl_cancer.plan.comorbid_planner import TRIGGER_KEYS

# Search up from this file: src/opl_cancer/plan/schema_validator.py → repo
# root has the schemas/ directory.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_SCHEMA_PATH = _REPO_ROOT / "schemas" / "profile.schema.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text())
_SCHEMA_KEYS: set[str] = set(_SCHEMA.get("properties", {}).keys())


class ProfileTriggerMismatch(ValueError):
    """Raised when profile.json contains keys neither in schema nor in
    ``TRIGGER_KEYS``. Almost always a typo — surface a Did-you-mean."""


def validate_profile(profile: dict[str, Any], strict_triggers: bool = False) -> None:
    jsonschema.validate(profile, _SCHEMA)
    if not strict_triggers:
        return
    unknown = [k for k in profile if k not in _SCHEMA_KEYS and k not in TRIGGER_KEYS]
    if unknown:
        # Compute Did-you-mean suggestion for each unknown key.
        import difflib

        all_known = sorted(_SCHEMA_KEYS | TRIGGER_KEYS)
        hints: list[str] = []
        for k in unknown:
            close = difflib.get_close_matches(k, all_known, n=3, cutoff=0.5)
            if close:
                hints.append(f"{k!r} → did you mean {close}?")
            else:
                hints.append(f"{k!r} (no close match)")
        raise ProfileTriggerMismatch(
            "profile keys not in schema or trigger table:\n  "
            + "\n  ".join(hints)
            + "\n\nFix: add the key to schemas/profile.schema.json properties "
              "OR to comorbid_planner.TRIGGER_KEYS — whichever applies."
        )
