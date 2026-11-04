"""Read-only, lossless candidate views behind exact role and source metadata."""
from pathlib import Path, PurePosixPath
import difflib
import hashlib
import json
import re

DATA_ROOT = 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
SCHEMA = 'LOSSLESS_REVIEW_READER_SCOPE_V1'
PROTOCOL = 'FULL_ORIGINAL_AND_LOSSLESS_CANDIDATE_V1'
LIMIT_BYTES = 20_000_000
VIEW_WIDTH = 4000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest().upper()


def data_path(root, name):
    """Reject unrelated paths lexically before resolving or opening them."""
    require(isinstance(name, str) and '\\' not in name, 'noncanonical data path')
    relative = PurePosixPath(name)
    prefix = PurePosixPath(DATA_ROOT).parts
    require(not relative.is_absolute() and '..' not in relative.parts and
            relative.parts[:len(prefix)] == prefix, 'path outside authorized data root')
    base = Path(root) / DATA_ROOT
    path = Path(root) / name
    require(path.resolve().is_relative_to(base.resolve()), 'resolved data path left scope')
    for item in (path, *path.parents):
        require(not item.is_symlink(), 'symlink data path denied')
        if item == base:
            break
    return path


def resolve_assignment(root, scope, role, cohort, source_id, read_metadata):
    require(scope.get('schema') == SCHEMA, 'wrong lossless scope schema')
    require(re.fullmatch(r'(?:expanded_train|validation):[0-9]+', source_id) is not None,
            'invalid source ID')
    contract = json.loads(read_metadata(root, scope['contract']))
    require(source_id not in contract['restricted_ids'], 'restricted source ID; no payload read')
    require(role in scope['roles'] and cohort in scope['roles'][role],
            'role or cohort outside exact assignment')
    pin = scope['roles'][role][cohort]
    require(pin['path'] == DATA_ROOT + '/' + cohort + '/manifest.json',
            'manifest outside exact cohort')
    data_path(root, pin['path'])
    manifest = json.loads(read_metadata(root, pin))
    matching = [r for r in manifest['rows'] if r.get('id') == source_id]
    require(len(matching) == 1, 'source is absent or ambiguous in this manifest')
    row = matching[0]
    require(row.get('role') == role, 'source belongs to another assigned role')
    pair = {key: dict(row[key]) for key in ('original', 'candidate')}
    # Both hashes are checked before either payload path is opened.
    for item in pair.values():
        require(re.fullmatch(r'[0-9A-F]{64}', item['sha256']) is not None, 'invalid source pin')
        require(item['sha256'] not in contract['restricted_hashes'],
                'restricted original or candidate SHA; no payload read')
    for item in pair.values():
        data_path(root, item['path'])
    parts = row.get('reading_parts', [])
    legacy_characters = None
    if parts:
        cursor = 0
        for item in parts:
            lo, hi = item['characters']
            require(lo == cursor and hi >= lo, 'noncontiguous legacy packet metadata')
            cursor = hi
        legacy_characters = cursor
    return dict(source_id=source_id, role=role, cohort=cohort, original=pair['original'],
                candidate=pair['candidate'], source_manifest=pin,
                legacy_manifest_frame_characters=legacy_characters,
                contract=scope['contract'], protected_prechecks_passed=True)


def bounded_payload(root, pin):
    path = data_path(root, pin['path'])
    with path.open('rb') as stream:
        return stream.read(LIMIT_BYTES)


def load_pair(root, scope, role, cohort, source_id, read_metadata, read_payload=None):
    context = resolve_assignment(root, scope, role, cohort, source_id, read_metadata)
    read_payload = read_payload or bounded_payload
    values = []
    for key in ('original', 'candidate'):
        pin = context[key]
        raw = read_payload(root, pin)
        require(len(raw) < LIMIT_BYTES and digest(raw) == pin['sha256'],
                'payload bytes differ from exact pin or exceed size limit')
        values.append(raw)
    return context, values[0], values[1]


def _offsets(lines):
    result = [0]
    for line in lines:
        result.append(result[-1] + len(line))
    return result


