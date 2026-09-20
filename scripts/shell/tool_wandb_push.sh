#!/usr/bin/env bash
# Push one completed full-training JSON to W&B without changing experiment rc.
# Network/key failures are warnings: runs/logs JSON remains the source of truth.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

tag="${1:-${TL_WB_TAG:-}}"
project="${TL_WB_PROJECT:-tinylm}"
if [[ -z "$tag" ]]; then
  printf '%s\n' '[STOP] wandb post-run push requires a raw experiment tag.' >&2
  printf '%s\n' '       Usage: scripts/shell/tool_wandb_push.sh <tag>' >&2
  exit 2
fi

printf '[wandb] project=%s exact_tag=%s\n' "$project" "$tag"
if ! "$python_bin" scripts/wandb_sync.py --push --project "$project" \
  --tag "$tag" --tag-exact --expect-count 1; then
  printf '%s\n' '[WARN] wandb push failed; training JSON is intact and the launcher continues.' >&2
fi
exit 0
