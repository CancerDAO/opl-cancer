# OPL for Cancer — Anti-Patterns

Each anti-pattern names a real failure mode and **the gate that mechanically
enforces against it** — so the prohibition is not a paper tiger. SKILL.md cites
these by number. New APs (AP-14…AP-17) were added in v2.7.0 (ADR-0026) after
session 0d1017d4.

| AP | Name | What it is | Enforced by |
|----|------|------------|-------------|
| AP-1 | Wave-3 silent skip | Declaring delivery while Wave 3 produced no real data artifact | `opl waveN` honest state-readers (exit 2) + G25 |
| AP-9 | Fakery / placeholder prose | Shipping "estimated N", "占位符", "TODO" as if it were retrieved | `fakery_sniffer` (CJK-aware) + delivery placeholder scan |
| AP-11 | Silent scope override | Quietly changing the plan/expert set without telling the user | comorbid-planner surface + G37 |
| AP-12 | Subagent write theatre | Claiming a file was written when it was not | subagent file-write contract + envelope check |
| AP-13 | File-handoff delivery | "报告已生成,请查看 brief.html" with no conclusions in chat | SKILL.md Step 10b inline-delivery contract |
| **AP-14** | **Free-handed brief** | **Writing a patient brief from model memory with no pipeline run behind it** | **G34 delivery_attestation** |
| **AP-15** | **Expert collapse** | **Substituting fewer generic agents for the 20 named personas to save tokens** | **G37 service_completeness (non-roster author detection)** |
| **AP-16** | **Fabricated clinical fact / citation** | **Inventing a lab value/stage/biomarker, or citing a PMID from memory / a wrong paper** | **G35 (clinical-fact provenance) + G1/G2/G36 (PMID existence/quote/relevance)** |
| **AP-17** | **Under-delivery** | **Stopping at a partial answer and waiting for the user to push for more** | **G37 service_completeness (planned team & waves must run)** |

---

## AP-14 — Free-handed brief

**Symptom (session 0d1017d4):** the executor ran `preflight`, then OCR'd a raw
folder itself, then wrote a polished report from its own knowledge — never calling
`plan` / `wave1..4` / `audit`. The 20 experts, the hypothesis tournament, Wave 3
data analysis, and the Henry audit all stayed dormant. The brief *looked*
professional and shipped.

**Why it happened:** the only terminal command SKILL.md told the agent to call
(`render`) was a `mkdir + {"ok":true}` stub. Nothing detected the *absence* of a
real run.

**Rule:** every delivered conclusion must originate from a `triggers/<run_id>/`
artifact. `plan` mints a `run_token` (run_manifest.json); the waves write a
provenance journal; `deliver --finalize` runs the real Henry audit. **G34**
refuses any brief lacking the token / journal / real audit, and refuses a brief
that cites a PMID with no provenance record. If you have not run the pipeline,
you have not run OPL — say so, then run it. Do not write a report from memory.

## AP-15 — Expert collapse

**Symptom:** "I used 4 general-purpose agents, each carrying several experts'
lenses, instead of the 20 named personas — it's more token-efficient." The
patient case warranted (and the planner assigned) a full team; the agent shipped
a quarter of it.

**Rule:** every expert in `plan.json` must produce its own
`tasks/w1_<task_id>/report.md`, authored by a **roster** persona. **G37** detects
non-roster authors ("general-purpose") and a planned-vs-executed shortfall, and
blocks delivery. Drop an expert only via a user-confirmed `replan.json`. Token
cost is never a reason to do less analysis (`models.yaml` principle #5).

## AP-16 — Fabricated clinical fact / citation

**Symptom:** the executor wrote "creatinine 88 (normal), GGT 19, Child-Pugh A"
*before OCR finished* — the numbers were invented and clinically wrong. It cited
4 PMIDs that point to a knee-osteoarthritis letter, a kefir-microbiome paper, a
glioma paper, and a macrophage paper (real PMIDs, wrong papers).

**Rule:** never write a clinical value you did not read — write `UNKNOWN`. Every
measured value carries a `[[src:...]]` anchor to an OCR sidecar (**G35**). Every
PMID comes from a live PubMed search this session, exists (**G1**), its quote
matches (**G2**), and it is actually about the claim's entities (**G36**).
Model-memory PMIDs are forbidden.

## AP-17 — Under-delivery (the founder's North Star failure)

**Symptom:** OPL gave a partial answer; it only became complete because a
domain-expert user kept pushing ("我们不是有 20 个专家么", "全都要补啊"). A normal
patient would have accepted the partial answer and never known to ask.

**Rule:** from one simple prompt, run the FULL planned team and every warranted
wave. Never stop at a partial answer and wait to be pushed. **G37** blocks
delivery when the service is incomplete relative to the plan. The patient should
not have to be sophisticated to receive professional, complete service.
