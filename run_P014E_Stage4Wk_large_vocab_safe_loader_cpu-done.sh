#!/usr/bin/env bash
# Packed-only CPU inference; no original checkpoint tensor reload.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
common=(--mode deploy-cpu --max-wall-sec 5400 --profile handoff/audit/oct27_independent/large_vocab_resume_profile_v1.json --profile-sha256 F07E18A2927C5F01B515AA135D328293B949CFCFBBE1482B8EF07685929556BC)
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -X utf8 scripts/diag_p014e_large_vocab_resume.py "${common[@]}" --check-only
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4Wk_large_vocab_cpu_deploy --num 099 --note 'New CPU1 packed-only from closed same-source export/reference. RealV262144 table: lookup selected rows/head1024; body4096 originalscales. Same4contexts/16numericpositions/forced16x3/observer1/natural32; retain tolerance and compare IDs/stops. Prefill/decode cost separate;5400s cap before27Oct17KST. No originalCP tensor reload/new300M/training/cleanup-data/install/download.'
timeout --signal=TERM --kill-after=20s 5460s "$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4Wk_large_vocab_cpu_deploy --num 099 -- "$python_bin" -B -X utf8 scripts/diag_p014e_large_vocab_resume.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4Wk_large_vocab_cpu_deploy --num 099 --note "Final CPU packed-only exit=$result. Storage/KV/RSS/actualanswers separated; technical0 is not speed/quality/whole40MiB/directKL adoption."
exit "$result"
