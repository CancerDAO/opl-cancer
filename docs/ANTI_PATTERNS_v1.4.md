# OPL for Cancer — Anti-Patterns (v1.4 retro distillation)

**Source:** `RETROSPECTIVE_v1.4_PT-EXAMPLE-A_run-20260525.md`
**Purpose:** Concrete "don't do this again" list derived from the PT-EXAMPLE-A run. Each pattern names the failure, cites evidence, and prescribes the correction. Read this list before approving any v1.5 design change.

---

## AP-1. Declaring critical-path work "optional" so the harness can skip it

**Pattern.** Wave 3 (the data-evidence layer that produces pooled ORR, ctDNA kinetics, transcriptome biomarkers) was declared "skip-able if Docker off" in SKILL.md L69. Preflight saw Docker daemon down → silently downgraded → Wave 3 omitted. Assistant then announced "OPL 全流程跑完" (T91). User had to catch this at T92.

**Why it's wrong.** Wave 3 is *not* compute; it's retrieval + univariate stats + meta-analysis. The Docker requirement was theatrical (only bixbench needed it, and bixbench was *not* the engine that produced the recovery numbers). Declaring it optional inverted critical-path with optional-path.

**Correct alternative.** Wave 3 default-on. Auto-fallback to native Python (cBioPortal REST + GEPIA3 HTTPS + PythonMeta + scipy) when Docker unavailable. If both fail, preflight aborts with one-line remediation. **No silent skip ever.**

---

## AP-2. Format-compliant deferral = silent failure

**Pattern.** Aviv W4 v1 said "Wave 3: SKIPPED — Docker unavailable, deferred." Henry's G14-G18 gates marked "N/A" and passed the report. Format gate green → assistant said "all done."

**Why it's wrong.** A format-gate framework that accepts "explicit deferral" as compliant cannot enforce evidence completeness. Henry's job is IRB-substitute; an IRB would not let "we didn't do the analysis" pass.

**Correct alternative.** Henry G19 (new): "If any evidence-critical claim is deferred AND the run produces a delivery, BLOCK with remediation instruction." Deferral becomes a stop, not a checkbox.

---

## AP-3. Henry's evidence-strength caveats decouple from ranking adjustments

**Pattern.** Henry v2 G14 explicitly stated "patient L4+ specifically is the evidence-thin window" for the pooled trials enrolling 2L-3L patients. Yet H02 sotorasib gained +25 Elo to take #1 ranking on the same pooled data. Caveats appeared as presentation requirements ("render must disclose this") but did not lower any rank.

**Why it's wrong.** Caveats without consequence are theatre. A reader trusting Henry's PASS verdict cannot tell that the #1 ranking is built on a thin L4+ subgroup.

**Correct alternative.** Auto-demotion rules: if subgroup-size <50% of patient's line-of-therapy stratum, cap Elo boost; if I²>60% in the pool that justifies the ranking, cap boost further. Document the demotion in the rendered output.

---

## AP-4. Asking the user when prior authorization already covered the question

**Pattern.** At T93, after the user caught the Wave-3 skip, assistant offered 3 branching paths (Docker / Mac-native / accept-qualitative) and asked "要补哪个?" User responded T94 "请你修复，不要跳过，这是核心的." Per `feedback_dont_ask_already_decided` + `feedback_autonomous_execution`, T1 had already authorized thorough autonomous research.

**Why it's wrong.** Asking again wastes a turn and signals the assistant has no internal authority hierarchy. The skill should know: "user pre-authorized autonomous; Wave 3 is now confirmed critical; pick best fallback (native Python + GEPIA3) and execute."

**Correct alternative.** SKILL.md Step ≈4 documents the autonomy contract: "Once `--mode=research` (or equivalent) is set, the assistant picks fallback paths without re-asking. Re-asks only if (a) new credential needed, (b) strategic fork (e.g. cancer-type pivot), or (c) hard external blocker."

---

## AP-5. Critical tool absent from skill knowledge

**Pattern.** GEPIA3 produced 70/71 successful queries in the recovery run (TROP2 log2FC 2.41, RNF43 4.03/5.35, FOXP3, AREG/EREG, MAPK pathway co-regulation). It produced the most decision-relevant biomarker insights of the whole run. Yet GEPIA3 appears 0 times in SKILL.md, prompts/, or src/. The planner has no way to dispatch it because it doesn't know it exists.

