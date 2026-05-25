"""Full-fidelity MTB pipeline for benchmark evaluation.

Loads the actual ``vmtb-skill`` agent prompts from disk (no copying) and runs:

1. Centralized retrieval — PubMed E-utilities + NCCN PageIndex tree-search.
2. Phase 1 expert fanout in parallel — Pathologist + Geneticist using the
   real prompt files from ``cancerdao-vmtb/scripts/config/prompts/``.
3. Phase 2/3 Oncologist using the real 905-line oncologist_prompt — integrates
   pathologist + geneticist + retrieval into a treatment plan.
4. Chair synthesis using the real 646-line chair_prompt.
5. Schema-shape pass — converts the Chair's free-form report into the
   benchmark CRC JSON schema.
6. Verifier orchestrator — facts + guidelines + safety verifiers run in
   parallel on the shaped output. If any returns critical, the schema-shape
   step is re-run with verifier feedback.

Cost: ~6–8 LLM calls per case (gpt-4o-mini ~$0.015 / case on n=30).
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import mtb_lite  # reuse openrouter_chat / pubmed / extract_json
import nccn_pageindex


# vMTB prompts are external to this repo (we run mtb-* arms here only for
# cross-framework comparison against opl-* arms). Resolution order:
#   1. $VMTB_PROMPTS_DIR (explicit override)
#   2. ../vmtb-skill/skills/cancerdao-vmtb/scripts/config/prompts (sibling clone)
#   3. ~/.claude/skills/vMTB/skills/cancerdao-vmtb/scripts/config/prompts (installed skill)
#   4. /Users/baozhiwei/work/mtb-bench/vmtb-skill/... (legacy mtb-bench cached path)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROMPT_CANDIDATES = [
    _REPO_ROOT.parent / "vmtb-skill" / "skills" / "cancerdao-vmtb" / "scripts" / "config" / "prompts",
    Path.home() / ".claude" / "skills" / "vMTB" / "skills" / "cancerdao-vmtb" / "scripts" / "config" / "prompts",
    Path("/Users/baozhiwei/work/mtb-bench/vmtb-skill/skills/cancerdao-vmtb/scripts/config/prompts"),
]
_DEFAULT_PROMPTS_DIR = next((p for p in _PROMPT_CANDIDATES if p.exists()), _PROMPT_CANDIDATES[-1])
VMTB_PROMPTS_DIR = Path(os.environ.get("VMTB_PROMPTS_DIR", str(_DEFAULT_PROMPTS_DIR)))


def _load_prompt(name: str) -> str:
    path = VMTB_PROMPTS_DIR / name
    return path.read_text(encoding="utf-8")


# Loaded once at import time.
PROMPTS = {
    "plan": _load_prompt("plan_agent_prompt.txt"),
    "pathologist": _load_prompt("pathologist_prompt.txt"),
    "geneticist": _load_prompt("geneticist_prompt.txt"),
    "oncologist": _load_prompt("oncologist_prompt.txt"),
    "chair": _load_prompt("chair_prompt.txt"),
    "verifier_facts": _load_prompt("verifier_facts_prompt.txt"),
    "verifier_guidelines": _load_prompt("verifier_guidelines_prompt.txt"),
    "verifier_safety": _load_prompt("verifier_safety_prompt.txt"),
}


# The vmtb-skill prompts were written for raw-PDF patient records. The benchmark
# inputs are already-structured dicts. This adapter note tells each agent to
# treat the structured case as ground-truth pre-extracted facts and skip the
# Phase 1 extraction tasks.
BENCHMARK_ADAPTATION_NOTE = """
---

## Benchmark adaptation note

The input below is **NOT a raw PDF medical record**. It is a pre-extracted, structured CRC case from the SBT_Benchmark suite. Treat every listed field as a confirmed clinical fact:

