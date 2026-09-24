#!/usr/bin/env bash
# P100 Stage0W: raw bilingual answer and format baseline on two existing models.
# About 0.3 h, GPU inference only; no protected benchmark or training.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 092 --name P100_Stage0W_capability_baseline --note "P100: compare same prompt in base and Q/A form on existing control/FineWeb2 models. These models have different tokenizers and pools; descriptive only."
"$python_bin" scripts/runlog.py --num 092 --name P100_Stage0W_capability_baseline --   "$python_bin" -B -X utf8 scripts/eval_p100_capability_panel.py     --model p097_ctrl_v2,ko-en-control-v2,dense     --model p097_fw2,ko-en-fw2,dense     --preset m100s10 --tokens 300M     --out runs/bench/p100_stage0w_capability_baseline.jsonl --max-new 80
rc=$?
if [ "$rc" -ne 0 ]; then
  printf '%s\n' "[FAIL] P100 Stage0W rc=$rc; inspect the test_result log" >&2
  exit "$rc"
fi
"$python_bin" scripts/runlog.py --num 092 --name P100_Stage0W_capability_baseline --note "Review full answers per ability and form; no automatic intelligence score. P097 Stage4W common benchmark remains separately required."
