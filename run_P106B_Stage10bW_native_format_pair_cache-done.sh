#!/usr/bin/env bash
# Authorized26Oct2026: CPU-only, write-once paired native cache preparation.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export CUDA_VISIBLE_DEVICES=
export TL_RUNLOG_GIT_SCOPE=codex-safe
export TL_WANDB_AUTO=0
policy="handoff/audit/oct26_research/native_format_pair_policy.json"
identity="C76D9CC964D05BF6315EAF1724EAEFF86B324D65BB96F797883032C3592A65BA"
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -I -B -X utf8 scripts/p106b_native_format_pair.py --check-only --policy "$policy" --policy-sha256 "$identity"
fi
exec timeout --signal=TERM --kill-after=10s 7260s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage10bW_native_format_pair_cache -- "$python_bin" -B -X utf8 -c '
import subprocess,sys
from scripts.p106b_stage_receipt import pipeline
py,policy,identity=sys.argv[1:4]
base=[py,"-I","-B","-X","utf8","scripts/p106b_native_format_pair.py","--policy",policy,"--policy-sha256",identity]
phases=[
 ("REGRESSION",[py,"-I","-B","-X","utf8","scripts/test_p106b_native_format_pair.py"]),
 ("PREFLIGHT",base+["--check-only"]),
 ("EXECUTE",base+["--execute","--output","data_cache/p106b_native_format_pair_v1_20261026_s1337","--max-wall-sec","7200","--deadline","2026-10-26T00:00:00Z"])]
def launch(command):return subprocess.run(command,stdin=subprocess.DEVNULL).returncode
raise SystemExit(pipeline(phases,launch,lambda line:print(line,flush=True),experiment="P106B_Stage10bW_native_format_pair_cache")["returncode"])
' "$python_bin" "$policy" "$identity"

