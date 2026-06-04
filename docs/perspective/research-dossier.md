# Research Dossier — "Going Founder Mode on Cancer in the AI Era"

**Working thesis.** When standard-of-care is exhausted, a patient faces an *options desert* + *information asymmetry* + *agency vacuum*. Sid Sijbrandij (GitLab CEO, recurrent osteosarcoma, no trials) reached "no evidence of disease" by going *founder mode* — assembling a multidisciplinary team, scRNA/bulk-seq, personalized immune profiling, international travel, an N=1 database. That solution is **not scalable** (it needs CEO-level resources). The article argues AI can **democratize** founder-mode via a patient's "AI scientist team," and the discipline that separates it from quackery is decomposing the need into **Pain-A** (retrieve/match/vet REAL existing options = the molecular tumor board job) **THEN Pain-B** (generate grounded NOVEL leads = N=1 / drug-repurposing / world-unknown) — Pain-A first, with **zero tolerance for fabricated evidence**.

This dossier merges findings from 5 parallel research agents (mtb-utility, patient-led-n1, ai-scientist-systems, llm-clinical-safety, access-mechanisms), deduplicated and organized by the article's section needs. Every "honesty flag" from the source agents is preserved — unverified figures are explicitly marked and must not be cited without primary-source confirmation.

---

## ⭐ STRONGEST ANCHOR CITATIONS (use these to carry the paper)

These 8 do the most argumentative work and are the highest-quality / most load-bearing:

1. **Frost et al., *British Journal of Cancer* 2022** — patient attrition in MTBs: only ~20% of patients entering an MTB actually receive the recommended treatment (51 studies, 19,430 patients). *The single strongest quantification of the options desert + agency vacuum — even a fully-resourced MTB loses ~80% before treatment.* DOI/URL: https://www.nature.com/articles/s41416-022-01922-3
2. **Fajgenbaum et al., *J Clin Invest* 2019 (JCI126091)** — physician-patient self-profiled, found mTOR hyperactivation, repurposed approved sirolimus, durable remission → formal trial. *The canonical disciplined founder-mode precedent (Pain-B grounded in real assets), AND it shows the democratization gap because Fajgenbaum had MD/lab access.* https://www.jci.org/articles/view/126091
3. **Gottweis, Natarajan, et al., "Towards an AI co-scientist," *Nature* 2026** — multi-agent Gemini system generating/ranking novel biomedical hypotheses; produced a world-unknown AMR mechanism matching unpublished Imperial College work + experimentally confirmed AML repurposing hits. *The peer-reviewed anchor for "patient's AI scientist team" + proof of genuine novel-lead generation (Pain-B).* DOI 10.1038/s41586-026-10644-y (re-verify exact title/authors against DOI — fetch socket-failed; cross-confirmed via Google Research blog).
4. **Robin (FutureHouse), *Nature* 2026** — first multi-agent system to run the full hypothesis→experiment→analysis loop and produce a genuinely novel therapeutic lead (ripasudil for dry AMD). *Best single real-world proof an AI agent team found a repurposing candidate humans had not.* DOI 10.1038/s41586-026-10652-y; arXiv:2505.13400.
5. **Jin et al., "Matching patients to clinical trials with large language models" (TrialGPT), *Nature Communications* 2024** — 87.3% criterion-level accuracy, >90% trial recall using <6% of corpus, 42.6% screening-time reduction, sentence-anchored explanations. *Empirical backbone that Pain-A (trial matching) is technically tractable at near-expert level WITH grounded explanations.* DOI 10.1038/s41467-024-53081-z
6. **Le Tourneau et al., SHIVA01 (*Lancet Oncol* 2015; crossover *Ann Oncol* 2017)** — first randomized precision-oncology trial: NEGATIVE (PFS 2.3 vs 2.0 mo). *Essential intellectual-honesty anchor; its failure is attributed to weak matching rules — which is exactly the Pain-A discipline argument.* https://www.annalsofoncology.org/article/S0923-7534(19)31978-7/fulltext
7. **Omar et al., "LLMs highly vulnerable to adversarial hallucination attacks during clinical decision support," *Communications Medicine* 2025** — every model elaborates on a planted fake clinical detail 50–83% of the time; a mitigation prompt nearly halves it but leaves ~23% residual. *The devastating case against naive founder-mode-by-chatbot; justifies retrieve-vet-attribute pipeline + human-in-loop.* DOI 10.1038/s43856-025-01021-3
8. **Batley et al., "Evidence and reporting standards in N-of-1 medical studies," *Translational Psychiatry* 2023** — of 115 N-of-1 articles, only 3.48% met all evidence standards; 99.1% failed to report a comparable effect size. *Quantifies that the N-of-1 field's default is evidentially sloppy — so AI's value-add is the discipline (Pain-A before Pain-B), not the ambition.* DOI 10.1038/s41398-023-02562-8

