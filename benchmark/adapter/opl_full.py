"""OPL-for-Cancer adapter for the SBT_Benchmark CRC + NCCN surfaces.

Mirrors ``mtb_full.py``'s shape and return contract, but loads OPL's actual
prompts from ``opl-cancer/prompts/`` and runs the OPL expert lineup:

    Stage 1 — Plan         (Sid intent parser → pubmed_queries + nccn_query)
    Stage 2 — Retrieve     (PubMed E-utilities + NCCN PageIndex tree-search)
    Stage 3 — Phase-1 fanout in parallel:
              · Rosa (pathology_interpretation)
              · Bert (molecular_ngs_interpretation)
    Stage 4 — Vince (treatment_line_recommendation) — integrates Rosa + Bert
    Stage 5 — Sid delivery (pi/delivery + intent_parser context)
    Stage 6 — Schema-shape pass → benchmark CRC / NCCN JSON
    Stage 7 — Henry L1 mechanical-gates audit (verifier)
              · Critical / flag triggers reshape pass with feedback

The intent is apples-to-apples vs ``mtb_full.run_full_mtb``: same model,
same OpenRouter HTTP path (via ``mtb_lite.openrouter_chat``), same retrieval
substrate (PubMed + NCCN PageIndex), same CRC + NCCN output schemas. The
only swap is the prompt corpus (vMTB scripts/config/prompts → OPL prompts/).

Anchor arm (``run_opl_anchor`` / ``run_opl_anchor_nccn``) is the OPL equivalent
of ``mtb_lite.run_mtb`` — planner + retrieve + Sid synth → schema, no
Rosa/Bert/Vince fanout. Two LLM calls + retrieval.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import mtb_lite  # reuse openrouter_chat / extract_json / PubMed retrieval / templates
import nccn_pageindex


# ---------------------------------------------------------------------------
# Prompt loading — OPL prompts live in <repo>/prompts/
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_OPL_PROMPTS_DIR = _REPO_ROOT / "prompts"
OPL_PROMPTS_DIR = Path(os.environ.get("OPL_PROMPTS_DIR", str(_DEFAULT_OPL_PROMPTS_DIR)))


def _read(rel: str) -> str:
    return (OPL_PROMPTS_DIR / rel).read_text(encoding="utf-8")


# Personas + task prompts loaded at import time so missing files fail fast.
PROMPTS: dict[str, str] = {
    "rosa_persona": _read("experts/rosa/persona.md"),
    "bert_persona": _read("experts/bert/persona.md"),
    "vince_persona": _read("experts/vince/persona.md"),
    "task_pathology": _read("tasks/pathology_interpretation.md"),
    "task_molecular": _read("tasks/molecular_ngs_interpretation.md"),
    "task_treatment": _read("tasks/treatment_line_recommendation.md"),
    "task_literature": _read("tasks/literature_synthesis.md"),
    "pi_intent": _read("pi/intent_parser.md"),
    "pi_delivery": _read("pi/delivery.md"),
    "auditor_l1": _read("auditor/l1_mechanical_gates.md"),
}


# OPL prompts were written for raw patient records + 29 live integrators. The
# benchmark inputs are already-structured CRC / NCCN cases. This note adapts
# each agent's role to the benchmark substrate.
BENCHMARK_ADAPTATION_NOTE = """
---

## Benchmark adaptation note

The input below is **NOT a raw patient record** and there are **NO 29 live integrators** running behind this prompt. It is a pre-extracted, structured colorectal cancer (CRC) case from the SBT_Benchmark suite plus a small literature/guideline bundle that the planner already retrieved.

- Treat every listed structured field as a confirmed clinical fact (CONFIDENCE: high).
- Do NOT invent fields not stated (KRAS / performance status / prior treatment / etc — treat as unknown).
- The `pubmed_results` / `nccn_excerpts` slots below ARE the pre-fetched integrator pool. Cite only PMIDs that appear in that bundle. If the bundle is empty for your role, say so explicitly per the OPL empty-integrator rule rather than synthesising.
- Skip OPL's full provenance machinery (no SHA-256 hashes / Henry G1-G27 enforcement / Wave-3 docker) — the schema-shape stage and Henry-L1 verifier at the end of the benchmark pipeline will run instead.
- Produce only the structured JSON your task prompt specifies. Cap the output at the schema — no preamble, no markdown fences. ~600 words of equivalent content is plenty.
"""


# ---------------------------------------------------------------------------
# Formatting helpers — mirror mtb_full so downstream parsing is consistent
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
        lines.append(f"[E{i}] PMID:{pmid} ({year}) — {title}\n  abstract: {abstract}")
    return "\n".join(lines)


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


# ---------------------------------------------------------------------------
# Stage 1 — Plan agent (OPL Sid intent-parser-style, adapted for retrieval planning)
# ---------------------------------------------------------------------------

OPL_PLAN_SYSTEM = """You are Sid, the patient's AI scientist team PI, in retrieval-planning mode. The patient has handed you a pre-extracted, structured colorectal cancer (CRC) case from the SBT_Benchmark suite. Your job is NOT intent classification (this is a NEW_GOAL clinical analysis by construction). Your job is to plan retrieval before the team fans out.

