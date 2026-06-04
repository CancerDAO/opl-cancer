#!/usr/bin/env python3
"""Lightweight MTB pipeline for benchmark evaluation.

Mirrors the *framework* contribution of cancerdao-vmtb without the heavy
multi-agent / organizer / verifier machinery. The three pillars exposed are:

  1. Planner   — LLM extracts focused literature / guideline queries from a
                 structured case (cancer_type, stage, molecular_profile, ...).
  2. Retrieval — Live PubMed E-utilities lookup for evidence per query, plus a
                 bundled NCCN-style guideline anchor extracted from the case.
  3. Synthesis — LLM consumes the case + retrieved evidence + guideline anchor
                 and produces the benchmark CRC JSON schema directly.

Both arms (baseline / mtb) call the same underlying LLM, so the contrast
isolates the framework's retrieval + multi-step structuring contribution.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


OPENROUTER_BASE_URL = os.environ.get(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
).rstrip("/")
PUBMED_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


NCCN_RESPONSE_TEMPLATE = """{
  "item_id": "copy the item id",
  "decision": "proceed | stop_missing_info | stop_need_evidence | routing",
  "next_step": "string or null",
  "basis": ["1 to 3 short supporting facts; if no sufficient facts are provided, state that briefly"],
  "missing_or_needed": [
    {
      "need_type": "discriminator | missing_information | evidence",
      "category": "stage | biomarker | prior_treatment | resectability | treatment_intent | performance_status | evidence | recurrence_or_progression | response_assessment | eligibility | other",
      "detail": "what is needed and why"
    }
  ],
  "reasoning": "one brief sentence"
}"""


CRC_RESPONSE_TEMPLATE = """{
  "item_id": "copy the item id",
  "treatment_intent": "neoadjuvant | adjuvant | first_line | later_line | palliative | maintenance | surveillance | uncertain",
  "recommendations": [
    {
      "rank": 1,
      "therapy": "specific therapy or management action",
      "therapy_class": "surgery | radiation | systemic | immunotherapy | targeted_therapy | chemotherapy | surveillance | testing | supportive_care | other",
      "rationale_brief": "one brief sentence"
    }
  ],
  "missing_information": [
    {
      "slot": "stage | biomarker | prior_treatment | resectability | treatment_intent | performance_status | evidence | molecular_profile | other",
      "detail": "what is missing and why"
    }
  ],
  "do_not_recommend_yet": false,
  "rationale_brief": "one brief sentence"
}"""


# ---------------------------------------------------------------------------
# OpenRouter chat (verbatim adaptation of the benchmark's runner — same shape)
# ---------------------------------------------------------------------------

def openrouter_chat(
    model: str,
    messages: list[dict[str, str]],
    *,
    max_tokens: int = 1200,
    timeout: int = 120,
    temperature: float = 0.0,
) -> dict[str, Any]:
    api_key = os.environ["OPENROUTER_API_KEY"]
    # Reasoning models (e.g. MiniMax-M2, deepseek-r1) emit <think>…</think>
    # blocks that consume the completion budget before the actual JSON answer.
    # The OPENROUTER_MAX_TOKENS_FLOOR env var lets the caller lift the per-call
    # max_tokens to a model-appropriate floor without editing every call site.
    floor = int(os.environ.get("OPENROUTER_MAX_TOKENS_FLOOR", "0") or "0")
    if floor and max_tokens < floor:
        max_tokens = floor
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if os.environ.get("OPENROUTER_HTTP_REFERER"):
        headers["HTTP-Referer"] = os.environ["OPENROUTER_HTTP_REFERER"]
    if os.environ.get("OPENROUTER_APP_TITLE"):
        headers["X-Title"] = os.environ["OPENROUTER_APP_TITLE"]
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": 1.0,
        "max_tokens": max_tokens,
    }
    started = time.time()
    max_retries = int(os.environ.get("OPENROUTER_MAX_RETRIES", "3"))
    last_exc: dict[str, Any] | None = None
    for attempt in range(max_retries + 1):
        request = urllib.request.Request(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
            body["_elapsed_seconds"] = round(time.time() - started, 3)
            return {"ok": True, "response": body}
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            # Retry 429 / 5xx; surface 4xx immediately.
            if exc.code in (429,) or 500 <= exc.code < 600:
                last_exc = {"error_type": "HTTPError", "http_status": exc.code, "error": error_body[:2000]}
                if attempt < max_retries:
                    time.sleep(min(2 ** attempt, 30))
                    continue
            return {
                "ok": False,
                "http_status": exc.code,
                "error": error_body[:2000],
                "_elapsed_seconds": round(time.time() - started, 3),
            }
        except Exception as exc:  # noqa: BLE001 — transient: timeout, connection reset, DNS hiccup, …
            last_exc = {"error_type": type(exc).__name__, "error": str(exc)}
            if attempt < max_retries:
                time.sleep(min(2 ** attempt, 30))
                continue
            return {
                "ok": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "_elapsed_seconds": round(time.time() - started, 3),
            }
    # Should be unreachable because every path either returns or continues, but
    # keep an explicit fallback for the type-checker.
    return {
        "ok": False,
        **(last_exc or {"error_type": "Unknown", "error": "retry loop exhausted"}),
        "_elapsed_seconds": round(time.time() - started, 3),
    }


def extract_json(content: str | None) -> tuple[bool, Any]:
    if not content:
        return False, None
    text = content.strip()
    # Strip reasoning-model think blocks (MiniMax-M2, deepseek-r1, qwq, etc).
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    # Drop a stray leading </think> if the opener was truncated server-side.
    text = re.sub(r"^</think>\s*", "", text, flags=re.IGNORECASE).strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return True, json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return True, json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    return False, None


# ---------------------------------------------------------------------------
# Case formatting helpers
# ---------------------------------------------------------------------------

def format_case_summary(case_facts: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, value in case_facts.items():
        if key == "case_id" or value in (None, "", [], {}):
            continue
        if isinstance(value, list):
            rendered_parts = []
            for entry in value:
                if isinstance(entry, dict):
                    rendered_parts.append("; ".join(f"{k}: {v}" for k, v in entry.items()))
                else:
                    rendered_parts.append(str(entry))
            rendered = " | ".join(rendered_parts)
        else:
            rendered = str(value)
        lines.append(f"- {key}: {rendered}")
    return "\n".join(lines) if lines else "- No case facts provided."


# ---------------------------------------------------------------------------
# Baseline arm — single LLM call (mirrors openrouter_smoke_run.py exactly)
# ---------------------------------------------------------------------------

BASELINE_CRC_SYSTEM = """You are an oncology clinical decision assistant. You will be given a clinical case summary for a colorectal cancer patient. Based only on the information provided, recommend up to three treatment options ranked by appropriateness.

