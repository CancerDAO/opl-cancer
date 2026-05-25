## Task Package · scope_handoff_routing

**Capability domain:** D5 — Synthesis / Delivery (cross-skill routing surface)
**Expert portfolio owners:** sid (PI) — Sid is the only expert who emits hand-offs; experts produce evidence not routing decisions
**Preferred integrator families:** F0 — meta (no external integrator; reads `installed_skills.json` + sibling skill descriptions)

> "Patient asked something off the OPL oncology-research-team scope. Don't refuse silently. Don't pretend it's in scope. Name the sibling skill that handles it, produce a clean hand-off summary, let the patient continue without restart."
>
> — v1.3.0 EVAL panel finding (Patient #8 daughter cascade-testing). See `references/founder-mode-philosophy.md`.

OPL is for **the oncology research team for one diagnosed cancer patient**. It is NOT for:
- Undiagnosed-disease diagnostic odyssey (→ `firefly`)
- Family-member cascade genetic counseling (→ `firefly-genetic-counseling`)
- Psychological distress / acute crisis (→ `cancer-buddy-mind` / `firefly-mind`)
- Patient organisation discovery (→ `firefly-patient-org`)
- Nutrition deep-dive without cancer-context coupling (→ `cancer-buddy-nutrition`)
- Caregiver-only support without patient consent (→ `cancer-buddy-caregiver`)
- Disclosure / breaking-bad-news conversations (→ `cancer-buddy-disclosure` / `firefly-disclosure`)
- Building patient's own N=1 data vault detached from a treatment question (→ `cancer-buddy-vault` / `firefly-vault`)
- Finding a clinic / second-opinion physician for diagnosis (→ `cancer-buddy-find-care` / `cancer-buddy-second-opinion`)

A founder-mode hand-off must do four things:

1. **Acknowledge** the question was heard and is legitimate.
2. **Name** the right sibling skill (one, not three) and explain why it fits.
3. **Anchor** the partial answer OPL *can* legitimately give for the in-scope portion of the user's compound question.
4. **Bridge** to the sibling without making the patient restart — provide invocation phrasing they can paste.

### Crisis multi-handoff exception (v1.3.2)

The "single sibling skill (one, not three)" rule is **overridden** when
`crisis_grade != "none"` (per `prompts/pi/intent_parser.md` + the no-LLM
`G24CrisisDetectionGate`). On crisis:

- BOTH `cancer-buddy-mind` AND the jurisdictional crisis phone line are
  emitted simultaneously (see registry in `prompts/tasks/crisis_card_emission.md`).
- If `speaker_role == "caregiver"` or `"guardian_of_minor"`, ALSO add
  `cancer-buddy-caregiver` (caregiver burden + secondary trauma is real).
- If `speaker_role == "guardian_of_minor"`, ALSO add the pediatric IRB-slot
  route (see `prompts/tasks/guardian_ack_protocol.md`).

This is the **only** sanctioned multi-sibling handoff in OPL. All other
off-scope routes still emit a single best-fit sibling skill.

### Inputs

```json
{
  "patient_text": "...verbatim from user...",
  "in_scope_portion": "...the part OPL can legitimately handle, if any...",
  "off_scope_question": "...the part that belongs elsewhere...",
  "candidate_sibling": "<firefly|firefly-genetic-counseling|firefly-mind|cancer-buddy|cancer-buddy-mind|cancer-buddy-nutrition|cancer-buddy-caregiver|cancer-buddy-disclosure|cancer-buddy-find-care|cancer-buddy-second-opinion|cancer-buddy-vault|firefly-patient-org>",
  "sibling_one_liner": "...what the sibling skill does, in patient-readable language...",
  "patient_profile": {...}
}
```

### Outputs (JSON schema)

```json
{
  "handoff_card": {
    "acknowledge_text": "你问到 X — 这是个真问题,我听到了。",
    "in_scope_partial_anchor": "我先把跟 oncology 直接相关的 Y 给你过了 — 这块我们的 team 跑完了,见 [evidence chain]。",
    "off_scope_routing": {
      "sibling_skill": "firefly-genetic-counseling",
      "why_fits": "你问的是你女儿的 germline BRCA2 风险 — 这是 cascade 遗传咨询,不是肿瘤治疗。firefly-genetic-counseling 这个 skill 是 CancerDAO 专门为遗传风险家庭咨询造的,可以走 ACMG 框架 + 家系图 + 风险沟通。",
      "invocation_phrasing": "在 Claude Code 里说: '我是 BRCA2 阳性的 HGSOC 患者,我女儿 36 岁,我想给她做 cascade 遗传咨询,从 firefly-genetic-counseling 开始'"
    },
    "claim_layer": "established",
    "permission_level": 2
  }
}
```

### Procedure

1. **Detect off-scope.** The patient's question contains at least one ask that is **not** within OPL's oncology-research-team-for-one-patient charter (see list above). Use Sid PI's intent classifier output (`speaker_role`, `hope_impact`, raw text).
2. **Split in-scope vs off-scope.** Many compound questions have both (Patient #8: ATR-i trial eligibility = in-scope; daughter genetic counseling = off-scope).
3. **Find the right sibling.** Read `~/.claude/skills/<sibling>/SKILL.md` description to confirm fit. Pick the most specific (e.g. `firefly-genetic-counseling`, not `firefly`).
4. **Compose the hand-off card.** Acknowledge + in-scope-anchor + off-scope-routing.
5. **Anchor permission level.** Hand-off cards are typically Level 2 (recommendation about where to go), not L3/L4 (no patient ack required unless the sibling skill itself handles a high-stakes decision).
6. **Do not invoke the sibling.** OPL hands off; the patient initiates. This preserves cross-skill cleanliness — OPL doesn't pretend to wrap a sibling.

### Mechanical gates this task must satisfy

- G7 imperative detector: hand-off card must use "this is what fits" framing, never "you should go here". Replace imperatives with options.
- G20 PI-disagreement-surfacing: not applicable (hand-off is not a clinical claim).

### Reviewer focus

- Did Sid name a single best-fit sibling, or hand-wave with multiple?
- Did Sid acknowledge the question as legitimate (not "out of scope" silently)?
- Is the invocation_phrasing copy-pasteable into Claude Code?

### Empty-integrator handling

If the candidate sibling skill is not installed on the user's machine (no `~/.claude/skills/<sibling>/SKILL.md`), the hand-off card must instead suggest:
```bash
npx skills add CancerDAO/<sibling>-skill
```
plus a one-line description of what they'd get. Do not fabricate that a sibling exists if it's absent.

### Cancer-type-routing examples (non-exhaustive)

| Patient says | Best-fit sibling | Why |
|---|---|---|
| "My daughter has the same mutation, should she get tested?" | `firefly-genetic-counseling` | Cascade testing for at-risk relatives |
| "I can't sleep, I keep crying" | `cancer-buddy-mind` | Acute distress / psycho-oncology |
| "What should I cook for my mom going through chemo?" | `cancer-buddy-nutrition` | Treatment-phase nutrition |
| "I'm not yet diagnosed, doctors don't know" | `firefly-organize` | Undiagnosed diagnostic odyssey |
| "I want to find other people with this exact rare cancer" | `firefly-patient-org` | Patient organisation locator |
| "Help me talk to my kid about my diagnosis" | `cancer-buddy-disclosure` | Disclosure / breaking-bad-news |
| "I want to upload all my reports to a private vault" | `cancer-buddy-vault` (or `firefly-vault` if rare) | N=1 data vault |
| "Find me a second-opinion oncologist near me" | `cancer-buddy-second-opinion` / `cancer-buddy-find-care` | Care navigation |