Output exactly one JSON object with two fields:
- "pubmed_queries": 1 to 3 focused English PubMed queries (each ≤ 120 chars). Encode cancer type + stage + molecular variants + treatment line where relevant.
- "nccn_query": one focused English NCCN colorectal guideline query (will be tree-searched against the local PageIndex).

Return ONLY the JSON object. No prose, no markdown fences. No intent / crisis_grade / speaker_role envelope — just the retrieval plan."""


def plan_stage(model: str, case_id: str, case_facts: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    user = f"Item ID: {case_id}\n\nStructured case:\n{format_case_text(case_id, case_facts)}\n\nReturn JSON only."
    result = mtb_lite.openrouter_chat(
        model,
        [{"role": "system", "content": OPL_PLAN_SYSTEM}, {"role": "user", "content": user}],
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
# Stage 2 — Retrieve (reuse mtb_lite.retrieve_evidence + nccn_pageindex)
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
    return {"pubmed": pubmed, "pubmed_elapsed_seconds": pm_elapsed, "nccn": nccn}


# ---------------------------------------------------------------------------
# Stage 3 — Phase-1 experts (Rosa pathology + Bert molecular) in parallel
# ---------------------------------------------------------------------------

def _expert_system(persona_key: str, task_key: str) -> str:
    """Compose persona + task into one system prompt + benchmark adaptation note."""
    return (
        PROMPTS[persona_key].rstrip()
        + "\n\n---\n\n"
        + PROMPTS[task_key].rstrip()
        + "\n"
        + BENCHMARK_ADAPTATION_NOTE
    )


def expert_user_prompt(case_id: str, case_facts: dict[str, Any], retrieval: dict[str, Any]) -> str:
    pubmed_text = format_evidence(retrieval.get("pubmed") or [])
    nccn_sections = nccn_pageindex.format_sections((retrieval.get("nccn") or {}).get("sections") or [])
    return f"""## Structured CRC case (pre-extracted facts — treat as ground truth)

{format_case_text(case_id, case_facts)}

## profile_json (synthesised from the structured case)

{json.dumps({"patient_code": case_id, "cancer_type": case_facts.get("cancer_type"), "stage": case_facts.get("stage"), "molecular_profile": case_facts.get("molecular_profile") or [], "line_of_therapy": case_facts.get("line_of_therapy")}, ensure_ascii=False)}

## pubmed_results (pre-fetched integrator pool — cite only these PMIDs)

{pubmed_text}

## nccn_excerpts (PageIndex tree-search results)

{nccn_sections}

## Other integrator slots referenced by the task prompt are NOT available in this benchmark substrate

- pathology_report: (use the structured `histology` / `stage` fields above)
- ngs_report: (use `molecular_profile` field above)
- treatment_history: (use `line_of_therapy` / structured fields above)
- oncokb_results / civic_results / clinvar_results / gnomad_results: not pre-fetched — treat as empty per the empty-integrator rule
- ctgov_results / chictr_results / fda_eap_results / nmpa_eap_results: not pre-fetched — treat as empty

---

Now produce the strict-JSON output your task prompt specifies, using ONLY the case facts + pubmed_results + nccn_excerpts above. No preamble, no markdown fences.
"""


def run_expert(
    model: str,
    persona_key: str,
    task_key: str,
    case_id: str,
    case_facts: dict[str, Any],
    retrieval: dict[str, Any],
) -> dict[str, Any]:
    system_prompt = _expert_system(persona_key, task_key)
    user = expert_user_prompt(case_id, case_facts, retrieval)
    result = mtb_lite.openrouter_chat(
        model,
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user}],
        max_tokens=1500,
    )
    response = result.get("response") or {}
    choice = (response.get("choices") or [{}])[0]
    content = (choice.get("message") or {}).get("content") or ""
    return {
        "role": persona_key,
        "ok": result.get("ok", False),
        "elapsed_seconds": result.get("_elapsed_seconds") or response.get("_elapsed_seconds"),
        "report": content.strip(),
        "error": None if result.get("ok") else result,
    }


# ---------------------------------------------------------------------------
# Stage 4 — Vince integration (treatment_line_recommendation task)
# ---------------------------------------------------------------------------

def vince_user_prompt(
    case_id: str,
    case_facts: dict[str, Any],
    retrieval: dict[str, Any],
    rosa_report: str,
    bert_report: str,
) -> str:
    return f"""## Structured CRC case