- Skip all Phase 1 *extraction* tasks (basic info / diagnostic info / treatment history extraction). The structured case already contains those.
- Skip SOURCE PROVENANCE machinery — the benchmark case has no source-type / confidence labels. Treat all listed fields as `CONFIDENCE: high`.
- Do NOT extrapolate clinical facts not stated in the structured case. Unstated parameters (e.g. KRAS status, performance status, prior treatment) must be treated as unknown.
- Produce only the *analysis / interpretation* output your role requires, using the structured fields plus the retrieved evidence bundle.
- Keep your output focused: ~600 words is enough. The downstream schema-shape step will compress it.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def format_case_text(case_id: str, case_facts: dict[str, Any]) -> str:
    lines = [f"# Structured CRC case: {case_id}", ""]
    for key, value in case_facts.items():
        if key == "case_id" or value in (None, "", [], {}):
            continue
        if isinstance(value, list):
            parts = []
            for entry in value:
                if isinstance(entry, dict):
                    parts.append("; ".join(f"{k}: {v}" for k, v in entry.items()))
                else:
                    parts.append(str(entry))
            rendered = " | ".join(parts)
        else:
            rendered = str(value)
        lines.append(f"- **{key}**: {rendered}")
    return "\n".join(lines)


def format_evidence(evidence: list[dict[str, Any]]) -> str:
    if not evidence:
        return "(no PubMed literature retrieved)"
    lines: list[str] = []
    for i, item in enumerate(evidence, start=1):
        title = item.get("title") or "(no title)"
        pmid = item.get("pmid") or ""
        year = item.get("year") or ""
        abstract = (item.get("abstract") or "").strip()
        if len(abstract) > 500:
            abstract = abstract[:500] + "..."
        lines.append(
            f"[E{i}] PMID:{pmid} ({year}) — {title}\n  abstract: {abstract}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Stage 1 — Plan agent (lightweight wrapper)
# ---------------------------------------------------------------------------

PLAN_SYSTEM = """You are the planning agent of a virtual molecular tumor board (vMTB). Given a structured colorectal cancer case, decide what evidence to retrieve.

Output one JSON object with exactly two keys:
- "pubmed_queries": 1 to 3 focused English PubMed queries (each ≤ 120 chars).
- "nccn_query": one focused English NCCN colorectal guideline query.

Return only the JSON. No prose, no markdown fences."""


def plan_stage(model: str, case_id: str, case_facts: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    user = f"Item ID: {case_id}\n\nCase summary:\n{format_case_text(case_id, case_facts)}\n\nReturn JSON only."
    result = mtb_lite.openrouter_chat(
        model,
        [
            {"role": "system", "content": PLAN_SYSTEM},
            {"role": "user", "content": user},
        ],
        max_tokens=400,
    )
    response = result.get("response") or {}
    content = (((response.get("choices") or [{}])[0]).get("message") or {}).get("content")
    json_ok, parsed = mtb_lite.extract_json(content)
    plan = parsed if (json_ok and isinstance(parsed, dict)) else {}
    queries = plan.get("pubmed_queries") or []
    if not isinstance(queries, list):
        queries = []
    queries = [str(q)[:200] for q in queries if str(q).strip()][:3]
    if not queries:
        fallback = mtb_lite.build_fallback_query(case_facts)
        queries = [fallback] if fallback else []
    nccn_query = plan.get("nccn_query") or plan.get("nccn_anchor")
    if not isinstance(nccn_query, str) or not nccn_query.strip():
        nccn_query = mtb_lite.build_fallback_query(case_facts) or "colorectal cancer treatment principles"
    return (
        {"pubmed_queries": queries, "nccn_query": nccn_query},
        {
            "ok": result.get("ok", False),
            "elapsed_seconds": result.get("_elapsed_seconds") or response.get("_elapsed_seconds"),
            "json_parse_ok": json_ok,
        },
    )


# ---------------------------------------------------------------------------
# Stage 2 — Centralized retrieval (reuse mtb_lite + nccn_pageindex)
# ---------------------------------------------------------------------------

def retrieve_stage(model: str, plan: dict[str, Any], case_facts: dict[str, Any]) -> dict[str, Any]:
    pm_started = time.time()
    pubmed = mtb_lite.retrieve_evidence(plan.get("pubmed_queries") or [], per_query=3)
    pm_elapsed = round(time.time() - pm_started, 3)

    nccn = nccn_pageindex.tree_search(
        model,
        plan.get("nccn_query") or "",
        case_facts.get("cancer_type") or "",
        max_nodes=4,
    )
    return {
        "pubmed": pubmed,
        "pubmed_elapsed_seconds": pm_elapsed,
        "nccn": nccn,
    }


# ---------------------------------------------------------------------------
# Stage 3 — Phase-1 expert fanout (parallel pathologist + geneticist)
# ---------------------------------------------------------------------------

def expert_user_prompt(case_id: str, case_facts: dict[str, Any], retrieval: dict[str, Any]) -> str:
    pubmed_text = format_evidence(retrieval.get("pubmed") or [])
    nccn_sections = nccn_pageindex.format_sections((retrieval.get("nccn") or {}).get("sections") or [])
    return f"""## Structured CRC case (treat as ground truth, pre-extracted)

{format_case_text(case_id, case_facts)}

## PubMed literature evidence (retrieved by the literature agent)

{pubmed_text}

## NCCN guideline sections (retrieved via PageIndex tree-search)

{nccn_sections}

---

Now produce your role-specific analysis report per the instructions above. Output prose (Chinese is fine if the original prompt requires it). Cap the report at ~600 words.
"""


def run_expert(
    model: str,
    role: str,
    case_id: str,
    case_facts: dict[str, Any],
    retrieval: dict[str, Any],
) -> dict[str, Any]:
    system_prompt = PROMPTS[role] + BENCHMARK_ADAPTATION_NOTE
    user = expert_user_prompt(case_id, case_facts, retrieval)
    result = mtb_lite.openrouter_chat(
        model,
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user},
        ],
        max_tokens=1200,
    )
    response = result.get("response") or {}
    choice = (response.get("choices") or [{}])[0]
    content = (choice.get("message") or {}).get("content") or ""
    return {
        "role": role,
        "ok": result.get("ok", False),
        "elapsed_seconds": result.get("_elapsed_seconds") or response.get("_elapsed_seconds"),
        "report": content.strip(),
        "error": None if result.get("ok") else result,
    }


