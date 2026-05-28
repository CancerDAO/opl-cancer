"""Tests for v2.2 P1-#16 atomic delivery_runner.

Henry audit + patient_plain_brief + patient_pi_brief must run as ONE
transaction. Partial failure rolls back — no half-shipped delivery
(plain brief written but Henry audit hadn't run yet, etc.).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from opl_cancer.glue.delivery_runner import (
    DeliveryFailure,
    DeliveryRunner,
    run_atomic_delivery,
)


def test_delivery_runner_dry_run_creates_no_files(tmp_path: Path) -> None:
    runner = DeliveryRunner(out_dir=tmp_path, dry_run=True)
    out = runner.run()
    assert out["status"] == "dry_run"
    # No real files
    assert not (tmp_path / "patient_plain_brief.md").exists()
    assert not (tmp_path / "patient_pi_brief.md").exists()
    assert not (tmp_path / "HENRY_AUDIT.json").exists()


def test_delivery_runner_succeeds_writes_three_artifacts(tmp_path: Path) -> None:
    runner = DeliveryRunner(out_dir=tmp_path)
    out = runner.run()
    assert out["status"] == "ok"
    assert (tmp_path / "HENRY_AUDIT.json").exists()
    assert (tmp_path / "patient_plain_brief.md").exists()
    assert (tmp_path / "patient_pi_brief.md").exists()
    # Manifest tracks them
    assert len(out["written_files"]) == 3


def test_delivery_runner_rollback_on_pi_brief_failure(tmp_path: Path) -> None:
    """If PI brief render raises, the plain brief + Henry audit must roll back."""
    runner = DeliveryRunner(out_dir=tmp_path)
    with patch.object(
        DeliveryRunner, "_render_pi_brief", side_effect=RuntimeError("pi render failed")
    ):
        with pytest.raises(DeliveryFailure):
            runner.run()
    # All three must be absent
    assert not (tmp_path / "HENRY_AUDIT.json").exists()
    assert not (tmp_path / "patient_plain_brief.md").exists()
    assert not (tmp_path / "patient_pi_brief.md").exists()


def test_delivery_runner_rollback_on_henry_failure(tmp_path: Path) -> None:
    runner = DeliveryRunner(out_dir=tmp_path)
    with patch.object(
        DeliveryRunner, "_run_henry_audit", side_effect=RuntimeError("henry failed")
    ):
        with pytest.raises(DeliveryFailure):
            runner.run()
    assert not (tmp_path / "HENRY_AUDIT.json").exists()
    assert not (tmp_path / "patient_plain_brief.md").exists()
    assert not (tmp_path / "patient_pi_brief.md").exists()


def test_run_atomic_delivery_top_level_wrapper(tmp_path: Path) -> None:
    """Convenience wrapper for cli.py — same atomicity contract."""
    out = run_atomic_delivery(out_dir=tmp_path)
    assert out["status"] == "ok"
    assert (tmp_path / "HENRY_AUDIT.json").exists()


def test_atomicity_marker_present_after_success(tmp_path: Path) -> None:
    """After a successful atomic delivery, the manifest carries
    `atomic_commit: true` so downstream consumers can verify the
    transaction completed."""
    out = run_atomic_delivery(out_dir=tmp_path)
    manifest = tmp_path / "delivery_manifest.json"
    assert manifest.exists()
    import json
    body = json.loads(manifest.read_text())
    assert body["atomic_commit"] is True
    assert "written_files" in body
