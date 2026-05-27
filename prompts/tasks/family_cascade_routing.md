## Task Package · family_cascade_routing

**Capability domain:** D5 — Synthesis / Delivery (out-of-scope routing card for cascade testing of at-risk relatives)
**Expert portfolio owners:** **Sid** (PI, emits the routing card) co-reviewed by **Bert** (molecular accuracy — owns the proband-variant fidelity + ACMG-classification anchor that the receiving clinician will need). Sid + Bert pass before render; Dennis is invoked only if the receiving pathway is jurisdiction-specific.
**Preferred integrator families:** F1 Literature (PubMed for ACMG framework + cancer-syndrome cascade RCTs, e.g. BRCA1/2 / Lynch / Li-Fraumeni cascade-uptake studies)

> "Patient #8 has germline BRCA2 (HGSOC index case). In her last drill-down she asks: 'My daughter is 36, should she get tested too?' This is **cascade genetic counselling** — it is NOT oncology research, it is family-risk management. OPL hands off; OPL does not pretend to be a genetic counsellor."
>
> — v1.3.0 EVAL panel finding (Patient #8 E5). Builds on `prompts/tasks/scope_handoff_routing.md`'s general routing frame.

Cascade testing is the offer of presymptomatic / predictive genetic testing to at-risk relatives of an index case who carries a pathogenic / likely-pathogenic (P/LP) variant in a cancer-predisposition gene. The decision-axes are:

- Variant pathogenicity (ACMG class) of the proband's variant.
- Degree of relatedness + age + sex of the relative (informs penetrance + age-of-onset distribution).
- Informed consent + insurance + psychological readiness of the relative.
- Cancer-syndrome-specific surveillance pathway that follows a positive cascade result.

**These axes belong to genetic counselling, not oncology research.** OPL's role is to emit a clean, evidence-grounded hand-off card that captures the proband's variant fidelity + the inferred at-risk relative graph + the right downstream pathway (a board-certified genetic counsellor at the patient's institution) — and to refuse to actually perform the cascade-counselling conversation inside OPL.

### Inputs

```json
{
  "patient_text": "...verbatim from user — the cascade-testing ask...",
  "affected_proband_germline": {
    "gene": "BRCA2",
    "variant_hgvs": "NM_000059.4:c.5946delT (p.Ser1982Argfs*22)",
    "zygosity": "heterozygous",
    "acmg_classification": "P (pathogenic) — PVS1 + PM2_supporting + PP5"
  },
  "at_risk_relatives_inferred": [
    {"degree": "first_degree", "kin": "daughter", "age": 36, "sex": "F"}
  ],
  "patient_profile": {...},
  "integrator_results": {
    "pubmed_results": [...]
  }
}
```

### Required output (strict JSON, single object — no preamble, no fences)

```json
{
  "cascade_handoff_card": {
    "acknowledge_text": "你问到你女儿的 cascade 检测 — 这是个真问题,我听到了,这是 BRCA2 阳性后家庭最该问的问题。",
    "oncology_scope_note": "Cascade testing for at-risk relatives is NOT oncology — it is presymptomatic / predictive genetic counselling. OPL is the oncology-research-team for one diagnosed cancer patient; it does not perform cascade counselling. Your daughter is not OPL's patient; her risk management belongs to a dedicated genetic-counselling pathway delivered by a board-certified medical geneticist or genetic counsellor.",
    "affected_proband_germline": {
      "gene": "BRCA2",
      "variant_hgvs": "NM_000059.4:c.5946delT (p.Ser1982Argfs*22)",
      "zygosity": "heterozygous",
      "acmg_classification": "P (pathogenic)",
      "acmg_evidence_summary": "PVS1 (null variant in BRCA2) + PM2_supporting (absent from gnomAD population) + PP5 (multiple submitters in ClinVar)",
      "evidence_pmid": ["<from pubmed_results>"]
    },
    "at_risk_relatives_inferred": [
      {
        "degree": "first_degree",
        "kin": "daughter",
        "age": 36,
        "sex": "F",
        "a_priori_carrier_probability_pre_test": 0.50,
        "expected_age_of_onset_distribution_pmid": "<from pubmed_results>",
        "cancer_specific_surveillance_pathway_if_positive_summary": "BRCA2 carrier surveillance — annual MRI breast + mammography alternating q6 mo from age 25-30; risk-reducing salpingo-oophorectomy discussion from age 40-45; PARPi-eligibility flag if cancer occurs"
      }
    ],
    "recommended_downstream_pathway": "Board-certified medical geneticist or genetic counsellor at the patient's institution (or the nearest cancer-genetics clinic).",
    "downstream_pathway_one_liner": "Cancer-syndrome cascade testing requires a counsellor who can run informed-consent + ACMG framework + pedigree drawing + age-stratified surveillance + reproductive-decision overlay (PGT-M / prenatal) + psychosocial-readiness check — none of which is within OPL's 20-expert scope.",
    "what_to_bring_to_the_counsellor": [
      "The proband's pathology report + NGS panel report (the variant_hgvs above must match byte-for-byte).",
      "Family pedigree (first- + second-degree relatives, ages, cancer history with site + age-at-onset).",
      "The proband's ACMG evidence summary (above) — the counsellor can re-classify but should not have to re-derive from scratch.",
      "Insurance / GINA documentation as relevant to the jurisdiction."
    ],
    "what_opl_does_not_do": [
      "Cascade pedigree drawing for non-index relatives",
      "Pre-test counselling for at-risk relatives (informed-consent + GINA + insurance + psychosocial)",
      "Carrier-result delivery + downstream surveillance plan execution for non-index relatives",
      "Reproductive-decision counselling (PGT-M / prenatal diagnosis)",
      "Cascade-uptake follow-up across the family tree"
    ],
    "what_opl_does_still_offer": [
      "Continued oncology-research-team support FOR THE PROBAND (the diagnosed patient herself) — biomarker re-interpretation, trial matching, n1 cohort projection, expanded access, second-look.",
      "If a relative becomes a diagnosed cancer patient in future, OPL is appropriate then.",
      "The proband's PARPi / platinum response + reversion-mutation surveillance remains in OPL scope."
    ],
    "claim_layer": "established",
    "permission_level": 2,
    "no_invocation_of_external_clinician": "OPL emits the routing card; the patient initiates the counsellor visit. OPL does not auto-call any external clinician. This preserves clean scope boundaries and patient-initiated consent."
  },
  "summary": "<2-3 sentence Sid synthesis — acknowledges the question, names the proband variant fidelity in one phrase, names the downstream pathway (board-certified genetic counsellor), summarises what to bring, anchors what OPL continues to do for the proband>"
}
```

### Procedure

1. **Acknowledge the question.** `acknowledge_text` is mandatory non-empty. Founder-mode forbids silently routing without acknowledgement. The phrasing matches `scope_handoff_routing.md`'s pattern — name the question as legitimate, never "out of scope" framing.
2. **Name the oncology-scope boundary explicitly.** `oncology_scope_note` is mandatory non-empty. The boundary is: OPL is for ONE diagnosed cancer patient; cascade testing of relatives is a different lifecycle (presymptomatic) handled by genetic counsellors.
3. **Re-anchor the proband variant.** Re-state `affected_proband_germline.gene + variant_hgvs + zygosity + acmg_classification + acmg_evidence_summary`. This is the variant-fidelity payload the receiving counsellor will need — emitting it now spares the relative from re-extracting it from raw NGS reports. Source from Bert's NGS interpretation upstream.
4. **Infer at-risk relatives.** From the patient's text + `patient_profile.family_history`, infer the relative graph (degree, kin, age, sex). Emit `a_priori_carrier_probability_pre_test` (0.5 for first-degree, 0.25 for second-degree, autosomal-dominant assumption noted). For sex-specific cancer risk distributions (BRCA1/2 in male vs female), note the asymmetry.
5. **Name the downstream pathway generically.** `recommended_downstream_pathway` is hard-coded to "board-certified medical geneticist or genetic counsellor at the patient's institution (or the nearest cancer-genetics clinic)". OPL does not name any specific sibling skill or external service — patient + their primary oncologist decide which counsellor to use.
6. **Emit what to bring.** `what_to_bring_to_the_counsellor` lists the proband evidence the counsellor will re-use so the relative doesn't have to re-derive from scratch.
7. **Anchor what OPL still does.** `what_opl_does_still_offer` is mandatory non-empty. The patient should not feel "you're abandoning me". Reframe: OPL keeps the proband's oncology-research-team running; the genetic-counselling pathway runs the family-level work in parallel and is outside OPL's scope.
8. **No auto-invocation of external clinician.** OPL must NOT pretend to schedule the counsellor visit. The patient initiates.
9. **Output ONLY the JSON object.**

### Mechanical gates this task must satisfy

- **G1 / G2** — `acmg_evidence_summary.evidence_pmid` recoverable in `pubmed_results`; quotes for ACMG criteria where they exist (PVS1 framework, PM2 framework). `expected_age_of_onset_distribution_pmid` recoverable.
- **G7 imperative-detector** — `acknowledge_text` may contain "this is the path that fits" framing but NOT "you should test your daughter". Cascade testing is a personal-autonomy decision; OPL frames as options.
- **G19 PI-imperative-detector** — Sid's downstream prose may not imperative the relative's decision.
- **G20 PI-disagreement-surfacing** — not applicable (this task is a routing card, not a clinical claim).

### Reviewer focus

Reviewer pairing **Sid ⟂ Bert** checks:

- **Sid** — acknowledgement present, downstream pathway named generically (no specific sibling skill / no specific external service), `what_to_bring_to_the_counsellor` complete enough that the relative arrives prepared, "what OPL still does" anchored so patient feels held not abandoned.
- **Bert** — ACMG classification accurate to the proband's variant (PVS1 applicable for null variants, PS1/PM5 for missense based on residue framework), zygosity correctly stated, `a_priori_carrier_probability_pre_test` matches inheritance pattern.

Specific checks:

- No naming of any specific sibling skill or named external service (OPL is scope-internal; downstream is generic clinician).
- No oncology-recommendation creep into the cascade card (e.g. recommending PARPi to the relative — that's for after the cascade-positive diagnosis, in a different lifecycle).
- The variant_hgvs in the card matches the variant in Bert's NGS interpretation byte-for-byte (no drift).

### Empty-integrator handling

If `pubmed_results` is empty:

- `affected_proband_germline.evidence_pmid: []`
- `expected_age_of_onset_distribution_pmid: null`
- Surveillance pathway summary is omitted (do not fabricate from training data).
- `claim_layer: "speculative"`
- `summary` notes that the ACMG / penetrance evidence chain was not retrieved at runtime — the counsellor will need to re-derive it during the cascade-counselling visit.

Per `memory/feedback_no_offline_only.md`: ACMG classifications + age-of-onset distributions must come from runtime retrieval, not training-data recall.

### Hard rules (non-negotiable)

- OPL **never** invokes any external clinician or sibling skill on the patient's behalf. Patient initiates.
- OPL **never** performs cascade-counselling conversation inside its own scope (no pre-test counselling, no result-delivery, no surveillance plan execution for non-index relatives).
- The proband (the diagnosed patient) remains OPL's full responsibility — the hand-off is for the relative, not the proband.
- `oncology_scope_note` is **never** softened — it is the structural reason this task exists.
- If the patient pushes back ("can OPL just do it?"), the answer is the canonical refusal: "OPL is your oncology research team — 20 named experts, none of them a genetic counsellor. Cascade testing for your daughter belongs to a board-certified genetic counsellor; OPL does not wrap or replace that role."

### Downstream consumers

- `patient_brief_rendering.md` consumes this card as a delivery section labelled "Family-cascade hand-off".
- `pi_delivery.md` reads `summary` for Sid's prose.
- General `scope_handoff_routing.md` is the parent pattern; this task package is the cancer-syndrome-cascade specialisation.