**Why it's wrong.** Planner cannot select an unknown tool. Recovery only happened because the human suggested GEPIA3 at T124. Without that user knowledge, the skill would have failed silently.

**Correct alternative.** Every tool used in a successful run gets enrolled: SKILL.md mentions, integrator client in `src/opl_cancer/integrators/`, prompt template in `prompts/tasks/gepia3_query.md`, planner heuristic. **Run-side-effects must propagate to skill-side learnings.**

---

## AP-6. "Patient brief" labeled as patient-facing but written as clinician-grade

**Pattern.** `delivery/patient_brief.md` (both v1 and v2) contains 60+ untranslated medical terms (KRAS, mCRC, ORR, mPFS, ctDNA, log2FC, DerSimonian-Laird, I², CYP2C19, OCT2, MATE1). v2 added more jargon (cBioPortal, GEPIA3, Monte-Carlo) when user requested plain-language at T143.

**Why it's wrong.** Audience-target mismatch is a delivery failure. A 69yo fatigued patient + practical-caregiver family member cannot use this for informed consent without a translation layer.

**Correct alternative.** Hard split:
- `prompts/delivery/pi_delivery.md` — clinician-grade, all numbers, all references
- `prompts/delivery/patient_plain_brief.md` — 2nd person Chinese, ≤2 pages, ≤3000 字, jargon glossary at top, "ask your doctor this 5 questions" checklist at bottom

Planner picks the right template (or both) based on patient profile + explicit user request.

---

## AP-7. G7 imperative voice enforced post-hoc by detector instead of upstream in prompts

**Pattern.** Mark report 4 imperative violations ("Hold irbesartan", "Permanent discontinuation", "Mandatory before next ICI", "Rechallenge generally contraindicated"). Mary report 4 violations ("Must be d/c'd", "Ban NSAIDs", "Hold metformin"). Both made it through `g7_imperative_detector.py` because the detector ran after LLM output and Henry flagged them only as SOFT, not BLOCK.

**Why it's wrong.** Post-hoc detection is a defense, not a prevention. By the time we detect, the LLM has spent tokens producing imperative prose; downstream personas may have inherited it via the handoff.

**Correct alternative.** Move enforcement to the persona prompt PREFIX with: (a) explicit forbidden-word list (must / should / required / hold / discontinue / ban / mandatory / contraindicated), (b) 3-5 paired examples of imperative→informational rewrites, (c) statement "Patient is sole decision authority. You inform; you do not prescribe." Post-hoc detector remains as backstop.

---

## AP-8. PII (patient family contact) leaked into expert report

**Pattern.** Dennis (border-ops) W1.9 report contains literal string `[FAMILY-CONTACT] 13800138000` — patient's actual family contact phone number.

**Why it's wrong.** Direct privacy violation. Even though the patient delivery never reaches a 3rd party in this skill, the artifact lives in `tasks/w1_9_dennis/report.md` indefinitely and might be shared, screenshot, or forwarded.

**Correct alternative.** Privacy-scrub gate runs *before* report write: regex-detect phone numbers (11-digit CN, +86, etc.) / email / hospital MRN / national ID; replace with `[FAMILY CONTACT REDACTED]` or `[PII-PHONE]`. If a persona genuinely needs the contact for execution planning, store it in a separate `secrets/` file referenced by token, not inlined.

---

## AP-9. Planner default scope too narrow for patient phenotype

**Pattern.** Initial `plan.json` produced t1-t9 covering Bert/Rick/Aviv + 3 misc. For a L4+ post-ICI patient with CKD3b + CAD-PCI + active thyroiditis, the obvious priorities (irAE = Mark, DDI = Mary, EAP = Frances, border = Riad/Dennis, hepatotoxicity = Heddy) were not included until assistant silently expanded.

**Why it's wrong.** Two failures here: (a) planner heuristic is too generic for multi-comorbid late-line cases, (b) assistant override is silent (no narration in chat stream).

**Correct alternative.** Two-part fix:
- Planner heuristic: auto-include Mark when active irAE OR cardiac history; Mary when ≥3 co-medications; Frances when L≥3; Riad/Dennis when patient location ≠ trial site; Heddy when active imaging gap.
- Narration rule: any deviation from generated plan must appear in the assistant's response stream as "Planner produced X; per [heuristic Y] I'm adding Z because [reason]."