{format_case_text(case_id, case_facts)}

## profile_json

{json.dumps({"patient_code": case_id, "cancer_type": case_facts.get("cancer_type"), "stage": case_facts.get("stage"), "molecular_profile": case_facts.get("molecular_profile") or [], "line_of_therapy": case_facts.get("line_of_therapy")}, ensure_ascii=False)}

## molecular_summary (from Bert)

{bert_report}

## pathology_summary (from Rosa — informs your line-of-therapy logic)

{rosa_report}

## pubmed_results (pre-fetched integrator pool — cite only these PMIDs)

{format_evidence(retrieval.get("pubmed") or [])}

## nccn_excerpts (PageIndex tree-search)

{nccn_pageindex.format_sections((retrieval.get("nccn") or {}).get("sections") or [])}

## ctgov_results / chictr_results / fda_eap_results / nmpa_eap_results

Not pre-fetched in the benchmark substrate — treat as empty.

## patient_value

Not specified by the structured case — assume balanced OS / QoL / toxicity, with NCCN-aligned default preference.

---

Produce the strict-JSON output your task prompt specifies (treatment_line_recommendation schema with options[], trade_off_summary, patient_value_alignment, etc). Cite PMIDs ONLY from pubmed_results above. No preamble, no markdown fences.
"""


def run_vince(
    model: str,
    case_id: str,
    case_facts: dict[str, Any],
    retrieval: dict[str, Any],
    rosa_report: str,
    bert_report: str,
) -> dict[str, Any]:
    system_prompt = _expert_system("vince_persona", "task_treatment")
    user = vince_user_prompt(case_id, case_facts, retrieval, rosa_report, bert_report)
    result = mtb_lite.openrouter_chat(
        model,
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user}],
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
# Stage 5 — Sid delivery (chair-equivalent)
# ---------------------------------------------------------------------------

def sid_user_prompt(
    case_id: str,
    case_facts: dict[str, Any],
    retrieval: dict[str, Any],
    rosa_report: str,
    bert_report: str,
    vince_report: str,
) -> str:
    team_outputs = {
        "rosa": rosa_report,
        "bert": bert_report,
        "vince": vince_report,
    }
    return f"""## Structured CRC case

{format_case_text(case_id, case_facts)}

## team_outputs_json

{json.dumps(team_outputs, ensure_ascii=False)[:6000]}

## henry_verdict_json

{{"l1_verdict": "deferred_to_post_synthesis", "per_gate": [], "blocking_failures": [], "non_blocking_warnings": []}}

## patient_value

Not specified — assume balanced OS / QoL / toxicity priority.

## pending_risk_cards

[]

## pubmed_results (for inline provenance anchors)

{format_evidence(retrieval.get("pubmed") or [])}

## nccn_excerpts (for inline provenance anchors)

{nccn_pageindex.format_sections((retrieval.get("nccn") or {}).get("sections") or [])}

---

Produce your patient-delivery brief per the OPL Sid delivery rules:
- Translate each expert JSON into patient-readable claims, each carrying its three-tier label and provenance anchor (`[PMID: ...]` / `[NCCN-section: ...]`).
- Surface trade-offs (OS / PFS / toxicity / QoL) explicitly.
- Never imperative — always optionful.
- Cap at ~1000 words.

This brief will be schema-shaped into the SBT_Benchmark CRC JSON by a downstream stage. Make the top-3 treatment recommendations + treatment intent + missing information unambiguous in your prose so the shape pass can extract them faithfully.
"""


def run_sid(
    model: str,
    case_id: str,
    case_facts: dict[str, Any],
    retrieval: dict[str, Any],
    rosa_report: str,
    bert_report: str,
    vince_report: str,
) -> dict[str, Any]:
    system_prompt = PROMPTS["pi_delivery"].rstrip() + BENCHMARK_ADAPTATION_NOTE
    user = sid_user_prompt(case_id, case_facts, retrieval, rosa_report, bert_report, vince_report)
    result = mtb_lite.openrouter_chat(
        model,
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user}],
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
# Stage 6 — Schema-shape pass (Sid brief → benchmark CRC JSON)
# ---------------------------------------------------------------------------

SCHEMA_SHAPE_SYSTEM = """You are a structure-mapping agent. You receive a Sid (PI) patient-delivery brief that integrates an OPL AI-scientist-team analysis of a colorectal cancer case, and you convert it into the benchmark CRC JSON schema *without changing the clinical content*. Pick the top 3 ranked treatment recommendations from the Sid brief and Vince's team_outputs, classify each, and copy the treatment-intent / missing-info content faithfully.

