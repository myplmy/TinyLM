#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
PY="$(tinylm_python)"
sha256sum --check --status <<'PREPARE_HASH'
cccb1c896791adc9459311e138a90e5fb64a17dc6b31915e1e86eb3de2be723f  handoff/audit/nov05_teacher_resume/english_view_v5/PREPARE_v1.json
PREPARE_HASH
export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
"${PY}" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ft3bW_typed_article_pilot --note "User109: English-only teacher MTP pilot, four candidates. Teacher/student see the same complete typed article; source question/answer lists are preserved in raw but excluded from inputs. V3 parent identity/split/cursor remain intact. No student, semantic output filtering or full-quality claim."
set +e
"${PY}" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ft3bW_typed_article_pilot -- timeout --signal=TERM --kill-after=20s 1100s "${PY}" -B -X utf8 -m scripts.diag_p106b_nov05_english_passage --mode pilot --max-wall-sec 900 --deadline-utc 2026-11-05T06:30:00+00:00 --stop-file tmp/P106B_Stage4ft3bW_STOP
worker_rc=$?
set -e
if [[ "$worker_rc" != 0 && "$worker_rc" != 8 ]]; then exit "$worker_rc"; fi
"${PY}" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ft3bW_typed_article_pilot -- "${PY}" -B -X utf8 -m scripts.diag_p106b_nov05_english_passage --mode read-pilot
"${PY}" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ft3bW_typed_article_pilot --note "Technical pilot closure verified; root must read the exact four article/question/answer pairs before any long resume. Controlled pause is not student improvement or75M completion."
