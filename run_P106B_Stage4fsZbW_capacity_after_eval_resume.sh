#!/usr/bin/env bash
# Authorized26Oct2026: same V3 production after the two full-arm evaluations.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe
export TL_WANDB_AUTO=0
entry="handoff/audit/oct26_research/resume_gemma_capacity.py"
identity="1B9705BE3995B6EDD533B75787293743D2E0DCB154AF0B979A3197A61590634B"
review="2D0C3FFC8558AA151311DDFAEB9E7E06AEE2170953707C210138B9A6B407BB0D"
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -I -B -X utf8 "$entry" --check-only --source-sha256 "$identity" --review-sha256 "$review"
fi
exec timeout --signal=TERM --kill-after=5s 14495s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4fsZbW_capacity_after_eval_resume -- "$python_bin" -B -X utf8 -c '
import subprocess,sys
from pathlib import Path
from scripts.p106b_stage_receipt import pipeline
py,source,review=sys.argv[1:4]
base=[py,"-I","-B","-X","utf8","handoff/audit/oct26_research/resume_gemma_capacity.py"]
pins=["--source-sha256",source,"--review-sha256",review]
phases=[
 ("REGRESSION",[py,"-I","-B","-X","utf8","scripts/test_p106b_capacity_resume.py"]),
 ("PREFLIGHT",base+["--check-only"]+pins),
 ("EXECUTE",base+["--execute","--output",
  str(Path.cwd()/"test_result/evidence/p106b_gemma_capacity_resume_v1_20261026_rootc"),
  "--max-wall-sec","14400","--deadline","2026-10-26T07:30:00Z"]+pins)]
def launch(command):
    return subprocess.run(command,stdin=subprocess.DEVNULL).returncode
raise SystemExit(pipeline(phases,launch,lambda line:print(line,flush=True),
                 experiment="P106B_Stage4fsZbW_capacity_after_eval_resume")["returncode"])
' "$python_bin" "$identity" "$review"