# ---------------------------------------------------------------------------
# Stage 4 — Oncologist (Phase 1 + 2a + 3 integrated)
# ---------------------------------------------------------------------------

def oncologist_user_prompt(
    case_id: str,
    case_facts: dict[str, Any],
    retrieval: dict[str, Any],
    pathologist_report: str,
    geneticist_report: str,
) -> str:
    return f"""## Structured CRC case

{format_case_text(case_id, case_facts)}

## Pathologist report

{pathologist_report}

## Geneticist report

{geneticist_report}

## PubMed literature evidence

{format_evidence(retrieval.get("pubmed") or [])}

## NCCN guideline sections

{nccn_pageindex.format_sections((retrieval.get("nccn") or {}).get("sections") or [])}

---

Produce your integrated oncologist plan:
- Phase 1 prior/current treatment evaluation (skip if line_of_therapy="initial").
- Phase 2a systemic treatment mapping (which classes are reasonable for this case).
- Phase 3 integrated plan with L1-L5 evidence levels, ranked top recommendations.

Cap the report at ~900 words. Cite NCCN node_ids (e.g. [0045]) and PubMed [E#] tags inline.
"""


def run_oncologist(
    model: str,
    case_id: str,
    case_facts: dict[str, Any],
    retrieval: dict[str, Any],
    pathologist_report: str,
    geneticist_report: str,
) -> dict[str, Any]:
    system_prompt = PROMPTS["oncologist"] + BENCHMARK_ADAPTATION_NOTE
    user = oncologist_user_prompt(case_id, case_facts, retrieval, pathologist_report, geneticist_report)
    result = mtb_lite.openrouter_chat(
        model,
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user},
        ],
        max_tokens=1600,
    )
    response = result.get("response") or {}
    choice = (response.get("choices") or [{}])[0]
    content = (choice.get("message") or {}).get("content") or ""
    return {
        "ok": result.get("ok", False),
        "elapsed_seconds": result.get("_elapsed_seconds") or response.get("_elapsed_seconds"),
        "report": content.strip(),
        "error": None if result.get("ok") else result,
    }


# ---------------------------------------------------------------------------
# Stage 5 — Chair synthesis
# ---------------------------------------------------------------------------

def chair_user_prompt(
    case_id: str,
    case_facts: dict[str, Any],
    retrieval: dict[str, Any],
    expert_reports: dict[str, str],
) -> str:
    parts = [
        "## Structured CRC case",
        format_case_text(case_id, case_facts),
        "",
        "## Phase 1 — Pathologist report",
        expert_reports.get("pathologist", "(missing)"),
        "",
        "## Phase 1 — Geneticist report",
        expert_reports.get("geneticist", "(missing)"),
        "",
        "## Phase 3 — Oncologist integration report",
        expert_reports.get("oncologist", "(missing)"),
        "",
        "## PubMed literature evidence",
        format_evidence(retrieval.get("pubmed") or []),
        "",
        "## NCCN guideline sections",
        nccn_pageindex.format_sections((retrieval.get("nccn") or {}).get("sections") or []),
        "",
        "---",
        "",
        "Synthesize the experts into your final MTB chair report.",
        "Focus on chapters 1-3 (background / diagnosis / treatment recommendation).",
        "The recruiter / nutritionist / pharmacist sub-reports are skipped for this benchmark — note that explicitly but proceed.",
        "Cap the synthesis at ~1000 words. Cite NCCN node_ids and PMIDs inline.",
    ]
    return "\n".join(parts)


