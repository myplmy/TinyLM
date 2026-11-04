"""Read frozen literal numeric contexts; hints never count as semantic proofs."""
from pathlib import Path
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
A = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
wanted = set(sys.argv[1:])
assert 1 <= len(wanted) <= 4
assert all(re.fullmatch(r'(?:expanded_train|validation):[0-9]+', item) for item in wanted)
guard_raw = (A / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').read_bytes()
assert hashlib.sha256(guard_raw).hexdigest().upper() == 'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF'
guard = json.loads(guard_raw)
assert wanted.isdisjoint(guard['restricted_ids'])
raw = (A / 'LITERAL_BOUND_BODY_DIAGNOSTICS_COMPLETE_V1.json').read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == '09850C948D8F411052DC05CEA3363D6550DE205262773528A8E2AA662CE81977'
complete = json.loads(raw)

def merge(spans):
    result = []
    for lo, hi in sorted(spans):
        if result and lo <= result[-1][1]:
            result[-1][1] = max(result[-1][1], hi)
        else:
            result.append([lo, hi])
    return result

found = set()
for shard in complete['shards']:
    raw = (ROOT / shard['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest().upper() == shard['sha256']
    for row in json.loads(raw):
        if row['id'] not in wanted:
            continue
        assert row['id'] not in found
        found.add(row['id'])
        assert row['id'] not in guard['restricted_ids']
        assert row['original']['sha256'] not in guard['restricted_hashes']
        texts = []
        for item in [row['original'], row['body']]:
            path = ROOT / item['path']
            assert path.resolve().is_relative_to(BASE) and not path.is_symlink()
            raw = path.read_bytes()
            assert hashlib.sha256(raw).hexdigest().upper() == item['sha256']
            texts.append(raw.decode('utf-8'))
        original, body = texts
        body_ranges, source_ranges, missing = [], [], []
        for flag in row['numeric_atom_flags']:
            start, end = flag['body_span']
            assert body[start:end] == flag['body_token']
            body_ranges.append([max(0, start-170), min(len(body), end+180)])
            point = None
            if flag.get('source_span') is not None:
                point = flag['source_span'][0]
            else:
                for width in (60, 40, 20):
                    before, after = body[max(0, start-width):start], body[end:end+width]
                    if len(before) >= 15 and original.count(before) == 1:
                        point = original.index(before) + len(before)
                        break
                    if len(after) >= 15 and original.count(after) == 1:
                        point = original.index(after)
                        break
            if point is None:
                missing.append(flag['body_span'])
            else:
                source_ranges.append([max(0, point-190), min(len(original), point+240)])
        if len(original) <= 2000:
            source_ranges = [[0, len(original)]]
        print(json.dumps(dict(id=row['id'], role=row['role'], original=row['original'],
            body=row['body'], review=row['review'], original_chars=len(original), body_chars=len(body),
            flags=row['numeric_atom_flags'],
            body_contexts=[dict(range=p, text=body[p[0]:p[1]]) for p in merge(body_ranges)],
            source_contexts_hints_not_proofs=[dict(range=p, text=original[p[0]:p[1]]) for p in merge(source_ranges)],
            targets_without_hint=missing), ensure_ascii=False))
assert found == wanted, 'requested source not in this frozen diagnostic'