Strictly enforce: each enum field receives EXACTLY ONE option (never use 'X | Y' from the template; choose one).

Return only the JSON object — no fences, no prose."""


SCHEMA_SHAPE_TEMPLATE = mtb_lite.CRC_RESPONSE_TEMPLATE


def shape_to_schema(
    model: str,
    case_id: str,
    case_facts: dict[str, Any],
    sid_report: str,
    verifier_feedback: str | None = None,
) -> dict[str, Any]:
    feedback_block = ""
    if verifier_feedback:
        feedback_block = f"""

## Henry L1 verifier feedback (from the previous pass — fix these issues before emitting JSON)

{verifier_feedback}

---
"""
    user = f"""Item ID: {case_id}

Case summary (only confirmed clinical facts):
{format_case_text(case_id, case_facts)}

Sid patient-delivery brief (extract top-3 treatment recommendations from here):
{sid_report}
{feedback_block}

Emit one valid JSON object matching this shape. Pick exactly one enum value per field — never include the '|' separator:

{SCHEMA_SHAPE_TEMPLATE}

The "recommendations" array must contain at most 3 entries. The "missing_information" array must contain at most 5 entries.
"""
    result = mtb_lite.openrouter_chat(
        model,
        [{"role": "system", "content": SCHEMA_SHAPE_SYSTEM}, {"role": "user", "content": user}],
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
# Stage 7 — Henry L1 mechanical-gates verifier (single pass; LLM-orchestrated
# in this benchmark substrate since the deterministic Python gates are not
# wired through SBT — we ask Henry to mechanically read the JSON against the
# OPL gate registry rubric and emit verdict).
# ---------------------------------------------------------------------------

HENRY_USER_TEMPLATE = """## Structured CRC case

{case_text}

## Final recommendation JSON (under audit)

{parsed_json}

## Sid brief excerpt (for provenance context)

{sid_excerpt}

## pubmed_results (for PMID existence + quote checks)

{pubmed_text}

---

Apply the L1 mechanical-gate rubric. For this benchmark substrate, only these gates are feasible:
- G1 PMIDExistenceGate — every cited PMID in the recommendation rationales must appear in `pubmed_results` above.
- G3 DrugINNNormalisationGate — every drug name should be a generic INN (no brand-only).
- G7 ImperativeDetectorGate — no command-form ("you should") at the patient.
- G14 DatasetPatientMatchGate — recommendations must match the case's stage / molecular profile / line of therapy.

Emit ONE JSON object:
{{"verdict": "pass | flag | critical", "issues": ["<short — gate id + what failed>"], "notes": "<one sentence>"}}

`critical` = G1 violation (fabricated PMID) or G14 stage/molecular mismatch.
`flag` = G3 brand name detected, or G7 imperative phrasing detected.
`pass` = all four gates satisfied.

