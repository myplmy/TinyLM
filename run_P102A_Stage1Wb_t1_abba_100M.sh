#!/usr/bin/env bash
# P102A Stage1Wb: user-run ABBA order control, four fresh 100M dense runs.
# Original T0->T1 pair is historical context, not one of these four same-session controls.
# Expected training 4x~31 min plus fixed-crop evaluation; reserve 2.5 h, 20 GiB free.
# No Codex GPU/model execution. A valid speed-screen negative returns 8.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
parent=runs/ckpt/m100_ko-en_300M_dense.pt
cache=data_cache/ko-en_600000000
if [[ ! -f "$parent" || -L "$parent" || ! -f "$cache/meta.json" || ! -f "$cache/val.bin" ]]; then
  printf '%s\n' '[STOP] exact dense parent or existing ko-en 600M val cache is absent; no download/build.'
  exit 9
fi
available_kib="$(df -Pk "$repo_root" | awk 'NR==2 {print $4}')"
if [[ -z "$available_kib" || "$available_kib" -lt 20971520 ]]; then
  printf '[STOP] need at least 20 GiB free for four final/best checkpoints; available KiB=%s\n' "$available_kib"
  exit 9
fi
for tag in dense_p102a_t0abba_a_s1337 dense_p102a_t1abba_a_s1337 dense_p102a_t1abba_b_s1337 dense_p102a_t0abba_b_s1337; do
  stem="m100s12_ko-en_100M_dense_$tag"
  best_path="runs/ckpt/$stem""_best.pt"
  if [[ -e "runs/logs/$stem.json" || -e "runs/ckpt/$stem.pt" || -e "$best_path" ]]; then
    printf '[STOP] ABBA write-once tag already has an output: %s\n' "$stem"
    exit 9
  fi
done
crop_out=runs/bench/p102a_stage1wb_abba_crops.json
if [[ -e "$crop_out" || -L "$crop_out" ]]; then
  printf '[STOP] fixed-crop output exists: %s\n' "$crop_out"
  exit 9
fi
"$python_bin" scripts/runlog.py --name P102A_Stage1Wb_abba_preflight -- "$python_bin" -B -X utf8 scripts/diag_p102a_t1_abba.py --self-test

rc_t0a=0
"$python_bin" scripts/runlog.py --name P102A_Stage1Wb_t0a -- "$python_bin" -B -X utf8 run100m.py train \
  --preset m100s12 --arch dense --data ko-en --tokens 100M --ckpt-tokens 300M \
  --pool-tokens 600M --exact-cache --steps 763 --micro-bs 8 --accum 16 --seq 1024 \
  --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 \
  --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role \
  --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 \
  --matrix-weight-decay 0 --eval-every 100 --save-every 0 --tag dense_p102a_t0abba_a_s1337 || rc_t0a=$?

rc_t1a=0
"$python_bin" scripts/runlog.py --name P102A_Stage1Wb_t1a -- "$python_bin" -B -X utf8 run100m.py train \
  --preset m100s12 --arch dense --data ko-en --tokens 100M --ckpt-tokens 300M \
  --pool-tokens 600M --exact-cache --steps 763 --micro-bs 8 --accum 16 --seq 1024 \
  --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 \
  --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role \
  --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 \
  --matrix-weight-decay 0 --eval-every 500 --save-every 1000 --tag dense_p102a_t1abba_a_s1337 || rc_t1a=$?

rc_t1b=0
"$python_bin" scripts/runlog.py --name P102A_Stage1Wb_t1b -- "$python_bin" -B -X utf8 run100m.py train \
  --preset m100s12 --arch dense --data ko-en --tokens 100M --ckpt-tokens 300M \
  --pool-tokens 600M --exact-cache --steps 763 --micro-bs 8 --accum 16 --seq 1024 \
  --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 \
  --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role \
  --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 \
  --matrix-weight-decay 0 --eval-every 500 --save-every 1000 --tag dense_p102a_t1abba_b_s1337 || rc_t1b=$?

rc_t0b=0
"$python_bin" scripts/runlog.py --name P102A_Stage1Wb_t0b -- "$python_bin" -B -X utf8 run100m.py train \
  --preset m100s12 --arch dense --data ko-en --tokens 100M --ckpt-tokens 300M \
  --pool-tokens 600M --exact-cache --steps 763 --micro-bs 8 --accum 16 --seq 1024 \
  --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 \
  --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role \
  --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 \
  --matrix-weight-decay 0 --eval-every 100 --save-every 0 --tag dense_p102a_t0abba_b_s1337 || rc_t0b=$?
if [[ "$rc_t0a" -eq 0 ]]; then scripts/shell/tool_wandb_push.sh dense_p102a_t0abba_a_s1337; fi
if [[ "$rc_t1a" -eq 0 ]]; then scripts/shell/tool_wandb_push.sh dense_p102a_t1abba_a_s1337; fi
if [[ "$rc_t1b" -eq 0 ]]; then scripts/shell/tool_wandb_push.sh dense_p102a_t1abba_b_s1337; fi
if [[ "$rc_t0b" -eq 0 ]]; then scripts/shell/tool_wandb_push.sh dense_p102a_t0abba_b_s1337; fi

if [[ "$rc_t0a" -ne 0 || "$rc_t1a" -ne 0 || "$rc_t1b" -ne 0 || "$rc_t0b" -ne 0 ]]; then
  printf '[FAIL] ABBA train exits T0a=%s T1a=%s T1b=%s T0b=%s; pair and quality NOT_RUN\n' "$rc_t0a" "$rc_t1a" "$rc_t1b" "$rc_t0b"
  exit 9
fi
panel_rc=0
"$python_bin" scripts/runlog.py --name P102A_Stage1Wb_abba_wall -- "$python_bin" -B -X utf8 scripts/diag_p102a_t1_abba.py \
  --t0a runs/logs/m100s12_ko-en_100M_dense_p102a_t0abba_a_s1337.json \
  --t1a runs/logs/m100s12_ko-en_100M_dense_p102a_t1abba_a_s1337.json \
  --t1b runs/logs/m100s12_ko-en_100M_dense_p102a_t1abba_b_s1337.json \
  --t0b runs/logs/m100s12_ko-en_100M_dense_p102a_t0abba_b_s1337.json || panel_rc=$?
quality_rc=0
"$python_bin" scripts/runlog.py --name P102A_Stage1Wb_abba_fixed_crops -- "$python_bin" -B -X utf8 scripts/paired_eval.py \
  --preset m100s12 --data ko-en --tokens 600M --ckpt-tokens 100M \
  --models dense_p102a_t0abba_a_s1337 dense_p102a_t1abba_a_s1337 \
           dense_p102a_t1abba_b_s1337 dense_p102a_t0abba_b_s1337 \
  --device cuda --seq 1024 --micro-bs 8 --dump-crops "$crop_out" || quality_rc=$?
if [[ "$quality_rc" -ne 0 ]]; then
  printf '[FAIL] fixed-crop evaluation exit=%s; ABBA result alone cannot authorize T1 adoption\n' "$quality_rc"
  exit "$quality_rc"
fi
if [[ "$panel_rc" -ne 0 ]]; then
  printf '[GATE] ABBA wall panel exit=%s; fixed-crop evidence was still collected\n' "$panel_rc"
  exit "$panel_rc"
fi
"$python_bin" scripts/runlog.py --name P102A_Stage1Wb_abba_summary --note "ABBA host-wall candidate only; same fixed-crop quality and 1-core deployment remain separate adoption gates."
