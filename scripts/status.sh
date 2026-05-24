#!/usr/bin/env bash
# OPL for Cancer — skill-form wrapper for `opl-cancer status`
exec python -m opl_cancer.cli status "$@"