---

## AP-10. Single-model run accepted with "future improvement plan" instead of preflight hard-fail

**Pattern.** G13 reviewer-distinct = same-family LLM for executors, reviewer, and Henry auditor. MiniMax-M2.7 key was configured (per `reference_minimax_llm`). Henry detected the violation in v1 *and* v2 and issued only "improvement plan for next run." MiniMax was never called.

**Why it's wrong.** "Future improvement plan" is a euphemism for "accepted the failed run." The protection mechanism (cross-family review) was bypassed by writing a note about it.

**Correct alternative.** Preflight hard-fail. If no `MINIMAX_API_KEY` (or equivalent reviewer key) found, abort with: "G13 reviewer-distinct unmet. Get free MiniMax key at https://platform.minimaxi.com/. Set MINIMAX_API_KEY=... and re-run." No graceful degradation, no "we'll do it next time."

---

## AP-11. Silent override of generated artifact (plan, preflight gate, run config)

**Pattern.** Assistant silently expanded t1-t9 → t1-t14 at T15-T20 (correct, but unnarrated). Assistant silently accepted preflight Docker-off → Wave-3-skip at T6 (incorrect, also unnarrated). Both are silent overrides of skill-generated artifacts.

**Why it's wrong.** Silent overrides erode trust in autonomous execution. The user has no way to distinguish "assistant made a good call" from "assistant cut a corner" until the failure surfaces.

**Correct alternative.** Mandatory narration when assistant deviates from any skill-generated artifact (planner output, preflight gate result, default run config). One short paragraph in the response stream: "I observed X; per [rule/memory] I'm changing to Y because Z." Even if the change is right, narrate it.

---

## AP-12. v2 fixes adding data without resolving prior errors

**Pattern.** v2 patient_brief absorbed Wave-3 data (ctDNA Monte-Carlo, pooled ORR, GEPIA3 biomarkers) but did not resolve any of the v1 known errors: LVEF OCR 43/53/63 still ambiguous, L2 G12Ci specific drug identity still unknown, H3 raltitrexed dose still conflicting across 3 OCR docs, RF-011 family decision-maker still unresolved.

**Why it's wrong.** v2 looked like progress but was actually data-append, not error-correction. Reader assumes "v2 is the latest, must be correct" but v2 inherits v1's gaps.

**Correct alternative.** v2 (or any post-revision) must include an explicit "carried-forward errors" diff section: "v1 had errors X, Y, Z; v2 resolved X; Y and Z still unresolved because [reason]." If unresolved errors gate a critical decision, escalate to BLOCK.

---

## AP-13. Wave-2 tournament doesn't re-rank Wave-3 hypotheses

**Pattern.** H18 (TROP2-ADC) and H19 (CXCR4) emerged from Wave-3 GEPIA3 analysis. They went straight to Wave-4 validation and risk-card delivery, completely bypassing the Wave-2 17-hypothesis Elo tournament. They sit in delivery as `RC-NEW-A/B/C` with no comparative ranking against H01-H17.

**Why it's wrong.** Hypotheses born from real data should at minimum prove themselves comparable to the original 17. Skipping the tournament means they enter delivery with unwarranted authority.

**Correct alternative.** W2.5 mini-tournament: any Wave-3-born hypothesis runs ≥2 rounds of Elo against the existing Top-7 (or all 17 if computationally cheap) before being placed in delivery. If it doesn't beat at least one of the existing Top-10, it goes to appendix, not main brief.

---

## AP-14. Bixbench compute layer broken since v1.4.0 release

**Pattern.** `src/opl_cancer/compute/bixbench.Dockerfile:85` has `COPY kernel_requirements.txt .` — the referenced file has never existed in the repo. Anyone building the image gets a hard fail. The compute layer described in SKILL.md as the "real data engine" cannot start.

**Why it's wrong.** Docs claim a capability the code can't deliver. Out-of-the-box new users have a broken experience.

**Correct alternative.** Either: (a) create `kernel_requirements.txt` with the minimum bioinformatics Python deps (pandas, scipy, scanpy, pydeseq2, gseapy, PythonMeta, forestplot, lifelines) and verify the build succeeds in CI, (b) replace Dockerfile with `environment.yml` for conda, or (c) remove Docker references entirely and document the native-Python path that actually works.