---

## SECTION 1 — The Options Desert, Information Asymmetry & Agency Vacuum

### 1.1 The attrition funnel — knowing an option exists ≠ getting it

- **Only ~20% of patients entering an MTB actually receive the recommended treatment** (adults 23%, pediatric 13%, mixed 7%). Attrition drivers: no mutations 27%, no actionable mutation 22%, clinical deterioration 15%, insufficient tissue 14%; **31% of studies reported "actionable mutation but no drug available."** — Frost et al., *Br J Cancer* 2022;127(8):1557-1564, https://www.nature.com/articles/s41416-022-01922-3. *Core stat for the thesis: clinical deterioration = patients die in the queue (agency/time vacuum). The 31% residual is precisely the Pain-A→Pain-B hand-off point.*
- **Single-center confirmation: MTB gave a recommendation in 54% of cases (matched 43%), but recommendations were implemented in only 28.8%.** — "Transitioning the MTB from Proof of Concept to Clinical Routine," 2021, https://pmc.ncbi.nlm.nih.gov/articles/PMC7962829/. *Recommendation ≠ delivery, at the institution level.*

### 1.2 Trials as the headline "option beyond SoC" — and how few they reach

- **Only ~2–8% of adult cancer patients ever enroll in a trial (≈3–5% of US adult cancer care).** — Overcoming Barriers to Clinical Trial Enrollment, ASCO Educational Book (PubMed 31099636). *The flagship mechanism reaches almost no one.*
- **Why patients don't enroll: ~56% had no suitable trial at their site, ~22% ineligible (restrictive criteria), ~15% of eligible patients declined.** — Unger JM et al., *JNCI* 2019 (cite primary; figures appeared in secondary reporting). *The dominant barrier is "no trial here" — a matching/geography problem solvable by an information layer across the global registry.*
- **Nearly 50% of patients with common metastatic cancers must drive >1 hour one-way to a trial site; ~70% of the public rarely/never consider a trial.** — CancerNetwork barriers literature. *Geographic + awareness asymmetry.*
- **Eligibility criteria are growing combinatorially complex: ECOG lung-cancer median criteria 17 (1986–95) → 27 (2006–16); required blood tests 11 → 19.** — Garcia S et al., *J Thorac Oncol* 2017 (PMC5610621). *Peer-reviewed measure of why human matching fails — 27 criteria × hundreds of trials. Strongest justification for an automated Pain-A matcher.*

### 1.3 Structural / socioeconomic asymmetry in even getting tested

- **Most US cancer patients are treated in community practices with limited precision-oncology infrastructure; NGS uptake correlates with commercial insurance.** — Nature Cancer, "Understanding inequities in precision oncology diagnostics," 2023, https://www.nature.com/articles/s43018-023-00568-1; Targeted Oncology (trade). *MTBs concentrate at academic centers; the late-line community patient often never gets comprehensive NGS.*
- **Barriers to timely biomarker results: tissue insufficiency, patient "too sick," insurance.** — Point of Care Molecular Testing, PMC8947443. *Maps to the same attrition drivers; the bottleneck is operational and time-sensitive — where AI orchestration could most help.*

---

## SECTION 2 — Founder-Mode Precedent & Its Non-Scalability

### 2.1 The patient-empowerment lineage (predates AI by 30 years)

