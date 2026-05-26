# v2 E2E Validation Matrix — `iter/v2-paradigm`

ADR-0010 success criteria checked via `scripts/verify_v2_e2e.py`.

## Methodology disclosure (honest scope)

This matrix records **synthetic E2E**: a real Wave 2 JSON output (assembled
from realistic clinical inputs per the two target patient profiles) is fed
through the **real Wave 5 renderer** to produce `patient_brief.html` +
`.md`, then the verifier reads the resulting artifacts. This validates that
the 5 paradigm-shift seams are wired end-to-end.

It does NOT replace a full live-LLM 5-wave run. A live run requires:
- MINIMAX_API_KEY (or Anthropic Opus key) — present in user env
- `opl-cancer plan → wave1 → ... → wave5` via the SKILL.md main-thread orchestrator
- ~20-40 min wall-time + ~$10-30 API cost per patient

Per `memory:feedback_no_false_completion` I'm reporting only what I actually
ran in this session. The user will perform the live-LLM E2E after pulling
this branch — see "Next step (user)" below.

## Matrix

| # | Patient | Cancer type | Stage | Synthetic Wave 2 fixture | Run dir | Verifier | Wall-time |
|---|---|---|---|---|---|---|---|
| 1 | PT-EE62321353 (template) | mCRC | IV L4+ KRAS G12C MSS | `tests/fixtures/v2/wave2_output_with_novelty.json` | `/tmp/v2-e2e-test-1` | ✅ PASS | <1s |
| 2 | TEST-HCC-001 (template) | HCC | TACE-refractory ICI-naive Child-Pugh A6 | `tests/fixtures/v2/wave2_output_hcc_novelty.json` | `/tmp/v2-e2e-test-2` | ✅ PASS | <1s |

Per `memory:feedback_multi_case_validation`: ≥2 patients ≥2 cancer types
covered (mCRC + HCC).

## What each verifier check confirms

`scripts/verify_v2_e2e.py` enforces 7 checks per run, mapped to ADR-0010:

1. `wave2_hypotheses.json` exists and is valid JSON.
2. ≥1 hypothesis with `generation_strategy: target_synergy_emergent`
   (proves Maya's strategy wired in).
3. ≥1 hypothesis with `generation_strategy: undrugged_target_design`
   (proves Julius's strategy wired in).
4. ≥2 hypotheses with `claim_layer: speculative` AND non-empty
   `testability_path` (proves the v2 synthesis policy works).
5. `delivery/patient_brief.html` exists.
6. HTML contains the `World-Unknown` section header (proves renderer
   template applied).
7. HTML contains both `未发表` AND `research direction` framing (proves
   ADR-0010 anti-recommendation rule enforced).

## Reproduction commands

```bash
# 1. Build synthetic patient 1 run dir
mkdir -p /tmp/v2-e2e-test-1/delivery
cp tests/fixtures/v2/wave2_output_with_novelty.json /tmp/v2-e2e-test-1/wave2_hypotheses.json
python3 -c "
import json
from pathlib import Path
from opl_cancer.glue.renderer import PatientBriefRenderer
fixture = json.loads(Path('tests/fixtures/v2/wave2_output_with_novelty.json').read_text())
r = PatientBriefRenderer()
ctx = {
    'language': 'zh', 'patient_code': 'PT-EE62321353',
    'run_id': 'v2-e2e-test-1', 'created_at': '2026-05-26T00:00:00Z',
    'sid_summary': 'test', 'experts': [], 'risk_cards': [],
    'world_unknown_candidates': [h for h in fixture['top_k_hypotheses'] if h['claim_layer']=='speculative'],
}
r.render_html(ctx, Path('/tmp/v2-e2e-test-1/delivery/patient_brief.html'))
"

# 2. Verify
python3 scripts/verify_v2_e2e.py /tmp/v2-e2e-test-1
# expect: ✅ v2 E2E verification PASS

# 3. Repeat for patient 2 with tests/fixtures/v2/wave2_output_hcc_novelty.json
```

## Next step (user)

After pulling `iter/v2-paradigm`, run the real 5-wave pipeline on
PT-EE62321353 via Claude Code orchestration:

```
/opl-cancer  (in Claude Code)
> 请用 v2 在 PT-EE62321353 上跑一次完整 5-wave
```

Then `python3 scripts/verify_v2_e2e.py <triggers/run-*/>` on the produced
run dir. Append the matrix row with real `wall-time` + live-LLM verdict.
Tracked as a TODO in `iter/v2-paradigm` PR description.
