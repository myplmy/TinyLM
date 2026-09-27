#!/usr/bin/env bash
# P106 Stage0pW: bounded full-GPU teacher and two P076 parent+compile student resource arms.
# Current-user authorization only; no real corpus, SFT, long training, or checkpoint writes.
# About 0.8 GPU-hour upper budget including two first compilations; free GPU >=14 GiB.
# Each arm runs in separate processes. A negative resource gate does not erase the other arm.
set -u -o pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
"$python_bin" scripts/runlog.py --name P106_Stage0pW_full_teacher_accum --num 098 --note \
  'Same 131072 tokens/update, full-GPU Bonsai teacher. A=P076 parent+compile micro4/accum32/no-ckpt; B=micro8/accum16/ckpt-on. Two tiny synthetic updates each. VRAM only; SFT/teacher truth NOT_RUN.'
"$python_bin" scripts/runlog.py --name P106_Stage0pW_full_teacher_accum --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_full_coload_accum.py --self-test || exit 9
"$python_bin" scripts/runlog.py --name P106_Stage0pW_full_teacher_accum --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_full_coload_accum.py --check-only --micro-bs 4 --accum 32 --no-ckpt || exit 9
"$python_bin" scripts/runlog.py --name P106_Stage0pW_full_teacher_accum --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_full_coload_accum.py --check-only --micro-bs 8 --accum 16 || exit 9
errors=0
negative=0
"$python_bin" scripts/runlog.py --name P106_Stage0pW_full_teacher_accum --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_full_coload_accum.py --micro-bs 4 --accum 32 --no-ckpt
rc=$?
if [[ "$rc" -eq 8 ]]; then negative=$((negative + 1)); elif [[ "$rc" -ne 0 ]]; then errors=$((errors + 1)); fi
"$python_bin" scripts/runlog.py --name P106_Stage0pW_full_teacher_accum --num 098 --note \
  'A collected; after process cleanup, B uses micro8/accum16 with activation checkpoint ON. No model quality interpretation.'
"$python_bin" scripts/runlog.py --name P106_Stage0pW_full_teacher_accum --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_full_coload_accum.py --micro-bs 8 --accum 16
rc=$?
if [[ "$rc" -eq 8 ]]; then negative=$((negative + 1)); elif [[ "$rc" -ne 0 ]]; then errors=$((errors + 1)); fi
if [[ "$errors" -ne 0 ]]; then
  printf '[FAIL] P106 Stage0pW execution failures=%s, resource negatives=%s; inspect both preserved rows\n' "$errors" "$negative" >&2
  exit 9
fi
if [[ "$negative" -ne 0 ]]; then
  printf '[GATE NEGATIVE] P106 Stage0pW resource negatives=%s; no long co-training claim\n' "$negative"
  exit 8
fi
printf '%s\n' '[COLLECTED] P106 Stage0pW two tiny resource arms. Full SFT, teacher accuracy and long-run stability NOT_RUN.'
