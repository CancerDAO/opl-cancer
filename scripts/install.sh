#!/usr/bin/env bash
# OPL for Cancer — one-time installer.
#
# Invoked automatically after `npx skills add CancerDAO/opl-cancer-skill` (or
# manually after `git clone`).  Idempotent — safe to re-run.
#
# Steps:
#   1. Verify Python ≥ 3.11
#   2. Install the opl_cancer package in editable mode (so the skill scripts
#      can `import opl_cancer` directly).
#   3. Create the patient root directory (default ~/CancerDAO/patients/).
#   4. Copy .env.example to .env if .env doesn't exist (so the user knows what
#      keys to fill in).
#   5. Print preflight verdict so the user knows what's missing.
#
# Does NOT install Docker / bixbench image — those are optional Wave-3 deps.
# See compute/README.md for that.

set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

echo "[opl-cancer] installer — repo root: ${REPO_ROOT}"

# ─── 1. Python check ──────────────────────────────────────────────────────
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not found on PATH. Install Python 3.11+ first."
    exit 1
fi

PYV=$(python3 -c 'import sys; print("{}.{}".format(sys.version_info.major, sys.version_info.minor))')
PYV_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYV_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

if [ "${PYV_MAJOR}" -lt 3 ] || { [ "${PYV_MAJOR}" -eq 3 ] && [ "${PYV_MINOR}" -lt 11 ]; }; then
    echo "ERROR: Python 3.11+ required; found ${PYV}"
    echo "       Try: pyenv install 3.11.10 && pyenv local 3.11.10"
    exit 1
fi
echo "  [ok] Python ${PYV}"

# ─── 2. Editable install ─────────────────────────────────────────────────
if python3 -c 'import opl_cancer' 2>/dev/null; then
    INSTALLED_VER=$(python3 -c 'from opl_cancer.cli import VERSION; print(VERSION)')
    echo "  [ok] opl_cancer ${INSTALLED_VER} already importable"
else
    echo "  [..] installing opl_cancer in editable mode"
    python3 -m pip install --quiet -e "${REPO_ROOT}"
    echo "  [ok] opl_cancer installed (editable)"
fi

# ─── 3. Patient root ─────────────────────────────────────────────────────
PATIENT_ROOT="${OPL_PATIENT_DATA_ROOT:-${HOME}/CancerDAO/patients}"
mkdir -p "${PATIENT_ROOT}"
echo "  [ok] patient root: ${PATIENT_ROOT}"

# ─── 4. .env scaffold ────────────────────────────────────────────────────
if [ ! -f "${REPO_ROOT}/.env" ] && [ -f "${REPO_ROOT}/.env.example" ]; then
    cp "${REPO_ROOT}/.env.example" "${REPO_ROOT}/.env"
    echo "  [ok] copied .env.example → .env (edit to add your API keys)"
fi

# ─── 5. Preflight ────────────────────────────────────────────────────────
echo ""
echo "[opl-cancer] running preflight:"
python3 "${REPO_ROOT}/scripts/cli.py" preflight || true

echo ""
echo "[opl-cancer] install complete."
echo ""
echo "Next step: in Claude Code, trigger the skill by saying something like"
echo "  「我有 NSCLC,想要 AI team 帮我分析」"
echo "  「OPL,帮我跑一次 hypothesis tournament」"
echo "  「founder mode against cancer — 给我我的 AI 科研团队」"
