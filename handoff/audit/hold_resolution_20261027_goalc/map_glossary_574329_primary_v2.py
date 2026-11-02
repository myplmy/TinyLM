"""Map publisher headwords to exact existing definitions; write evidence, not corpus prose."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
EVIDENCE = BASE / 'glossary_574329_primary_evidence_v1'
source_path = EVIDENCE / 'primary_sequence.json'
manifest_path = BASE / 'repeat_named_full_independent_v1/manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
source = next(r for r in manifest['rows'] if r['id'] == 'expanded_train:574329')
contract = json.loads((AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').read_text())
assert source['id'] not in contract['restricted_ids']
assert source['original']['sha256'] not in contract['restricted_hashes']


def sha(value):
    if isinstance(value, str):
        value = value.encode('utf-8')
    return hashlib.sha256(value).hexdigest().upper()


raw_bytes = (ROOT / source['original']['path']).read_bytes()
assert sha(raw_bytes) == source['original']['sha256']
raw = raw_bytes.decode('utf-8')
sequence = json.loads(source_path.read_text(encoding='utf-8'))
records = sequence['records']
# These mixed-case/cross-reference headings were read in the actual publisher sequence.
extra = {24, 25, 63, 74, 135, 144, 150, 269, 303, 313, 519, 521}
heads = []
for index, record in enumerate(records):
    text = record['text']
    letters = [c for c in text if c.isalpha()]
    uppercase = letters and sum(c.isupper() for c in letters) / len(letters) > .72
    if 6 <= index < 528 and text != 'BACK TO TOP' and (
        len(text) < 100 and uppercase or index in extra or
        text.startswith(('AIR-BRUSH (', 'ETCHING “A la Plume”', 'INTAGLIO.'))
    ):
        if text.startswith('INTAGLIO.'):
            head, inline = text.split(' A printing process', 1)
            inline = 'A printing process' + inline
        else:
            head, inline = text, ''
        heads.append(dict(index=index, heading=head, inline=inline))
assert len(heads) == 216
chars, offsets = [], []
for offset, char in enumerate(raw):
    if not char.isspace():
        chars.append(char)
        offsets.append(offset)
normalized = ''.join(chars)
rows, counts = [], Counter()
for number, head in enumerate(heads):
    stop = heads[number + 1]['index'] if number + 1 < len(heads) else 528
    definitions = ([head['inline']] if head['inline'] else []) + [
        r['text'] for r in records[head['index'] + 1:stop] if r['text'] != 'BACK TO TOP']
    definition = chr(10).join(definitions)
    if head['heading'] == 'PROOF.':
        suffix = ' Read more: What is an artist proof?'
        assert definition.endswith(suffix)
        definition = definition[:-len(suffix)]
    needle = ''.join(c for c in definition if not c.isspace())
    positions = [m.start() for m in re.finditer(re.escape(needle), normalized)] if needle else []
    row = dict(heading=head['heading'], publisher_sequence_index=head['index'],
        publisher_window=records[head['index']]['window'],
        publisher_window_line=records[head['index']]['line'],
        definition_sha256=sha(definition), definition_characters=len(definition),
        exact_normalized_definition_matches=len(positions), source_url=sequence['source_url'])
    if len(positions) == 1:
        start = offsets[positions[0]]
        end = offsets[positions[0] + len(needle) - 1] + 1
        prefix = raw[max(0, start - len(head['heading']) - 30):start]
        present = ''.join(c for c in head['heading'] if not c.isspace()) in ''.join(prefix.split())
        row.update(original_definition_span=[start, end],
            original_line=raw.count(chr(10), 0, start) + 1,
            original_definition_sha256=sha(raw[start:end]),
            original_definition_prefix=raw[start:min(end, start + 100)],
            status='HEADING_ALREADY_PRESENT' if present else 'EXACT_PRIMARY_HEADWORD_RESTORATION_CANDIDATE')
    elif not needle and ''.join(head['heading'].split()) in normalized:
        row['status'] = 'HEADING_ALREADY_PRESENT'
        row['definition_not_required_for_existing_cross_reference_heading'] = True
    else:
        row['status'] = 'NO_UNIQUE_FULL_DEFINITION_MATCH_REQUIRES_MANUAL_CONTEXT'
    counts[row['status']] += 1
    rows.append(row)
result = dict(status='PUBLISHER_DEFINITION_ALIGNMENT_EVIDENCE_NOT_CLEANED_CORPUS',
    id=source['id'], original=source['original'], source_url=sequence['source_url'],
    publisher_sequence=dict(path=str(source_path.relative_to(ROOT)), sha256=sha(source_path.read_bytes())),
    counts=dict(counts), rows=rows,
    limits='Whitespace-only normalization; unmatched definitions are not approved. A textual publisher match does not recover cache source provenance. Luna must read context and write any actual cleaned TXT.',
    producer_sha256=sha(Path(__file__).read_bytes()), root_approved=False, cache_admitted=False,
    goal_complete=False, training_authorized=False)
out = AUDIT / 'GLOSSARY_574329_PRIMARY_DEFINITION_ALIGNMENT_V2.json'
payload = (json.dumps(result, ensure_ascii=False, indent=2) + chr(10)).encode('utf-8')
assert len(payload) < 20_000_000
with out.open('xb') as stream:
    stream.write(payload)
lines = ['# 574329의 발행처 정의 대조 근거', '',
    '출처: ' + sequence['source_url'],
    '원문 정의와 공백만 무시한 전문 일치가 한 곳인 경우에만 표제 복원 후보로 제시한다. 실제 새 본문은 Luna가 작성한다.',
    '캐시의 출처 종류 UNKNOWN은 유지한다. 불일치 정의·미지 용어·빈 범례를 추측하지 않는다.', '',
    '| 발행처 표제 | 원문 정의 줄 | 문자 범위 | 상태 |', '|---|---:|---|---|']
for row in rows:
    span = row.get('original_definition_span', [])
    lines.append('| ' + row['heading'].replace('|', '&#124;') + ' | ' + str(row.get('original_line', '—')) +
        ' | ' + str(span) + ' | ' + row['status'] + ' |')
with (EVIDENCE / 'ROOT_PRIMARY_ALIGNMENT_V2.md').open('x', encoding='utf-8') as stream:
    stream.write(chr(10).join(lines) + chr(10))
print(json.dumps(dict(counts=dict(counts), unmatched=[r['heading'] for r in rows if
    r['status'] == 'NO_UNIQUE_FULL_DEFINITION_MATCH_REQUIRES_MANUAL_CONTEXT']), ensure_ascii=False))
