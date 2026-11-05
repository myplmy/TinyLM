"""Census exact change shapes; never approve content or author training TXT."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import sys
import time

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path.insert(0, str(AUDIT)); sys.path.insert(0, str(ROOT))
from active_guard_v5_preflight_v1 import activate, checked_contract, assert_no_protected_opens
from scripts import p106b_hold_resolution_inventory as inv

activate()
guard = checked_contract()
blocked_ids = set(guard['restricted_ids']) | set(guard['trusted_metadata'])
blocked_hashes = set(guard['restricted_hashes'])
pins = {}


def read_metadata(path, expected=None):
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest().upper()
    assert expected is None or sha == expected
    pins[str(path.relative_to(ROOT))] = sha
    return json.loads(raw)


def classify(before, after):
    if before == after:
        return 'IDENTICAL_BYTES_REQUIRES_CONTENT_REVIEW', ''
    source, candidate = before.rstrip(), after.rstrip()
    if source == candidate:
        return 'TRAILING_WHITESPACE_ONLY', ''
    if source.startswith(candidate) and candidate:
        return 'EXACT_SUFFIX_DELETION', source[len(candidate):]
    no_empty_parens = source.replace('()', '')
    if no_empty_parens == candidate:
        return 'EXACT_LITERAL_EMPTY_PARENS_ONLY', ''
    if no_empty_parens.startswith(candidate) and candidate:
        return 'EXACT_LITERAL_EMPTY_PARENS_AND_SUFFIX', no_empty_parens[len(candidate):]
    return 'OTHER_CHANGE_REQUIRES_CONTEXT', ''


started = time.monotonic()
opaque_path = AUDIT/'OPAQUE_UNADOPTED_HOLD_ROOT32_ROSTER23_V1.json'
opaque = read_metadata(opaque_path, '87EB0550B9F11BC3EC4E6CBF6B75673A8785633B0522762F7E4277849292EFEF')
remaining = set(opaque['hold_hashes'])
index_path = inv.BASE/'remaining_field_title_readers_v1/complete.json'
index = read_metadata(index_path)
out = inv.BASE/'workflow_only_format_shapes_v1'
assert not out.exists()
writer = inv.cache.ShardWriter(out, 'shape_metadata', limit=3_999_999)
shapes, positions, suffixes = Counter(), Counter(), Counter()
selected = skipped = 0
for page in index['pages']:
    manifest = read_metadata(ROOT/page['path'], page['sha256'])
    for row in manifest['rows']:
        reasons = set(row.get('remaining_reasons', [])) | set(row.get('candidate_reasons', []))
        if row['original_text_sha256'] not in remaining or reasons != {'FIELD_OR_TITLE_ROLE_REQUIRES_INDEPENDENT_SOURCE_READING'}:
            continue
        if not row.get('guards') or not all(row['guards'].values()):
            continue
        if row['id'] in blocked_ids or any(row[label]['sha256'] in blocked_hashes for label in ['original', 'candidate']):
            skipped += 1
            continue
        texts = []
        for label in ['original', 'candidate']:
            pin = row[label]
            path = (ROOT/pin['path']).resolve()
            assert path.is_relative_to(inv.BASE) and not path.is_symlink()
            raw = path.read_bytes()
            assert hashlib.sha256(raw).hexdigest().upper() == pin['sha256']
            texts.append(raw.decode('utf-8'))
        original, candidate = texts
        shape, suffix = classify(original, candidate)
        shapes[shape] += 1
        positions[shape] += row['occurrences']
        if suffix and len(suffix) <= 180:
            suffixes[suffix] += 1
        selected += 1
        writer.append(dict(id=row['id'], original=row['original'], candidate=row['candidate'],
            occurrences=row['occurrences'], shape=shape,
            original_characters=len(original), candidate_characters=len(candidate),
            suffix_characters=len(suffix), suffix_sha256=inv.sha(suffix) if suffix else None,
            has_code_fence_marker=('```' in original or '~~~' in original),
            root_approved=False, cache_admitted=False))
    if page['page'] % 6 == 0:
        print(json.dumps(dict(phase='FORMAT_SHAPES', through_page=page['page'], examined=selected)), flush=True)
assert_no_protected_opens()
for path in [Path(__file__), AUDIT/'WORKFLOW_ONLY_FORMAT_SHAPES_F3_F4_V1.md',
             AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V5.json']:
    pins[str(path.relative_to(ROOT))] = inv.file_sha(path)
manifest = writer.close(lineage=dict(input_pins=pins, content_approval=False))
result = dict(status='EXACT_CHANGE_SHAPE_CENSUS_NOT_CONTENT_APPROVAL',
    basis='ROOT32_ROSTER23_EXPECTED_HOLD_WORKFLOW_ONLY_FIELD_ROWS',
    examined_unique=selected, protected_metadata_rows_skipped=skipped,
    shapes_unique=dict(shapes), shapes_positions=dict(positions),
    frequent_short_deleted_suffixes=[dict(suffix=key, sources=value) for key, value in suffixes.most_common(12)],
    metadata_directory=str(out.relative_to(ROOT)), metadata_manifest=manifest,
    input_pins=pins, elapsed_seconds=time.monotonic()-started,
    source_candidate_hashes_verified=True, original_candidate_modified=False,
    training_TXT_authored_by_root=0, automatically_admitted=0,
    identity_is_not_content_quality=True, semantic_quality_threshold_defined=False,
    goal_complete=False, training_authorized=False)
inv.write_json(AUDIT/'WORKFLOW_ONLY_FORMAT_SHAPES_V1.json', result)
print(json.dumps({key:result[key] for key in ['status', 'examined_unique',
    'shapes_unique', 'shapes_positions', 'elapsed_seconds', 'automatically_admitted']}, ensure_ascii=False), flush=True)
