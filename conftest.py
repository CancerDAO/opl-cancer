"""Root pytest configuration.

Note for contributors: this repo is not editable-installed in every env.
Run the suite with::

    PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q

(PYTHONPATH so ``opl_cancer`` resolves; PYTEST_DISABLE_PLUGIN_AUTOLOAD so an
env-level dash/jupyter pytest plugin can't break collection — audit P1-7.)

History: the orchestrator/* + evolution/* engine tests used to be parked here
(``collect_ignore``) while that engine was being extracted to a standalone
``opl-cancer-evolution`` repo — they imported the deleted ``opl_cancer.llm``
package. Founder decision A (docs/iteration/IMPLEMENTATION_STATUS.md) REVERSED
that extraction: the tournament + evolution engine stays in the patient path.
The tests now import the in-repo ``opl_cancer._llm_contract`` shim and run as
first-class coverage of the engine, so the park is gone.
"""
