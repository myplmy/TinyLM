"""Read at most five explicitly assigned source/body contexts; write no packets."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path[:0] = [str(AUDIT), str(ROOT)]
import active_guard_v6_preflight_v1 as guard
import lossless_review_packet_v3 as core
from assigned_final_literal_review_v1 import exact_changes, changes_view
from authored_literal_readiness_v1 import deferrals
from scripts import p106b_hold_resolution_policy_v32 as policy

WIDTH = 3500
MAX_OUTPUT = 30000


def preflight(scope, role, idents):
    assert scope['role'] == role
    assert 1 <= len(idents) <= 5 and len(idents) == len(set(idents))
    assigned = {row['id']: row for row in scope['cases']}
    assert len(assigned) == len(scope['cases'])
    assert set(idents) <= set(assigned), 'unassigned ID; no source opened'
    selected = [assigned[ident] for ident in idents]
    contract = guard.checked_contract()
    for row in selected:
        guard.require_payload_context(dict(source_id=row['id'], original=row['original'], candidate=row['body']), contract)
    return selected


def paragraph_context(source, changes):
    intervals = []
    blocks = [(match.start(), match.end()) for match in re.finditer(r'(?s)\S.*?(?=\n\s*\n|\Z)', source)]
    for change in changes:
        a, b = change['source_range']
        touched = [i for i, (lo, hi) in enumerate(blocks) if lo <= b and a <= hi]
        if not touched:
            continue
        lo = blocks[max(0, min(touched) - 1)][0]
        hi = blocks[min(len(blocks) - 1, max(touched) + 1)][1]
        if intervals and lo <= intervals[-1][1]:
            intervals[-1] = (intervals[-1][0], max(hi, intervals[-1][1]))
        else:
            intervals.append((lo, hi))
    parts = []
    for lo, hi in intervals:
        parts.extend(['SOURCE_PARAGRAPH_CONTEXT ' + json.dumps(dict(source_range=[lo, hi])) + chr(10),
                      source[lo:hi], chr(10) + 'SOURCE_PARAGRAPH_CONTEXT_END' + chr(10)])
    return ''.join(parts)


def view_text(source, body, changes, view):
    if view == 'source':
        return source
    if view == 'body':
        return body
    if view == 'flags':
        blocks = []
        for match in re.finditer(r'(?s)\S.*?(?=\n\s*\n|\Z)', body):
            value = match[0]
            reasons = sorted(set(deferrals(value) + policy.literal_holes(value)))
            if reasons:
                blocks.append('BODY_FLAG_CONTEXT ' + json.dumps(dict(body_range=list(match.span()), reasons=reasons), ensure_ascii=False)
                              + chr(10) + value + chr(10) + 'BODY_FLAG_CONTEXT_END' + chr(10))
        return ''.join(blocks) if blocks else 'NO_LOCAL_BLOCK_FLAGS; inspect assigned metadata flags and request body context if needed.'
    assert view == 'changes'
    parts = ['SOURCE_INTRO_CONTEXT' + chr(10), source[:700], chr(10) + 'SOURCE_INTRO_CONTEXT_END' + chr(10),
             changes_view(source, changes), paragraph_context(source, changes)]
    if len(body.encode('utf-8')) <= WIDTH:
        parts.extend(['SMALL_FINAL_BODY_FULL' + chr(10), body, chr(10) + 'SMALL_FINAL_BODY_EOF' + chr(10)])
    return ''.join(parts)


def collect(scope, role, idents, view, first, count, loader=None):
    assert first >= 1 and 1 <= count <= 3
    assert len(idents) * count * WIDTH + len(idents) * 2000 <= MAX_OUTPUT, 'reduce batch/count before any source opened'
    selected = preflight(scope, role, idents)
    loader = loader or core.base.bounded_payload
    output = []
    for row in selected:
        raw, final_raw = loader(ROOT, row['original']), loader(ROOT, row['body'])
        assert len(raw) < core.base.LIMIT_BYTES and len(final_raw) < core.base.LIMIT_BYTES
        assert hashlib.sha256(raw).hexdigest().upper() == row['original']['sha256']
        assert hashlib.sha256(final_raw).hexdigest().upper() == row['body']['sha256']
        source, body = raw.decode('utf-8'), final_raw.decode('utf-8')
        changes = exact_changes(source, body, core)
        text = view_text(source, body, changes, view)
        first_piece = core.view_part(dict(candidate=text), 'candidate', first, width=WIDTH)
        pieces = [first_piece] + [core.view_part(dict(candidate=text), 'candidate', n, width=WIDTH)
                                  for n in range(first + 1, min(first + count, first_piece['parts'] + 1))]
        header = dict(id=row['id'], role=role, original=row['original'], body=row['body'], view=view,
                      original_full_read_is_prior_primary_author_claim=row.get('prior_full_read_claim', True),
                      prior_read_scope_excerpt=(row.get('prior_read_scope') or '')[:350],
                      prior_reason_excerpt=(row.get('prior_reason') or '')[:200],
                      primary_review=row.get('primary_review'),
                      exact_changes=len(changes), exact_final_reconstruction=True,
                      unchanged_text_outside_delivered_changes_preserved=True,
                      source_full_view_delivered=view == 'source' and pieces[-1]['end_of_view'] and first == 1,
                      new_first_read_credit=0, root_or_cache_admission=False)
        output.append('B_ASSIGNED_CONTEXT ' + json.dumps(header, ensure_ascii=False, separators=(',', ':')) + chr(10))
        for piece in pieces:
            meta = {key: value for key, value in piece.items() if key != 'text'}
            output.extend(['B_CONTEXT_FRAME ' + json.dumps(meta, ensure_ascii=False) + chr(10), piece['text'],
                           chr(10) + ('B_CONTEXT_VIEW_EOF' if piece['end_of_view'] else 'B_CONTEXT_MORE_PARTS_REMAIN') + chr(10)])
    result = ''.join(output)
    assert len(result.encode('utf-8')) <= MAX_OUTPUT, 'bounded output exceeded; no partial output printed'
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scope', required=True)
    parser.add_argument('--scope-sha', required=True)
    parser.add_argument('--role', required=True)
    parser.add_argument('--ids', nargs='+', required=True)
    parser.add_argument('--view', choices=['changes', 'flags', 'body', 'source'], default='changes')
    parser.add_argument('--part', type=int, default=1)
    parser.add_argument('--count', type=int, default=1)
    args = parser.parse_args()
    guard.activate()
    path = Path(args.scope).resolve()
    assert path.parent == AUDIT and not path.is_symlink()
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest().upper() == args.scope_sha
    scope = json.loads(raw)
    assert scope['reader']['path'] == str(Path(__file__).relative_to(ROOT))
    assert scope['reader']['sha256'] == guard.inv.file_sha(Path(__file__))
    for name, sha in scope['code_pins'].items():
        assert not (ROOT / name).is_symlink() and guard.inv.file_sha(ROOT / name) == sha, name
    idents = ['expanded_train:' + value if value.isdigit() else value for value in args.ids]
    result = collect(scope, args.role, idents, args.view, args.part, args.count)
    guard.assert_no_protected_opens()
    print(result, end='')


if __name__ == '__main__':
    main()
