#!/usr/bin/env bash
# P060B Stage1W: 250-step off/on training speed and reserved-memory gate.
# 32.768M tokens are below the 50M W&B threshold; do not upload these probes.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 088 --name P060B_Stage1W_sdpa_gqa_training_gate \
  --note "P060B Stage1W: same 250-step Muon RMS4 recipe, only sdpa_gqa off/on; speed and reserved memory only" \
  || exit $?

failures=0
"$python_bin" scripts/runlog.py --num 088 --name P060B_Stage1W_sdpa_gqa_training_gate -- \
  "$python_bin" run100m.py train --arch dense --preset m100s10 --data ko-en \
  --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 \
  --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.60 --decay-frac 0.20 \
  --eval-every 250 --optimizer muon --muon-scale rms --muon-lr-mult 4 \
  --matrix-weight-decay 0 --cla-group 2 --no-ckpt --compile --seed 1337 \
  --tag p060b_s1w_off250
off_rc=$?
if (( off_rc != 0 )); then
  printf '%s\n' '[WARN] P060B off arm failed; continuing' >&2
  failures=$((failures + 1))
fi

"$python_bin" scripts/runlog.py --num 088 --name P060B_Stage1W_sdpa_gqa_training_gate -- \
  "$python_bin" run100m.py train --arch dense --preset m100s10 --data ko-en \
  --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 \
  --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.60 --decay-frac 0.20 \
  --eval-every 250 --optimizer muon --muon-scale rms --muon-lr-mult 4 \
  --matrix-weight-decay 0 --cla-group 2 --sdpa-gqa --no-ckpt --compile --seed 1337 \
  --tag p060b_s1w_on250
on_rc=$?
if (( on_rc != 0 )); then
  printf '%s\n' '[WARN] P060B on arm failed; continuing' >&2
  failures=$((failures + 1))
fi

if (( failures > 0 )); then
  printf '[FAIL] P060B Stage1W training failures=%d; pair gate not run\n' "$failures" >&2
  exit 4
fi

exec "$python_bin" scripts/runlog.py --num 088 --name P060B_Stage1W_sdpa_gqa_training_gate -- \
  "$python_bin" scripts/diag_sdpa_gqa_training_pair.py \
  --off-tag p060b_s1w_off250 --on-tag p060b_s1w_on250 \
  --max-speed-ratio 1.05 --min-memory-reduction 0.10