Return only the JSON. No fences."""


def run_henry(
    model: str,
    case_id: str,
    case_facts: dict[str, Any],
    parsed: dict[str, Any],
    sid_report: str,
    retrieval: dict[str, Any],
) -> dict[str, Any]:
    system_prompt = PROMPTS["auditor_l1"].rstrip() + BENCHMARK_ADAPTATION_NOTE
    user = HENRY_USER_TEMPLATE.format(
        case_text=format_case_text(case_id, case_facts),
        parsed_json=json.dumps(parsed, indent=2, ensure_ascii=False),
        sid_excerpt=(sid_report or "")[:1500],
        pubmed_text=format_evidence(retrieval.get("pubmed") or []),
    )
    result = mtb_lite.openrouter_chat(
        model,
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user}],
        max_tokens=600,
    )
    response = result.get("response") or {}
    choice = (response.get("choices") or [{}])[0]
    content = (choice.get("message") or {}).get("content")
    json_ok, verdict_parsed = mtb_lite.extract_json(content)
    record = verdict_parsed if (json_ok and isinstance(verdict_parsed, dict)) else {"verdict": "pass", "issues": [], "notes": ""}
    return {
        "name": "henry_l1",
        "ok": result.get("ok", False),
        "elapsed_seconds": result.get("_elapsed_seconds") or response.get("_elapsed_seconds"),
        "verdict": record.get("verdict", "pass"),
        "issues": record.get("issues") or [],
        "notes": record.get("notes") or "",
        "raw_content": content,
    }


def verify_stage(
    model: str,
    case_id: str,
    case_facts: dict[str, Any],
    parsed: dict[str, Any],
    sid_report: str,
    retrieval: dict[str, Any],
) -> dict[str, Any]:
    henry = run_henry(model, case_id, case_facts, parsed, sid_report, retrieval)
    has_critical = henry.get("verdict") == "critical"
    has_flag = henry.get("verdict") == "flag"
    feedback_lines: list[str] = []
    if henry.get("verdict") in ("critical", "flag"):
        feedback_lines.append(f"[henry_l1/{henry['verdict']}] {henry.get('notes') or ''}")
        for issue in henry.get("issues") or []:
            feedback_lines.append(f"  - {issue}")
    return {
        "verifiers": [henry],
        "has_critical": has_critical,
        "has_flag": has_flag,
        "feedback": "\n".join(feedback_lines) if feedback_lines else None,
    }


# ---------------------------------------------------------------------------
# OPL anchor arm — planner + retrieve + Sid synth (no Rosa / Bert / Vince)
# ---------------------------------------------------------------------------

OPL_ANCHOR_SYNTH_SYSTEM = """You are Sid, the patient's AI scientist team PI, producing a single-pass synthesis for a structured colorectal cancer case from the SBT_Benchmark suite. There has been no Rosa / Bert / Vince fanout — you have only the case facts plus a small retrieved literature + NCCN bundle.

Output up to three ranked treatment recommendations directly, matching the benchmark CRC JSON schema. Cite only PMIDs from the provided pubmed_results bundle. Use three-tier discipline (established / exploratory / speculative) in your rationale_brief fields where space permits.

Return only valid JSON matching the schema provided. Do not include chain-of-thought."""


def run_opl_anchor(
    model: str,
    case_id: str,
    case_facts: dict[str, Any],
    *,
    per_query_results: int = 3,
    nccn_max_nodes: int = 4,
) -> dict[str, Any]:
    total_started = time.time()
    plan, plan_diag = plan_stage(model, case_id, case_facts)

    pm_started = time.time()
    evidence = mtb_lite.retrieve_evidence(plan.get("pubmed_queries") or [], per_query=per_query_results)
    pm_elapsed = round(time.time() - pm_started, 3)

    nccn = nccn_pageindex.tree_search(
        model,
        plan.get("nccn_query") or "",
        case_facts.get("cancer_type") or "",
        max_nodes=nccn_max_nodes,
    )
    nccn_sections_text = nccn_pageindex.format_sections(nccn.get("sections") or [])

    user = f"""Item ID: {case_id}

Case summary (only confirmed clinical facts):
{format_case_text(case_id, case_facts)}

NCCN guideline sections (retrieved via PageIndex tree-search):
{nccn_sections_text}

Retrieved literature evidence (from PubMed):
{format_evidence(evidence)}

Respond with one valid JSON answer object using this shape (pick exactly one enum value per field, never use '|'):

{mtb_lite.CRC_RESPONSE_TEMPLATE}

