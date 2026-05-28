"""G31: figure_reproducible — Wave 6 manuscript invariant.

Spec §5.3 (ADR-0023). Each ``figures/fig_N.png`` MUST have a matching
``figures/fig_N.py`` reproducer. If the reproducer declares
``random_seed = X``, the seed is logged in the gate result. Otherwise the
gate flags potential stochasticity (PASS-with-warning style — we still
PASS because Wave 3 may use deterministic SVG renders that don't need
seeds, but the warning surfaces in evidence).

Failure modes guarded:
* F-WAVE6-FIG-ORPHAN-PNG: PNG exists without reproducer ``.py``.
* F-WAVE6-FIG-ORPHAN-SCRIPT: ``.py`` exists without rendered PNG.

The gate accepts:
* ``figures_dir`` — direct path, OR
* ``bundle_root`` — directory containing ``figures/``.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus


_FIG_PNG_RE = re.compile(r"^fig_(\d+|[a-zA-Z0-9_\-]+)\.png$")
_FIG_PY_RE = re.compile(r"^fig_(\d+|[a-zA-Z0-9_\-]+)\.py$")
_SEED_RE = re.compile(
    r"^\s*(?:random_seed|np_seed|seed)\s*=\s*(\d+)",
    re.MULTILINE,
)


def _resolve_figures_dir(claim: dict[str, Any]) -> Path | None:
    if (d := claim.get("figures_dir")):
        p = Path(d)
        return p if p.is_dir() else None
    if (root := claim.get("bundle_root")):
        p = Path(root) / "figures"
        return p if p.is_dir() else None
    return None


class G31FigureReproducibleGate(Gate):
    name = "G31_figure_reproducible"
    description = (
        "Each figures/fig_N.png must have a matching figures/fig_N.py "
        "reproducer. Stochastic reproducers must declare random_seed = X."
    )
    failure_mode_code = "F-WAVE6-FIG-REPRO"

    def check(self, claim: dict[str, Any]) -> GateResult:
        stage = (claim.get("run_stage") or claim.get("wave") or "").lower()
        if stage and not (
            "wave6" in stage
            or stage in {"manuscript", "n1a_bundle", "delivery"}
            or stage == "6"
        ):
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message=f"G31 SKIP — non-wave6 stage {stage!r}",
            )

        figures_dir = _resolve_figures_dir(claim)
        if figures_dir is None:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message=(
                    "G31 SKIP — no figures_dir / bundle_root pointing to "
                    "an existing figures/ directory."
                ),
            )

        pngs: dict[str, Path] = {}
        pys: dict[str, Path] = {}
        for entry in figures_dir.iterdir():
            if not entry.is_file():
                continue
            if m := _FIG_PNG_RE.match(entry.name):
                pngs[m.group(1)] = entry
            elif m := _FIG_PY_RE.match(entry.name):
                pys[m.group(1)] = entry

        orphan_png = sorted(set(pngs) - set(pys))
        orphan_py = sorted(set(pys) - set(pngs))

        if orphan_png:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"G31 FAIL — {len(orphan_png)} PNG(s) without matching .py "
                    f"reproducer: {orphan_png}. Add fig_<N>.py for each PNG."
                ),
                evidence={
                    "figures_dir": str(figures_dir),
                    "orphan_png": orphan_png,
                    "remediation": "add_matching_reproducer_py_files",
                },
            )

        if orphan_py:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"G31 FAIL — {len(orphan_py)} reproducer .py without rendered "
                    f"PNG: {orphan_py}. Run the reproducer or remove the script."
                ),
                evidence={
                    "figures_dir": str(figures_dir),
                    "orphan_py": orphan_py,
                    "remediation": "render_png_or_remove_orphan_py",
                },
            )

        if not pngs:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message="G31 SKIP — no figures present.",
                evidence={"figures_dir": str(figures_dir)},
            )

        # Inspect each .py for seed declarations.
        seeds: dict[str, int | None] = {}
        stochastic_unseeded: list[str] = []
        for ident, py_path in pys.items():
            try:
                src = py_path.read_text(encoding="utf-8")
            except OSError:
                seeds[ident] = None
                continue
            m = _SEED_RE.search(src)
            if m:
                seeds[ident] = int(m.group(1))
            else:
                # Heuristic stochasticity check: uses np.random or random.
                if re.search(r"\b(?:np\.random|numpy\.random|random\.(?:rand|randint|choice|sample|shuffle|gauss|normal))\b", src):
                    stochastic_unseeded.append(ident)
                seeds[ident] = None

        warning = ""
        if stochastic_unseeded:
            warning = (
                f" WARNING: {len(stochastic_unseeded)} reproducer(s) appear "
                f"stochastic without random_seed declaration: {stochastic_unseeded}."
            )

        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=(
                f"G31 OK — {len(pngs)} figure(s) each have matching .py reproducer."
                + warning
            ),
            evidence={
                "figures_dir": str(figures_dir),
                "figures": sorted(pngs.keys()),
                "seeds": seeds,
                "stochastic_unseeded": stochastic_unseeded,
            },
        )