For each recommendation:
- State the specific therapy or management action.
- Classify it by therapy class.
- Provide a one-sentence rationale.

Also assess:
- The most appropriate treatment intent for this clinical scenario.
- Whether any critical clinical information is missing that would be needed before finalizing a treatment recommendation.
- Whether proceeding with a specific recommendation would be unsupported given the available information.

Do not assume or infer any clinical fact not explicitly stated, including biomarker status, staging details, prior treatment history, resectability, treatment intent, or performance status.

No additional clinical information is available beyond the case summary provided.

Return only valid JSON matching the schema provided. Do not include chain-of-thought.
"""


def baseline_user_prompt(case_id: str, case_facts: dict[str, Any]) -> str:
    return f"""Item ID: {case_id}

Case summary:
{format_case_summary(case_facts)}

Based only on the information above, provide up to three ranked treatment recommendations for this colorectal cancer case.

If the available information is insufficient to support a specific treatment recommendation, indicate what is missing instead of advancing to an unsupported recommendation.

No additional clinical information is available beyond the case summary above.

Respond with one valid JSON answer object using this shape:

{CRC_RESPONSE_TEMPLATE}

Do not return a JSON Schema definition. Do not include "$schema", "title", "type", "properties", "required", or "additionalProperties".
The "recommendations" array must contain at most 3 objects. The "missing_information" array must contain at most 5 objects.
"""


NCCN_SYSTEM_PROMPT = """You are an oncology clinical decision assistant evaluating whether the available patient information is sufficient to determine the next clinical management step.

