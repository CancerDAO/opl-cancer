# OPL for Cancer — Product Review & Iteration (v2.6.0)

**Reviewer stance:** independent product-owner + code auditor. **Method:** scenario/data-flow-first
(not static bug-hunting), 7 parallel third-party reviewers across distinct dimensions + adversarial
verification of every BLOCKER/HIGH finding, plus first-hand end-to-end CLI runs.
**Date:** 2026-05-29. **Base:** v2.5.1 (`fe73f48`).

**Signal quality:** 63 findings; 38 BLOCKER/HIGH adversarially verified → **21 CONFIRMED, 17 PARTIAL,
0 REFUTED**. Clean-env test suite = 1714 → **1734 passing** after this iteration (+20 TDD cases).

---

## 1. Executive verdict

OPL is an **unusually disciplined, honest-by-intent** medical-AI repo — the transparency machinery
(provenance hashes, 3-tier labels, 33 gates, Henry's 4-layer audit, a fakery sniffer, an ADR ledger
that openly logs its own debt) is real and rare. **But the shipped substance does not yet match the
marketed surface, and that gap lands hardest exactly where the product stakes its value: honesty and
patient safety.**

One thesis explains most findings:

> **The pip-installable Python package is a *harness* (it plans, validates, gates, fetches from live
> integrators, and emits honest scaffolds + state). The actual reasoning — the 20 experts, the Wave-2
> tournament, Henry's per-claim audit, the patient prose — runs only on the Claude Code SKILL main
> thread. The README/CLI marketed the harness as the finished product.**

This is a legitimate engine-vs-plugin architecture. The defect was that the code *claimed to be the
product*: `opl deliver` shipped a placeholder scaffold while reporting `status: ok` /
`henry_real_audit: true`, and the safety gates that justify the founder-mode "no human sign-off" model
were built but **not wired onto the ship path**.

**Does it meet its positioning + customer needs today?**

| Promise | Verdict |
|---|---|
| "Honest / transparent / no fake output" | **Was violated at the sharpest point** (delivery). v2.6.0 fixes the delivery lie + B5 hollow gate. |
| "Every claim PMID-anchored + gated by Henry" | **Not on the wired path** — gate battery + `audit_claim` not run at ship (v2.7.0). |
| "Patient safety via mechanical transparency (replaces HITL)" | **G24 crisis gate was never invoked** — now wired (v2.6.0). Full gate battery still pending. |
| "Covers all cancers, bilingual" | **Partial** — retrieval is API-driven & cancer-agnostic, but front-of-funnel routing is ~30 keyword rows → silent low-resolution degradation for unlisted cancers/drugs/phrasings. |
| "World-Unknown candidates (v2 flagship)" | **Aspirational on the CLI** — generated only by the orchestrator, which is dead code on the wired path. |
| "MTB on your laptop" | **Only via the SKILL**, not the standalone CLI. |

---

## 2. Seven-dimension verdicts

| Dimension | Verdict |
|---|---|
| E2E data-flow & wiring | **does-not-deliver** — CLI alone never produces a real brief; wave runners + 20 experts + orchestrator are dead code outside tests. |
| Truthfulness (claims vs code) | **does-not-deliver** — `henry_real_audit:true`/`status:pass` over a scaffold; "real 4-layer audit" false; B5 file-existence-only. |
| Medical safety & evidence gates | **does-not-deliver** — none of G1/G2/G6/G9/G24/G27/G8 wired onto the ship path; no single gate battery before a brief ships. |
| Integrators / live data | **partial** — ~26/40 genuinely live & raise-don't-fabricate (good); count over-claimed; HTML scrapers silently return empty on regex drift. |
| SKILL.md product surface / UX | **partial** — contracts well-designed & assets exist, but Steps 5–10 wire state-check no-ops, `drilldown` CLI doesn't exist, `patient-data-layout.md` missing. |
| Engineering / tests / CI | **does-not-deliver** — clean-env suite green, but `mypy --strict` (40) and `ruff` (37) FAIL on the shipped commit; CI installs `[dev]` only → collection breaks; some tests lock in the scaffold. |
| Product positioning / customer fit | **partial** — discipline real; headline deliverable not reachable via the documented path; founder-mode safety model un-backstopped at delivery. |

---

## 3. What v2.6.0 shipped (this iteration — complete + verified)

Theme: **Truthful Delivery + Safety Wiring** — the patient-safety + delivery-honesty cluster, the
items that matter most for a medical product and are fixable without an architectural decision.

