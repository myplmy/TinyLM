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

tl_smoke_policy=""
if "$python_bin" scripts/queue_menu_linux.py --has-smoke "$tl_pick"; then
    printf '%s\n' 'smoke failure policy:'
    printf '%s\n' '  1) stop  - stop immediately and fail the queue'
    printf '%s\n' '  2) collect - run the remaining entries, then fail the queue'
    printf '%s\n' '  3) warn  - run the remaining entries and do not fail the queue for smoke alone'
    read -r -p 'choose 1, 2, or 3: ' tl_smoke_choice
    case "$tl_smoke_choice" in
        1) tl_smoke_policy="stop" ;;
        2) tl_smoke_policy="collect" ;;
        3) tl_smoke_policy="warn" ;;
        *)
            printf '%s\n' '[queue] invalid smoke policy; cancelled.' >&2
            exit 0
            ;;
    esac
else
    tl_detect_rc=$?
    if [[ "$tl_detect_rc" -ne 1 ]]; then
        printf '[queue] unable to inspect the smoke selection (exit %s); cancelled.\n' "$tl_detect_rc" >&2
        exit 8
    fi
fi

tl_build=("$python_bin" scripts/queue_menu_linux.py --build "$tl_pick")
if [[ -n "$tl_smoke_policy" ]]; then
    tl_build+=(--smoke-policy "$tl_smoke_policy")
fi
if ! "${tl_build[@]}"; then
    printf '%s\n' '[queue] plan validation failed; nothing was run.' >&2
    exit 8
fi
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