You will be given a set of known patient facts for a case at a specific point in a guideline-derived oncology decision pathway. You do not have access to guideline text, pathway diagrams, web browsing, or retrieval tools.

Based only on the facts provided, determine the appropriate next clinical management step:

- If the provided information is sufficient to identify the next management action or pathway, state it and cite the key supporting facts.
- If critical clinical information is missing and must be obtained before a management decision can be made, identify what is missing and why it is needed.
- If specific diagnostic evidence, pathology confirmation, or test results are required before the decision pathway can be resolved, state what is needed.
- If the case should be directed to a different management pathway, module, or specialist evaluation, state the appropriate routing target.
- Pathway-level routing or handoff is itself a valid management decision. Choose decision="routing" when the appropriate upstream pathway, module, handoff, or specialist evaluation can be identified from the provided facts, even if downstream regimen-level details remain unknown. Do not stop solely because regimen-level details are missing.

Do not assume or infer any clinical fact not explicitly stated, including but not limited to: staging details, biomarker or molecular status, prior treatment history, surgical resectability, treatment intent, performance status, or response assessment results. Treat any unstated clinical parameter as unknown.

No additional clinical information is available beyond what is listed below.

Return only valid JSON matching the schema provided. Include one brief reasoning sentence; do not provide chain-of-thought.
"""


def format_patient_facts(patient_facts: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for fact in patient_facts:
        label = fact.get("slot_label") or fact.get("label") or "clinical fact"
        value = fact.get("value")
        if value in (None, "", [], {}):
            value = "not available"
        lines.append(f"- {label}: {value}")
    return "\n".join(lines) if lines else "- No patient facts provided."


def nccn_user_prompt(item_id: str, scenario_label: str, patient_facts: list[dict[str, Any]]) -> str:
    return f"""Item ID: {item_id}

Scenario:
{scenario_label or "Not specified"}

Patient facts:
{format_patient_facts(patient_facts)}

Based only on the facts above, determine the appropriate next clinical management step. If the available information is insufficient, state what is missing or what evidence is needed instead of advancing to a specific downstream treatment or management action.

No additional clinical information is available beyond the facts listed above.

Respond with one valid JSON answer object using this shape:

{NCCN_RESPONSE_TEMPLATE}

