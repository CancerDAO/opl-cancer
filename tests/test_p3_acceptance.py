"""P3 acceptance suite — high-level smoke over the P3 surface area."""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest


P3_INTEGRATOR_MODULES = (
    "opl_cancer.integrators.geo",
    "opl_cancer.integrators.arrayexpress",
    "opl_cancer.integrators.sra",
    "opl_cancer.integrators.depmap",
    "opl_cancer.integrators.ccle",
)

P3_TASK_PROMPTS = (
    "dataset_acquisition",
    "bioinformatics_data_analysis",
    "single_cell_reanalysis",
    "pathway_enrichment",
    "hypothesis_validation",
)


@pytest.mark.parametrize("modname", P3_INTEGRATOR_MODULES)
def test_p3_integrators_importable(modname: str) -> None:
    mod = importlib.import_module(modname)
    assert mod is not None


def test_tyler_module_importable() -> None:
    mod = importlib.import_module("opl_cancer.experts.tyler")
    assert hasattr(mod, "TylerExpert")


def test_tyler_in_roster() -> None:
    from opl_cancer.experts.roster import get_expert_profile

    assert get_expert_profile("tyler").name == "tyler"


def test_aviv_has_p3_portfolio_extension() -> None:
    from opl_cancer.experts.aviv import AvivExpert

    portfolio = set(AvivExpert.portfolio)
    assert "dataset_acquisition" in portfolio
    assert "bioinformatics_data_analysis" in portfolio
    assert "F7" in AvivExpert.preferred_families


def test_wave3_runner_importable() -> None:
    from opl_cancer.glue.wave3_runner import Wave3Runner

    assert Wave3Runner is not None


def test_bixbench_dockerfile_present() -> None:
    df = (
        Path(__file__).resolve().parent.parent
        / "src/opl_cancer/compute/bixbench.Dockerfile"
    )
    assert df.exists()
    assert "miniconda3" in df.read_text(encoding="utf-8")


def test_bixbench_runner_dry_run_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPL_BIXBENCH_LIVE", raising=False)
    from opl_cancer.compute import BixbenchRunner

    nb = tmp_path / "nb.ipynb"
    nb.write_text("{}", encoding="utf-8")
    r = BixbenchRunner().run_notebook(notebook_path=nb, workdir=tmp_path)
    assert r.mode == "dry-run"


@pytest.mark.parametrize("task", P3_TASK_PROMPTS)
def test_p3_task_prompts_present(task: str) -> None:
    from opl_cancer.llm.prompts import find_prompts_root

    p = find_prompts_root() / "tasks" / f"{task}.md"
    assert p.exists()


def test_tyler_in_roster_persona_path() -> None:
    from opl_cancer.llm.prompts import find_prompts_root

    p = find_prompts_root() / "experts" / "tyler" / "persona.md"
    assert p.exists()
    assert "Tyler" in p.read_text(encoding="utf-8")


def test_bixbench_image_tag_versioned() -> None:
    from opl_cancer.compute import BIXBENCH_IMAGE_TAG

    assert "v0.3.0" in BIXBENCH_IMAGE_TAG


def test_p3_integrator_families() -> None:
    from opl_cancer.integrators.arrayexpress import ArrayExpressIntegrator
    from opl_cancer.integrators.ccle import CCLEIntegrator
    from opl_cancer.integrators.depmap import DepMapIntegrator
    from opl_cancer.integrators.geo import GEOIntegrator
    from opl_cancer.integrators.sra import SRAIntegrator

    assert GEOIntegrator.family == "F6"
    assert ArrayExpressIntegrator.family == "F6"
    assert SRAIntegrator.family == "F6"
    assert DepMapIntegrator.family == "F7"
    assert CCLEIntegrator.family == "F7"
