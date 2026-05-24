#!/usr/bin/env bash
# OPL for Cancer — skill-form wrapper for `opl-cancer init-patient`
# Usage: ./scripts/init_patient.sh <patient_code> [--root <dir>]
exec python -m opl_cancer.cli init-patient "$@"
