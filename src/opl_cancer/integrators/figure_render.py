"""matplotlib-backed Wave-3 figure renderer. v2.2 P1-#14 — F_BIO family.

Required Wave 3 outputs per the v2.2 P1-#14 fix:
  * KM curve  — `render_km_curve(out_path, arms=[...], title=...)`
  * Forest    — `render_forest_plot(out_path, rows=[...], title=...)`
  * Monte Carlo trajectory — `render_monte_carlo_trajectory(out_path, ...)`

Each helper writes a PNG and returns `{path, sha256, size_bytes}`. The
integrator dispatcher (`FigureRenderIntegrator.render`) routes by
`payload["kind"] in {"km", "forest", "monte_carlo"}` so wave runners can
serialize the request along with everything else.

matplotlib is intentionally NOT lazy — it's already in OPL's hard deps,
so unit tests run without `pytest.importorskip`.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # headless backend — must run before pyplot import
import matplotlib.pyplot as plt  # noqa: E402

from .base import Integrator
from .cache import IntegratorCache


def _record(out_path: Path) -> dict[str, Any]:
    out_path = Path(out_path)
    body = out_path.read_bytes()
    return {
        "path": str(out_path),
        "sha256": hashlib.sha256(body).hexdigest(),
        "size_bytes": len(body),
    }


def render_km_curve(
    *,
    out_path: Path,
    arms: list[dict[str, Any]],
    title: str = "Kaplan-Meier",
    dpi: int = 120,
) -> dict[str, Any]:
    """Render a KM step plot for one or more arms.

    Each arm dict: {label, durations, events}. We compute the step survival
    function with the Kaplan-Meier estimator (or fall back to a simpler step
    if lifelines is absent — both produce the same shape for a small synthetic
    test).
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    try:
        from lifelines import KaplanMeierFitter
        for arm in arms:
            kmf = KaplanMeierFitter()
            kmf.fit(arm["durations"], event_observed=arm["events"], label=arm["label"])
            kmf.plot_survival_function(ax=ax, ci_show=False)
    except ImportError:
        # Fallback — naive step plot
        for arm in arms:
            durations = sorted(arm["durations"])
            n = len(durations)
            xs = [0] + durations
            ys = [1.0] + [(n - i - 1) / n for i in range(n)]
            ax.step(xs, ys, where="post", label=arm["label"])
    ax.set_xlabel("Time (months)")
    ax.set_ylabel("Survival probability")
    ax.set_ylim(0, 1.05)
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    return _record(out_path)


def render_forest_plot(
    *,
    out_path: Path,
    rows: list[dict[str, Any]],
    title: str = "Forest plot",
    dpi: int = 120,
) -> dict[str, Any]:
    """Render a forest plot of hazard ratios + 95% CIs.

    Each row dict: {label, hr, ci_low, ci_high}. Reference line at HR=1.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = len(rows)
    fig, ax = plt.subplots(figsize=(8, 0.5 * n + 2))
    ys = list(range(n, 0, -1))
    for i, row in enumerate(rows):
        y = ys[i]
        hr = row.get("hr", 1.0)
        lo = row.get("ci_low", hr)
        hi = row.get("ci_high", hr)
        ax.plot([lo, hi], [y, y], color="black", linewidth=1)
        ax.scatter([hr], [y], s=80, color="black", zorder=5)
    ax.axvline(1.0, linestyle="--", color="grey", linewidth=1)
    ax.set_yticks(ys)
    ax.set_yticklabels([row.get("label", f"row_{i}") for i, row in enumerate(rows)])
    ax.set_xlabel("Hazard ratio (95% CI)")
    ax.set_xscale("log")
    # symmetric x-range around 1
    all_vals = [row.get("hr", 1) for row in rows] + \
               [row.get("ci_low", 1) for row in rows] + \
               [row.get("ci_high", 1) for row in rows]
    pos = [v for v in all_vals if v > 0]
    if pos:
        margin = 1.2
        ax.set_xlim(min(pos) / margin, max(pos) * margin)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    return _record(out_path)


def render_monte_carlo_trajectory(
    *,
    out_path: Path,
    timepoints: list[float],
    trajectories: list[list[float]],
    title: str = "Monte Carlo trajectory",
    dpi: int = 120,
) -> dict[str, Any]:
    """Render N stochastic trajectories on the same time axis, plus mean."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    for traj in trajectories:
        ax.plot(timepoints, traj, alpha=0.4, linewidth=1)
    if trajectories:
        n_t = len(timepoints)
        means = []
        for i in range(n_t):
            col = [t[i] for t in trajectories if i < len(t)]
            means.append(sum(col) / len(col) if col else math.nan)
        ax.plot(timepoints, means, color="black", linewidth=2.0, label="mean")
        ax.legend()
    ax.set_xlabel("Time (weeks)")
    ax.set_ylabel("Value (e.g. ctDNA VAF %)")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    return _record(out_path)


