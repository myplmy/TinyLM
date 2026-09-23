#!/usr/bin/env bash
# P029 Stage2W: repeat the historical five prompts on mA and p6d.
# Inference only, about 0.2 h; greedy EOS-aware output, not a quality score.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 013 --name P029_Stage2W_wiki_eos_panel --note "P029 Stage2W: raw continuation and footer/repetition review after EOS/KV-cache correction; old temperature-dependent result remains historical."
"$python_bin" scripts/runlog.py --num 013 --name P029_Stage2W_wiki_eos_panel --   "$python_bin" -B -X utf8 scripts/eval_recipe_prompt_panel.py     --models mA_g4s34_k4 p6d --model-data ko-en ko-en     --model-arch tied dense --preset m100 --tokens 300M     --max-new 80 --device cuda --out runs/bench/p029_stage2w_wiki_eos_panel.jsonl
rc=$?
if [ "$rc" -ne 0 ]; then
  printf '%s\n' "[FAIL] P029 Stage2W rc=$rc; inspect the test_result log" >&2
  exit "$rc"
fi
"$python_bin" scripts/runlog.py --num 013 --name P029_Stage2W_wiki_eos_panel --note "Review raw JSONL output by hand. Five prompts x two models cannot rank architecture or prove dataset causality."