The "recommendations" array must contain at most 3 objects. The "missing_information" array must contain at most 5 objects.
"""
    synth = mtb_lite.openrouter_chat(
        model,
        [{"role": "system", "content": OPL_ANCHOR_SYNTH_SYSTEM}, {"role": "user", "content": user}],
        max_tokens=1500,
    )
    response = synth.get("response") or {}
    choice = (response.get("choices") or [{}])[0]
    content = (choice.get("message") or {}).get("content")
    json_ok, parsed = mtb_lite.extract_json(content)
    total_elapsed = round(time.time() - total_started, 3)
    return {
        "ok": synth.get("ok", False) and plan_diag.get("ok", False),
        "elapsed_seconds": total_elapsed,
        "finish_reason": choice.get("finish_reason"),
        "content_present": bool(content),
        "json_parse_ok": json_ok,
        "parsed_json": parsed if json_ok else None,
        "raw_response": response if synth.get("ok") else None,
        "error": None if synth.get("ok") else synth,
        "intermediate": {
            "plan": plan,
            "plan_elapsed_seconds": plan_diag.get("elapsed_seconds"),
            "pubmed_elapsed_seconds": pm_elapsed,
            "pubmed_n_hits": len(evidence),
            "nccn_node_ids": nccn.get("node_ids"),
            "nccn_ok": nccn.get("ok"),
            "synth_elapsed_seconds": synth.get("_elapsed_seconds") or response.get("_elapsed_seconds"),
        },
    }


# ---------------------------------------------------------------------------
# OPL full arm — planner + retrieve + Rosa∥Bert + Vince + Sid + shape + Henry
# ---------------------------------------------------------------------------

def run_opl_full(model: str, case_id: str, case_facts: dict[str, Any]) -> dict[str, Any]:
    total_started = time.time()

    plan, plan_diag = plan_stage(model, case_id, case_facts)
    retrieval = retrieve_stage(model, plan, case_facts)

    # Phase-1 parallel experts: Rosa (pathology) + Bert (molecular)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        rosa_fut = pool.submit(run_expert, model, "rosa_persona", "task_pathology", case_id, case_facts, retrieval)
        bert_fut = pool.submit(run_expert, model, "bert_persona", "task_molecular", case_id, case_facts, retrieval)
        rosa = rosa_fut.result()
        bert = bert_fut.result()

    # Vince integration
    vince = run_vince(model, case_id, case_facts, retrieval, rosa["report"], bert["report"])

    # Sid delivery synthesis
    sid = run_sid(model, case_id, case_facts, retrieval, rosa["report"], bert["report"], vince["report"])

    # Schema-shape pass 1
    shape1 = shape_to_schema(model, case_id, case_facts, sid["report"])
    parsed = shape1.get("parsed_json")

    # Henry L1 verifier
    verify_result: dict[str, Any] = {"verifiers": [], "has_critical": False, "has_flag": False, "feedback": None}
    shape2: dict[str, Any] | None = None
    if isinstance(parsed, dict):
        verify_result = verify_stage(model, case_id, case_facts, parsed, sid["report"], retrieval)
        if verify_result["has_critical"] or verify_result["has_flag"]:
            shape2 = shape_to_schema(model, case_id, case_facts, sid["report"], verifier_feedback=verify_result["feedback"])
            if shape2.get("parsed_json"):
                parsed = shape2["parsed_json"]

    final_shape = shape2 or shape1
    total_elapsed = round(time.time() - total_started, 3)
    return {
        "ok": all([plan_diag.get("ok"), rosa.get("ok"), bert.get("ok"), vince.get("ok"), sid.get("ok"), final_shape.get("ok")]),
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
            "rosa_elapsed_seconds": rosa.get("elapsed_seconds"),
            "rosa_ok": rosa.get("ok"),
            "bert_elapsed_seconds": bert.get("elapsed_seconds"),
            "bert_ok": bert.get("ok"),
            "vince_elapsed_seconds": vince.get("elapsed_seconds"),
            "vince_ok": vince.get("ok"),
            "sid_elapsed_seconds": sid.get("elapsed_seconds"),
            "sid_ok": sid.get("ok"),
            "shape1_elapsed_seconds": shape1.get("elapsed_seconds"),
            "verifier_pass": "fail" if verify_result.get("has_critical") else ("flag" if verify_result.get("has_flag") else "pass"),
            "verifier_results": verify_result.get("verifiers"),
            "reshape_triggered": shape2 is not None,
            "shape2_elapsed_seconds": shape2.get("elapsed_seconds") if shape2 else None,
        },
    }


# ---------------------------------------------------------------------------
# NCCN surface — same pipeline, NCCN schema output
# ---------------------------------------------------------------------------

OPL_NCCN_SYNTH_SYSTEM = """You are Sid, the patient's AI scientist team PI, evaluating whether the structured patient facts for an NCCN-derived decision case are sufficient to determine the next clinical management step.

Output one JSON object matching the SBT_Benchmark NCCN decision schema. Use three-tier discipline; cite only PMIDs from the provided pubmed_results bundle; never fabricate. Choose `decision="routing"` when the appropriate upstream pathway / specialist can be identified even if downstream regimen details are unknown.

Return only valid JSON. No prose, no markdown fences."""


def shape_to_nccn_schema(
    model: str,
    item_id: str,
    scenario_label: str,
    patient_facts: list[dict[str, Any]],
    sid_report: str,
    verifier_feedback: str | None = None,
) -> dict[str, Any]:
    feedback_block = ""
    if verifier_feedback:
        feedback_block = f"\n\n## Henry L1 verifier feedback (fix these issues before emitting JSON)\n{verifier_feedback}\n"
    user = f"""Item ID: {item_id}

