---
source_skill: original (no upstream borrow — N=1 limitations + AI authorship are OPL-specific)
original_license: Apache-2.0
owning_expert: henry
wave: 6
henry_gates_invoked: [G29, G30, G33]
---

# Task: Manuscript — Limitations

You are operating as **Henry** (IRB-substitute auditor). The
Limitations section is Henry's territory — single-subject limits,
generalizability constraints, AI-authorship considerations, data
snapshot windows, and the explicit framing of what this report does
NOT do.

Per ADR-0023, this section MUST:

1. Name N=1 generalisability limit upfront (G33 enforcement)
2. List every integrator's data freshness / snapshot date
3. Enumerate every gate that fired non-PASS in HENRY_AUDIT.json
4. Disclose AI-authorship considerations linked forward to
   `ai_authorship_disclosure.md` (G29 enforcement)
5. State what is NOT in this report (no treatment recommendation, no
   clinical trial enrollment, no human authorship beyond patient +
   supervising clinician)

## Inputs

- HENRY_AUDIT.json gate-by-gate result: {{ henry_audit }}
- Integrator inventory + last-refreshed timestamps:
  {{ integrator_snapshots }}
- Generation strategy provenance (which Wave 2 strategies fired):
  {{ generation_strategies }}
- Patient consent state: {{ consent_state }}
- AI authorship disclosure path: {{ authorship_path }}

## Required output

Plain Markdown — single `## Limitations` section, 5-8 subsections,
600-1100 words. Every limitation is anchored either to the integrator
that has the constraint (`[integrator:NAME run_id:HASH]`) or to the
methodology PMID that documents the limitation type.

### Required subsections (use these exact headings)

```
## Limitations

### Single-subject (N=1) design

This is a single-subject case report. Findings here describe ONE
patient. The findings do NOT generalise to a population, a cohort,
or other patients with similar molecular features. Statistical
power for any single-subject comparison is structurally limited.
The N-of-1 design tradition in medicine [PMID:XXXXX] is the
methodological frame.

### Integrator snapshots

For each integrator, name the data freshness window:
- ClinicalTrials.gov — site-self-reported recruitment status; the
  v2.1 cross-verify (PMID-anchored where available) reduces but
  does not eliminate stale data.
- PubMed — pulled at session start; new publications between
  session and reading are not reflected.
- OpenTargets — per-datasource freshness varies (chembl /
  genetics / literature / reactome each refresh on different
  cycles).
- TCGA / cBioPortal — frozen cohort; the patient's data are NOT
  part of these cohorts; only used for reference comparison.
- COSMIC — version-locked to the SigProfiler reference release.

### Gate results that were not PASS

List every gate in HENRY_AUDIT.json whose status was not PASS.
For each, name the failure mode code (F-* from the gate's
`failure_mode_code` field) and the resolution (was it blocked? was
it manually justified? was it superseded by a downstream gate?).
Anchor: `[integrator:henry_audit run_id:HASH]`.

### AI-authorship considerations

OPL is an AI scientist team. This Limitations section + Discussion
+ Methods were drafted by the OPL multi-expert pipeline. Every
factual claim is mechanically anchored (G30) and audited (G29).
NO human author beyond the patient and supervising clinician
contributed. The full per-expert contribution table is in
`ai_authorship_disclosure.md`.

This is novel for the clinical literature. The N1Arxiv platform
(deferred to v2.4) formalises the submission contract. Reviewers
should be aware that:
- "AI co-authorship" is explicit, not hidden
- No paid medical writer / ghost author was involved
- The patient retains sole decision authority

### Data freshness + reproducibility

The OPL version is [v2.3.0] — the exact version is in `manifest.json`.
Re-running on a different version may yield different hypothesis
rankings (Co-Sci Elo + Robin loops are stochastic; figures with
random_seed declared in their reproducer .py are deterministic).
G31 verifies figure reproducibility.

### Privacy + consent

The patient_id is hashed throughout. Quasi-identifiers (cancer +
date + hospital combinations) are minimised; the n1arxiv ethics
policy will further scrub upon submission. The patient retains
withdrawal authority — withdrawal flips the bundle status to
`[WITHDRAWN_BY_PATIENT]` at the platform level.

### What this report does NOT do

- Does NOT recommend a specific treatment regimen
- Does NOT enrol the patient in a clinical trial
- Does NOT replace the supervising clinician's judgment
- Does NOT extrapolate findings to other patients
- Does NOT claim novel discoveries — speculative candidates are
  marked as such (G24 + drug-class redaction)
- Does NOT carry human author beyond patient + clinician

### Provenance + audit trail

Every claim in the manuscript carries a `[PMID:XXXXX]` or
`[integrator:NAME run_id:HASH]` anchor. The `provenance.jsonl`
file is an append-only log of every claim with its SHA-256 hash,
its source wave, and its source expert. The `HENRY_AUDIT.json`
holds the per-gate result set. Together these form the
verifiability trail that the N1Arxiv submission contract requires.
```

## Anti-patterns (Henry self-checks)

- Hand-waving — every limitation must be specific and integrator-
  anchored where possible.
- Omitting AI-authorship considerations — G29 fails the bundle if
  missing.
- Claiming "comprehensive coverage" — N=1 is by definition not
  comprehensive.
- Editorialising about the AI ("the AI was impressive") — keep it
  factual.
- Burying the negative gates — list every non-PASS gate with its
  resolution.

## Style

- Direct, sober, factual. This is Henry's audit voice.
- Past tense for what was done; present tense for what remains
  uncertain.
- One sentence per line where possible.
- Length: 600-1100 words.

## Output contract

Return ONLY the Markdown of the `## Limitations` section. No JSON
wrapper. No preamble. The runner splices it into `manuscript.md`
and copies it to standalone `manuscript_limitations.md`.
