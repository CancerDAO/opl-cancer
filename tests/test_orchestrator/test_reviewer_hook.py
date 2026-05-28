"""v2.1 P0-#7: reviewer_hook auto-dispatches distinct-model+distinct-expert
reviewer after each expert write."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from opl_cancer.orchestrator.reviewer_hook import run_reviewer_pairing


def test_reviewer_runs_after_expert_write(tmp_path: Path) -> None:
    report_path = tmp_path / "report.md"
    report_path.write_text("Claim X [PMID:12345].")
    with patch(
        "opl_cancer.orchestrator.reviewer_hook._dispatch_reviewer_subagent"
    ) as disp:
        disp.return_value = {"g1_passed": True, "g2_passed": True, "findings": []}
        result = run_reviewer_pairing(
            report_path=report_path,
            primary_expert="bert",
            primary_model="claude-opus-4-7",
        )
        assert result["status"] == "pass"
        review_json = tmp_path / "review.json"
        assert review_json.exists()
        disp.assert_called_once()
        kwargs = disp.call_args.kwargs
        # reviewer must use a distinct expert AND distinct model
        assert kwargs["reviewer_expert"] != "bert"
        assert kwargs["reviewer_model"] != "claude-opus-4-7"


def test_reviewer_fail_propagates(tmp_path: Path) -> None:
    report_path = tmp_path / "report.md"
    report_path.write_text("Claim X.")
    with patch(
        "opl_cancer.orchestrator.reviewer_hook._dispatch_reviewer_subagent"
    ) as disp:
        disp.return_value = {"g1_passed": False, "g2_passed": True, "findings": [
            {"gate": "G1", "msg": "PMID not found"},
        ]}
        result = run_reviewer_pairing(
            report_path=report_path,
            primary_expert="rosa",
            primary_model="claude-opus-4-7",
        )
        assert result["status"] == "fail"


def test_reviewer_distinct_when_primary_minimax(tmp_path: Path) -> None:
    report_path = tmp_path / "report.md"
    report_path.write_text("Claim X.")
    with patch(
        "opl_cancer.orchestrator.reviewer_hook._dispatch_reviewer_subagent"
    ) as disp:
        disp.return_value = {"g1_passed": True, "g2_passed": True, "findings": []}
        run_reviewer_pairing(
            report_path=report_path,
            primary_expert="iain",
            primary_model="minimax-m2.7",
        )
        kwargs = disp.call_args.kwargs
        assert kwargs["reviewer_model"] != "minimax-m2.7"
        assert kwargs["reviewer_expert"] != "iain"