def run_chair(
    model: str,
    case_id: str,
    case_facts: dict[str, Any],
    retrieval: dict[str, Any],
    expert_reports: dict[str, str],
) -> dict[str, Any]:
    system_prompt = PROMPTS["chair"] + BENCHMARK_ADAPTATION_NOTE
    user = chair_user_prompt(case_id, case_facts, retrieval, expert_reports)
    result = mtb_lite.openrouter_chat(
        model,
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user},
        ],
        max_tokens=2000,
    )
    response = result.get("response") or {}
    choice = (response.get("choices") or [{}])[0]
    content = (choice.get("message") or {}).get("content") or ""
    return {
        "ok": result.get("ok", False),
        "elapsed_seconds": result.get("_elapsed_seconds") or response.get("_elapsed_seconds"),
        "report": content.strip(),
        "error": None if result.get("ok") else result,
    }


# ---------------------------------------------------------------------------
# Stage 6 — Schema-shape (convert chair report → benchmark CRC JSON)
# ---------------------------------------------------------------------------

SCHEMA_SHAPE_SYSTEM = """You are a structure-mapping agent. You receive an MTB chair report and convert it into the benchmark CRC JSON schema *without changing the clinical content*. Pick the top 3 ranked recommendations from the chair report, classify each, and copy the treatment-intent / missing-info content faithfully.

Strictly enforce: each enum field receives EXACTLY ONE option (never use 'X | Y' from the template; choose one).

Return only the JSON object — no fences, no prose."""


SCHEMA_SHAPE_TEMPLATE = mtb_lite.CRC_RESPONSE_TEMPLATE


def shape_to_schema(
    model: str,
    case_id: str,
    case_facts: dict[str, Any],
    chair_report: str,
    verifier_feedback: str | None = None,
) -> dict[str, Any]:
    feedback_block = ""
    if verifier_feedback:
        feedback_block = f"""

## Verifier feedback (from the previous pass — fix these issues before emitting JSON)

{verifier_feedback}

---
"""
    user = f"""Item ID: {case_id}

Case summary (only confirmed clinical facts):
{format_case_text(case_id, case_facts)}

Chair report (extract top-3 recommendations from here):
{chair_report}
{feedback_block}

Emit one valid JSON object matching this shape. Pick exactly one enum value per field — never include the '|' separator:

{SCHEMA_SHAPE_TEMPLATE}

The "recommendations" array must contain at most 3 entries. The "missing_information" array must contain at most 5 entries.
"""
    result = mtb_lite.openrouter_chat(
        model,
        [
            {"role": "system", "content": SCHEMA_SHAPE_SYSTEM},
            {"role": "user", "content": user},
        ],
        max_tokens=1500,
    )
    response = result.get("response") or {}
    choice = (response.get("choices") or [{}])[0]
    content = (choice.get("message") or {}).get("content")
    json_ok, parsed = mtb_lite.extract_json(content)
    return {
        "ok": result.get("ok", False),
        "elapsed_seconds": result.get("_elapsed_seconds") or response.get("_elapsed_seconds"),
        "finish_reason": choice.get("finish_reason"),
        "content_present": bool(content),
        "json_parse_ok": json_ok,
        "parsed_json": parsed if json_ok else None,
        "raw_response": response if result.get("ok") else None,
        "error": None if result.get("ok") else result,
    }


# ---------------------------------------------------------------------------
# Stage 7 — Verifier orchestrator (3 verifiers in parallel)
# ---------------------------------------------------------------------------

def verifier_user_prompt(case_id: str, case_facts: dict[str, Any], parsed: dict[str, Any], chair_report: str) -> str:
    return f"""## Structured CRC case

{format_case_text(case_id, case_facts)}

## Final recommendation JSON

{json.dumps(parsed, indent=2, ensure_ascii=False)}

## Chair report excerpt (for context)

{chair_report[:1500]}

---

Apply your verifier rubric. Output ONE JSON object:
{{"verdict": "pass | flag | critical", "issues": ["..."], "notes": "..."}}

Return only the JSON. No fences, no extra prose.
"""


