"""NCCN PageIndex RAG — minimal port of vmtb-skill's tool/rag/pageindex_rag.py.

Loads the locally-built NCCN PageIndex for CRC (结肠癌 / 直肠癌), runs an LLM
tree-search over node summaries, and returns the concatenated page text of the
selected sections.

This is the same shape as ``cancerdao-vmtb/scripts/tools/rag/pageindex_rag.py``
(LLM tree-search + Expert Preference), trimmed of vmtb-skill internals so it
runs standalone inside the benchmark adapter.
"""

from __future__ import annotations

import copy
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


# NCCN PageIndex artifacts ship with the vmtb-skill install (not opl-cancer).
# Resolution order:
#   1. $VMTB_PAGEINDEX_ROOT (explicit override)
#   2. ../vmtb-skill/skills/cancerdao-vmtb/references/pageindex (sibling clone)
#   3. ~/.claude/skills/vMTB/skills/cancerdao-vmtb/references/pageindex (installed)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_PAGEINDEX_CANDIDATES = [
    _REPO_ROOT.parent / "vmtb-skill" / "skills" / "cancerdao-vmtb" / "references" / "pageindex",
    Path.home() / ".claude" / "skills" / "vMTB" / "skills" / "cancerdao-vmtb" / "references" / "pageindex",
]
_DEFAULT_PAGEINDEX_ROOT = next((p for p in _PAGEINDEX_CANDIDATES if p.exists()), _PAGEINDEX_CANDIDATES[-1])
PAGEINDEX_ROOT = Path(os.environ.get("VMTB_PAGEINDEX_ROOT", str(_DEFAULT_PAGEINDEX_ROOT)))


# Map benchmark cancer_type → PageIndex directory name.
CANCER_TYPE_TO_DIR = {
    "COLON_CANCER": "结肠癌",
    "COLORECTAL_CANCER": "结肠癌",  # default to colon; rectal cases fall through to RECTAL_CANCER below
    "RECTAL_CANCER": "直肠癌",
}


EXPERT_PREFERENCE = """
NCCN colorectal guideline retrieval rules:
- Targeted / immunotherapy questions → prefer Discussion sections on dMMR/MSI-H, RAS/BRAF, anti-EGFR, anti-VEGF systemic therapy principles.
- Surgical decisions → prefer surgical principles + Discussion on Surgical Management (resectable vs unresectable, liver mets).
- Molecular testing / biomarker questions → prefer pathology + biomarker testing principles.
- Adjuvant chemo → prefer Discussion on Adjuvant Chemotherapy + adjuvant principles.
- Stage IV / metastatic → prefer Discussion on Metastatic Disease + systemic therapy options.
- Surveillance / follow-up → prefer surveillance principles in Discussion.
- Flowchart nodes labelled (COL-N) / (REC-N) carry no extra information beyond Discussion + Principles.
"""


_BOILERPLATE_PATTERNS = [
    re.compile(r"Version\s+\d+\.\d+,?\s+\d+/\d+/\d+\s*©.*?(?=NCCN|$)", re.IGNORECASE),
    re.compile(r"©\s*\d+\s*National Comprehensive Cancer Network.*?(?=NCCN|$)", re.IGNORECASE),
    re.compile(r"All rights reserved\..*?(?=NCCN|$)", re.IGNORECASE),
    re.compile(
        r"NCCN Guidelines® and this illustration may not be reproduced.*?(?=NCCN|$)",
        re.IGNORECASE,
    ),
    re.compile(r"NCCN Clinical Practice Guidelines in Oncology.*?(?=NCCN|$)", re.IGNORECASE | re.DOTALL),
    re.compile(r"NCCN Guidelines Version \d+\.\d+\s*Colon Cancer", re.IGNORECASE),
    re.compile(r"NCCN Guidelines Version \d+\.\d+\s*Rectal Cancer", re.IGNORECASE),
]


def strip_boilerplate(text: str) -> str:
    """Remove repetitive NCCN copyright / version boilerplate so the LLM
    tree-search sees the meaningful page content."""
    out = text or ""
    for pattern in _BOILERPLATE_PATTERNS:
        out = pattern.sub(" ", out)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def is_flowchart_node(node: dict[str, Any]) -> bool:
    title = node.get("title", "") or ""
    return bool(re.search(r"\((?:COL|REC)-\d+\)", title))


_INDEX_CACHE: dict[str, dict[str, Any]] = {}


def _load_index(cancer_dir_name: str) -> dict[str, Any]:
    if cancer_dir_name in _INDEX_CACHE:
        return _INDEX_CACHE[cancer_dir_name]

    cancer_dir = PAGEINDEX_ROOT / cancer_dir_name
    structure_path = cancer_dir / "structure.json"
    pdf_path = cancer_dir / "guideline.pdf"
    if not structure_path.exists():
        raise FileNotFoundError(f"Missing structure.json for {cancer_dir_name}: {structure_path}")
    if not pdf_path.exists():
        raise FileNotFoundError(f"Missing guideline.pdf for {cancer_dir_name}: {pdf_path}")

    with structure_path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    raw_nodes = data["structure"]

    # Filter flowchart nodes (their content is duplicated in Discussion/Principles).
    nodes = [n for n in raw_nodes if not is_flowchart_node(n)]

    # Lazy PDF text extraction.
    import PyPDF2

    pdf_reader = PyPDF2.PdfReader(str(pdf_path))
    page_text: dict[int, str] = {}
    for idx, page in enumerate(pdf_reader.pages, start=1):
        page_text[idx] = page.extract_text() or ""

    # Attach text + a cleaned summary to each node, build node_map and a compact
    # tree for the LLM search prompt.
    node_map: dict[str, dict[str, Any]] = {}
    compact_nodes: list[dict[str, Any]] = []
    for node in nodes:
        start = int(node.get("start_index") or 1)
        end = int(node.get("end_index") or start)
        text_parts = [page_text.get(p, "") for p in range(start, end + 1)]
        full_text = "\n".join(text_parts).strip()
        cleaned_summary = strip_boilerplate(node.get("summary") or "")[:500]
        node_record = {
            "node_id": node.get("node_id"),
            "title": node.get("title"),
            "start_index": start,
            "end_index": end,
            "text": full_text,
        }
        node_map[node["node_id"]] = node_record
        # Only include nodes whose cleaned summary is non-empty to keep the
        # search prompt focused — drop pure-boilerplate pages.
        if cleaned_summary:
            compact_nodes.append(
                {
                    "node_id": node.get("node_id"),
                    "title": (node.get("title") or "")[:80],
                    "pages": f"p.{start}-{end}",
                    "summary": cleaned_summary,
                }
            )

    _INDEX_CACHE[cancer_dir_name] = {
        "node_map": node_map,
        "compact_nodes": compact_nodes,
    }
    return _INDEX_CACHE[cancer_dir_name]


