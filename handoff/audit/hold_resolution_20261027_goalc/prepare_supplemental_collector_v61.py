"""Extend the frozen collector only for every new named-repeat assignment."""
from pathlib import Path

AUDIT=Path(__file__).resolve().parent
source=AUDIT/'collect_supplemental_candidates_v60.py'
target=AUDIT/'collect_supplemental_candidates_v61.py'
assert not target.exists()
text=source.read_text(encoding='utf-8')
replacements=[
 ('OUT = AUDIT / "supplemental_candidates_snapshot_v60.json"',
  'OUT = AUDIT / "supplemental_candidates_snapshot_v61.json"'),
 ('groups += ["post_semantic_independent_v1", "runtime_guard_counter_v1"]',
  'groups += ["post_semantic_independent_v1", "runtime_guard_counter_v1", "repeat_named_roles_counter_v2"]'),
 ('("runtime_guard_counter_v1", 23)]:',
  '("runtime_guard_counter_v1", 23), ("repeat_named_roles_counter_v2", 732)]:')
]
for before,after in replacements:
    assert text.count(before)==1,before
    text=text.replace(before,after)
before='"post_semantic_independent_v1", "runtime_guard_counter_v1"}:'
assert text.count(before)==1
text=text.replace(before,'"post_semantic_independent_v1", "runtime_guard_counter_v1", "repeat_named_roles_counter_v2"}:')
anchor='incident_path = BASE / "agents/context_controls/semantic_field_counter_v1/path_error_note_v1.md"'
assert text.count(anchor)==1
new='''for guidance_name in ["ROOT_MEDIATION_V1.md", "ROOT_EVIDENCE_1403490_CREDIT_V1.md"]:
    guidance_path=BASE / "repeat_named_roles_counter_v2" / guidance_name
    input_pins[str(guidance_path.relative_to(ROOT))]=inv.file_sha(guidance_path)
for role in ["context_controls","context_hangul","context_latin","historical_review","legacy_review"]:
    owned_notes=BASE / "agents" / role / "repeat_named_roles_counter_v2"
    for note in sorted(owned_notes.glob("path_error_note*.md")):
        input_pins[str(note.relative_to(ROOT))]=inv.file_sha(note)
'''
text=text.replace(anchor,new+'\n'+anchor)
anchor='for detail in coverage.values():'
assert text.count(anchor)==1
text=text.replace(anchor,'inv.require(coverage["repeat_named_roles_counter_v2"]["expected"] == 732, "every new repeat source must remain visible")\n'+anchor)
with target.open('x',encoding='utf-8') as stream:
    stream.write(text)
print('새 수집61: 지정732 전량·정확 TASK/출력 결합·이전 실패/대기 이력 보존')
