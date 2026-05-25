#!/usr/bin/env bash
# Post-run orchestration: dedup-merge → score → render unified report.
# Run after both surfaces (CRC + NCCN) have a raw_outputs_v1.jsonl (initial)
# and raw_outputs.jsonl (resumed) in their out-dirs.

set -euo pipefail

MTB_BENCH="${MTB_BENCH:-/Users/baozhiwei/work/mtb-bench}"
ADAPTER="$(dirname "$(realpath "$0")")"
CRC_DIR="${CRC_DIR:-${MTB_BENCH}/runs/mtb_vs_opl_n30_crc}"
NCCN_DIR="${NCCN_DIR:-${MTB_BENCH}/runs/mtb_vs_opl_n30_nccn}"
REPORT_OUT="${REPORT_OUT:-/Users/baozhiwei/work/opl-cancer/benchmark/reports/REPORT_MTB_vs_OPL.md}"

echo "==> dedup-merging CRC"
python3 "$ADAPTER/dedup_merge.py" \
  --out "$CRC_DIR/raw_outputs_final.jsonl" \
  "$CRC_DIR/raw_outputs_v1.jsonl" "$CRC_DIR/raw_outputs.jsonl"

echo "==> dedup-merging NCCN"
python3 "$ADAPTER/dedup_merge.py" \
  --out "$NCCN_DIR/raw_outputs_final.jsonl" \
  "$NCCN_DIR/raw_outputs_v1.jsonl" "$NCCN_DIR/raw_outputs.jsonl"

echo "==> scoring CRC"
cd "$MTB_BENCH/SBT_Benchmark"
python3 scripts/score_model_outputs.py \
  "$CRC_DIR/raw_outputs_final.jsonl" \
  --out-dir "$CRC_DIR/scores"

echo "==> scoring NCCN"
python3 scripts/score_model_outputs.py \
  "$NCCN_DIR/raw_outputs_final.jsonl" \
  --out-dir "$NCCN_DIR/scores"

echo "==> rendering unified report"
python3 "$ADAPTER/render_mtb_vs_opl_report.py" \
  --crc-scores  "$CRC_DIR/scores" \
  --nccn-scores "$NCCN_DIR/scores" \
  --crc-raw     "$CRC_DIR/raw_outputs_final.jsonl" \
  --nccn-raw    "$NCCN_DIR/raw_outputs_final.jsonl" \
  --out         "$REPORT_OUT"

echo "==> done: $REPORT_OUT"
