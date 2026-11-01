"""Reuse strict collector38 and add the full579 current-body review cohort."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
source = (AUDIT / 'collect_supplemental_candidates_v38.py').read_text(encoding='utf-8')

def replace_once(before, after):
    global source
    assert source.count(before) == 1, before
    source = source.replace(before, after)

replace_once('supplemental_candidates_snapshot_v38.json', 'supplemental_candidates_snapshot_v39.json')
replace_once('records, errors, review_pins, input_pins = [], [], [], {}',
             'groups += ["root_selected_lexical_counter_v1"]' + chr(10)
             + 'records, errors, review_pins, input_pins = [], [], [], {}')
anchor = 'views_manifest["rows"].extend(structural_views["rows"])'
replace_once(anchor, anchor + '''
lexical_views_path = BASE / "root_selected_lexical_counter_v1/reading_views_manifest_v1.json"
lexical_views = inv.cache.read(lexical_views_path)
inv.require(inv.file_sha(ROOT / lexical_views["source_manifest"]["path"]) == lexical_views["source_manifest"]["sha256"],
            "all579 lexical reading views refer to another assignment")
input_pins[str(lexical_views_path.relative_to(ROOT))] = inv.file_sha(lexical_views_path)
views_manifest["rows"].extend(lexical_views["rows"])
''')
anchor = 'def digest(payload):'
replace_once(anchor, 'strict_task_cohorts.add("root_selected_lexical_counter_v1")' + chr(10) * 2 + anchor)
anchor = 'for detail in coverage.values():'
replace_once(anchor, '''inv.require(coverage["root_selected_lexical_counter_v1"]["expected"] == 579,
            "all current lexical assignments must remain visible, including unfinished ones")
''' + anchor)
output = AUDIT / 'collect_supplemental_candidates_v39.py'
compile(source, str(output), 'exec')
with output.open('x', encoding='utf-8') as stream:
    stream.write(source)
print('Prepared collector39 from38: full579 assignments, strict TASK and partial-view checks preserved.')
