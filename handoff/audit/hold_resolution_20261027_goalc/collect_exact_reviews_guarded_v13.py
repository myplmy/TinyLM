"""Reuse parser12 under guard6; materialize the actual-filter HOLD as metadata."""
from pathlib import Path
import hashlib
import json
import runpy
import sys
from unittest.mock import patch

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path[:0] = [str(AUDIT),str(ROOT)]
import active_guard_v6_preflight_v1 as guard
import exact_review_metadata_guard_v3 as old_meta
import exact_review_metadata_guard_v4 as new_meta

guard.install_for_legacy()
arguments = sys.argv[1:]
if '--cohort' in arguments:
    cohort = arguments[arguments.index('--cohort')+1]
    assert cohort == 'remaining_rule30_independent_context_v1'
    scope_path = AUDIT/'RULE30_CONTEXT_LOSSLESS_SCOPE_V1.json'
    scope = json.loads(scope_path.read_bytes())
    expected_pin = scope['roles']['historical_review'][cohort]
    assert guard.inv.file_sha(ROOT/expected_pin['path']) == expected_pin['sha256']
else:
    phase = arguments[arguments.index('--phase')+1]
    page = int(arguments[arguments.index('--page')+1])
    assert phase in {'field','other'}
    cohort = ('remaining_field_title_page_' if phase=='field' else 'remaining_other_types_page_')+format(page,'03d')+'_counter_v1'
version = arguments[arguments.index('--version')+1]
frozen = AUDIT/'collect_exact_reviews_guarded_v12.py'
assert not frozen.is_symlink() and guard.inv.file_sha(frozen) == '3AEBA990DF70C3BB6B5E35277345EB9F31A3FB3D83D9474D4F4CF68DF8236C0D'
with patch.object(old_meta,'load_receipts',new_meta.load_receipts), \
        patch.object(old_meta,'validate_sources',new_meta.validate_sources), \
        patch.object(old_meta,'validate_review',new_meta.validate_review), \
        patch.object(old_meta,'materialize_metadata_only',new_meta.materialize_metadata_only), \
        patch.object(old_meta,'install_open_observer',new_meta.install_open_observer):
    if '--cohort' not in arguments:
        runpy.run_path(str(frozen),run_name='__main__')
    else:
        import exact_review_header_alias_v2 as headers
        import exact_review_output_cell_alias_v2 as aliases
        adapter = AUDIT/'collect_exact_reviews_guarded_v8.py'
        assert guard.inv.file_sha(adapter) == 'FAB264CA899755A5BFCA3DCCB812B7B4460231A46D30A8A2DFEDA564D480556C'
        raw = adapter.read_text(encoding='utf-8')
        last = "exec(compile(code, str(scope['frozen']), 'exec'), dict(__name__=__name__,"
        assert raw.count(last) == 1
        prepare = dict(__name__='supplement_collector8_transform',__file__=str(adapter))
        with patch.object(headers,'wrap_review_entries',aliases.wrap_review_entries):
            exec(compile(raw.split(last)[0],str(adapter),'exec'),prepare)
            library = dict(__name__='exact_supplement_collector13_library',__file__=str(Path(__file__)),frozen=prepare['scope']['frozen'])
            exec(compile(prepare['code'],str(adapter),'exec'),library)
            environment = library['load_collector']()
            environment['ALLOWED'] = {cohort:6}
            environment['collect'](cohort,version)
guard.assert_no_protected_opens()
summary = guard.inv.BASE/(cohort+'_snapshots')/version/'complete.json'
complete = json.loads(summary.read_bytes())
assert not complete['errors'], 'preserved failing snapshot; not a successful collection'
receipt = dict(status='GUARD6_EXACT_COLLECTION_WITH_BODY_FREE_FILTER_HOLD',
    cohort=cohort,version=version,active_guard_sha256=guard.EXPECTED,
    metadata_only_ids=complete['metadata_only_ids'],protected_payload_open_attempts=0,
    actual_snapshot=dict(path=str(summary.relative_to(ROOT)),sha256=guard.inv.file_sha(summary)),
    input_pins={str(p.relative_to(ROOT)):guard.inv.file_sha(p) for p in
        [Path(__file__),frozen,AUDIT/'exact_review_metadata_guard_v4.py',guard.CONTRACT,
         AUDIT/'ROOT_360211_METADATA_ONLY_NONADMISSION_V1.json']},
    inherited_guard_pins_are_preserved_provenance=True,
    root_adopted=0,cache_admitted=0,goal_complete=False,training_authorized=False)
out = AUDIT/('GUARD6_'+cohort.upper()+'_'+version.upper()+'_COLLECTION_BINDING_V1.json')
assert not out.exists()
guard.inv.write_json(out,receipt)
print(json.dumps(dict(status=receipt['status'],cohort=cohort,version=version,
    metadata_only_ids=receipt['metadata_only_ids'],errors=0,protected_payload_open_attempts=0)))