def run_one_verifier(model: str, name: str, case_id: str, case_facts: dict[str, Any], parsed: dict[str, Any], chair_report: str) -> dict[str, Any]:
    system_prompt = PROMPTS[f"verifier_{name}"]
    user = verifier_user_prompt(case_id, case_facts, parsed, chair_report)
    result = mtb_lite.openrouter_chat(
        model,
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user},
        ],
        max_tokens=600,
    )
    response = result.get("response") or {}
    choice = (response.get("choices") or [{}])[0]
    content = (choice.get("message") or {}).get("content")
    json_ok, parsed_v = mtb_lite.extract_json(content)
    verdict_record = parsed_v if (json_ok and isinstance(parsed_v, dict)) else {"verdict": "pass", "issues": [], "notes": ""}
    return {
        "name": name,
        "ok": result.get("ok", False),
        "elapsed_seconds": result.get("_elapsed_seconds") or response.get("_elapsed_seconds"),
        "verdict": verdict_record.get("verdict", "pass"),
        "issues": verdict_record.get("issues") or [],
        "notes": verdict_record.get("notes") or "",
        "raw_content": content,
    }


def verify_stage(
    model: str,
    case_id: str,
    case_facts: dict[str, Any],
    parsed: dict[str, Any],
    chair_report: str,
) -> dict[str, Any]:
    names = ["facts", "guidelines", "safety"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(names)) as pool:
        futures = {pool.submit(run_one_verifier, model, n, case_id, case_facts, parsed, chair_report): n for n in names}
        verifiers: list[dict[str, Any]] = [fut.result() for fut in concurrent.futures.as_completed(futures)]
    has_critical = any(v.get("verdict") == "critical" for v in verifiers)
    has_flag = any(v.get("verdict") == "flag" for v in verifiers)
    feedback_lines: list[str] = []
    for v in verifiers:
        if v.get("verdict") in ("critical", "flag"):
            feedback_lines.append(f"[{v['name']}/{v['verdict']}] {v.get('notes') or ''}")
            for issue in v.get("issues") or []:
                feedback_lines.append(f"  - {issue}")
    return {
        "verifiers": verifiers,
        "has_critical": has_critical,
        "has_flag": has_flag,
        "feedback": "\n".join(feedback_lines) if feedback_lines else None,
    }


# ---------------------------------------------------------------------------
# Top-level run_full_mtb
# ---------------------------------------------------------------------------

def format_patient_facts_block(scenario_label: str, patient_facts: list[dict[str, Any]]) -> str:
    parts = [f"## Scenario: {scenario_label or '(unspecified)'}", "", "## Structured patient facts"]
    for fact in patient_facts:
        if not isinstance(fact, dict):
            continue
        label = fact.get("slot_label") or fact.get("label") or "clinical fact"
        value = fact.get("value")
        if value in (None, "", [], {}):
            value = "not available"
        parts.append(f"- **{label}**: {value}")
    return "\n".join(parts)


NCCN_SHAPE_SYSTEM = """You are a structure-mapping agent. You receive an MTB chair report for an NCCN-derived decision case and convert it into the benchmark NCCN JSON schema *without changing clinical content*.

Strictly enforce: each enum field receives EXACTLY ONE option (never use 'X | Y' from the template; choose one).

Return only the JSON object — no fences, no prose."""


def shape_to_nccn_schema(
    model: str,
    item_id: str,
    scenario_label: str,
    patient_facts: list[dict[str, Any]],
    chair_report: str,
    verifier_feedback: str | None = None,
) -> dict[str, Any]:
    feedback_block = ""
    if verifier_feedback:
        feedback_block = f"\n\n## Verifier feedback (fix these issues before emitting JSON)\n{verifier_feedback}\n"
    user = f"""Item ID: {item_id}

{format_patient_facts_block(scenario_label, patient_facts)}

Chair report (extract the decision from here):
{chair_report}
{feedback_block}

Emit one valid JSON object matching this NCCN-decision shape. Pick exactly one enum value per field — never include '|':

{mtb_lite.NCCN_RESPONSE_TEMPLATE}

The "basis" array must contain 1 to 3 strings. The "missing_or_needed" array must contain at most 5 objects.
"""
    result = mtb_lite.openrouter_chat(
        model,
        [
            {"role": "system", "content": NCCN_SHAPE_SYSTEM},
            {"role": "user", "content": user},
        ],
        max_tokens=1200,
    )
    response = result.get("response") or {}
    choice = (response.get("choices") or [{}])[0]
    content = (choice.get("message") or {}).get("content")
    json_ok, parsed = mtb_lite.extract_json(content)
    return {
        "ok": result.get("ok", False),
        "elapsed_seconds": result.get("_elapsed_seconds") or response.get("_elapsed_seconds"),
        "finish_reason": choice.get("finish_reason"),
        "content_present": bool(content),
        "json_parse_ok": json_ok,
        "parsed_json": parsed if json_ok else None,
        "raw_response": response if result.get("ok") else None,
        "error": None if result.get("ok") else result,
    }