- **The "e-patient" paradigm (equipped, enabled, empowered, engaged) is a named 2007 academic framework** — and its author, Tom Ferguson MD, himself died of multiple myeloma. — *e-Patients: How They Can Help Us Heal Health Care*, Society for Participatory Medicine, 2007, https://participatorymedicine.org/e-patients-white-paper/. *The founding text of patient empowerment came from an exhausted-options cancer patient — directly prefigures Sijbrandij.*
- **ACOR — first internet-scale self-organized cancer network — founded by a caregiver (Gilles Frydman, 1995), grew to ~200 communities / >500,000 patients.** — The Health Care Blog, 2010. *The "assemble a team / pool intelligence" instinct predates AI but was bottlenecked by being human-labor-intensive — the bottleneck AI lifts.*
- **Patient communities built research-grade infrastructure (tissue banks, registries).** — Count Me In Leiomyosarcoma Project, Dana-Farber, 2022, https://www.dana-farber.org/newsroom/news-releases/2022/count-me-in-launches-a-rare-cancer-research-project-to-engage-leiomyosarcoma-patients-and-families. ⚠️ *The "400 samples / 18 months" + "Norman Scherzer/Catherine Poole" attribution could NOT be verified — use the documented Count Me In / NLMSF precedent instead.*

### 2.2 Individual founder-mode precedents (the Sid pattern, documented)

