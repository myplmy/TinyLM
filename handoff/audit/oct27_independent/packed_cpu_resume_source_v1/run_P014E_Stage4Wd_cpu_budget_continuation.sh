#!/usr/bin/env bash
# Continue only the previously NOT_RUN full packed CPU suite, with a new5400s cap.
# Reuse frozen export/reference receipts; no re-export, source edit or smaller set.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export CUDA_VISIBLE_DEVICES="" TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
common=(--mode deploy-cpu --max-wall-sec 5400 --profile handoff/audit/oct27_independent/packed_cpu_continuation_profile_v1.json --profile-sha256 8CF1A2408C8A02E5D545A8A99FB63BE44F6336135B66959E370F9C1941B8EF9D)
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -X utf8 scripts/diag_p014e_deploy_resume.py "${common[@]}" --check-only
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4Wd_cpu_budget_continuation --num 099 --note 'Previous Stage4Wb parent5234 exit8 is preserved: full CPU suite NOT_RUN because1789.356s forecast exceeded20min cap. This separate root-authorized90min CPU1 continuation keeps all4 prompts, fixed16,3 repeats,natural32 and same tolerances. No source/oldreceipt/CP edits or baseline rerun. No GPU/training/new300M. Two-variant forecast plus600s reserve must fit; shared host load disclosed.'
timeout --signal=TERM --kill-after=20s 5460s "$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4Wd_cpu_budget_continuation --num 099 -- "$python_bin" -B -X utf8 scripts/diag_p014e_deploy_resume.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4Wd_cpu_budget_continuation --num 099 --note "Final continuation exit=$result. New5400s execution and prior1200s metadata contract are distinct. Technical0, budgetHOLD8 and error9 are separate; oldHOLD is never overwritten or relabeled. Read new raw answers, same-device oracle, bytes and release proof."
exit "$result"