def run_full_mtb_nccn(
    model: str,
    item_id: str,
    scenario_label: str,
    patient_facts: list[dict[str, Any]],
    cancer_type_hint: str = "COLON_CANCER",
) -> dict[str, Any]:
    """Full multi-agent + verifier pipeline on the NCCN decision surface."""
    total_started = time.time()

    # Plan — reuse a tiny planner shaped for NCCN facts.
    plan_user = f"""Item ID: {item_id}

{format_patient_facts_block(scenario_label, patient_facts)}

Return JSON only with pubmed_queries (1-3) and nccn_query (1).
"""
    plan_res = mtb_lite.openrouter_chat(
        model,
        [
            {"role": "system", "content": PLAN_SYSTEM},
            {"role": "user", "content": plan_user},
        ],
        max_tokens=400,
    )
    plan_resp = plan_res.get("response") or {}
    plan_content = (((plan_resp.get("choices") or [{}])[0]).get("message") or {}).get("content")
    plan_ok, plan_parsed = mtb_lite.extract_json(plan_content)
    plan_dict = plan_parsed if (plan_ok and isinstance(plan_parsed, dict)) else {}
    queries = plan_dict.get("pubmed_queries") or []
    queries = [str(q)[:200] for q in queries if str(q).strip()][:3]
    if not queries:
        queries = [(scenario_label or "colorectal cancer management").strip()[:200]]
    nccn_query = plan_dict.get("nccn_query") or plan_dict.get("nccn_anchor") or scenario_label or "colorectal cancer decision pathway"

    pm_start = time.time()
    pubmed = mtb_lite.retrieve_evidence(queries, per_query=3)
    pm_elapsed = round(time.time() - pm_start, 3)

    nccn = nccn_pageindex.tree_search(model, nccn_query, cancer_type_hint or "COLON_CANCER", max_nodes=4)
    retrieval = {"pubmed": pubmed, "nccn": nccn, "pubmed_elapsed_seconds": pm_elapsed}

    # Replace case_text with a patient-facts block in the user prompt for experts.
    nccn_text = format_patient_facts_block(scenario_label, patient_facts)

    def expert_user(role: str) -> str:
        return f"""## NCCN-derived decision case (treat fields as ground truth)

{nccn_text}

## PubMed literature evidence

{format_evidence(retrieval.get("pubmed") or [])}

## NCCN guideline sections (retrieved via PageIndex tree-search)

{nccn_pageindex.format_sections((retrieval.get("nccn") or {}).get("sections") or [])}

---

Now produce your role-specific analysis report. Output prose (≤ 600 words).
"""

    def run_role(role: str) -> dict[str, Any]:
        result = mtb_lite.openrouter_chat(
            model,
            [
                {"role": "system", "content": PROMPTS[role] + BENCHMARK_ADAPTATION_NOTE},
                {"role": "user", "content": expert_user(role)},
            ],
            max_tokens=1200,
        )
        resp = result.get("response") or {}
        ch = (resp.get("choices") or [{}])[0]
        return {
            "role": role,
            "ok": result.get("ok", False),
            "elapsed_seconds": result.get("_elapsed_seconds") or resp.get("_elapsed_seconds"),
            "report": ((ch.get("message") or {}).get("content") or "").strip(),
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        path_fut = pool.submit(run_role, "pathologist")
        gene_fut = pool.submit(run_role, "geneticist")
        pathologist = path_fut.result()
        geneticist = gene_fut.result()

    # Oncologist
    onc_user = f"""## NCCN-derived decision case

{nccn_text}

## Pathologist report

{pathologist['report']}

## Geneticist report

{geneticist['report']}

## PubMed literature evidence

{format_evidence(retrieval.get("pubmed") or [])}

## NCCN guideline sections

{nccn_pageindex.format_sections((retrieval.get("nccn") or {}).get("sections") or [])}

---

Produce your oncologist analysis identifying:
- Whether the case has sufficient information to proceed, or whether discriminators / missing info / evidence are required.
- The most defensible next clinical management step.
- The rationale and any unresolved decision gaps.

Cap at ~900 words. Cite NCCN node_ids and PMIDs.
"""
    onc_res = mtb_lite.openrouter_chat(
        model,
        [
            {"role": "system", "content": PROMPTS["oncologist"] + BENCHMARK_ADAPTATION_NOTE},
            {"role": "user", "content": onc_user},
        ],
        max_tokens=1600,
    )
    onc_resp = onc_res.get("response") or {}
    oncologist = {
        "ok": onc_res.get("ok", False),
        "elapsed_seconds": onc_res.get("_elapsed_seconds") or onc_resp.get("_elapsed_seconds"),
        "report": ((((onc_resp.get("choices") or [{}])[0]).get("message") or {}).get("content") or "").strip(),
    }

    # Chair
    chair_user = f"""## NCCN-derived decision case

{nccn_text}

## Phase 1 — Pathologist report

{pathologist['report']}

## Phase 1 — Geneticist report

{geneticist['report']}

## Phase 3 — Oncologist integration report

{oncologist['report']}

## PubMed literature evidence

{format_evidence(retrieval.get("pubmed") or [])}

## NCCN guideline sections

{nccn_pageindex.format_sections((retrieval.get("nccn") or {}).get("sections") or [])}

---

Synthesize into your final MTB chair report. Focus on the **decision**:
- Is information sufficient to proceed with a specific next step?
- If not, what discriminators / missing info / evidence are needed?
- If yes, what is the next clinical management action?

Cap at ~1000 words. Cite NCCN node_ids and PMIDs inline.
"""
    chair_res = mtb_lite.openrouter_chat(
        model,
        [
            {"role": "system", "content": PROMPTS["chair"] + BENCHMARK_ADAPTATION_NOTE},
            {"role": "user", "content": chair_user},
        ],
        max_tokens=2000,
    )
    chair_resp = chair_res.get("response") or {}
    chair = {
        "ok": chair_res.get("ok", False),
        "elapsed_seconds": chair_res.get("_elapsed_seconds") or chair_resp.get("_elapsed_seconds"),
        "report": ((((chair_resp.get("choices") or [{}])[0]).get("message") or {}).get("content") or "").strip(),
    }

    # Schema-shape pass 1 (NCCN schema)
    shape1 = shape_to_nccn_schema(model, item_id, scenario_label, patient_facts, chair["report"])
    parsed = shape1.get("parsed_json")

    # Verifier pass
    verify_result: dict[str, Any] = {"verifiers": [], "has_critical": False, "has_flag": False, "feedback": None}
    shape2: dict[str, Any] | None = None
    if isinstance(parsed, dict):
        # Reuse the CRC verifiers — they read the chair report + parsed JSON and emit flag/critical/pass.
        verify_result = verify_stage(model, item_id, {"scenario_label": scenario_label, "patient_facts": patient_facts}, parsed, chair["report"])
        if verify_result["has_critical"] or verify_result["has_flag"]:
            shape2 = shape_to_nccn_schema(model, item_id, scenario_label, patient_facts, chair["report"], verifier_feedback=verify_result["feedback"])
            if shape2.get("parsed_json"):
                parsed = shape2["parsed_json"]

    final_shape = shape2 or shape1
    total_elapsed = round(time.time() - total_started, 3)
    return {
        "ok": all([plan_res.get("ok"), pathologist.get("ok"), geneticist.get("ok"), oncologist.get("ok"), chair.get("ok"), final_shape.get("ok")]),
        "elapsed_seconds": total_elapsed,
        "finish_reason": final_shape.get("finish_reason"),
        "content_present": final_shape.get("content_present"),
        "json_parse_ok": final_shape.get("json_parse_ok"),
        "parsed_json": parsed if final_shape.get("json_parse_ok") else None,
        "raw_response": final_shape.get("raw_response"),
        "error": final_shape.get("error"),
        "intermediate": {
            "plan": {"pubmed_queries": queries, "nccn_query": nccn_query},
            "pubmed_n_hits": len(pubmed),
            "nccn_node_ids": nccn.get("node_ids"),
            "nccn_ok": nccn.get("ok"),
            "pathologist_ok": pathologist.get("ok"),
            "geneticist_ok": geneticist.get("ok"),
            "oncologist_ok": oncologist.get("ok"),
            "chair_ok": chair.get("ok"),
            "verifier_pass": "fail" if verify_result.get("has_critical") else ("flag" if verify_result.get("has_flag") else "pass"),
            "reshape_triggered": shape2 is not None,
        },
    }


def run_full_mtb(model: str, case_id: str, case_facts: dict[str, Any]) -> dict[str, Any]:
    total_started = time.time()

    plan, plan_diag = plan_stage(model, case_id, case_facts)
    retrieval = retrieve_stage(model, plan, case_facts)

    # Phase 1 parallel experts
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        path_fut = pool.submit(run_expert, model, "pathologist", case_id, case_facts, retrieval)
        gene_fut = pool.submit(run_expert, model, "geneticist", case_id, case_facts, retrieval)
        pathologist = path_fut.result()
        geneticist = gene_fut.result()

    # Phase 3 oncologist
    oncologist = run_oncologist(
        model, case_id, case_facts, retrieval, pathologist["report"], geneticist["report"]
    )

    # Chair
    chair = run_chair(
        model,
        case_id,
        case_facts,
        retrieval,
        {
            "pathologist": pathologist["report"],
            "geneticist": geneticist["report"],
            "oncologist": oncologist["report"],
        },
    )

    # Schema-shape pass 1
    shape1 = shape_to_schema(model, case_id, case_facts, chair["report"])
    parsed = shape1.get("parsed_json")

    # Verifier orchestrator (only if we have a parseable JSON to verify)
    verify_result: dict[str, Any] = {"verifiers": [], "has_critical": False, "has_flag": False, "feedback": None}
    shape2: dict[str, Any] | None = None
    if isinstance(parsed, dict):
        verify_result = verify_stage(model, case_id, case_facts, parsed, chair["report"])
        if verify_result["has_critical"] or verify_result["has_flag"]:
            shape2 = shape_to_schema(
                model, case_id, case_facts, chair["report"], verifier_feedback=verify_result["feedback"]
            )
            if shape2.get("parsed_json"):
                parsed = shape2["parsed_json"]

    final_shape = shape2 or shape1
    total_elapsed = round(time.time() - total_started, 3)
    return {
        "ok": all(
            [
                plan_diag.get("ok"),
                pathologist.get("ok"),
                geneticist.get("ok"),
                oncologist.get("ok"),
                chair.get("ok"),
                final_shape.get("ok"),
            ]
        ),
        "elapsed_seconds": total_elapsed,
        "finish_reason": final_shape.get("finish_reason"),
        "content_present": final_shape.get("content_present"),
        "json_parse_ok": final_shape.get("json_parse_ok"),
        "parsed_json": parsed if final_shape.get("json_parse_ok") else None,
        "raw_response": final_shape.get("raw_response"),
        "error": final_shape.get("error"),
        "intermediate": {
            "plan": plan,
            "plan_elapsed_seconds": plan_diag.get("elapsed_seconds"),
            "pubmed_elapsed_seconds": retrieval.get("pubmed_elapsed_seconds"),
            "pubmed_n_hits": len(retrieval.get("pubmed") or []),
            "nccn_node_ids": (retrieval.get("nccn") or {}).get("node_ids"),
            "nccn_ok": (retrieval.get("nccn") or {}).get("ok"),
            "pathologist_elapsed_seconds": pathologist.get("elapsed_seconds"),
            "pathologist_ok": pathologist.get("ok"),
            "geneticist_elapsed_seconds": geneticist.get("elapsed_seconds"),
            "geneticist_ok": geneticist.get("ok"),
            "oncologist_elapsed_seconds": oncologist.get("elapsed_seconds"),
            "oncologist_ok": oncologist.get("ok"),
            "chair_elapsed_seconds": chair.get("elapsed_seconds"),
            "chair_ok": chair.get("ok"),
            "shape1_elapsed_seconds": shape1.get("elapsed_seconds"),
            "verifier_pass": "fail" if verify_result.get("has_critical") else ("flag" if verify_result.get("has_flag") else "pass"),
            "verifier_results": verify_result.get("verifiers"),
            "reshape_triggered": shape2 is not None,
            "shape2_elapsed_seconds": shape2.get("elapsed_seconds") if shape2 else None,
        },
    }
