"""Keep the full source; bound long diffs and choose the smaller exact transport."""
from bisect import bisect_left
from collections import Counter
from pathlib import Path
import difflib
import hashlib
import importlib.util
from unittest.mock import patch

PREVIOUS = Path(__file__).with_name('lossless_review_packet_v2.py')
assert not PREVIOUS.is_symlink()
assert hashlib.sha256(PREVIOUS.read_bytes()).hexdigest().upper() == '431CA48F79CF022EECFA558AFC600430829BE119C22C04F95741603957248FCB'
spec = importlib.util.spec_from_file_location('frozen_lossless_v2_for_v3', PREVIOUS)
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
base = previous.base
resolve_assignment, load_pair = previous.resolve_assignment, previous.load_pair
view_part, require = previous.view_part, previous.require
PROTOCOL, VIEW_BYTES = previous.PROTOCOL, previous.VIEW_BYTES
MAX_OPTIMIZED_CHARACTERS = 2_000_000
MAX_OPTIMIZED_LINES = 200_000
SMALL_GAP_CHARACTERS = 6000


def ordered_anchors(old_lines, new_lines):
    old_counts, new_counts = Counter(old_lines), Counter(new_lines)
    positions = {line:n for n,line in enumerate(new_lines) if new_counts[line] == 1}
    pairs = [(n,positions[line]) for n,line in enumerate(old_lines)
             if old_counts[line] == 1 and line in positions]
    tails, indices, links = [], [], [-1]*len(pairs)
    for n, (_a,b) in enumerate(pairs):
        k = bisect_left(tails,b)
        if k:
            links[n] = indices[k-1]
        if k == len(tails):
            tails.append(b);indices.append(n)
        else:
            tails[k],indices[k] = b,n
    if not indices:
        return []
    result = []
    n = indices[-1]
    while n >= 0:
        result.append(pairs[n]);n=links[n]
    return result[::-1]


def anchored_changes(source, candidate):
    old_lines, new_lines = source.splitlines(keepends=True), candidate.splitlines(keepends=True)
    if max(len(old_lines),len(new_lines)) > MAX_OPTIMIZED_LINES:
        return None
    anchors = ordered_anchors(old_lines,new_lines)
    if not anchors:
        return None
    old_offsets, new_offsets = base._offsets(old_lines), base._offsets(new_lines)
    changes = []

    def add(tag,a,b,c,d):
        if tag != 'equal':
            changes.append(dict(op=tag,source_range=[a,b],candidate_range=[c,d],after=candidate[c:d]))

    def gap(a,b,c,d):
        before, after = source[a:b],candidate[c:d]
        if before == after:
            return
        if len(before)+len(after) <= SMALL_GAP_CHARACTERS:
            for tag,i,j,k,l in difflib.SequenceMatcher(None,before,after,autojunk=True).get_opcodes():
                add(tag,a+i,a+j,c+k,c+l)
            return
        first = 0
        while first < min(len(before),len(after)) and before[first] == after[first]:
            first += 1
        last = 0
        while (last < min(len(before),len(after))-first and
               before[len(before)-last-1] == after[len(after)-last-1]):
            last += 1
        i,j,k,l = a+first,b-last,c+first,d-last
        add('insert' if i==j else 'delete' if k==l else 'replace',i,j,k,l)

    a = c = 0
    for old_n,new_n in anchors:
        b,d = old_offsets[old_n],new_offsets[new_n]
        gap(a,b,c,d)
        require(old_lines[old_n] == new_lines[new_n], 'line anchor differs')
        a,c = old_offsets[old_n+1],new_offsets[new_n+1]
    gap(a,len(source),c,len(candidate))
    require(base.reconstruct(source,changes) == candidate, 'anchored candidate reconstruction differs')
    return changes


def prepare_views(original_raw, candidate_raw):
    baseline = previous.prepare_views(original_raw,candidate_raw)
    source,candidate = baseline['original'],candidate_raw.decode('utf-8')
    if source == candidate or not 80_000 < len(source)+len(candidate) <= MAX_OPTIMIZED_CHARACTERS:
        return baseline
    changes = anchored_changes(source,candidate)
    if changes is None:
        return baseline
    with patch.object(base,'changes_between',lambda _source,_candidate:changes):
        optimized = previous.prepare_views(original_raw,candidate_raw)
    if len(optimized['pair'].encode('utf-8')) < len(baseline['pair'].encode('utf-8')):
        return optimized
    return baseline