def _openrouter_chat(model: str, messages: list[dict[str, str]], *, max_tokens: int, timeout: int = 120) -> dict[str, Any]:
    api_key = os.environ["OPENROUTER_API_KEY"]
    base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        body["_elapsed_seconds"] = round(time.time() - started, 3)
        return {"ok": True, "response": body}
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "http_status": exc.code,
            "error": exc.read().decode("utf-8", errors="replace")[:1000],
            "_elapsed_seconds": round(time.time() - started, 3),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "_elapsed_seconds": round(time.time() - started, 3),
        }


def _extract_json(content: str | None) -> Any:
    if not content:
        return None
    text = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        s = text.find("{")
        e = text.rfind("}")
        if s >= 0 and e > s:
            try:
                return json.loads(text[s : e + 1])
            except json.JSONDecodeError:
                pass
    return None


def cancer_dir_for(cancer_type: str | None) -> str | None:
    if not cancer_type:
        return None
    key = str(cancer_type).strip().upper()
    return CANCER_TYPE_TO_DIR.get(key)


def tree_search(
    model: str,
    query: str,
    cancer_type: str,
    *,
    max_nodes: int = 4,
) -> dict[str, Any]:
    """Run LLM tree-search and return {ok, node_ids, thinking, sections, elapsed_seconds, error}."""
    started = time.time()
    cancer_dir = cancer_dir_for(cancer_type)
    if not cancer_dir:
        return {
            "ok": False,
            "node_ids": [],
            "thinking": "",
            "sections": [],
            "elapsed_seconds": 0.0,
            "error": f"unsupported_cancer_type:{cancer_type}",
        }
    try:
        index = _load_index(cancer_dir)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "node_ids": [],
            "thinking": "",
            "sections": [],
            "elapsed_seconds": round(time.time() - started, 3),
            "error": f"{type(exc).__name__}: {exc}",
        }

    prompt = f"""You are given a question and a list of node summaries from an NCCN clinical guideline.
Each node has a node_id, title, page range, and a short content summary.
Identify the {max_nodes} or fewer node_ids most likely to contain the answer to the question.

Question: {query}

Cancer directory: {cancer_dir}

Nodes (JSON list):
{json.dumps(index["compact_nodes"], ensure_ascii=False)}

Expert preference:
{EXPERT_PREFERENCE}

Reply in this exact JSON format:
{{"thinking": "<short reasoning>", "node_list": ["node_id_1", "node_id_2"]}}

Return only that JSON. No prose, no markdown fences. Cap node_list at {max_nodes} entries."""

    result = _openrouter_chat(
        model,
        [{"role": "user", "content": prompt}],
        max_tokens=600,
    )
    response = result.get("response") or {}
    choice = (response.get("choices") or [{}])[0]
    content = (choice.get("message") or {}).get("content")
    parsed = _extract_json(content)
    if not isinstance(parsed, dict):
        return {
            "ok": False,
            "node_ids": [],
            "thinking": "",
            "sections": [],
            "elapsed_seconds": round(time.time() - started, 3),
            "error": result.get("error") or "tree_search_parse_failed",
        }
    node_ids = parsed.get("node_list") or []
    if not isinstance(node_ids, list):
        node_ids = []
    node_ids = [str(nid) for nid in node_ids if str(nid).strip()][:max_nodes]

    sections: list[dict[str, Any]] = []
    seen: set[str] = set()
    for nid in node_ids:
        node = index["node_map"].get(nid)
        if not node or nid in seen:
            continue
        seen.add(nid)
        text = node.get("text") or ""
        text = strip_boilerplate(text)
        if len(text) > 2500:
            text = text[:2500] + "..."
        sections.append(
            {
                "node_id": nid,
                "title": node.get("title"),
                "pages": f"p.{node.get('start_index')}-{node.get('end_index')}",
                "text": text,
            }
        )
    return {
        "ok": True,
        "node_ids": node_ids,
        "thinking": str(parsed.get("thinking") or "")[:600],
        "sections": sections,
        "elapsed_seconds": round(time.time() - started, 3),
        "error": None,
    }


def format_sections(sections: list[dict[str, Any]]) -> str:
    if not sections:
        return "(no NCCN sections retrieved)"
    parts: list[str] = []
    for s in sections:
        parts.append(
            f"### [{s['node_id']}] {s.get('title') or ''} ({s.get('pages')})\n{s.get('text') or ''}"
        )
    return "\n\n---\n\n".join(parts)
