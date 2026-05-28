---
name: Bug report
about: A code defect — wrong behaviour, crash, false output, refusal that should not happen
title: "[bug] <one-line summary>"
labels: bug
assignees: ''
---

## What happened

(One paragraph. What you ran, what you expected, what you got.)

## Reproducer

Minimum failing case — please include the exact commands:

```bash
opl <command> --patient <PATH> --run-id <ID> --json
```

## Observed output

```
(paste structured output / stack trace / error)
```

## Expected output

```
(what should have happened)
```

## Environment

- OPL version: (output of `opl status`)
- Python: (output of `python --version`)
- OS: (macOS 14.x / Ubuntu 22.04 / …)
- Installed extras: (e.g. `pip install -e .[dev,bio]`)

## Patient-data note

⚠️ **Do not paste real patient records.** If the bug reproduces only on a
specific patient, please anonymise or use the reference Riaz fixture.

## Additional context

(Anything else — related ADR, suspected commit, etc.)
