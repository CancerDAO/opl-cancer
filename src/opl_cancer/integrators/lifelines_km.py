"""lifelines-backed Kaplan-Meier + log-rank wrapper. v2.2 ADR-0022 — F_BIO.

source_skill_a: BioTender-max/awesome-bio-agent-skills/bio-clinical-biostatistics-survival-analysis
source_skill_b: BioTender-max/awesome-bio-agent-skills/bio-clinical-biostatistics-subgroup-analysis
original_license: CC0-1.0

`lifelines` (Davidson-Pilon) is the canonical Python survival library.
This wrapper exposes:
  * KM curve fit + median/CI extraction
  * log-rank test between two arms
  * subgroup filter helper (used by P1-#12 / #13 to narrow cBioPortal /
    TROP2-KRAS-G12C cohorts before KM)
  * a min-n-per-arm enforcement (G15 / G17 prereq — refuses to run on
    tiny cohorts where the p-value is uninterpretable)

Heavy-ish dep; lazy-import. Tests skip if not installed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .base import Integrator, IntegratorError
from .cache import IntegratorCache


def require_lifelines(*, strict: bool = True) -> bool:
    """Return True if lifelines is importable. Raise (or return False) otherwise."""
    try:
        import lifelines  # noqa: F401
        return True
    except ImportError:
        if strict:
            raise IntegratorError(
                "lifelines not installed. Install via the `[bio]` extras group: "
                "`pip install opl-cancer[bio]` or `pip install lifelines`. "
                "No silent fallback (no-silent-fallback policy)."
            )
        return False


@dataclass
class KMResult:
    median_months: float
    ci95_lower_months: float | None
    ci95_upper_months: float | None
    n_at_risk_start: int
    n_events: int
    engine: str
    label: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "median_months": self.median_months,
            "ci95_lower_months": self.ci95_lower_months,
            "ci95_upper_months": self.ci95_upper_months,
            "n_at_risk_start": self.n_at_risk_start,
            "n_events": self.n_events,
            "engine": self.engine,
            "label": self.label,
            **self.extra,
        }


def apply_subgroup_filter(
    cohort: Iterable[dict[str, Any]], filters: dict[str, Any]
) -> list[dict[str, Any]]:
    """Narrow a cohort iterable to rows where every filter key matches.

    Filter values may be a scalar (exact match) or a list/tuple/set (membership).
    P1-#12 (cBioPortal L3+ subset KM) + P1-#13 (TROP2 KRAS G12C subset filter)
    both use this helper before invoking the KM fit, so KM applies to a
    relevant cohort instead of the full denominator (which masks effect size).
    """
    out: list[dict[str, Any]] = []
    for row in cohort:
        match = True
        for k, want in filters.items():
            got = row.get(k)
            if isinstance(want, (list, tuple, set)):
                if got not in want:
                    match = False
                    break
            else:
                if got != want:
                    match = False
                    break
        if match:
            out.append(row)
    return out


class LifelinesKMIntegrator(Integrator):
    """Wrapper for KaplanMeierFitter + log-rank.

    family = ``F_BIO``. TTL 7 days (cohort-derived, refresh on new data).
    """

    family = "F_BIO"
    ttl_seconds = 7 * 24 * 3600

    def __init__(
        self,
        cache: IntegratorCache | None = None,
        *,
        min_n_per_arm: int = 5,
    ) -> None:
        super().__init__(cache=cache)
        self.min_n_per_arm = int(min_n_per_arm)

    async def fetch(self, key: str) -> dict[str, Any]:
        # Generic fetch dispatcher — most callers use fetch_km / fetch_logrank
        # directly. Key form: ``km:<label>`` or ``logrank:<a>:<b>``.
        raise IntegratorError(
            "LifelinesKM: use fetch_km(durations=..., events=..., label=...) "
            "or fetch_logrank(arm_a={...}, arm_b={...}) directly."
        )

    async def fetch_km(
        self,
        *,
        durations: list[float],
        events: list[int],
        label: str = "cohort",
    ) -> dict[str, Any]:
        if len(durations) != len(events):
            raise IntegratorError(
                f"LifelinesKM: durations({len(durations)}) != events({len(events)})"
            )
        n = len(durations)
        if n < self.min_n_per_arm:
            raise IntegratorError(
                f"LifelinesKM: cohort n={n} < min_n_per_arm={self.min_n_per_arm} "
                "(G15/G17 prereq — refuse small-n KM)."
            )
        require_lifelines(strict=True)
        from lifelines import KaplanMeierFitter

        kmf = KaplanMeierFitter()
        kmf.fit(durations, event_observed=events, label=label)
        median = float(kmf.median_survival_time_)
        # lifelines exposes a confidence_interval_ DataFrame; take the row
        # closest to the median for a CI snapshot.
        ci_low, ci_high = None, None
        try:
            ci_df = kmf.confidence_interval_
            # column names are like `<label>_lower_0.95`, `<label>_upper_0.95`
            low_col = [c for c in ci_df.columns if "lower" in c][0]
            high_col = [c for c in ci_df.columns if "upper" in c][0]
            # closest timepoint to median
            target_t = float(median) if median == median else 0.0  # NaN-safe
            idx = (ci_df.index - target_t).to_series().abs().idxmin()
            ci_low = float(ci_df.loc[idx, low_col])
            ci_high = float(ci_df.loc[idx, high_col])
        except Exception:  # pragma: no cover — defensive
            pass

        res = KMResult(
            median_months=median,
            ci95_lower_months=ci_low,
            ci95_upper_months=ci_high,
            n_at_risk_start=n,
            n_events=int(sum(events)),
            engine="lifelines",
            label=label,
        )
        return res.to_dict()

    async def fetch_logrank(
        self,
        *,
        arm_a: dict[str, Any],
        arm_b: dict[str, Any],
    ) -> dict[str, Any]:
        for name, arm in (("arm_a", arm_a), ("arm_b", arm_b)):
            n = len(arm.get("durations") or [])
            if n < self.min_n_per_arm:
                raise IntegratorError(
                    f"LifelinesKM logrank: {name} n={n} < min_n_per_arm="
                    f"{self.min_n_per_arm}. Refuse to compute uninterpretable p."
                )
        require_lifelines(strict=True)
        from lifelines.statistics import logrank_test

        result = logrank_test(
            arm_a["durations"], arm_b["durations"],
            event_observed_A=arm_a["events"],
            event_observed_B=arm_b["events"],
        )
        # also return per-arm medians for context
        km_a = await self.fetch_km(
            durations=arm_a["durations"],
            events=arm_a["events"],
            label=arm_a.get("label", "arm_a"),
        )
        km_b = await self.fetch_km(
            durations=arm_b["durations"],
            events=arm_b["events"],
            label=arm_b.get("label", "arm_b"),
        )
        return {
            "engine": "lifelines",
            "p_value": float(result.p_value),
            "test_statistic": float(result.test_statistic),
            "arm_a_label": km_a.get("label"),
            "arm_a_median": km_a.get("median_months"),
            "arm_a_n": km_a.get("n_at_risk_start"),
            "arm_b_label": km_b.get("label"),
            "arm_b_median": km_b.get("median_months"),
            "arm_b_n": km_b.get("n_at_risk_start"),
        }


__all__ = [
    "LifelinesKMIntegrator",
    "KMResult",
    "apply_subgroup_filter",
    "require_lifelines",
]
