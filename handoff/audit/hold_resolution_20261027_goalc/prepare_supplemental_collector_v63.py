"""Take another immutable full-cohort snapshot after explicit author corrections."""
from pathlib import Path

AUDIT=Path(__file__).resolve().parent
target=AUDIT/'collect_supplemental_candidates_v63.py'
assert not target.exists()
text=(AUDIT/'collect_supplemental_candidates_v62.py').read_text(encoding='utf-8')
before='OUT = AUDIT / "supplemental_candidates_snapshot_v62.json"'
assert text.count(before)==1
text=text.replace(before,'OUT = AUDIT / "supplemental_candidates_snapshot_v63.json"')
with target.open('x',encoding='utf-8') as stream:
    stream.write(text)
print('새 전량 수집63 준비')