| ID | Sev | Fix | Proof |
|---|---|---|---|
| CRISIS-1 | BLOCKER | G24 crisis gate wired as **Path 0** of `route_intake` (mechanical, ahead of all routing) | `route_intake("…想结束这一切…")` → `crisis_card_emission`, `crisis_block=True`, empty `method_dag` |
| AUDIT-1 | BLOCKER | `DeliveryRunner` honest 2-mode: scaffold (`scaffold_pending_fill`, `henry_real_audit:false`) vs `--finalize` (real `audit_claim` over `claims.json`) | `opl deliver` → `{status: scaffold_pending_fill, henry_real_audit: false}` + 4 placeholder hits flagged |
| B5-SEMANTIC | BLOCKER | `verify_upstream_artifacts` now refuses **hollow** upstream (empty plan / empty wave arrays / trivial report) | `test_upstream_semantic_b5` |
| REDACT-1 | HIGH | Drug-class redaction **fails CLOSED** (INN-stem + investigational-code backstop) instead of leaking unlisted drugs | `MRTX1133`/`datopotamab` no longer render verbatim |
| FAKERY-CJK | MED | fakery sniffer gains scoped **CJK** placeholder patterns (was English-only on a zh-primary product) | `test_fakery_sniffer_cjk` |
| DOC-SYNC | — | README delivery section + quickstart + `list-experts` (18→20) + version (2.5.1→2.6.0; `__init__` drift 0.0.1→2.6.0) | suite green |

**Tests:** +20 TDD cases (5 new files), updated the v2.5.1 tests that locked in the scaffold-as-pass
behavior. Full suite **1734 passed / 8 skipped**, clean env.

---

## 4. Prioritized roadmap for what remains (full list — not self-capped)

### P0 — needs a maintainer **strategic decision** first (the engine-vs-skill fork)

The single highest-order decision: **is the standalone Python CLI a real executor, or explicitly a
harness driven by the SKILL?** Everything below branches on it.

- **A1 — Resolve CLI-vs-SKILL.** Either (a) wire `opl run --wave N` to construct the real
  `Wave{1..4}Runner` + `expert_factory` + LLM client (the classes exist, take these as ctor args), or
  (b) formally demote the CLI to "harness" in README/`status`/`list-experts` and make the SKILL the
  sole advertised executor. Removes the DF-1/DF-2/DF-3 "dead code / overstated" cluster.
- **A2 — Wire the gate battery + `audit_claim` onto the ship path.** A single stage that loads the
  Wave 1–4 claim corpus, runs the applicable G1–G28 gates (async G1/G2/G9 with live integrators) +
  `HenryAuditor.audit_claim()` per claim, and reports the true `gates_run`. This is what makes the
  founder-mode "mechanical transparency replaces HITL" model actually load-bearing. (v2.6.0 `--finalize`
  laid the consumption seam; this wires the full battery.)

### P0 — generalization (the maintainer's hardcoded-Python directive)

- **A3 — Collapse the keyword routing spine into ONE LLM plan-composer** (RFC's own M5
  `task_composer.py`): `goal_router.yaml` (11 rows; misses CAR-T/ADC/radioligand), the cancer-type-blind
  t1–t9 skeleton, and `intake_router` keyword maps all answer the same question. One structured-output
  classifier over `(goal, profile, experts, MethodRegistry, task catalog)` closes the bilingual
  generalization hole for all cancers; demote the keyword rows to a deterministic fallback floor.
  **Keep mechanical** (do NOT LLM-ify): G24 crisis gate, fakery sniffer, G3 (already live RxNorm).
- **A4 — `comorbid_planner` triggers** (AFib/dialysis/hepatitis-irAE missed) → fold into A3 or back with
  an LLM extractor; **redaction class-map** → resolve via RxNorm/OncoKB (the v2.6.0 fail-closed backstop
  is the floor, not the ceiling).

### P1 — engineering truth + safety completeness

- **E1** `mypy --strict` (40 errors) + `ruff` (37) currently FAIL on the shipped commit though README
  claims they pass — fix or stop claiming. Includes the **G21 gate** (uninstantiable + builds
  `GateResult` with invalid kwargs).
- **E2** CI installs `[dev]` only → `matplotlib` absent → collection breaks; install `[dev,bio]` or guard
  the `figure_render` module import + `importorskip` the figure tests.
- **S1** Wire **G27 PII scrub** over brief output (currently never applied to patient/clinician briefs).
- **S2** HTML-scraper integrators (chictr/nmpa_eap/ema_eap/isrctn) — port the eu_ctr/hkctr schema-drift
  guard so regex breakage **raises** instead of silently returning empty (no silent fallback).
- **D1** Implement (or stop advertising) `opl-cancer drilldown`; author missing
  `references/patient-data-layout.md`; reconcile `models.yaml`/SKILL GPT-5/Gemini reviewers the router
  can't build; refresh stale `DISCLAIMER.md` (v1.x / "18 experts").

### P2 — honesty polish

- Integrator count claims drift (29 vs ~26 vs 5 registered) — state an honest split.
- `intake_router` over-triggers `unknown_task_intake`/AutoML-decline on generic clinical goals.
- Entry-point `IntegratorRegistry.discover()` is decorative (never consumed) — consume or drop.
- PrimeKG/Maya KG-synergy is a stub — label as roadmap; `tmp_live_v2_e2e/` example link is `.gitignore`d.

---

## 5. Strategic note (product-owner)

The honesty scaffolding is the moat — protect it by never letting the code out-claim itself. The two
moves that most increase real value: **(A1) decide the CLI boundary** so nothing is "dead code that
looks shipped," and **(A3) the LLM plan-composer** so the "all cancers, bilingual" promise stops
silently degrading. The founder-mode "no HITL" posture is defensible *only once A2 makes the mechanical
safety battery actually run at delivery* — until then the safety model is documented, not enforced.