Do not return a JSON Schema definition. Do not include "$schema", "title", "type", "properties", "required", or "additionalProperties".
The "basis" array must contain 1 to 3 strings. The "missing_or_needed" array must contain at most 5 objects.
"""


def run_baseline_nccn(model: str, item_id: str, scenario_label: str, patient_facts: list[dict[str, Any]]) -> dict[str, Any]:
    messages = [
        {"role": "system", "content": NCCN_SYSTEM_PROMPT},
        {"role": "user", "content": nccn_user_prompt(item_id, scenario_label, patient_facts)},
    ]
    result = openrouter_chat(model, messages)
    response = result.get("response") or {}
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content")
    json_ok, parsed = extract_json(content)
    return {
        "ok": result.get("ok", False),
        "elapsed_seconds": result.get("_elapsed_seconds") or response.get("_elapsed_seconds"),
        "finish_reason": choice.get("finish_reason"),
        "content_present": bool(content),
        "json_parse_ok": json_ok,
        "parsed_json": parsed if json_ok else None,
        "raw_response": response if result.get("ok") else None,
        "error": None if result.get("ok") else result,
        "intermediate": None,
    }


def run_baseline(model: str, case_id: str, case_facts: dict[str, Any]) -> dict[str, Any]:
    messages = [
        {"role": "system", "content": BASELINE_CRC_SYSTEM},
        {"role": "user", "content": baseline_user_prompt(case_id, case_facts)},
    ]
    result = openrouter_chat(model, messages)
    response = result.get("response") or {}
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content")
    json_ok, parsed = extract_json(content)
    return {
        "ok": result.get("ok", False),
        "elapsed_seconds": result.get("_elapsed_seconds") or response.get("_elapsed_seconds"),
        "finish_reason": choice.get("finish_reason"),
        "content_present": bool(content),
        "json_parse_ok": json_ok,
        "parsed_json": parsed if json_ok else None,
        "raw_response": response if result.get("ok") else None,
        "error": None if result.get("ok") else result,
        "intermediate": None,
    }


# ---------------------------------------------------------------------------
# MTB arm — planner + PubMed + guideline anchor + synthesis
# ---------------------------------------------------------------------------

PLANNER_SYSTEM = """You are the planning agent of a virtual molecular tumor board (vMTB). Given a structured colorectal cancer case, decide what evidence to retrieve before any treatment recommendation is made.

Output a single JSON object with two fields:
- "pubmed_queries": 1 to 3 short literature queries, each a focused English search string suitable for PubMed (use cancer type + stage + molecular variants + clinical context). Each ≤ 120 characters.
- "nccn_query": one focused English query to look up in the NCCN colorectal cancer guideline tree (e.g., "stage IV colon cancer first-line systemic therapy RAS/BRAF wildtype"). The downstream tool runs an LLM tree-search over the actual NCCN PageIndex.

Return only JSON. No prose, no markdown fences."""


def planner_user_prompt(case_id: str, case_facts: dict[str, Any]) -> str:
    return f"""Item ID: {case_id}

Case summary:
{format_case_summary(case_facts)}

