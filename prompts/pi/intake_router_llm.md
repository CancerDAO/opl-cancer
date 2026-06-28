# PI intake router — LLM task/method routing (E2 / ADR-0038)

Route a patient's question to the right task package (or compose a method DAG for
open-set questions) by REASONING about meaning — not by substring-matching a
keyword table. This is the de-scripting replacement for `intake_router.py`'s
`_KNOWN_TASK_KEYWORDS` and `_UNKNOWN_DAG_STUBS` (judgment belongs to the LLM, not
an `if keyword in text` map; a patient phrasing that misses the keywords today is
silently misrouted).

## Inputs

- The patient's verbatim question + profile.json.
- The task-package registry: the names under `prompts/tasks/*.md` (enumerated by
  Python — that part stays deterministic).
- The method registry: available analysis methods (Cox/KM/GSEA/conformal/…).

## Procedure

1. Read the question. Does it semantically match a known task package? If yes,
   return that package name + a one-line rationale + confidence.
2. If it is an open-set / composite question (e.g. "build an AutoML prognosis
   model from my omics"), COMPOSE a method DAG from the method registry that
   answers it — list the methods in dependency order + why each is needed. (This
   finally implements the stubbed M5 method-composer.)
3. If nothing fits, return `unknown_task_intake` + explicit decline_reasons (what
   you would need to route it). Never force a bad match.

## Output (JSON)

```json
{
  "matched_task_package": "<registry name | unknown_task_intake>",
  "rationale": "<why this route>",
  "confidence_0_1": 0.0,
  "method_dag": ["<method_id>", "..."],
  "decline_reasons": ["<if unknown>"]
}
```

## Boundary (what stays Python — the dividing line)

Python may ENUMERATE the registry (list package names) and VALIDATE the chosen
package exists (schema/file check). Python must NOT decide the route by keyword.
The LLM judges the route; Python verifies the chosen package is real.

## Rules

1. Semantic match, never substring match. A question that does not say "AutoML"
   but means it must still route correctly.
2. A chosen `matched_task_package` MUST exist in the registry (Python rejects an
   invented name).
3. Output ONLY the JSON object — no preamble, no fences.
