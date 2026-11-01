"""Recover an already observed primary reference from this exact chat only."""
from pathlib import Path
import hashlib
import json

AUDIT = Path(__file__).resolve().parent
SESSION = Path('/mnt/c/Users/Uranus/.codex/sessions/2026/10/26/rollout-2026-10-26T17-08-28-01a17740-f435-7243-874c-2b5d58181c4c.jsonl')
TARGET = 'turn33view0'

def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for element in value:
            yield from strings(element)
    elif isinstance(value, dict):
        for element in value.values():
            yield from strings(element)

matches = []
with SESSION.open(encoding='utf-8') as stream:
    for line in stream:
        row = json.loads(line)
        payload = row.get('payload', {})
        if row.get('type') != 'response_item' or payload.get('type') != 'custom_tool_call_output':
            continue
        for value in strings(payload.get('output', [])):
            start = value.find('cite' + TARGET)
            if start < 0:
                continue
            end = value.find('--------------------------------------------------------------------------------', start)
            excerpt = value[max(0, value.rfind(chr(10), 0, start - 1)):end if end >= 0 else len(value)]
            if '1913' not in excerpt or '100th' not in excerpt:
                continue
            matches.append(dict(ordinal=row.get('ordinal'), timestamp=row.get('timestamp'),
                response_sha256=hashlib.sha256(value.encode()).hexdigest().upper(), excerpt=excerpt))
assert len(matches) == 1, [(row['ordinal'], len(row['excerpt'])) for row in matches]
receipt = dict(status='PREVIOUSLY_OBSERVED_PRIMARY_REFERENCE_RECOVERED_NOT_NEW_FETCH',
    source_session=str(SESSION), source_session_id='01a17740-f435-7243-874c-2b5d58181c4c',
    reference=TARGET, observations=matches, later_refetch_timeout_does_not_replace_observation=True)
destination = AUDIT / 'EVIDENCE_291381_PRIOR_PRIMARY_OBSERVATION_V1.json'
body = json.dumps(receipt, ensure_ascii=False, indent=2) + chr(10)
assert len(body.encode()) < 20000000
with destination.open('x', encoding='utf-8') as stream:
    stream.write(body)
print(json.dumps(dict(path=str(destination), ordinal=matches[0]['ordinal'],
    sha256=hashlib.sha256(body.encode()).hexdigest().upper(), excerpt=matches[0]['excerpt'][:2500]), ensure_ascii=False))