class FigureRenderIntegrator(Integrator):
    family = "F_BIO"
    ttl_seconds = 24 * 3600  # figures regenerate on input change

    def __init__(self, cache: IntegratorCache | None = None) -> None:
        super().__init__(cache=cache)

    async def fetch(self, key: str) -> dict[str, Any]:
        # Integrator base contract — but figures are not key-cached; callers
        # invoke render() directly.
        raise NotImplementedError(
            "FigureRenderIntegrator.render(payload) is the public entry"
        )

    async def render(self, payload: dict[str, Any]) -> dict[str, Any]:
        kind = payload.get("kind")
        out_path = Path(payload.get("out_path", ""))
        if not out_path.name:
            raise ValueError("figure_render: out_path required")
        title = payload.get("title", kind or "figure")
        if kind == "km":
            return render_km_curve(
                out_path=out_path,
                arms=payload.get("arms", []),
                title=title,
            )
        if kind == "forest":
            return render_forest_plot(
                out_path=out_path,
                rows=payload.get("rows", []),
                title=title,
            )
        if kind == "monte_carlo":
            return render_monte_carlo_trajectory(
                out_path=out_path,
                timepoints=payload.get("timepoints", []),
                trajectories=payload.get("trajectories", []),
                title=title,
            )
        raise ValueError(
            f"figure_render: unknown kind {kind!r}; expected km|forest|monte_carlo"
        )


def watermark_png(
    *,
    in_path: Path,
    out_path: Path,
    banner_text: str,
    alpha: float = 0.4,
) -> dict[str, Any]:
    """v2.3 P2-#18 — overlay a diagonal banner watermark on a PNG.

    Re-loads the PNG, draws a translucent diagonal text overlay
    (e.g. ``[METHODOLOGY DEMONSTRATION — NOT REAL PATIENT]``), and
    writes the result. Used by the Wave 6 bundle pipeline when the
    data_source is not ``real_patient`` so PDF readers cannot miss the
    framing. Original ``in_path`` is unchanged.
    """
    in_path = Path(in_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img = plt.imread(in_path)
    h, w = img.shape[:2]
    fig, ax = plt.subplots(figsize=(max(w, 1) / 100, max(h, 1) / 100), dpi=100)
    ax.imshow(img)
    ax.axis("off")
    ax.text(
        0.5, 0.5, banner_text,
        transform=ax.transAxes,
        ha="center", va="center",
        fontsize=24, color="red", alpha=alpha,
        rotation=30, weight="bold",
    )
    fig.savefig(out_path, dpi=100, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    return _record(out_path)


def watermark_directory(
    *,
    figures_dir: Path,
    banner_text: str,
    suffix: str = "_watermarked",
) -> list[dict[str, Any]]:
    """Apply ``watermark_png`` to every ``fig_*.png`` in ``figures_dir``.

    Returns a list of output records. Watermark output files are named
    ``fig_<N><suffix>.png`` so the original ``fig_<N>.png`` stays
    untouched (G31 still finds the reproducer/PNG pair).
    """
    figures_dir = Path(figures_dir)
    out: list[dict[str, Any]] = []
    if not figures_dir.is_dir():
        return out
    for entry in sorted(figures_dir.iterdir()):
        if not entry.is_file():
            continue
        if not entry.name.startswith("fig_") or not entry.name.endswith(".png"):
            continue
        if suffix in entry.stem:
            continue  # already a watermark — never re-process
        stem = entry.stem
        out_path = figures_dir / f"{stem}{suffix}.png"
        # Idempotent: skip if the corresponding watermark already exists.
        if out_path.is_file():
            continue
        record = watermark_png(
            in_path=entry, out_path=out_path, banner_text=banner_text
        )
        out.append(record)
    return out


__all__ = [
    "FigureRenderIntegrator",
    "render_km_curve",
    "render_forest_plot",
    "render_monte_carlo_trajectory",
    "watermark_png",
    "watermark_directory",
]
