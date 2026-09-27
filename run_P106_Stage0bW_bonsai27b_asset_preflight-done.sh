#!/usr/bin/env bash
# P106 G0a prerequisite: exact local Bonsai 2 27B GGUF and Prism binary metadata.
# User-run WSL, about 0.1 h, GPU 0 and model generation 0. Exit 8 is a valid HOLD.
# Missing license/card or CUDA plugin never becomes teacher readiness by filename.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
"$python_bin" scripts/runlog.py --name P106_Stage0bW_bonsai27b_asset_preflight --note "P106 asset-only gate: exact GGUF v3/size, Prism fork version, license/card and CUDA plugin. No model loading or teacher generation. Exit 8 is HOLD."
"$python_bin" scripts/runlog.py --name P106_Stage0bW_bonsai27b_asset_preflight -- "$python_bin" -B -X utf8 scripts/diag_p106_bonsai_assets.py --self-test
"$python_bin" scripts/runlog.py --name P106_Stage0bW_bonsai27b_asset_preflight -- "$python_bin" -B -X utf8 scripts/diag_p106_bonsai_assets.py --check-only
"$python_bin" scripts/runlog.py --name P106_Stage0bW_bonsai27b_asset_preflight -- "$python_bin" -B -X utf8 scripts/diag_p106_bonsai_assets.py