- **David Fajgenbaum (iMCD)** — the cleanest N=1→published→trial pipeline (see ⭐ anchor #2). Durable remission 66/19/19 months across 3 patients. *The anti-quackery model: Pain-B grounded in an approved drug + his own molecular data, published top-journal, escalated to a trial.* **Caveat: he had MD/researcher training + lab access — still CEO-level capability, reinforcing the democratization gap.**
- **Kathy Giusti (multiple myeloma)** — patient-founder who built the precision-medicine infrastructure (MMRF CoMMpass: 1,000+ patients, longitudinal WES/WGS/RNAseq, open data; >4,000 sample tissue bank; 15 drugs approved / survival tripled). — themmrf.org; HBS case #814026. *Founder-mode works but required raising >$500M — the non-scalability point made concrete.*

### 2.3 Collective self-experimentation — works only with method

- **PatientsLikeMe lithium-in-ALS: ~149 patients self-organized, used a patient-matching algorithm vs 447 controls, correctly REFUTED the hyped 2008 result (no effect at 12 mo) — pre-empting failed RCTs.** — Wicks et al., *Nat Biotechnol* 2011;29(5):411-414, DOI 10.1038/nbt.1837. *Patient-led data can generate real (even money-saving negative) evidence — but the value was the matching algorithm + controls, not the enthusiasm.*
- **Collective self-experimentation is a studied phenomenon with explicit caveats (group dynamics can substitute social proof for evidence).** — *Social Science & Medicine* 2019, S027795361930351X (⚠️ abstract only, full text 403-blocked — cite at abstract level).

---

## SECTION 3 — MTB Utility & Its Pain-A Coverage + Gaps

### 3.1 The MTB *is* a multidisciplinary team (the role-set AI must reproduce)

- **A core MTB = medical oncologist + molecular biologist/pathologist + bioinformatician + geneticist, with case-by-case specialists.** — "MTB as a Clinical Tool for Converting Molecular Data Into Real-World Patient Care," *JCO Precision Oncology* 2023, https://ascopubs.org/doi/full/10.1200/PO.23.00067. *Directly supports the Pain-A decomposition: the MTB job is itself a team of specialized roles.*
- **EU consensus formalizes a core team (oncologists, pathologists, molecular biologists, geneticists, pharmacologists) + a non-core team (radiation oncologists, surgeons, radiologists, nurses, bioethicists, patient reps).** — CAN.HEAL Consortium, "A decalogue of MTB recommendations," *Eur J Cancer* 2025, https://www.sciencedirect.com/science/article/pii/S095980492500214X. *A dozen+ specialists per case = the labor cost that makes founder-mode unscalable and that AI must compress.*

### 3.2 Actionability & utility when matching is done well (associative)

- **Actionable alterations found ~50% (study-dependent); comprehensive panels vastly outperform small ones (81% vs 21%).** — systematic review + IMPACT/MD Anderson (*JCO PO* 2017). *Quality of the retrieval substrate determines how many real options surface.*
- **Higher matching score (≥50% alterations targeted) independently correlates with longer PFS/OS; I-PREDICT N-of-1 combination improved disease control (83 patients, single-arm).** — Sicklick/Kurzrock et al., *Nat Med* 2019;25:744-750, DOI 10.1038/s41591-019-0407-5; follow-up *JCO* 2025. *Sid's strategy validated in a cohort — the problem is access/scalability, not validity.* ⚠️ *Exact HR/DCR could not be extracted from paywalled PDF — verify before quoting.*
- **MTB-recommendation adherence associated with markedly better OS** (non-adherent median 19.5 mo vs "not reached"). — *JCO PO* 2024, https://ascopubs.org/doi/10.1200/PO-24-00387. ⚠️ *Confounded by selection (healthier patients adhere) — use carefully.*
- **Best-case utility: NSCLC rare/complex mutations, 81% adherence → 67% ORR, PFS 6.3 mo, OS 10.4 mo.** — *JCO PO* 2022, https://ascopubs.org/doi/10.1200/PO.20.00008.

### 3.3 The randomized complication (DO NOT omit)

- **SHIVA01 (n=195, refractory): NEGATIVE — PFS 2.3 vs 2.0 mo, no significant difference.** — see ⭐ anchor #6. *Failure attributed to weak single-alteration/off-label matching; a subgroup (35% of crossover) showed PFS ratio >1.3. The lesson — rigor of matching/vetting IS what separates benefit from noise — is the article's thesis. Present MTB utility as "associative, with one negative RCT," not proven causation.*

### 3.4 Pain-A coverage gaps MTBs leave for late-line patients

- **Even with a target identified, ~31% of studies report "actionable but no available drug/trial" and ~33% ineligibility.** — Frost et al. 2022 (same source as 1.1). *This is the empirical Pain-A→Pain-B boundary: Pain-A first exhausts the real-option space; only the residual "actionable-but-no-drug" cohort legitimately motivates Pain-B.*

---

## SECTION 4 — Pain-B / N=1 / AI Co-Scientist Landscape

### 4.1 AI scientist-team systems that generate grounded NOVEL leads

- **Google AI co-scientist** (⭐ anchor #3) — coalition of Gemini agents (Generation, Reflection, Ranking, Proximity, Evolution); idea-tournament with Elo self-play ranking correlating with accuracy; world-unknown AMR mechanism matching unpublished experimental work; AML repurposing hits inhibiting tumor viability in multiple cell lines (KIRA6 strongest); anti-fibrotic targets active in human hepatic organoids (p<0.01). *Strongest peer-reviewed model for the article's conceit + the "idea tournament" as the discipline separating ranked candidates from raw LLM spew.* **Complication: all wins are in vitro/organoid — complicates the leap to patient benefit.**
- **Robin (FutureHouse)** (⭐ anchor #4) — full autonomous loop → ripasudil for dry AMD (Y-27632 hit → RNA-seq ABCA1 upregulation → ripasudil). *Best real-world proof of the thesis.* **Complication: the announcement contains no discussion of failure modes / false-positive rate / hallucination safeguards — the candor gap is itself citable.**

### 4.2 The legitimacy & discipline of N-of-1

- **N-of-1 trials are a legitimate precision-oncology tool — but the authoritative review warns they are not a substitute for validation; classic crossover N-of-1 is often unsuitable for aggressive cancer.** — Gouda et al., *Cancer Discov* 2023;13(6):1301-1309, DOI 10.1158/2159-8290.CD-22-1377. *Top-tier venue endorses the drug-centric→patient-centric shift; stresses consensus expert discussion.*
- **Single N-of-1 anecdotes are not evidence; pooling frameworks (NIH Exceptional Responders, Canada POG) turn anecdotes into signal.** — Samuel et al., *J Clin Transl Sci* 2023;7:e161, DOI 10.1017/cts.2023.583; Oncology News Central 2025. Useful quote: *"Molecular logic may point us toward promising therapies, but without disciplined, thoughtfully designed trials, we risk leading patients into the dark."*
- **The N-of-1 field's default is under-rigorous: only 3.48% of 115 studies met all evidence standards** (⭐ anchor #8). *The quantitative case that AI's value is the discipline, not the ambition.*

### 4.3 Engineering grounding for novel-lead generation

- **Knowledge-graph–grounded multi-agent / RAG systems explicitly mitigate hallucination + give traceable mechanistic explanations** (BioScientist Agent: 6.3M nodes/41M edges; CLADD; PharmaSwarm). RAG gives +41–50% over string-matching. — bioRxiv 2025.08.08.669291; *Anal Chem* 2025 (PMC12750412). *Concrete evidence that "zero tolerance for fabricated evidence" is achievable via KG + retrieval.* ⚠️ *Mostly preprints/methods, not clinical validation — cite as engineering precedent.*

---

## SECTION 5 — Fabrication / Safety Risks & Mitigations (the discipline that separates OPL from quackery)

### 5.1 LLMs fabricate citations — worst exactly where founder-mode patients live

- **~47% of ChatGPT medical references fabricated; 87% of real ones contain errors.** — Bhattacharyya et al., *Cureus* 2023;15(5):e39238, DOI 10.7759/cureus.39238, https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10277170/. *Canonical baseline: "ask the LLM and trust its citations" is unsafe.*
- **Citation fabrication is topic-dependent: ~6% for well-covered conditions vs ~28–29% for rarer ones.** — JMIR 2025 (PMC12658395). *The exact zone founder-mode patients occupy (rare/recurrent/under-studied) is where hallucination is WORST — "be most paranoid precisely where the patient is most desperate."*
- **Fabricated references in published biomedical papers rose >12-fold since 2023; review articles hit hardest (+57%).** — Topaz et al., *The Lancet* 2026 correspondence (⚠️ paywalled; rate figures from abstract + secondary reporting, treat 2026 weekly rate as provisional). *Contamination is now in the literature itself — grounding alone is insufficient without active verification.*
- **Citation hallucination rates 14.2–94.9% depending on domain (GhostCite, arXiv 2602.06718); Bard 91.4% / GPT-4 28.6% fabricated refs on systematic-review prompts (JMIR 2024 e53164).** *The corpus quantifying why PMID-anchoring / Pain-A-first is non-negotiable.*

### 5.2 LLMs cite retracted / discredited science silently

- **ChatGPT never flags retractions: 0 of 6,510 evaluations of 217 retracted/concerning papers mentioned retraction; 190 still scored highly.** — Thelwall, *Learned Publishing* 2025;38:e2018, DOI 10.1002/leap.2018 (⚠️ paywalled; figures from abstract + Sheffield press release).
- **Oncology-specific: retracted cancer-imaging articles keep getting cited AND GPT-4o uses them (~10% of cases) without disclosing retraction.** — Gu et al., *J Adv Res* 2025, DOI 10.1016/j.jare.2025.03.020 (PMC12126723). *Cleanest cancer-focused example — supports a mandatory citation-verification + retraction-screen layer.*
- **LLMs unreliable at identifying retracted papers even when asked directly (21-chatbot study).** — Retraction Watch 2025-11-19 (⚠️ secondary/journalism only, no primary located — use as lead).

### 5.3 Over-confidence & adversarial fragility

- **Every tested LLM elaborates on a planted fake clinical detail 50–83% of the time** (⭐ anchor #7; Omar et al., *Commun Med* 2025). *A patient typing in their own OCR-corrupted records IS the adversarial-prompt scenario.*
- **Agentic reasoning systems ignored available evidence in 68% of reasoning traces; revised beliefs against contrary findings only 26% of the time.** — April 2026 arXiv (⚠️ secondary reporting via TechTimes; primary arXiv ID not captured — verify before citing as fact). *Even tournament/debate architectures can be epistemically stubborn — argues for external grounding + human verification over self-consistency.*
- **Raw GPT-4 cancer-treatment concordance 86.7% NCCN / 88.5% approval — but drops to 73.8% on RECURRENT cancers.** — Tsai et al., *Digital Health* 2024;10, DOI 10.1177/20552076241269538 (PMC11325467). *GOLD: Sijbrandij had RECURRENT osteosarcoma — exactly where the raw LLM degrades most. Why founder-mode patients can't just "ask ChatGPT."*
- **Even when an LLM names a concordant option, it frequently ALSO names non-concordant ones (~34% of outputs).** — HNC NCCN study via oncology review PMC12164365 (⚠️ exact primary HNC DOI not isolated — treat 34.3% as needing confirmation). *Patient/family can't tell which of 6 recs is the NCCN one — argument for Pain-A = retrieve+match+VET, not just generate.*

### 5.4 Mitigations — what makes founder-mode safe (and their residual limits)

- **A targeted mitigation prompt nearly halves adversarial hallucination (66%→44%; GPT-4o 53%→23%); temperature changes do nothing.** — Omar et al. 2025 (mitigation OR 0.27, p<0.001). *Prompt hygiene works and is cheap — but leaves ~23% residual; NOT sufficient alone, need external retrieval + verification on top.*
- **Retrieval-Augmented / Agentic-RAG GPT-4 reaches ~92–100% NCCN concordance WITH verifiable source citations (document + page).** — arXiv 2502.15698 (Agentic-RAG 100% adherence, 24/24, no hallucinations; Graph-RAG ~92–95.8%; ChatGPT-4 ~91.6–94% but NO references); corroborating ASH abstract Yost et al., *Blood* 2025 (⚠️ paywalled, figures not extracted — cite arXiv for hard numbers). *Core constructive evidence: grounding + verifiable attribution raises concordance toward ceiling AND gives a checkable paper trail.*
- **BUT contextualization/RAG introduces a NEW failure mode: omitting guideline-concordant options.** — Precision Oncology NSCLC contextualized-ChatGPT study, PMC12017742. *The precise tension: too loose = quackery; too tight = miss the rare option the patient needs. Supports "retrieve broadly, vet strictly, never silently drop."*
- **Medical-hallucination detection is still weak (MedHallu best model 0.625 F1 on hard cases); ECRI 2026 ranked misuse of unregulated AI chatbots as the #1 health-technology hazard.** *A patient-facing AI scientist team must be architecturally constrained (retrieval + KG grounding + human-in-loop).*

### 5.5 The system-level honesty caveat

- **The AI co-scientist is explicitly NOT clinically validated and does not replace a research team** — the *Nature* paper states it "did not achieve autonomous scientific discovery, did not complete clinical trials, did not replace a biomedical research team." MIT's Ritu Raman: "Science is a team sport. Co-Scientist can't do science by itself." *Forces precision: AI democratizes hypothesis generation + option-vetting, not bedside decisions. The patient remains decision authority.*

---

## SECTION 6 — Access Mechanisms (Pain-A territory: the real options that exist but are invisible)

### 6.1 FDA Expanded Access — the regulator is almost never the bottleneck

- **FDA allows ~99% of expanded-access requests to proceed.** — FDA Expanded Access / Project Facilitate; corroborated in *Expanded Access Versus Right-to-Try*, Mayo Clin Proc Innov Qual Outcomes 2020 (PMC7081483). *Demolishes "the FDA stands between the patient and the drug." The real gates are upstream (manufacturer consent, physician initiative, money) and informational (does the patient know the drug exists?) — supports the agency-vacuum thesis.*
- **Form FDA 3926 cut physician burden from ~8h (single patient)/16h (emergency) to ~45 min.** — FDA Form 3926 OMB statement / Federal Register 2015 & 2018. *The paperwork is no longer the wall — but 45 min still presumes a motivated, informed oncologist. Exactly the founder-mode labor an AI could shoulder (draft the 3926, find the drug + manufacturer contact).*
- **FDA created "Project Facilitate" because oncologists found expanded access too burdensome to navigate.** — fda.gov OCE Project Facilitate; Reagan-Udall Expanded Access Navigator. *The FDA's own admission of the navigation problem + its concierge response. AI = the scalable version of Project Facilitate for every patient.*
- **But real-world uptake is gated by manufacturer consent (true veto-holder) + cost (insurance won't cover investigational drugs).** — American Cancer Society; PMC7081483. *Honest framing: AI can find and request, but cannot force a company to say yes or pay the bill.*
- ⚠️ **EXCLUDED — unverified:** "<10% of eligible patients pursue EA," "$10K–$40K OOP," "72% of hospitals no billing policy," "60% of oncology EA = trial-excluded." Traced only to a non-peer-reviewed Medium blog. The directional point (cost + non-coverage is a major barrier) IS supported by ACS + PMC7081483; the specific numbers are NOT — source fresh if needed.

### 6.2 EU / Europe — 27 rulebooks

- **EU compassionate use is fragmented by design: Article 83 of Reg (EC) 726/2004 lets CHMP recommend, but each Member State implements separately — no single EU pathway.** — EMA Compassionate Use overview; PMC5116859. *A textbook information-asymmetry / navigation problem — exactly the Pain-A decomposition.*
- **"Compassionate use" (population programmes) ≠ "named-patient" supply (doctor obtains unauthorized medicine directly from manufacturer, on own responsibility, no EMA notification).** — EMA; WEP Clinical. *Precision the article needs; same agency-vacuum pattern across jurisdictions.*

### 6.3 China / NMPA — even more arid, plus regional pilots (directly relevant to CancerDAO users)

- **China has no finalized national compassionate-use statute (2017 NMPA draft never finalized); access runs through company managed-access programs + regional pilot zones.** — Remap Consulting; DIA Global Forum 2022. *For a Chinese patient the formal door is largely absent — the options desert is more arid.*
- **Hainan Boao Lecheng pilot zone = principal channel for overseas-approved-but-China-unapproved drugs: by 2023 >450 overseas drugs / >28,000 patients; 485 products (308 devices, 177 drugs) as of July 1, 2025.** — Lexology; PharmExec; *Frontiers in Medicine* 2025 (PMC12588950). *A real, vettable option invisible to almost every patient without expert navigation, and geographically gated (must physically travel). Perfect Pain-A example.*
- **Parallel Greater Bay Area pilot (since 2020): Guangdong approves Hong Kong/Macau-marketed drugs for designated hospitals across nine cities.** — same sources. *Reinforces the patchwork, regional nature of Chinese access.*

### 6.4 Off-label use — mainstream, evidence-graded oncology (NOT quackery)

- **~50–75% of US cancer drug/biologic uses are off-label; most (in a Medicare analysis) met NCCN Compendium criteria.** — NCCN estimates via Managed Healthcare Executive; *J Oncol Pract* (PMC2794406); Conti et al., *J Clin Oncol* 2013 (PMC3595423). *The line between legitimate off-label and quackery IS the evidence-vetting step (compendium support) — the cleanest illustration of Pain-A discipline.*
- **Since 1993, US Medicare must cover off-label oncology uses listed in approved compendia (NCCN) or specified peer-reviewed journals — compendium inclusion is the de facto reimbursement gate.** — PMC2794406. *"Evidence-graded" is the literal mechanism converting a paper into a payable treatment, with money-real consequence.*

### 6.5 Trial-matching tools — tractable but must be vetted

- **TrialGPT (⭐ anchor #5) near-expert** — plus real-world: improved screening sensitivity to **81.8% vs 36.4% for manual** (JAMIA 2026 adaptation, 33(4):909). *AI nearly DOUBLED the catch rate of relevant trials vs humans.*
- **But automated matching is imperfect and must be human-confirmed; accuracy is bounded by registry data quality.** — "A prospective pragmatic evaluation of automatic trial matching tools in a molecular tumor board," *npj Precision Oncology* 2025 (s41698-025-00806-y); neuro-symbolic multi-agent eval, 3,804 patients (PMC13091143). *Validates "match-then-verify, never match-then-trust."*
- **Registry data quality caps any matcher: a 13-year ChiCTR analysis found thousands of records with missing/incorrect fields (~848 wrong initiation year, ~472 missing funding, 190 missing study design of 32,017); no QC of uploaded protocols.** — *Frontiers in Medicine* 2023 (PMC10602811); 2024 (fmed.2024.1394803). *Garbage-in-garbage-out, especially for ChiCTR (directly relevant to Chinese patients) — "you cannot trust a match you cannot trace to a verifiable record."*

### 6.6 The quackery boundary (cross-border tourism without Pain-A discipline)

- **Cross-border oncology travel for UNPROVEN therapies (esp. stem-cell tourism) carries documented harms: tumor formation, infection (incl. hepatitis), neuro/cardiac complications, no continuity of care, weak legal recourse; most clinics in LMICs with minimal oversight.** — "International stem cell tourism: a critical literature review," 2021 (PMC8890798); City of Hope. *The quackery boundary made concrete — what happens when patients pursue Pain-B-style "world-unknown" options WITHOUT Pain-A vetting. Strongest argument for the sequencing: Pain-A first, then Pain-B with the same evidentiary rigor — otherwise founder-mode degrades into expensive, dangerous tourism.*
- **Self-sourcing has legal rails: FDA Expanded Access (codified 1987), federal Right to Try (2018), online petition/advocacy campaigns; Abigail Alliance v. von Eschenbach established no constitutional right to investigational drugs.** — en.wikipedia.org/wiki/Expanded_access; PMC4739083. *The agency-vacuum + self-sourcing behavior is real and already has lawful rails — retrieving/matching/vetting access pathways (Pain-A) is a concrete, lawful job AI can do, distinct from inventing therapies (Pain-B).*

---

## GAPS / THIN LITERATURE → the paper's "Limitations & Future Work"

1. **No validated pipeline does BOTH Pain-A (trial-matching) AND Pain-B (novel-lead generation) in one system.** TrialGPT (Pain-A) and AI co-scientist / Robin (Pain-B) are separate. *This dual-phase integration is arguably the paper's white space — state it explicitly.*
2. **All AI co-scientist / Robin wins are in vitro / organoid / preclinical.** No peer-reviewed evidence that an AI-generated novel lead has helped a real patient. The patient-benefit leap is unproven.
3. **Precision-oncology survival benefit is associative, with one negative RCT (SHIVA).** I-PREDICT/WINTHER and adherence studies are single-arm/observational and selection-confounded. Do NOT claim proven causation.
4. **Hallucination mitigations reduce but never eliminate error (~23% residual even at best).** And over-tight grounding creates a new failure (omitting valid options). No published architecture demonstrably solves both simultaneously in oncology.
5. **Registry data quality is an external ceiling on all matchers**, especially ChiCTR — under-studied as a systematic limitation of AI patient-navigation.
6. **Medical-hallucination detection is weak** (MedHallu best 0.625 F1) and agentic systems are epistemically stubborn (ignore evidence 68% of traces — but this figure is from secondary reporting, primary unconfirmed).
7. **Expanded-access cost/uptake statistics are essentially unsourced** in peer-reviewed literature — a real evidence gap (the credible numbers trace to a blog). A primary study quantifying EA cost barriers and uptake would be valuable.
8. **The democratization claim itself is untested.** Every documented founder-mode success (Fajgenbaum, Giusti, Sijbrandij) still required elite resources (MD training, lab access, or >$500M). No published study shows AI closing that gap for an ordinary patient.

---

## SOURCES FLAGGED AS UNVERIFIED / DO-NOT-CITE-AS-FACT (consolidated)

- Leiomyosarcoma "400 samples / 18 months" + Scherzer/Poole attribution — no primary source. Use Count Me In / NLMSF instead.
- "Stephanie Lee melanoma self-funded peptide vaccine" — no citable primary source. DROP.
- Expanded-access cost cluster ("<10% pursue," "$10K–$40K OOP," "72% no billing policy," "60% trial-excluded") — Medium blog only. EXCLUDED.
- 68% ignore-evidence / 26% belief-revision agentic figures — secondary reporting of an uncaptured April 2026 arXiv preprint. Verify before citing.
- Google co-scientist DOI page socket-failed; exact title/author string cross-confirmed via Google Research blog only — re-verify against DOI 10.1038/s41586-026-10644-y.
- I-PREDICT exact HR/DCR; MD Anderson "6.4% matched" figure; WINTHER ~35% matched — verify against primaries (Sicklick *Nat Med* 2019; Meric-Bernstam; Rodon *Nat Med* 2019).
- HNC 34.3% non-concordance — primary DOI not isolated (umbrella: oncology review PMC12164365).
- Lancet 2.5M-paper audit weekly rate; Thelwall retraction figures; ASH lymphoma abstract numbers — all paywalled, figures from abstracts/press releases (secondary).
- Unger *JNCI* 2019 56/22/15% split — cite primary, not CancerNetwork secondary.
- Social Science & Medicine 2019 collective-self-experimentation — abstract only (403-blocked).
- 21-chatbot retraction study — Retraction Watch journalism only, no primary located.
