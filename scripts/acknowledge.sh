#!/usr/bin/env bash
# OPL for Cancer — skill-form wrapper for `opl-cancer acknowledge`
# Usage: ./scripts/acknowledge.sh <card_id> [--outstanding-dir <dir>] [--serious-risks <path>]
exec python -m opl_cancer.cli acknowledge "$@"
