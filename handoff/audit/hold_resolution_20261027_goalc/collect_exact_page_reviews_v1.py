"""Reuse the frozen exact-cohort collector for one pinned full-queue page."""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

parser = argparse.ArgumentParser()
parser.add_argument('--phase', choices=('field', 'other'), required=True)
parser.add_argument('--page', type=int, required=True)
parser.add_argument('--version', required=True)
args = parser.parse_args()
directory, expected_pages, expected_sources = {
    'field': ('remaining_field_title_readers_v1', 36, 18237),
    'other': ('remaining_other_types_readers_v1', 98, 50162),
}[args.phase]
index_path = inv.BASE / directory / 'complete.json'
index = inv.cache.read(index_path)
assert len(index['pages']) == expected_pages and index['sources'] == expected_sources
assert 1 <= args.page <= expected_pages
pages = [row for row in index['pages'] if row['page'] == args.page]
assert len(pages) == 1
page = pages[0]
cohort = page['group']
manifest_path = ROOT / page['path']
assert manifest_path == inv.BASE / cohort / 'manifest.json'
assert inv.file_sha(manifest_path) == page['sha256']
manifest = inv.cache.read(manifest_path)
assert len(manifest['rows']) == page['sources']
assert {role: len(value['ids']) if isinstance(value, dict) else len(value)
        for role, value in manifest['assignments'].items()} == page['assignments']
source = AUDIT / 'collect_exact_cohort_reviews_v5.py'
environment = {'__name__': 'exact_page_review_collector_library', '__file__': str(source)}
exec(compile(source.read_text(encoding='utf-8'), str(source), 'exec'), environment)
environment['ALLOWED'] = {cohort: page['sources']}
result = environment['collect'](cohort, args.version)
assert result['root_adopted'] == result['cache_admitted'] == 0
receipt = AUDIT / ('EXACT_PAGE_REVIEW_' + args.phase.upper() + '_' + str(args.page).zfill(3) + '_' + args.version.upper() + '.json')
assert not receipt.exists()
inv.write_json(receipt, {
    'status': 'ACTUAL_PAGE_REVIEW_BINDING_SNAPSHOT_NOT_ADMISSION',
    'phase': args.phase, 'page': args.page, 'cohort': cohort, 'version': args.version,
    'expected_sources': page['sources'], 'counts': result['counts'], 'coverage': result['coverage'],
    'errors': len(result['errors']), 'snapshot': str((inv.BASE / (cohort + '_snapshots') / args.version / 'complete.json').relative_to(ROOT)),
    'input_pins': {str(path.relative_to(ROOT)): inv.file_sha(path) for path in (index_path, manifest_path, source, Path(__file__))},
    'root_adopted': 0, 'cache_admitted': 0, 'goal_complete': False, 'training_authorized': False})
