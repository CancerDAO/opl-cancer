#!/usr/bin/env bash
# OPL for Cancer — skill-form wrapper for Wave 1 retrieval pipeline
# Wraps the underlying Wave1Runner via the opl_cancer.orchestrator module.
# Usage: ./scripts/run_wave1.sh <patient_code> [extra args...]
exec python -m opl_cancer.orchestrator.wave1_runner "$@"
