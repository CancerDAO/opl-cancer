"""Test CLI subcommands skeleton."""
import json
from pathlib import Path

from click.testing import CliRunner

from opl_cancer.cli import main


def test_cli_progress_renders_dashboard() -> None:
    r = CliRunner().invoke(main, [
        "progress", "--run-id", "run-x", "--phase", "Wave1 查证据",
        "--detail", "Bert(遗传) 解读 NGS — 3/20", "--eta", "~12–18 min",
    ])
    assert r.exit_code == 0
    assert "▶Wave1 查证据" in r.output and "4/9" in r.output
    assert "Bert(遗传) 解读 NGS — 3/20" in r.output


def test_cli_progress_rejects_unknown_phase() -> None:
    r = CliRunner().invoke(main, ["progress", "--run-id", "r", "--phase", "zzz"])
    assert r.exit_code != 0


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
    # Version is derived from the package single-source-of-truth (no drift);
    # assert dynamically so the test moves with every bump automatically.
    from opl_cancer import __version__
    assert f"v{__version__}" in r.output
    # v2.0.0 (ADR-0010): roster expanded 18 → 20 with Maya + Julius
    assert "Experts active: 20" in r.output
    # v2.3 (ADR-0023): G29-G33 added (Wave 6 manuscript invariants). 28 → 33.
    # v2.7.0 (ADR-0026): G34-G37 delivery-integrity gates. 33 → 37.
    # v2.7.1 (ADR-0026 P1): G39-G43 reasoning-quality gates (G38 reserved). 37 → 42.
    # v2.8 research-team iteration: +G54 (A1 ledger, ADR-0027) +G45/G46 (B1
    # false-hope firewall, ADR-0029) +G48 (A3 research-delta, ADR-0028) +G52 (C3
    # failure-ledger, ADR-0033) +G47 (B2 read-deep, ADR-0030) +G49 (C2 forecast
    # pre-registration, ADR-0032) +G50/G51 (C1 honest tournament, ADR-0031). G44
    # reserved for the in-flight retrieval-standardization branch. +G53/G55 (D1
    # outcome-backward planner, ADR-0034). 42 → 53.
    # v2.12.0 (ADR-0042): +G60 insight_abstraction_written (WARN). G56-G59 reserved
    # for the parallel value-source/CRC branch. 53 → 54.
    assert "Mechanical gates: 54" in r.output
    # v2.2 (ADR-0022): +7 bio-skill integrators (MSI/TMB/SigProfiler/ACMG/KM/CPIC/PaperQA-FT)
    assert "Integrators wired: 36" in r.output
    # v2.3 (ADR-0023): Wave 6 manuscript+.n1a wave runner.
    assert "Wave6" in r.output


def test_cli_wave6_help_lists_command() -> None:
    """The `opl wave6` command must be in the help output."""
    r = CliRunner().invoke(main, ["--help"])
    assert r.exit_code == 0
    assert "wave6" in r.output


def test_cli_wave6_refuses_without_wave5(tmp_path: Path) -> None:
    """`opl wave6` must fail with exit_code 2 when Wave 5 outputs missing."""
    patient_dir = tmp_path / "patient"
    (patient_dir / "triggers" / "abc").mkdir(parents=True)
    r = CliRunner().invoke(
        main,
        [
            "wave6",
            "--patient-dir", str(patient_dir),
            "--run-id", "abc",
            "--patient-code", "cli-test",
            "--final",
            "--json",
        ],
    )
    assert r.exit_code == 2
    assert "wave5_prerequisite_missing" in r.output


def test_cli_wave6_dry_run_returns_plan(tmp_path: Path) -> None:
    """`opl wave6 --dry-run` returns the planned steps without writing disk."""
    patient_dir = tmp_path / "patient"
    run_dir = patient_dir / "triggers" / "abc"
    run_dir.mkdir(parents=True)
    (run_dir / "patient_plain_brief.md").write_text("p", encoding="utf-8")
    (run_dir / "patient_pi_brief.md").write_text("p", encoding="utf-8")
    r = CliRunner().invoke(
        main,
        [
            "wave6",
            "--patient-dir", str(patient_dir),
            "--run-id", "abc",
            "--patient-code", "cli-test",
            "--dry-run",
            "--json",
        ],
    )
    assert r.exit_code == 0
    assert "dry_run" in r.output


def test_cli_init_patient_runs(tmp_path: Path) -> None:
    r = CliRunner().invoke(
        main, ["init-patient", "anon_test", "--root", str(tmp_path)]
    )
    assert r.exit_code == 0
    assert (tmp_path / "anon_test" / "memory").exists()
    assert (tmp_path / "anon_test" / "pi_session").exists()
    assert (tmp_path / "anon_test" / "inbox").exists()
    assert (tmp_path / "anon_test" / "triggers").exists()


def test_cli_integrator_plugins_json() -> None:
    r = CliRunner().invoke(main, ["integrator-plugins", "--json"])
    assert r.exit_code == 0, r.output
    payload = json.loads(r.output)
    names = {row["name"] for row in payload["integrators"]}
    assert {"pubmed", "opentargets", "clinicaltrials", "cbioportal", "oncokb"} <= names
    assert payload["entry_point_group"] == "opl_cancer.integrators"


def test_cli_list_experts_runs() -> None:
    r = CliRunner().invoke(main, ["list-experts"])
    assert r.exit_code == 0
    for name in ("sid", "rosa", "bert", "vince"):
        assert name in r.output
