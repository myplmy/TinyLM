#!/usr/bin/env bash
# Offline source packet only. No model/teacher/download/training corpus.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4ca1W_source_template_packet_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ca1W_source_template_packet_cpu_"$run_stamp" --num 101 --note 'CPU6 and source/template hash8 packet. Raw text stays isolated under HF; metadata only in Git. Original question/answer quality and usable token supply remain unreviewed. No teacher/model/new download/training corpus. Full smoke is user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ca1W_source_template_packet_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_source_template_samples.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ca1W_source_template_packet_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_source_template_packet.py --execute --max-wall-sec 1800
