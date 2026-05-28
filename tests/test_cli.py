"""Test CLI subcommands skeleton."""
from pathlib import Path

from click.testing import CliRunner

from opl_cancer.cli import main


def test_cli_status_runs() -> None:
    r = CliRunner().invoke(main, ["status"])
    assert r.exit_code == 0
    # v1.4.0 — Round-2/3 deferred backlog batch fix (A1-A5 + B1-B6):
    #   - 11 backlog items closed (5 priority A + 6 priority B)
    #   - HKCTR integrator wired (28 → 29)
    #   - mechanical gate count unchanged (23)
    #   - 3 new task packages: surveillance_schedule + caregiver_filter_protocol + patient_pushback_handling (38 → 41)
    #   - 2 substantive task package extensions: irae_rechallenge (multi-organ schema) + n1_cohort_projection (fallback + lab_trajectory) + boundary_unregulated (retrospective)
    #   - intent_parser.md: delivery_tone_hint extraction
    #   - SKILL.md Step 4: TNBC + LM planner row
    #   - cli.py acknowledge --batch ack-batch UX + ack_consolidation_card
    assert "OPL for Cancer" in r.output
    assert "v2.2.0" in r.output  # v2.2.0 Equipped Experts release (ADR-0022)
    # v2.0.0 (ADR-0010): roster expanded 18 → 20 with Maya + Julius
    assert "Experts active: 20" in r.output
    # v2.2 (ADR-0022): G28 absolute_date added (P1-#15 LLM 5wk/5mo fix). 27 → 28.
    assert "Mechanical gates: 28" in r.output
    # v2.2 (ADR-0022): +7 bio-skill integrators (MSI/TMB/SigProfiler/ACMG/KM/CPIC/PaperQA-FT)
    assert "Integrators wired: 36" in r.output


def test_cli_init_patient_runs(tmp_path: Path) -> None:
    r = CliRunner().invoke(
        main, ["init-patient", "anon_test", "--root", str(tmp_path)]
    )
    assert r.exit_code == 0
    assert (tmp_path / "anon_test" / "memory").exists()
    assert (tmp_path / "anon_test" / "pi_session").exists()
    assert (tmp_path / "anon_test" / "inbox").exists()
    assert (tmp_path / "anon_test" / "triggers").exists()


def test_cli_list_experts_runs() -> None:
    r = CliRunner().invoke(main, ["list-experts"])
    assert r.exit_code == 0
    for name in ("sid", "rosa", "bert", "vince"):
        assert name in r.output