def changes_between(source, candidate):
    """Line diff, with bounded character refinement, never a content policy."""
    if source == candidate:
        return []
    if len(source) + len(candidate) > 80_000:
        # Bound matching work for long or adversarially repetitive documents.
        first = 0
        while first < min(len(source), len(candidate)) and source[first] == candidate[first]:
            first += 1
        last = 0
        while (last < min(len(source), len(candidate))-first and
               source[len(source)-last-1] == candidate[len(candidate)-last-1]):
            last += 1
        a, b, c, d = first, len(source)-last, first, len(candidate)-last
        tag = 'insert' if a == b else 'delete' if c == d else 'replace'
        result = [dict(op=tag, source_range=[a, b], candidate_range=[c, d],
                       after=candidate[c:d])]
        require(reconstruct(source, result) == candidate, 'bounded reconstruction failed')
        return result
    old_lines = source.splitlines(keepends=True)
    new_lines = candidate.splitlines(keepends=True)
    old_offsets, new_offsets = _offsets(old_lines), _offsets(new_lines)
    result = []

    def add(tag, a, b, c, d):
        if tag != 'equal':
            result.append(dict(op=tag, source_range=[a, b], candidate_range=[c, d],
                               after=candidate[c:d]))

    for tag, a, b, c, d in difflib.SequenceMatcher(
            None, old_lines, new_lines, autojunk=True).get_opcodes():
        i, j, k, l = old_offsets[a], old_offsets[b], new_offsets[c], new_offsets[d]
        if tag == 'replace' and (j-i) + (l-k) <= 6000:
            for inner, x, y, z, w in difflib.SequenceMatcher(
                    None, source[i:j], candidate[k:l], autojunk=True).get_opcodes():
                add(inner, i+x, i+y, k+z, k+w)
        else:
            add(tag, i, j, k, l)
    require(reconstruct(source, result) == candidate, 'lossless diff reconstruction failed')
    return result


def reconstruct(source, changes):
    """Independent range application; rejects missing, overlapping or shifted data."""
    cursor = 0
    position = 0
    output = []
    for item in changes:
        tag = item['op']
        require(tag in {'insert', 'delete', 'replace'}, 'invalid change operation')
        a, b = item['source_range']
        c, d = item['candidate_range']
        after = item['after']
        require(type(a) is type(b) is type(c) is type(d) is int,
                'change ranges must be integer codepoint offsets')
        require(0 <= cursor <= a <= b <= len(source), 'source change range is unordered')
        require(c == position + a-cursor and d >= c and len(after) == d-c,
                'candidate change range is shifted or incomplete')
        require((tag == 'insert' and a == b and bool(after)) or
                (tag == 'delete' and a < b and not after) or
                (tag == 'replace' and a < b and bool(after)), 'change shape is invalid')
        output.extend((source[cursor:a], after))
        cursor, position = b, d
    output.append(source[cursor:])
    return ''.join(output)


def candidate_representation(source, candidate, changes):
    index = [dict(number=n, op=r['op'], source_range=r['source_range'],
                  candidate_range=r['candidate_range']) for n, r in enumerate(changes, 1)]
    header = 'ALL_CHANGE_RANGES ' + json.dumps(index, ensure_ascii=False, separators=(',', ':'))
    if not changes:
        require(source == candidate, 'empty change index hides different candidate')
        return 'EXACT_IDENTICAL', header + '\nCANDIDATE_EQUALS_FULL_ORIGINAL\n'
    patch = [header]
    for n, item in enumerate(changes, 1):
        if item['after']:
            patch.extend((f'CHANGE_{n}_NEW_TEXT_BEGIN', item['after'], f'CHANGE_{n}_NEW_TEXT_END'))
    patch = '\n'.join(patch) + '\n'
    full = header + '\nFULL_CANDIDATE_BEGIN\n' + candidate + '\nFULL_CANDIDATE_END\n'
    return ('EXACT_PATCH', patch) if len(patch) < len(full) else ('INDEX_AND_FULL_CANDIDATE', full)


def prepare_views(original_raw, candidate_raw):
    source = original_raw.decode('utf-8')
    candidate = candidate_raw.decode('utf-8')
    changes = changes_between(source, candidate)
    rebuilt = reconstruct(source, changes).encode('utf-8')
    require(rebuilt == candidate_raw, 'candidate UTF-8 bytes were not exactly reconstructed')
    mode, representation = candidate_representation(source, candidate, changes)
    return dict(protocol=PROTOCOL, original=source, candidate=representation,
                candidate_representation=mode, changes=changes,
                original_sha256=digest(original_raw), candidate_sha256=digest(candidate_raw),
                original_characters=len(source), candidate_characters=len(candidate),
                original_bytes=len(original_raw), candidate_bytes=len(candidate_raw),
                exact_candidate_byte_reconstruction=True,
                original_final_LF=original_raw.endswith(b'\n'),
                candidate_final_LF=candidate_raw.endswith(b'\n'))


def view_part(views, view, part, width=VIEW_WIDTH):
    require(view in {'original', 'candidate'}, 'unknown logical view')
    require(type(part) is int and type(width) is int and part >= 1 and 1 <= width <= VIEW_WIDTH,
            'invalid logical view part')
    value = views[view]
    parts = max(1, (len(value)+width-1)//width)
    require(part <= parts, 'part outside logical view')
    lo, hi = width*(part-1), min(width*part, len(value))
    return dict(view=view, part=part, parts=parts, range=[lo, hi],
                range_unit='UNICODE_CODEPOINTS', text=value[lo:hi],
                end_of_view=part == parts, next_part=None if part == parts else part+1)