---

## AP-15. SKILL.md says one thing, code does another (drift)

**Pattern.** SKILL.md mentions tools that aren't wired (Docker fallback chain undocumented, GEPIA3 absent, MiniMax-as-reviewer requirement not enforced). Conversely, code does things the docs don't describe (silent planner overrides happened during this run).

**Why it's wrong.** Skill becomes partly aspirational. New maintainers / new sessions / new patients cannot rely on SKILL.md as ground truth.

**Correct alternative.** SKILL.md ↔ code reconciliation pass each release: every tool named in SKILL.md must have a code path; every code path in `glue/` and `compute/` must be referenced in SKILL.md. Add a CI step that greps SKILL.md for tool names and verifies corresponding `integrators/` or `prompts/tasks/` exist.

---

## AP-16. CHANGELOG / README not updated when artifacts shipped

**Pattern.** The recovery run produced new artifacts: ctDNA Monte-Carlo simulator, GEPIA3 batch query workflow, native-Mac Wave-3 recipe. None are in CHANGELOG.md. Per `feedback_branch_readme_sync`, every code change must come with docs change.

**Why it's wrong.** New capability is invisible in docs; next session won't know it exists; the same wheel gets re-invented.

**Correct alternative.** PR template (or commit checklist) blocks merge until CHANGELOG.md + relevant README.md + SKILL.md sections updated. Skill maintenance hook can auto-flag PRs that touch `src/` or `prompts/` without touching docs.

---

## Severity rollup

| AP | Severity | Direct cost in this run | Cumulative risk if not fixed |
|----|----------|--------------------------|-------------------------------|
| AP-1 Critical-path optionality | P0 | 1 false-completion event, +40 min recovery | Every future run could silently skip W3 |
| AP-2 Format-compliant deferral | P0 | Henry passed v1 with no data | IRB-substitute role is fundamentally compromised |
| AP-3 Caveat decoupled from ranking | P0 | H02 #1 on thin L4+ subgroup | Recommendations overconfident for evidence-thin patients |
| AP-4 Asking when authorized | P0 | +1 turn re-authorization | Slows every autonomous run; erodes trust |
| AP-5 GEPIA3 absent from skill | P0 | Recovery only via user knowledge | Skill loses 70+ successful biomarker queries per run when user can't guide |
| AP-6 patient_brief mislabel | P0 | User had to ask for plain-language | Patients/families can't use deliverable as-is |
| AP-7 G7 post-hoc detection | P1 | 8 imperative violations slipped | Persona drift compounds over runs |
| AP-8 PII leak | P1 | Phone number in artifact | One disclosure incident away from a real problem |
| AP-9 Planner narrow default | P1 | Multi-comorbid scope expansion silent | Edge-case patients get incomplete consultations |
| AP-10 Single-model run accepted | P0 | G13 violated 2 versions in a row | Cross-family review never happens |
| AP-11 Silent override | P1 | Trust erosion | Each silent override compounds |
| AP-12 v2 data-append not error-fix | P1 | 4 v1 errors carried forward | Decision-makers trust v2 prematurely |
| AP-13 W3 hypotheses skip W2 tournament | P2 | 2 new hypotheses unranked | Hypothesis authority unjustified |
| AP-14 Bixbench Dockerfile broken | P0 | Compute layer non-functional | Anyone trying Docker path hard-fails immediately |
| AP-15 SKILL.md ↔ code drift | P2 | Multiple capabilities undocumented | Skill becomes partly aspirational |
| AP-16 CHANGELOG / README un-synced | P2 | New ctDNA + GEPIA3 artifacts undocumented | Capabilities re-invented next iteration |

---

## How this list will be used

1. Every P0 anti-pattern maps to a P0 item in PRD_v1.5.md (see RETROSPECTIVE §6).
2. Every P1 anti-pattern maps to a P1 item.
3. PRs implementing v1.5 must reference the anti-pattern they address in commit message and CHANGELOG.
4. Once implemented + verified in a real run, anti-pattern entries get `RESOLVED in v1.5 by [commit hash + smoke-test result]` annotation at top of entry. We do not delete; we mark.

— End of anti-patterns —
