#!/usr/bin/env bash
# P102A Stage0bW: tiny CPU-model S1 loss-first correctness gate.
# New stage because S1 code is now wired after Stage0W math/T1 JSON fixtures.
# About 0.1 h CPU; no training corpus, GPU quality or speed adoption.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 093 --name P102A_Stage0bW_loss_first_model_gate --note "Compare full CE vs loss-first on the same tiny model: loss, all gradients, one optimizer update. A CPU function PASS is not a GPU speed PASS."
"$python_bin" scripts/runlog.py --num 093 --name P102A_Stage0bW_loss_first_model_gate -- "$python_bin" -B -X utf8 scripts/diag_p102a_model_loss_first.py