Decide retrieval. Output JSON only:
{{"pubmed_queries": ["..."], "nccn_anchor": "..."}}"""


def plan_retrieval(model: str, case_id: str, case_facts: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    messages = [
        {"role": "system", "content": PLANNER_SYSTEM},
        {"role": "user", "content": planner_user_prompt(case_id, case_facts)},
    ]
    result = openrouter_chat(model, messages, max_tokens=400)
    response = result.get("response") or {}
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content")
    json_ok, parsed = extract_json(content)
    plan = parsed if (json_ok and isinstance(parsed, dict)) else {}
    diag = {
        "ok": result.get("ok", False),
        "elapsed_seconds": result.get("_elapsed_seconds") or response.get("_elapsed_seconds"),
        "json_parse_ok": json_ok,
        "raw_content": content,
        "error": None if result.get("ok") else result,
    }
    # Defensive defaults
    queries = plan.get("pubmed_queries") or []
    if not isinstance(queries, list):
        queries = []
    queries = [str(q)[:200] for q in queries if isinstance(q, (str, int, float)) and str(q).strip()][:3]
    if not queries:
        # Fallback heuristic
        fallback = build_fallback_query(case_facts)
        queries = [fallback] if fallback else []
    nccn_query = plan.get("nccn_query") or plan.get("nccn_anchor")  # accept legacy field name
    if not isinstance(nccn_query, str) or not nccn_query.strip():
        nccn_query = build_fallback_query(case_facts) or "colorectal cancer treatment principles"
    return {"pubmed_queries": queries, "nccn_query": nccn_query}, diag


def build_fallback_query(case_facts: dict[str, Any]) -> str:
    parts: list[str] = []
    cancer = case_facts.get("cancer_type")
    if cancer:
        parts.append(str(cancer).replace("_", " ").lower())
    stage = case_facts.get("stage")
    if stage:
        parts.append(f"stage {stage}")
    line = case_facts.get("line_of_therapy")
    if line:
        parts.append(str(line).replace("_", " "))
    mol = case_facts.get("molecular_profile") or []
    for entry in mol[:3]:
        if isinstance(entry, dict):
            g = entry.get("gene")
            s = entry.get("status")
            if g and s:
                parts.append(f"{g} {s}")
    parts.append("treatment")
    return " ".join(parts)[:200]


# ---- PubMed E-utilities ----------------------------------------------------

def _pubmed_get_json(url: str, *, timeout: int = 30) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "vmtb-bench/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _pubmed_get_text(url: str, *, timeout: int = 30) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "vmtb-bench/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def pubmed_search(query: str, *, retmax: int = 3, timeout: int = 30) -> list[dict[str, str]]:
    """Lightweight PubMed search. Returns list of {pmid, title, abstract, year}."""
    if not query.strip():
        return []
    try:
        esearch_url = (
            f"{PUBMED_EUTILS}/esearch.fcgi?db=pubmed"
            f"&term={urllib.parse.quote(query)}"
            f"&retmax={retmax}&sort=relevance&retmode=json"
        )
        data = _pubmed_get_json(esearch_url, timeout=timeout)
        ids = (data.get("esearchresult") or {}).get("idlist") or []
        if not ids:
            return []
        # Use efetch for title + abstract (XML, parse minimally).
        efetch_url = (
            f"{PUBMED_EUTILS}/efetch.fcgi?db=pubmed"
            f"&id={','.join(ids)}&retmode=xml&rettype=abstract"
        )
        xml = _pubmed_get_text(efetch_url, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        return [{"pmid": "", "title": f"[pubmed_error: {type(exc).__name__}]", "abstract": str(exc)[:200], "year": ""}]

    return _parse_pubmed_xml(xml)


def _parse_pubmed_xml(xml: str) -> list[dict[str, str]]:
    # Use ElementTree to avoid pulling lxml.
    import xml.etree.ElementTree as ET
    out: list[dict[str, str]] = []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return out
    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//PMID")
        title_el = article.find(".//ArticleTitle")
        abstract_parts = []
        for ab in article.findall(".//Abstract/AbstractText"):
            label = ab.attrib.get("Label")
            text = "".join(ab.itertext()).strip()
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
        year_el = article.find(".//PubDate/Year")
        out.append(
            {
                "pmid": (pmid_el.text or "").strip() if pmid_el is not None else "",
                "title": ("".join(title_el.itertext()).strip() if title_el is not None else ""),
                "abstract": " ".join(abstract_parts).strip()[:1200],
                "year": (year_el.text or "").strip() if year_el is not None else "",
            }
        )
    return out


def retrieve_evidence(queries: list[str], *, per_query: int = 3) -> list[dict[str, Any]]:
    bundle: list[dict[str, Any]] = []
    seen_pmids: set[str] = set()
    for q in queries:
        results = pubmed_search(q, retmax=per_query)
        for r in results:
            pmid = r.get("pmid") or ""
            if pmid and pmid in seen_pmids:
                continue
            if pmid:
                seen_pmids.add(pmid)
            bundle.append({"query": q, **r})
    return bundle


def format_evidence(evidence: list[dict[str, Any]]) -> str:
    if not evidence:
        return "(no literature evidence retrieved)"
    lines: list[str] = []
    for i, item in enumerate(evidence, start=1):
        title = item.get("title") or "(no title)"
        pmid = item.get("pmid") or ""
        year = item.get("year") or ""
        abstract = (item.get("abstract") or "").strip()
        if len(abstract) > 600:
            abstract = abstract[:600] + "..."
        lines.append(
            f"[E{i}] PMID:{pmid} ({year}) — {title}\n     query: {item.get('query', '')}\n     abstract: {abstract}"
        )
    return "\n".join(lines)


# ---- Synthesis agent --------------------------------------------------------

SYNTH_SYSTEM = """You are the chair of a virtual molecular tumor board (vMTB) for colorectal cancer.

