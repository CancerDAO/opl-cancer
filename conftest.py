"""Root pytest configuration.

Two jobs:

1. Park the evolution/self-improvement test suite. Per
   docs/iteration/HARNESS_SPLIT_PRD.md + docs/iteration/EVOLUTION_EXTRACTION_TODO.md
   the orchestrator/* + evolution/* engine is being extracted to a standalone
   ``opl-cancer-evolution`` repo. Its tests still import the now-deleted
   ``opl_cancer.llm`` module (the patient path no longer calls an LLM in
   Python — reasoning is the host agent's job). They are ignored here so the
   patient-repo suite is green; they travel to the extraction repo with their
   code. Do NOT delete them — they are the only coverage for that engine.

2. Note for contributors: this repo is not editable-installed in every env.
   Run the suite with::

       PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q

   (PYTHONPATH so ``opl_cancer`` resolves; PYTEST_DISABLE_PLUGIN_AUTOLOAD so an
   env-level dash/jupyter pytest plugin can't break collection — audit P1-7.)
"""

# Extraction-bound tests: code still present, pending move to opl-cancer-evolution.
collect_ignore = [
    "tests/test_orchestrator/test_debate_judge.py",
    "tests/test_orchestrator/test_evolution.py",
    "tests/test_orchestrator/test_generation.py",
    "tests/test_orchestrator/test_meta_critique.py",
    "tests/test_orchestrator/test_pi_session_llm.py",
    "tests/test_orchestrator/test_reflection.py",
    "tests/test_orchestrator/test_tournament_loop.py",
    "tests/test_e2e/test_p2_hypothesis_e2e.py",
    "tests/test_glue/test_wave2_runner.py",
    "tests/test_p2_acceptance.py",
]
