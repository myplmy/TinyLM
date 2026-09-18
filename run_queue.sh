#!/usr/bin/env bash
# TinyLM Linux/WSL interactive queue. experiments.tsv remains the one metadata source.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/shell/tinylm_env.sh
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"

if [[ ! -f run100m.py || ! -f experiments.tsv ]]; then
    printf '%s\n' '[STOP] run_queue.sh must live in the TinyLM repository root.' >&2
    exit 9
fi

python_bin="$(tinylm_python)" || exit $?

if [[ -n "${TL_EXPAND:-}" ]]; then
    export PYTORCH_ALLOC_CONF=expandable_segments:True
    printf '%s\n' '[queue] PYTORCH_ALLOC_CONF=expandable_segments:True is ON'
    printf '%s\n' '[queue] peak reserved is not comparable with the existing table.'
fi

"$python_bin" scripts/queue_menu_linux.py --list || exit 8
printf '\n'
read -r -p 'ids or shell names, in order, space separated: ' tl_pick
if [[ -z "$tl_pick" ]]; then
    printf '%s\n' '[queue] empty selection; nothing was run.'
    exit 0
fi

"$python_bin" scripts/queue_menu_linux.py --build "$tl_pick" || exit 0
read -r -p 'start now, y or n: ' tl_go
if [[ "$tl_go" != "y" && "$tl_go" != "Y" ]]; then
    printf '%s\n' '[queue] cancelled; nothing was run.'
    exit 0
fi

export TL_NOPAUSE=1
printf '\n[queue] started\n'
date
bash runs/_queue_plan.sh
tl_rc=$?
unset TL_NOPAUSE

printf '\n[queue] finished\n'
date
printf '%s\n' 'Logs: test_result for experiments, smoketest_logs for smoke gates.'
if [[ "$tl_rc" -ne 0 ]]; then
    printf '[queue] plan returned %s - inspect the logs above.\n' "$tl_rc" >&2
fi
exit "$tl_rc"
