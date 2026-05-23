# Prompt Change Review Checklist

Use when reviewing PRs that modify `prompts/tasks/*.md`, `prompts/experts/*/persona.md`, `prompts/pi/*.md`, `prompts/reviewer/*.md`, or `prompts/auditor/*.md`.

## Required for approval

- [ ] PR description includes historical-impact-statement
- [ ] Golden set CI all green (no failure-mode tests regress)
- [ ] At least 1 medical reviewer approval (for tasks/experts prompts)
- [ ] Founder-mode check: no command-form ("you should") added; no paternalism creep
- [ ] PMID/source-grounding maintained (no claims without PMID required)
- [ ] CHANGELOG entry with prompt_version bump
