"""Separate value-count alarms from source-bound formatting and new hypotheses."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
from numeric_local_atom_proof_v1 import atoms
source_path = AUDIT / 'FIELD_BOUND_BODY_DIAGNOSTICS_COMPLETE_V1.json'
diagnostic = json.loads(source_path.read_text(encoding='utf-8'))
contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
assert hashlib.sha256(contract_path.read_bytes()).hexdigest().upper() == 'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF'
contract = json.loads(contract_path.read_text(encoding='utf-8'))
rows = []
for shard in diagnostic['shards']:
    data = (ROOT / shard['path']).read_bytes()
    assert hashlib.sha256(data).hexdigest().upper() == shard['sha256']
    rows += json.loads(data)
observations = {
    'expanded_train:222': ('COMMA_LIST_SPACING', '位치공간의1,2,3목록에서쉼표뒤공백만달라숫자atom분해가달라졌다.'),
    'expanded_train:20261': ('CONDITIONAL_PARTICLE_NOT_DAY_UNIT', '29일때/37일때/41일때의일을날짜단위로오인했다.목록값은원형에실제로있다.'),
    'expanded_train:26844': ('CONDITIONAL_PARTICLE_NOT_DAY_UNIT', '실제N=32와기수2한단계/기수4두단계의자연어가있다.32일때의일은새날짜단위가아니다.소실지수식을복원하지않는다.'),
    'expanded_train:20265': ('EXPLICIT_EXISTING_TABLE_OPERANDS_REUSED_IN_PROSE', '원형의세로셈27/59/86에서앞산문의아래27과59참조를명시한것이다.새수값은아니다.'),
    'expanded_train:45903': ('MODEL_IDENTIFIER_REPEATED_AS_SUBJECT', '실제AK-4이름을두변형과생산지산문의주어로반복한것이며새음수값을추가한것이아니다.'),
}
pending = {
    'expanded_train:29112': ('AMBIGUOUS_DECIMAL_ACROSS_NEWLINE', 'Total = $1431.5 per kW.', '$1431.\n5 per kW', 'legacy_review'),
    'expanded_train:33415': ('CITATION_DIGIT_ATTACHED_TO_RANGE', 'mm. 8-12.7 In Schenkerian', 'similar fashion.7 Here the melody', 'legacy_review'),
    'expanded_train:85646': ('MISSING_TARGET_FILLED_FROM_NEARBY_FORMULA', 'The use of M-1 is necessary to include zeros at both endpoints.', 'The use of is necessary to include zeros at both endpoints.', 'context_hangul'),
}
result_rows = []
unchanged_counts = 0
flagged_sources = 0
for row in rows:
    if not row['numeric_atom_flags']:
        continue
    flagged_sources += 1
    assert row['id'] not in contract['restricted_ids']
    assert row['original']['sha256'] not in contract['restricted_hashes']
    texts = []
    for key in ('original', 'body'):
        pin = row[key]
        data = (ROOT / pin['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest().upper() == pin['sha256']
        texts.append(data.decode('utf-8'))
    before, after = [Counter((atom['value'], atom['unit']) for atom in atoms(text, 0)) for text in texts]
    additions = after - before
    if not additions:
        unchanged_counts += 1
        continue
    ident = row['id']
    item = dict(id=ident, original=row['original'], body=row['body'], review=row['review'],
                added_value_unit_counts=[dict(value=value, unit=unit, count=count)
                                         for (value, unit), count in additions.items()],
                source_context_not_whole_document_factual_verification=True,
                automatic_flag_waiver=False, root_or_cache_adopted=False)
    if ident in observations:
        kind, reason = observations[ident]
        item.update(status='BOUNDED_COUNT_DIFFERENCE_EXPLAINED_FROM_ACTUAL_SOURCE', kind=kind, reason=reason)
        if ident.endswith(':222'):
            old, new = '위치 공간(보통 1,2,3)', '위치 공간(보통 1, 2, 3)'
            assert old in texts[0] and new in texts[1]
            assert re.findall(r'\d+', old) == re.findall(r'\d+', new)
        elif ident.endswith(':20261'):
            assert 'n=29일 때, 37일 때, 41일 때, 그리고 43, 47일 때' in texts[0]
            assert 'n=29, 37, 41, 43, 47일 때' in texts[1]
        elif ident.endswith(':26844'):
            assert 'N=32=2 1×4 2 즉 기수2 한 단계와 기수4  두 단계를 수행한다.' in texts[0]
            assert 'N=32일 때 기수 2 한 단계와 기수 4 두 단계를 수행한다.' in texts[1]
        elif ident.endswith(':20265'):
            assert '   27\n + 59\n ————\n   86' in texts[0]
            assert '아래 27과 59의 계산에서' in texts[1]
        else:
            assert 'G3A2/A3를 AK-4란 이름으로 면허생산.' in texts[0]
            assert '스웨덴에서 생산된 AK-4' in texts[0]
            assert 'AK-4는 두 가지 변형' in texts[1]
    else:
        kind, changed, source_quote, owner = pending[ident]
        assert changed in texts[1] and source_quote in texts[0]
        item.update(status='NEW_NARROW_AUTHOR_FOLLOWUP_DELEGATED_NOT_YET_VERIFIED',
                    kind=kind, current_body_fragment=changed, exact_original_fragment=source_quote,
                    owner=owner, prior_bounded_followups_not_reopened=True)
    result_rows.append(item)
assert flagged_sources == 79 and unchanged_counts == 71
assert {row['id'] for row in result_rows} == set(observations) | set(pending)
report = dict(status='EIGHT_NUMERIC_COUNT_CONTEXTS_TRIAGED_FIVE_EXPLAINED_THREE_AUTHOR_FOLLOWUPS',
              numeric_flag_sources=79, numeric_flag_atoms=425,
              no_globally_added_value_unit_counts=71,
              added_value_unit_count_sources=8, bounded_contexts_explained=5,
              new_author_followups_pending_verification=3, rows=result_rows,
              counts_are_not_atom_context_or_semantic_proofs=True,
              local_atom_diagnostic_v1_manual_context_atoms=412,
              old_numeric_or_code_flags_automatically_waived=0,
              actual_initial_count_check='0bec32', actual_body_added_count_contexts='619130',
              actual_original_punctuation_and_conditional_contexts='4de812',
              exact_own_copy_paths_and_sha_check='bc6730',
              input_pins={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest().upper()
                          for path in (source_path, contract_path, Path(__file__).resolve(), AUDIT/'numeric_local_atom_proof_v1.py')},
              source_data_changed=False, root_or_cache_adoptions=0,
              whole_goal_complete=False, training_authorized=False)
with (AUDIT / 'FIELD_BOUND_NUMERIC_COUNT_TRIAGE_V1.json').open('x', encoding='utf-8') as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(status=report['status'], explained=5, delegated_pending=3,
                     unchanged_count_not_semantic_pass=71, automatic_waivers=0)))
