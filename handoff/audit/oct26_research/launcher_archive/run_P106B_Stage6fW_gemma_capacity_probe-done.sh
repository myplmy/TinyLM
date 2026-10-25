#!/usr/bin/env bash
# Authorized26Oct2026 resource observation only; four generation requests.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe
export TL_WANDB_AUTO=0
probe="handoff/audit/oct26_research/probe_gemma_capacity.py"
identity="20E9CC072993D530655C875C81E464E760D1261F34FE3645E1B40620558D4FA5"
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -I -B -X utf8 "$probe" --check-only --source-sha256 "$identity"
fi
exec "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage6fW_gemma_capacity_probe -- "$python_bin" -B -X utf8 -c '
import subprocess,sys
from pathlib import Path
from scripts.p106b_stage_receipt import pipeline
py=sys.argv[1]; source=sys.argv[2]
base=[py,"-I","-B","-X","utf8","handoff/audit/oct26_research/probe_gemma_capacity.py"]
phases=[
 ("REGRESSION",[py,"-I","-B","-X","utf8","scripts/test_p106b_gemma_capacity_probe.py"]),
 ("PREFLIGHT",base+["--check-only","--source-sha256",source]),
 ("EXECUTE",["timeout","--signal=TERM","--kill-after=5s","595s"]+base+
  ["--execute","--output",str(Path.cwd()/"test_result/evidence/p106b_gemma_capacity_v1_20261026_roota"),
   "--source-sha256",source,"--max-wall-sec","590","--deadline","2026-10-26T08:00:00Z"])]
def launch(command):
    return subprocess.run(command,stdin=subprocess.DEVNULL).returncode
raise SystemExit(pipeline(phases,launch,lambda line:print(line,flush=True),
                 experiment="P106B_Stage6fW_gemma_capacity_probe")["returncode"])
' "$python_bin" "$identity"
