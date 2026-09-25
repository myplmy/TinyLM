#!/usr/bin/env bash
# P100: audit saved 36 answers without loading a model or claiming accuracy.
# Cost: about 0.1 h CPU, GPU 0. Abort if the fixture or original file fails.
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
name=P100_Stage0bW_saved_answer_triage
"$python_bin" scripts/runlog.py --num 092 --name P100_Stage0bW_saved_answer_triage --note "P100 Stage0bW: read exact saved 36-row JSONL; strict leading-answer/JSON signals only, not accuracy."
"$python_bin" scripts/runlog.py --num 092 --name "$name" -- "$python_bin" -B -X utf8 scripts/diag_p100_answer_triage.py --self-test
"$python_bin" scripts/runlog.py --num 092 --name "$name" -- "$python_bin" -B -X utf8 scripts/diag_p100_answer_triage.py --input-jsonl runs/bench/p100_stage0w_capability_baseline.jsonl
"$python_bin" scripts/runlog.py --num 092 --name "$name" --note "Read result 092 with the raw answers. A strict signal is not an intelligence or dataset-effect score."
