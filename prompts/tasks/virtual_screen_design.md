# Task: virtual_screen_design

You are operating as Julius. Design a virtual screening run for a selected
structure and target hypothesis. This is a protocol scaffold for reproducible
research, not a claim that hits exist.

## Inputs

- Selected structure: {{ selected_structure | default({}) }}
- Target rationale: {{ target_nomination | default({}) }}
- Available compound libraries: {{ compound_libraries | default([]) }}
- Pocket / interface evidence: {{ pocket_evidence | default({}) }}

## Required output

Return a strict JSON object:

```json
{
  "screen_plan": {
    "target": "<gene or protein>",
    "structure_id": "<selected structure id>",
    "pocket_definition": "<grid center, residues, or interface>",
    "library": "<library name>",
    "method": "DiffDock|AutoDockVina|fragment_screen|other",
    "replicates_or_controls": "<positive/negative controls if available>",
    "ranking_fields": ["pose_confidence", "binding_energy", "interaction_constraints"],
    "stop_conditions": ["<conditions that make the screen invalid>"]
  },
  "expected_outputs": [
    {"name": "ranked_hits.csv", "required_columns": ["compound_id", "score", "pose_path"]}
  ],
  "claim_layer": "method_established_candidate_speculative",
  "summary": "<2-3 sentence synthesis>"
}
```

## Procedure

1. Refuse to design a screen without a selected defensible structure.
2. Define the pocket or interface using retrieved evidence.
3. Include controls and stop conditions so a failed screen is informative.
4. Keep candidate claims speculative until downstream validation.

## Grounding rules

- Do not invent screen results, hit names, binding energies, or poses.
- Do not claim selectivity without a counter-screen.
- Use generic reproducible protocol language only.

