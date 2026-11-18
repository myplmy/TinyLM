"""Read every native missing-field match with bounded context; never copy bodies."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path[:0] = [str(AUDIT), str(ROOT)]
import read_authored_workset_context_v1 as previous
import authored_literal_readiness_v1 as readiness

guard, core, policy = previous.guard, previous.core, previous.policy
FROZEN_SHA = 'CE947DF5D8668EE6A8B8C7ECA1785D4F3F7F5A0954F5A06907014B5408950AC6'


def native_windows(body, radius=220):
    plain = policy.plain_text(body)
    found = {}
    for name, pattern in [('DANGLING_FIELD', readiness.native.DANGLING_FIELD),
                          ('MISSING_FIELD', readiness.native.cache.MISSING_FIELD)]:
        for match in pattern.finditer(plain):
            found.setdefault(match.span(), []).append(name)
    matches = [dict(start=a, end=b, patterns=found[a, b]) for a, b in sorted(found)]
    intervals = []
    for match in matches:
        lo, hi = max(0, match['start']-radius), min(len(plain), match['end']+radius)
        if intervals and lo <= intervals[-1][1]:
            intervals[-1][1] = max(intervals[-1][1], hi)
        else:
            intervals.append([lo, hi])
    windows = [dict(plain_range=[lo, hi], match_numbers=[i+1 for i, m in enumerate(matches)
                    if lo <= m['start'] and m['end'] <= hi], text=plain[lo:hi]) for lo, hi in intervals]
    assert {i for window in windows for i in window['match_numbers']} == set(range(1, len(matches)+1))
    # This view is a reader, so do not run the admission policy's program parser.
    # The full policy remains mandatory in the separate ROOT readiness checker.
    other = sorted(set(readiness.deferrals(body)) - {
        'NATIVE_UNRESOLVED_FIELD_NOT_LOCALLY_PROVEN',
        'GLOBAL_PROGRAM_WORD_DOES_NOT_PROVE_EACH_EMPTY_PAREN_LITERAL'})
    return dict(view='ALL_NATIVE_REGEX_MATCH_WINDOWS', offset_unit='UNICODE_CODEPOINTS_IN_PINNED_POLICY_PLAIN_TEXT',
        plain_text_sha256=guard.inv.sha(plain), plain_characters=len(plain),
        match_count=len(matches), matches=matches, windows=windows,
        all_matches_of_both_native_patterns_delivered=True,
        matches_are_not_automatically_approved=True, other_deferral_types_not_resolved=True,
        non_native_readiness_deferrals=other)


def render(value):
    head = {key: item for key, item in value.items() if key != 'windows'}
    parts = ['B_NATIVE_MATCH_COVERAGE '+json.dumps(head, ensure_ascii=False)+chr(10)]
    for window in value['windows']:
        parts += ['B_NATIVE_CONTEXT '+json.dumps({key: item for key, item in window.items() if key != 'text'}, ensure_ascii=False)+chr(10),
                  window['text'], chr(10)+'B_NATIVE_CONTEXT_END'+chr(10)]
    if not value['matches']:
        parts += ['NO_NATIVE_REGEX_MATCHES; this does not discharge other source/context flags.'+chr(10)]
    return ''.join(parts)


def collect(scope, ids, first, count):
    assert first >= 1 and 1 <= count <= 3
    assert len(ids)*count*previous.WIDTH+len(ids)*2000 <= previous.MAX_OUTPUT
    selected = previous.preflight(scope, 'c_local_calls', ids)
    output = []
    for row in selected:
        raw = core.base.bounded_payload(ROOT, row['body'])
        assert hashlib.sha256(raw).hexdigest().upper() == row['body']['sha256']
        body = raw.decode('utf-8')
        value = native_windows(body)
        text = render(value)
        first_piece = core.view_part(dict(candidate=text), 'candidate', first, width=previous.WIDTH)
        pieces = [first_piece]+[core.view_part(dict(candidate=text), 'candidate', n, width=previous.WIDTH)
            for n in range(first+1, min(first+count, first_piece['parts']+1))]
        header = dict(id=row['id'], role='c_local_calls', body=row['body'], view=value['view'],
            body_bytes=len(raw), total_native_matches=value['match_count'],
            context_view_bytes=len(text.encode('utf-8')), original_source_opened=False,
            exact_change_diff_recomputed=False, new_first_read_credit=0, root_or_cache_admission=False)
        output.append('B_ASSIGNED_NATIVE_WINDOWS '+json.dumps(header, ensure_ascii=False)+chr(10))
        for piece in pieces:
            output += ['B_CONTEXT_FRAME '+json.dumps({key: item for key, item in piece.items() if key != 'text'}, ensure_ascii=False)+chr(10),
                       piece['text'], chr(10)+('B_CONTEXT_VIEW_EOF' if piece['end_of_view'] else 'B_CONTEXT_MORE_PARTS_REMAIN')+chr(10)]
    result = ''.join(output)
    assert len(result.encode('utf-8')) <= previous.MAX_OUTPUT
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scope', type=Path, required=True)
    parser.add_argument('--scope-sha', required=True)
    parser.add_argument('--ids', nargs='+', required=True)
    parser.add_argument('--part', type=int, default=1)
    parser.add_argument('--count', type=int, default=1)
    args = parser.parse_args()
    guard.activate()
    assert guard.inv.file_sha(Path(previous.__file__)) == FROZEN_SHA
    path = args.scope.resolve()
    assert path.parent == AUDIT and not path.is_symlink()
    assert guard.inv.file_sha(path) == args.scope_sha
    scope = json.loads(path.read_bytes())
    assert scope['reader']['path'] == str(Path(__file__).relative_to(ROOT))
    assert scope['reader']['sha256'] == guard.inv.file_sha(Path(__file__))
    for name, sha in scope['code_pins'].items():
        assert not (ROOT/name).is_symlink() and guard.inv.file_sha(ROOT/name) == sha
    ids = ['expanded_train:'+value if value.isdigit() else value for value in args.ids]
    result = collect(scope, ids, args.part, args.count)
    guard.assert_no_protected_opens()
    print(result, end='')


if __name__ == '__main__':
    main()
