"""CLI evolve subcommand tests."""
from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from opl_cancer.cli import main


def _make_synthetic_run(tmp_path: Path) -> Path:
    """Construct a minimally-valid run dir with deliberately weak Wave 2."""
    run_dir = tmp_path / "run-synthetic-cli"
    run_dir.mkdir()
    (run_dir / "tasks").mkdir()
    (run_dir / "tasks" / "w1_bert").mkdir()
    (run_dir / "tasks" / "w1_bert" / "report.md").write_text("ok\n", encoding="utf-8")
    (run_dir / "wave2_hypotheses.json").write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "id": "h1",
                        "claim_layer": "established",
                        "generation_strategy": "literature_gap",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "delivery").mkdir()
    (run_dir / "delivery" / "patient_brief.html").write_text(
        "<html>summary</html>", encoding="utf-8"
    )
    return run_dir


def test_evolve_writes_proposals_dir(tmp_path: Path):
    run_dir = _make_synthetic_run(tmp_path)
    r = CliRunner().invoke(main, ["evolve", str(run_dir), "--iter-n", "1", "--json"])
    assert r.exit_code == 0, r.output
    payload = json.loads(r.output)
    assert payload["ok"] is True
    proposals_dir = Path(payload["proposals_dir"])
    assert proposals_dir.exists()
    assert (proposals_dir / "status.yaml").exists()
    assert (proposals_dir / "README.md").exists()


def test_evolve_never_writes_into_baseline(tmp_path: Path):
    """Per ADR-0020: evolve must write ONLY under <run_dir>/proposals/."""
    run_dir = _make_synthetic_run(tmp_path)
    # Seed a fake baseline
    baseline = tmp_path / "src" / "opl_cancer"
    baseline.mkdir(parents=True)
    (baseline / "sentinel.py").write_text("# sentinel", encoding="utf-8")

    r = CliRunner().invoke(main, ["evolve", str(run_dir), "--json"])
    assert r.exit_code == 0, r.output

    # sentinel untouched
    assert (baseline / "sentinel.py").read_text(encoding="utf-8") == "# sentinel"
    # only proposals/ dir under run_dir was created
    assert (run_dir / "proposals").exists()


def test_evolve_heuristic_fallback_marker_in_summary(tmp_path: Path):
    run_dir = _make_synthetic_run(tmp_path)
    r = CliRunner().invoke(main, ["evolve", str(run_dir), "--json"])
    payload = json.loads(r.output)
    # No LLM configured → heuristic
    assert payload["used_heuristic_fallback"] is True


def test_evolve_no_auto_apply_flag_exists():
    """Guarantees ADR-0020 §What we drop #5: there must be no --auto-apply."""
    r = CliRunner().invoke(main, ["evolve", "--help"])
    assert r.exit_code == 0
    assert "--auto-apply" not in r.output
    # Click wraps help text — normalise whitespace
    normalised = " ".join(r.output.split())
    assert "NEVER auto-applies" in normalised


def test_evolve_aims_at_disease_frontier(tmp_path: Path):
    """D4/ADR-0037: in the patient path (a run under <patient>/triggers/ with a
    research ledger), evolve feeds the disease-frontier digest so the analyzer
    learns about THIS disease, not OPL-the-software."""
    from opl_cancer.memory.schemas import Hypothesis
    from opl_cancer.memory.store import ProjectMemoryStore, default_patient_memory_db

    run_dir = tmp_path / "patients" / "PT-X" / "triggers" / "r1"
    run_dir.mkdir(parents=True)
    (run_dir / "tasks" / "w1_bert").mkdir(parents=True)
    (run_dir / "tasks" / "w1_bert" / "report.md").write_text("ok\n", encoding="utf-8")
    (run_dir / "wave2_hypotheses.json").write_text(
        json.dumps({"hypotheses": [{"id": "h1", "claim_layer": "speculative",
                                    "generation_strategy": "literature_gap"}]}),
        encoding="utf-8",
    )
    # seed the patient ledger: a falsified + an open-frontier hypothesis
    store = ProjectMemoryStore(default_patient_memory_db(run_dir))
    store.save_hypothesis(Hypothesis(id="H9", text="MTAP/PRMT5 synthetic lethality"), run_id="r1")
    store.save_hypothesis(Hypothesis(id="H2", text="dead end", status="falsified"), run_id="r1")

    r = CliRunner().invoke(main, ["evolve", str(run_dir), "--json"])
    assert r.exit_code == 0, r.output
    payload = json.loads(r.output)
    assert payload["ok"] is True
    assert "frontier" in payload["analysis_summary"].lower()


def test_evolve_registered_unconditionally():
    """D4/ADR-0037: evolution stays in the patient path — evolve is no longer
    conditionally registered behind a find_spec probe."""
    import opl_cancer.cli as cli_mod

    assert not hasattr(cli_mod, "_EVOLUTION_AVAILABLE")
    assert "evolve" in main.commands