{format_patient_facts_block(scenario_label, patient_facts)}

Sid patient-delivery brief (extract the decision from here):
{sid_report}
{feedback_block}

Emit one valid JSON object matching this NCCN-decision shape. Pick exactly one enum value per field — never include '|':

{mtb_lite.NCCN_RESPONSE_TEMPLATE}

The "basis" array must contain 1 to 3 strings. The "missing_or_needed" array must contain at most 5 objects.
"""
    result = mtb_lite.openrouter_chat(
        model,
        [{"role": "system", "content": SCHEMA_SHAPE_SYSTEM}, {"role": "user", "content": user}],
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


def run_opl_anchor_nccn(
    model: str,
    item_id: str,
    scenario_label: str,
    patient_facts: list[dict[str, Any]],
    cancer_type_hint: str = "COLON_CANCER",
    *,
    per_query_results: int = 3,
    nccn_max_nodes: int = 4,
) -> dict[str, Any]:
    """OPL anchor arm on the NCCN decision surface (planner + retrieve + Sid synth)."""
    total_started = time.time()

    # Plan stage adapted to NCCN facts
    plan_user = f"""Item ID: {item_id}

{format_patient_facts_block(scenario_label, patient_facts)}

Return JSON only with pubmed_queries (1-3) and nccn_query (1).
"""
    plan_res = mtb_lite.openrouter_chat(
        model,
        [{"role": "system", "content": OPL_PLAN_SYSTEM}, {"role": "user", "content": plan_user}],
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

    pm_started = time.time()
    evidence = mtb_lite.retrieve_evidence(queries, per_query=per_query_results)
    pm_elapsed = round(time.time() - pm_started, 3)

    nccn = nccn_pageindex.tree_search(model, nccn_query, cancer_type_hint or "COLON_CANCER", max_nodes=nccn_max_nodes)
    nccn_sections_text = nccn_pageindex.format_sections(nccn.get("sections") or [])

    synth_user = f"""Item ID: {item_id}

{format_patient_facts_block(scenario_label, patient_facts)}

NCCN guideline sections (retrieved via PageIndex tree-search):
{nccn_sections_text}

Retrieved literature evidence (from PubMed):
{format_evidence(evidence)}

Respond with one valid JSON answer object using this shape (pick exactly one enum value per field, never use '|'):

{mtb_lite.NCCN_RESPONSE_TEMPLATE}

The "basis" array must contain 1 to 3 strings. The "missing_or_needed" array must contain at most 5 objects.
"""
    synth = mtb_lite.openrouter_chat(
        model,
        [{"role": "system", "content": OPL_NCCN_SYNTH_SYSTEM}, {"role": "user", "content": synth_user}],
        max_tokens=1200,
    )
    s_resp = synth.get("response") or {}
    s_choice = (s_resp.get("choices") or [{}])[0]
    s_content = (s_choice.get("message") or {}).get("content")
    json_ok, parsed = mtb_lite.extract_json(s_content)
    total_elapsed = round(time.time() - total_started, 3)
    return {
        "ok": synth.get("ok", False) and plan_res.get("ok", False),
        "elapsed_seconds": total_elapsed,
        "finish_reason": s_choice.get("finish_reason"),
        "content_present": bool(s_content),
        "json_parse_ok": json_ok,
        "parsed_json": parsed if json_ok else None,
        "raw_response": s_resp if synth.get("ok") else None,
        "error": None if synth.get("ok") else synth,
        "intermediate": {
            "plan": {"pubmed_queries": queries, "nccn_query": nccn_query},
            "pubmed_n_hits": len(evidence),
            "pubmed_elapsed_seconds": pm_elapsed,
            "nccn_node_ids": nccn.get("node_ids"),
            "nccn_ok": nccn.get("ok"),
            "synth_elapsed_seconds": synth.get("_elapsed_seconds") or s_resp.get("_elapsed_seconds"),
        },
    }


def run_opl_full_nccn(
    model: str,
    item_id: str,
    scenario_label: str,
    patient_facts: list[dict[str, Any]],
    cancer_type_hint: str = "COLON_CANCER",
) -> dict[str, Any]:
    """OPL full pipeline (Rosa∥Bert + Vince + Sid + Henry) on the NCCN surface."""
    total_started = time.time()

    # Plan
    plan_user = f"""Item ID: {item_id}

{format_patient_facts_block(scenario_label, patient_facts)}

