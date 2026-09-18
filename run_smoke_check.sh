#!/usr/bin/env bash
# Linux/WSL companion for run_smoke_check.bat.
# This is a user-run GPU/model gate. Codex static checks must use --check instead.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/shell/tinylm_env.sh
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"

if [[ ! -f run100m.py ]]; then
    printf '%s\n' '[STOP] run this from the TinyLM working folder.' >&2
    exit 9
fi
python_bin="$(tinylm_python)" || exit $?

export TL_OUTDIR=smoketest_logs
export TL_LOGNAME=smoke
export TL_NOPAUSE=1
export PYTHONIOENCODING=utf-8

"$python_bin" scripts/smoke_module.py --name smoke
module_rc=$?
if [[ "$module_rc" -ne 0 ]]; then
    printf '%s\n' '[STOP] POSIX smoke adapter rejected the canonical BAT module.' >&2
    unset TL_OUTDIR TL_LOGNAME TL_NOPAUSE
    exit "$module_rc"
fi

printf '\n'
"$python_bin" scripts/runlog.py --name smoke --     "$python_bin" scripts/summarize_smoke.py
summary_rc=$?
if [[ "$summary_rc" -ne 0 ]]; then
    printf '%s\n' '[WARN] summarize_smoke reported a failing arm or contract.' >&2
fi

"$python_bin" scripts/runlog.py --name smoke --note     "================================================================="     "VERDICT: the single answer is the last line of the SUMMARY above,"     "  which joins BOTH checks - every arm exit code and the field contract."     "  Neither one alone is the verdict."     "================================================================="     "done."
note_rc=$?

unset TL_OUTDIR TL_LOGNAME TL_NOPAUSE
if [[ "$summary_rc" -ne 0 ]]; then
    exit "$summary_rc"
fi
exit "$note_rc"
