#!/usr/bin/env bash
# P102A Stage1W: T0/T1 eval/save cadence only, same 100M draw and 600M pool.
# About 1.4 GPU-h combined on one 16 GiB GPU; not a quality/adoption gate.
# Independent arms continue after one failure; pair needs both successful JSON files.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
for required in runs/ckpt/m100_ko-en_300M_dense.pt data_cache/ko-en_600000000/meta.json data_cache/ko-en_600000000/train.bin data_cache/ko-en_600000000/val.bin data_cache/tok-ko-en-32768.json; do
    if [[ ! -f "$required" ]]; then
        printf "[STOP] missing T1 preflight asset: %s\n" "$required" >&2
        exit 2
    fi
done
for tag in dense_p102a_t0_s1337 dense_p102a_t1_s1337; do
    for suffix in runs/logs/m100s12_ko-en_100M_${tag}.json runs/ckpt/m100s12_ko-en_100M_${tag}.pt runs/ckpt/m100s12_ko-en_100M_${tag}_best.pt; do
        if [[ -e "$suffix" || -L "$suffix" ]]; then
            printf "[STOP] T1 output already exists: %s\n" "$suffix" >&2
            exit 2
        fi
    done
done
"$python_bin" scripts/runlog.py --num 093 --name P102A_Stage1W_t1_evalsave_pair --note "Matched 100M, same seed/parent/600M pool. Only eval/save cadence differs. Single order is descriptive."
"$python_bin" scripts/runlog.py --num 093 --name P102A_Stage1W_t0 --note "Control eval100/save0. Read phase wall and whole wall separately; runlog handles post-run W&B."
first_rc=0
"$python_bin" scripts/runlog.py --num 093 --name P102A_Stage1W_t0 -- "$python_bin" run100m.py train \
    --preset m100s12 --arch dense --data ko-en --tokens 100M --ckpt-tokens 300M \
    --pool-tokens 600M --exact-cache --steps 763 --micro-bs 8 --accum 16 --seq 1024 \
    --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 \
    --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role \
    --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 \
    --matrix-weight-decay 0 --eval-every 100 --save-every 0 \
    --tag dense_p102a_t0_s1337 || first_rc=$?
sleep 15
"$python_bin" scripts/runlog.py --num 093 --name P102A_Stage1W_t1 --note "Candidate eval500/save1000. In-run val crops differ from control; fixed-crop quality is separate."
second_rc=0
"$python_bin" scripts/runlog.py --num 093 --name P102A_Stage1W_t1 -- "$python_bin" run100m.py train \
    --preset m100s12 --arch dense --data ko-en --tokens 100M --ckpt-tokens 300M \
    --pool-tokens 600M --exact-cache --steps 763 --micro-bs 8 --accum 16 --seq 1024 \
    --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 \
    --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role \
    --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 \
    --matrix-weight-decay 0 --eval-every 500 --save-every 1000 \
    --tag dense_p102a_t1_s1337 || second_rc=$?
if [[ "$first_rc" -ne 0 || "$second_rc" -ne 0 ]]; then
    "$python_bin" scripts/runlog.py --num 093 --name P102A_Stage1W_t1_evalsave_pair --note "One or both arms failed; retain both logs and do not infer T1 speed or quality."
    exit 4
fi
"$python_bin" scripts/runlog.py --num 093 --name P102A_Stage1W_t1_evalsave_pair -- "$python_bin" -B -X utf8 scripts/diag_p102a_t1_wall_contract.py \
    --baseline runs/logs/m100s12_ko-en_100M_dense_p102a_t0_s1337.json \
    --candidate runs/logs/m100s12_ko-en_100M_dense_p102a_t1_s1337.json
rc=$?
if [[ "$rc" -ne 0 ]]; then
    printf "[FAIL] T1 JSON condition/phase contract rc=%s\n" "$rc" >&2
    exit "$rc"
fi
"$python_bin" scripts/runlog.py --num 093 --name P102A_Stage1W_t1_evalsave_pair --note "Use identical fixed-crop paired evaluation before any quality claim. One run order cannot establish stable speedup."