You will be given:
1. A structured patient case (the only ground-truth clinical facts).
2. NCCN guideline sections — retrieved from the official NCCN colorectal cancer PageIndex via tree-search.
3. A bundle of recent PubMed abstracts retrieved by the literature agent.

Your job is to integrate the retrieved evidence with the case facts and produce up to three ranked treatment recommendations matching the benchmark CRC JSON schema.

Rules:
- Do not assume or invent clinical facts not stated in the case (staging, biomarker status, prior treatment, resectability, treatment intent, performance status). Treat unstated parameters as missing.
- Recommendations must be consistent with the case facts AND aligned with the retrieved NCCN sections.
- Cite supporting evidence by referencing the [E#] tag for PubMed entries, or the bracketed NCCN node_id, in the rationale_brief field when applicable.
- If the case lacks information critical to recommend a specific therapy, list it in missing_information; if no defensible recommendation can be made, set do_not_recommend_yet=true with empty recommendations.

Return only valid JSON matching the schema provided. Do not include chain-of-thought.
"""


def synth_user_prompt(
    case_id: str,
    case_facts: dict[str, Any],
    nccn_sections_text: str,
    evidence: list[dict[str, Any]],
) -> str:
    return f"""Item ID: {case_id}

Case summary (only clinical facts available):
{format_case_summary(case_facts)}

NCCN guideline sections (retrieved via PageIndex tree-search):
{nccn_sections_text}

Retrieved literature evidence (from PubMed):
{format_evidence(evidence)}

Integrate the case facts with the retrieved NCCN sections and literature evidence. Provide up to three ranked treatment recommendations for this colorectal cancer case.

Respond with one valid JSON answer object using this shape:

{CRC_RESPONSE_TEMPLATE}

Do not return a JSON Schema definition. Do not include "$schema", "title", "type", "properties", "required", or "additionalProperties".
The "recommendations" array must contain at most 3 objects. The "missing_information" array must contain at most 5 objects.
"""


NCCN_SYNTH_SYSTEM = """You are the chair of a virtual molecular tumor board (vMTB) helping evaluate whether available patient information is sufficient to determine the next clinical management step in an NCCN-derived decision pathway.

You will be given:
1. A scenario label + structured patient facts (the only ground-truth clinical facts).
2. NCCN guideline sections retrieved from the local PageIndex tree-search.
3. PubMed abstracts retrieved by the literature agent.

Output exactly one JSON object matching the benchmark NCCN schema:
- "decision": one of "proceed", "stop_missing_info", "stop_need_evidence", "routing".
- "next_step": a short string describing the next management action, or null.
- "basis": 1–3 short supporting facts. If the case lacks sufficient facts, state that briefly.
- "missing_or_needed": list of objects with need_type / category / detail. Empty array if everything is sufficient.
- "reasoning": one brief sentence.

Rules:
- Do NOT assume or invent facts not explicitly stated (staging, biomarker, prior treatment, performance status, etc.). Treat unstated parameters as unknown.
- Choose decision="routing" when the right upstream pathway / module / specialist can be identified even if downstream regimen details are unknown.
- Cite supporting evidence by referencing NCCN node_ids or [E#] PubMed tags in the basis or reasoning when applicable.
- Return only valid JSON, no chain-of-thought, no markdown fences.
"""


def nccn_synth_user_prompt(
    item_id: str,
    scenario_label: str,
    patient_facts: list[dict[str, Any]],
    nccn_sections_text: str,
    evidence: list[dict[str, Any]],
) -> str:
    return f"""Item ID: {item_id}

Scenario:
{scenario_label or "Not specified"}

Patient facts:
{format_patient_facts(patient_facts)}

NCCN guideline sections (retrieved via PageIndex tree-search):
{nccn_sections_text}

Retrieved literature evidence (from PubMed):
{format_evidence(evidence)}

Based only on the facts above, determine the appropriate next clinical management step.

Respond with one valid JSON answer object using this shape:

{NCCN_RESPONSE_TEMPLATE}

Do not return a JSON Schema definition. The "basis" array must contain 1 to 3 strings. The "missing_or_needed" array must contain at most 5 objects.
"""


def _facts_to_dict(patient_facts: list[dict[str, Any]]) -> dict[str, Any]:
    """Lightweight conversion of NCCN patient_facts into a {slot: value} dict
    that the CRC planner / fallback-query helpers can consume."""
    out: dict[str, Any] = {}
    for fact in patient_facts:
        if not isinstance(fact, dict):
            continue
        label = fact.get("slot_label") or fact.get("label")
        if not label:
            continue
        out[str(label)] = fact.get("value")
    return out


def run_mtb_nccn(
    model: str,
    item_id: str,
    scenario_label: str,
    patient_facts: list[dict[str, Any]],
    cancer_type_hint: str = "",
    *,
    per_query_results: int = 3,
    nccn_max_nodes: int = 4,
) -> dict[str, Any]:
    """MTB-lite + real NCCN PageIndex on the NCCN surface (decision schema)."""
    facts_dict = _facts_to_dict(patient_facts)
    # Plan stage — reuse the CRC planner: it just emits pubmed_queries + nccn_query.
    plan_user = f"""Item ID: {item_id}

Scenario: {scenario_label or 'Not specified'}

Patient facts:
{format_patient_facts(patient_facts)}

Return JSON only."""
    plan_result = openrouter_chat(
        model,
        [
            {"role": "system", "content": PLANNER_SYSTEM},
            {"role": "user", "content": plan_user},
        ],
        max_tokens=400,
    )
    plan_resp = plan_result.get("response") or {}
    plan_content = (((plan_resp.get("choices") or [{}])[0]).get("message") or {}).get("content")
    plan_json_ok, plan_parsed = extract_json(plan_content)
    plan = plan_parsed if (plan_json_ok and isinstance(plan_parsed, dict)) else {}
    queries = plan.get("pubmed_queries") or []
    if not isinstance(queries, list):
        queries = []
    queries = [str(q)[:200] for q in queries if str(q).strip()][:3]
    if not queries:
        # Build fallback from scenario_label
        fallback = (scenario_label or "colorectal cancer management").strip()[:200]
        queries = [fallback]
    nccn_query = plan.get("nccn_query") or plan.get("nccn_anchor") or scenario_label or "colorectal cancer decision pathway"
    if not isinstance(nccn_query, str) or not nccn_query.strip():
        nccn_query = "colorectal cancer decision pathway"

    # Retrieve
    pm_started = time.time()
    evidence = retrieve_evidence(queries, per_query=per_query_results)
    pm_elapsed = round(time.time() - pm_started, 3)

    # NCCN PageIndex
    import nccn_pageindex
    cancer_type = cancer_type_hint or "COLON_CANCER"
    nccn_result = nccn_pageindex.tree_search(model, nccn_query, cancer_type, max_nodes=nccn_max_nodes)
    nccn_sections_text = nccn_pageindex.format_sections(nccn_result.get("sections") or [])

    # Synth (NCCN schema)
    synth = openrouter_chat(
        model,
        [
            {"role": "system", "content": NCCN_SYNTH_SYSTEM},
            {
                "role": "user",
                "content": nccn_synth_user_prompt(item_id, scenario_label, patient_facts, nccn_sections_text, evidence),
            },
        ],
        max_tokens=1200,
    )
    s_resp = synth.get("response") or {}
    s_choice = (s_resp.get("choices") or [{}])[0]
    s_content = (s_choice.get("message") or {}).get("content")
    json_ok, parsed = extract_json(s_content)
    elapsed_synth = synth.get("_elapsed_seconds") or s_resp.get("_elapsed_seconds") or 0
    total = (plan_result.get("_elapsed_seconds") or 0) + pm_elapsed + (nccn_result.get("elapsed_seconds") or 0) + (elapsed_synth or 0)
    return {
        "ok": synth.get("ok", False) and plan_result.get("ok", False),
        "elapsed_seconds": round(total, 3),
        "finish_reason": s_choice.get("finish_reason"),
        "content_present": bool(s_content),
        "json_parse_ok": json_ok,
        "parsed_json": parsed if json_ok else None,
        "raw_response": s_resp if synth.get("ok") else None,
        "error": None if synth.get("ok") else synth,
        "intermediate": {
            "plan": {"pubmed_queries": queries, "nccn_query": nccn_query},
            "pubmed_n_hits": len(evidence),
            "nccn_node_ids": nccn_result.get("node_ids"),
            "nccn_ok": nccn_result.get("ok"),
        },
    }


def run_mtb(
    model: str,
    case_id: str,
    case_facts: dict[str, Any],
    *,
    per_query_results: int = 3,
    nccn_max_nodes: int = 4,
) -> dict[str, Any]:
    plan, planner_diag = plan_retrieval(model, case_id, case_facts)

    evidence_started = time.time()
    evidence = retrieve_evidence(plan.get("pubmed_queries", []), per_query=per_query_results)
    evidence_elapsed = round(time.time() - evidence_started, 3)

    # NCCN PageIndex tree-search using the real local index.
    import nccn_pageindex

    nccn_result = nccn_pageindex.tree_search(
        model,
        plan.get("nccn_query", ""),
        case_facts.get("cancer_type") or "",
        max_nodes=nccn_max_nodes,
    )
    nccn_sections_text = nccn_pageindex.format_sections(nccn_result.get("sections") or [])

    messages = [
        {"role": "system", "content": SYNTH_SYSTEM},
        {
            "role": "user",
            "content": synth_user_prompt(
                case_id, case_facts, nccn_sections_text, evidence
            ),
        },
    ]
    synth = openrouter_chat(model, messages, max_tokens=1500)
    response = synth.get("response") or {}
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content")
    json_ok, parsed = extract_json(content)
    elapsed_synth = synth.get("_elapsed_seconds") or response.get("_elapsed_seconds") or 0
    total_elapsed = (
        (planner_diag.get("elapsed_seconds") or 0)
        + evidence_elapsed
        + (nccn_result.get("elapsed_seconds") or 0)
        + (elapsed_synth or 0)
    )
    return {
        "ok": synth.get("ok", False) and planner_diag.get("ok", False),
        "elapsed_seconds": round(total_elapsed, 3),
        "finish_reason": choice.get("finish_reason"),
        "content_present": bool(content),
        "json_parse_ok": json_ok,
        "parsed_json": parsed if json_ok else None,
        "raw_response": response if synth.get("ok") else None,
        "error": None if synth.get("ok") else synth,
        "intermediate": {
            "plan": plan,
            "planner_elapsed_seconds": planner_diag.get("elapsed_seconds"),
            "planner_ok": planner_diag.get("ok"),
            "planner_json_parse_ok": planner_diag.get("json_parse_ok"),
            "pubmed_elapsed_seconds": evidence_elapsed,
            "pubmed_n_hits": len(evidence),
            "pubmed_evidence": [
                {"pmid": e.get("pmid"), "title": e.get("title"), "year": e.get("year"), "query": e.get("query")}
                for e in evidence
            ],
            "nccn_elapsed_seconds": nccn_result.get("elapsed_seconds"),
            "nccn_ok": nccn_result.get("ok"),
            "nccn_node_ids": nccn_result.get("node_ids"),
            "nccn_thinking": nccn_result.get("thinking"),
            "nccn_error": nccn_result.get("error"),
            "synth_elapsed_seconds": elapsed_synth,
        },
    }
