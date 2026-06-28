# Task: n1_applicability_audit (read the appendix · B2 / ADR-0030)

For every established / exploratory PMID that drives a patient-facing option, go
past the abstract: read the full text, the supplementary tables, and the
paper's own limitations, and decide whether the trial actually APPLIES to THIS
patient. This is the single highest-leverage false-hope catch for an N=1 patient
past standard-of-care.

> The appendix is where the bodies are buried; the limitations paragraph is the
> most honest one. An abstract HR is not evidence the patient is in the
> benefiting subgroup.

## Inputs

- The driving claims + their PMIDs (from treatment_line / trial_matching /
  drug_repurposing / literature_synthesis).
- The patient's axes from profile.json: line of therapy, biomarker(s), ECOG,
  organ function, age, prior regimens.
- Full text: use the PaperQA2 corpus / web-access skill to fetch the PMC-OA full
  text + supplementary package. If a source is closed-access and no full text is
  retrievable, tag it `[ABSTRACT-ONLY]` — never fabricate the subgroup figure.

## Procedure (per driving PMID)

1. Tag how deep you actually read it: set `source_section` on that evidence entry
   to one of `abstract | full_text | supplementary | subgroup_table |
   limitations` (the deepest you reached). G47 caps an `established` claim whose
   PMID evidence is all abstract-only.
2. Extract the trial's inclusion / exclusion criteria. Does the patient meet
   them? (`exclusion_hit: true` if the trial would have excluded this patient.)
3. Find the subgroup / forest-plot effect matching the patient's axes (their
   line, biomarker, ECOG, organ status). Quote the subgroup HR/CI verbatim.
   Is the patient in the benefiting subgroup, a non-benefiting one, or not
   represented?
4. Quote the source paper's OWN limitations sentence (verbatim).
5. If a pivotal trial EXCLUDED patients like this one, or showed NO benefit in
   their subgroup, emit a risk-card for Henry (RC: "your subgroup not
   represented / excluded").

## Output (JSON only)

```json
{
  "per_pmid": [
    {
      "pmid": "<id>",
      "source_section": "full_text|supplementary|subgroup_table|limitations|abstract",
      "applicability_to_n1": {
        "patient_in_subgroup": "yes|no|unknown",
        "subgroup_effect": "<verbatim subgroup HR/CI or 'not reported'>",
        "exclusion_hit": false,
        "source_limitation_quote": "<verbatim from the paper's limitations>"
      },
      "risk_card": "<text if exclusion_hit or no subgroup benefit, else null>"
    }
  ]
}
```

## Rules

1. `source_section` must reflect what you ACTUALLY read — do not claim
   `subgroup_table` if you only read the abstract.
2. Every quote (subgroup effect, limitation) is verbatim with the PMID; never
   paraphrased from memory. Closed-access ⇒ `[ABSTRACT-ONLY]`, no fabrication.
3. A trial that excluded this patient, or showed no benefit in their subgroup, is
   a false-hope signal — surface it as loudly as a positive headline.
4. Output ONLY the JSON object — no preamble, no fences.

## Why this matters

A citation can pass G1 (exists) + G2 (quote-match) + G9 (not retracted) carrying
an 'established' headline HR from an abstract, while the trial's supplementary
forest plot shows NO benefit in the patient's exact subgroup, or the trial
EXCLUDED patients like them. That is the difference between informed hope and
false hope, and it lives in the appendix the abstract never shows.
