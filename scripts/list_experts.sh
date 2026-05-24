#!/usr/bin/env bash
# OPL for Cancer — skill-form wrapper for `opl-cancer list-experts`
# Requires: pip install -e . (in repo root)
exec python -m opl_cancer.cli list-experts "$@"
