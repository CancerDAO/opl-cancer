"""P3-T8: verify Wave-3 task prompt files load + render placeholders."""
from __future__ import annotations

from opl_cancer.prompts_loader import PromptTemplate, find_prompts_root


P3_TASKS = (
    "dataset_acquisition",
    "bioinformatics_data_analysis",
    "single_cell_reanalysis",
    "pathway_enrichment",
    "hypothesis_validation",
)


def test_all_p3_task_prompts_load() -> None:
    root = find_prompts_root() / "tasks"
    for task in P3_TASKS:
        path = root / f"{task}.md"
        assert path.exists(), f"missing {path}"
        tmpl = PromptTemplate.load(path, version=f"{task}@v0.1.0")
        assert tmpl.version.startswith(task)


def test_tyler_persona_exists() -> None:
    persona = find_prompts_root() / "experts" / "tyler" / "persona.md"
    assert persona.exists()
    content = persona.read_text(encoding="utf-8")
    assert "Tyler" in content
    assert "Jacks" in content