Return JSON only with pubmed_queries (1-3) and nccn_query (1).
"""
    plan_res = mtb_lite.openrouter_chat(
        model,
        [{"role": "system", "content": OPL_PLAN_SYSTEM}, {"role": "user", "content": plan_user}],
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

    pm_started = time.time()
    pubmed = mtb_lite.retrieve_evidence(queries, per_query=3)
    pm_elapsed = round(time.time() - pm_started, 3)
    nccn = nccn_pageindex.tree_search(model, nccn_query, cancer_type_hint or "COLON_CANCER", max_nodes=4)
    retrieval = {"pubmed": pubmed, "nccn": nccn, "pubmed_elapsed_seconds": pm_elapsed}

    # Construct a synthetic "case_facts"-shaped dict for expert prompts that read case_text
    case_id = item_id
    case_facts: dict[str, Any] = {
        "cancer_type": cancer_type_hint or "COLON_CANCER",
        "scenario_label": scenario_label,
        "patient_facts": patient_facts,
    }
    nccn_text = format_patient_facts_block(scenario_label, patient_facts)

    def expert_user(persona_key: str, task_key: str) -> str:
        return f"""## NCCN-derived decision case (treat fields as ground truth)

{nccn_text}

## profile_json (synthesised from the structured case)

{json.dumps({"item_id": item_id, "scenario_label": scenario_label, "cancer_type": cancer_type_hint or "COLON_CANCER"}, ensure_ascii=False)}

## pubmed_results

{format_evidence(retrieval.get("pubmed") or [])}

## nccn_excerpts (PageIndex tree-search)

{nccn_pageindex.format_sections((retrieval.get("nccn") or {}).get("sections") or [])}

---

Now produce the strict-JSON output your task prompt specifies, using ONLY the facts + retrieved evidence above. No preamble, no markdown fences.
"""

    def run_role(persona_key: str, task_key: str) -> dict[str, Any]:
        system_prompt = _expert_system(persona_key, task_key)
        result = mtb_lite.openrouter_chat(
            model,
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": expert_user(persona_key, task_key)}],
            max_tokens=1500,
        )
        resp = result.get("response") or {}
        ch = (resp.get("choices") or [{}])[0]
        return {
            "role": persona_key,
            "ok": result.get("ok", False),
            "elapsed_seconds": result.get("_elapsed_seconds") or resp.get("_elapsed_seconds"),
            "report": ((ch.get("message") or {}).get("content") or "").strip(),
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        rosa_fut = pool.submit(run_role, "rosa_persona", "task_pathology")
        bert_fut = pool.submit(run_role, "bert_persona", "task_molecular")
        rosa = rosa_fut.result()
        bert = bert_fut.result()

    vince = run_vince(model, case_id, case_facts, retrieval, rosa["report"], bert["report"])
    sid = run_sid(model, case_id, case_facts, retrieval, rosa["report"], bert["report"], vince["report"])

    # Schema-shape pass 1 (NCCN schema)
    shape1 = shape_to_nccn_schema(model, item_id, scenario_label, patient_facts, sid["report"])
    parsed = shape1.get("parsed_json")

    # Henry verifier
    verify_result: dict[str, Any] = {"verifiers": [], "has_critical": False, "has_flag": False, "feedback": None}
    shape2: dict[str, Any] | None = None
    if isinstance(parsed, dict):
        verify_result = verify_stage(model, item_id, case_facts, parsed, sid["report"], retrieval)
        if verify_result["has_critical"] or verify_result["has_flag"]:
            shape2 = shape_to_nccn_schema(model, item_id, scenario_label, patient_facts, sid["report"], verifier_feedback=verify_result["feedback"])
            if shape2.get("parsed_json"):
                parsed = shape2["parsed_json"]

    final_shape = shape2 or shape1
    total_elapsed = round(time.time() - total_started, 3)
    return {
        "ok": all([plan_res.get("ok"), rosa.get("ok"), bert.get("ok"), vince.get("ok"), sid.get("ok"), final_shape.get("ok")]),
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
            "pubmed_elapsed_seconds": pm_elapsed,
            "nccn_node_ids": nccn.get("node_ids"),
            "nccn_ok": nccn.get("ok"),
            "rosa_ok": rosa.get("ok"),
            "bert_ok": bert.get("ok"),
            "vince_ok": vince.get("ok"),
            "sid_ok": sid.get("ok"),
            "verifier_pass": "fail" if verify_result.get("has_critical") else ("flag" if verify_result.get("has_flag") else "pass"),
            "reshape_triggered": shape2 is not None,
        },
    }
