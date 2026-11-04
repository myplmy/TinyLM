"""Reuse immutable V5 with V2 preflight and an exact metadata-only HOLD branch."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
from exact_review_header_alias_v2 import wrap_review_entries
from exact_review_metadata_guard_v2 import (validate_sources, validate_review,
    materialize_metadata_only, install_open_observer)

FROZEN = 'DAB0FBC8312B4331DD147F0B78AD185E9A2B1BC830B5BDB479C72A48514FDB48'
GUARD = 'E0EF117564ED4632D1A2C63F40AB66EB9620D416AE8BF516FD1AE3204286EF8B'


def replace_once(text, before, after):
    inv.require(text.count(before) == 1, 'frozen collector transformation anchor changed')
    return text.replace(before, after)


def load_collector():
    guard_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V2.json'
    inv.require(inv.file_sha(guard_path) == GUARD, 'active guard changed')
    contract = inv.cache.read(guard_path)
    receipt_path = AUDIT / 'ROOT_28876_METADATA_ONLY_NONADMISSION_V1.json'
    receipt = inv.cache.read(receipt_path)
    inv.require(receipt['guard']['sha256'] == GUARD, 'receipt names a different guard')
    for label in ('author_review', 'sidecar', 'manifest'):
        pin = receipt[label]
        inv.require(inv.file_sha(ROOT / pin['path']) == pin['sha256'],
                    'metadata-only evidence changed')
    receipt = dict(receipt, receipt_pin=dict(path=str(receipt_path.relative_to(ROOT)),
                                           sha256=inv.file_sha(receipt_path)))
    attempts = install_open_observer(ROOT, contract)
    frozen = AUDIT / 'collect_exact_cohort_reviews_v5.py'
    inv.require(inv.file_sha(frozen) == FROZEN, 'frozen V5 collector changed')
    code = frozen.read_text(encoding='utf-8')
    code = replace_once(code, "contract_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'",
                        "contract_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V2.json'")
    before = "    inv.require(not (set(sources)&blocked_ids),'restricted source id in cohort')\n    inv.require(not ({r['original']['sha256'] for r in sources.values()}&blocked_hashes),\n                'restricted source body in cohort')"
    code = replace_once(code, before,
        '    metadata_only_ids = metadata_guard_sources(sources, contract, cohort, METADATA_RECEIPT)')
    code = replace_once(code, '    for source in sources.values():\n        views={}',
        "    for source in sources.values():\n        if source['id'] in metadata_only_ids:\n            continue\n        views={}")
    marker = "                if row['decision'] not in {'EXCLUDE','NEEDS_ROOT'}:"
    code = replace_once(code, marker,
        "                if key in metadata_only_ids:\n                    metadata_guard_review(row, METADATA_RECEIPT)\n" + marker)
    code = replace_once(code, "                env['materialize'](row,sources[key],directory)",
        "                if key in metadata_only_ids:\n                    metadata_only_materialize(row,sources[key],METADATA_RECEIPT)\n                else:\n                    env['materialize'](row,sources[key],directory)")
    code = replace_once(code, "        elapsed_seconds=time.time()-started,root_adopted=0,cache_admitted=0,",
        "        metadata_only_ids=sorted(metadata_only_ids),protected_payload_open_attempts=len(PROTECTED_OPEN_ATTEMPTS),\n        active_guard_sha256=ACTIVE_GUARD_SHA,\n        elapsed_seconds=time.time()-started,root_adopted=0,cache_admitted=0,")
    code = replace_once(code, "    receipt=write_json_new(output/'complete.json',summary)",
        "    inv.require(not PROTECTED_OPEN_ATTEMPTS,'protected payload open was attempted')\n    receipt=write_json_new(output/'complete.json',summary)")
    environment = dict(__name__='guarded_exact_collector_library', __file__=str(frozen),
        metadata_guard_sources=validate_sources, metadata_guard_review=validate_review,
        metadata_only_materialize=materialize_metadata_only, METADATA_RECEIPT=receipt,
        PROTECTED_OPEN_ATTEMPTS=attempts, ACTIVE_GUARD_SHA=GUARD)
    exec(compile(code, str(frozen), 'exec'), environment)
    previous = environment['load_reused']

    def load(path, scope):
        scope = previous(path, scope)
        scope['review_entries'] = wrap_review_entries(scope['review_entries'])
        for pin_path in (Path(__file__), AUDIT/'exact_review_metadata_guard_v2.py',
                         AUDIT/'exact_review_header_alias_v2.py', guard_path, receipt_path):
            scope['input_pins'][str(pin_path.relative_to(ROOT))] = inv.file_sha(pin_path)
        return scope

    environment['load_reused'] = load
    return environment


def main():
    parser = argparse.ArgumentParser()
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--cohort')
    choice.add_argument('--phase', choices=('field', 'other'))
    parser.add_argument('--page', type=int)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    environment = load_collector()
    if args.cohort:
        inv.require(args.page is None, 'a direct cohort does not have a page argument')
        return environment['collect'](args.cohort, args.version)
    directory, expected_pages, expected_sources = {
        'field': ('remaining_field_title_readers_v1', 36, 18237),
        'other': ('remaining_other_types_readers_v1', 98, 50162),
    }[args.phase]
    index_path = inv.BASE / directory / 'complete.json'
    index = inv.cache.read(index_path)
    inv.require(len(index['pages']) == expected_pages and index['sources'] == expected_sources,
                'full queue index changed')
    inv.require(args.page is not None and 1 <= args.page <= expected_pages, 'invalid page')
    page, = [row for row in index['pages'] if row['page'] == args.page]
    cohort = page['group']
    manifest_path = ROOT / page['path']
    inv.require(manifest_path == inv.BASE / cohort / 'manifest.json' and
                inv.file_sha(manifest_path) == page['sha256'], 'page manifest pin changed')
    manifest = inv.cache.read(manifest_path)
    inv.require(len(manifest['rows']) == page['sources'] and
        {role: len(value['ids']) if isinstance(value, dict) else len(value)
         for role, value in manifest['assignments'].items()} == page['assignments'],
        'page assignment changed')
    environment['ALLOWED'] = {cohort: page['sources']}
    result = environment['collect'](cohort, args.version)
    receipt_path = AUDIT / ('EXACT_PAGE_REVIEW_' + args.phase.upper() + '_' +
        str(args.page).zfill(3) + '_' + args.version.upper() + '.json')
    inv.require(not receipt_path.exists(), 'new immutable page receipt required')
    environment['write_json_new'](receipt_path, dict(
        status='ACTUAL_PAGE_REVIEW_BINDING_SNAPSHOT_NOT_ADMISSION', phase=args.phase,
        page=args.page, cohort=cohort, version=args.version, expected_sources=page['sources'],
        counts=result['counts'], coverage=result['coverage'], errors=len(result['errors']),
        metadata_only_ids=result['metadata_only_ids'],
        protected_payload_open_attempts=result['protected_payload_open_attempts'],
        snapshot=str((inv.BASE/(cohort+'_snapshots')/args.version/'complete.json').relative_to(ROOT)),
        input_pins={str(path.relative_to(ROOT)): inv.file_sha(path)
                    for path in (index_path, manifest_path, Path(__file__))},
        root_adopted=0, cache_admitted=0, goal_complete=False, training_authorized=False))
    return result


if __name__ == '__main__':
    main()
