#!/usr/bin/env bash
# Same old G270Tfull CP; export and independent CPU/CUDA references, no training.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
common=(--profile handoff/audit/oct27_independent/large_vocab_deploy_profile_v3.json --profile-sha256 82C18522085C8D58F821FCB93FBFE95CD34341B88C214E061CF9380E5FCA6514)
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -X utf8 scripts/diag_p014e_large_vocab_deploy.py --mode export --max-wall-sec 900 "${common[@]}" --check-only
fi
aggregate=0
for mode in export baseline-cpu baseline-cuda; do
    case "$mode" in baseline-cpu) cap=1200 ;; *) cap=900 ;; esac
    "$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4Wg_large_vocab_export_baseline --num 99 --note "phase=$mode cap=$cap. Exact old G270Tfull/V262144/E256/tied20 CP; CPU1 original quantizer then device transfer. New payloads only, same four128/512 plus16x3/natural32. EOS1/extra-image-ID range guard; historical training tokenizerSHA unknown. No new300M/training/install/download/data cleanup."
    timeout --signal=TERM --kill-after=20s "$((cap+60))s" "$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4Wg_large_vocab_export_baseline --num 99 -- "$python_bin" -B -X utf8 scripts/diag_p014e_large_vocab_deploy.py --mode "$mode" --max-wall-sec "$cap" "${common[@]}" --execute
    result=$?
    "$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4Wg_large_vocab_export_baseline --num 99 --note "Final phase=$mode actual_exit=$result; full0/HOLD8/error9 distinct; source/CP/cleanup verified in JSON, no quality claim."
    if [[ "$result" != 0 ]]; then aggregate="$result"; fi
    if [[ "$mode" == export && "$result" != 0 ]]; then exit "$aggregate"; fi
done
exit "$aggregate"
