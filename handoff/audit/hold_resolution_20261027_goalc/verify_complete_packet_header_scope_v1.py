"""Reproduce full packet bytes behind stale internal-piece header fields."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
config_path = AUDIT / 'BIRTH_INPUT_DELIVERY_CONFIG_V1.json'
config = json.loads(config_path.read_bytes())
pins = {str(config_path.relative_to(ROOT)): hashlib.sha256(config_path.read_bytes()).hexdigest().upper()}


def read_pin(pin):
    path = ROOT / pin['path']
    assert not path.is_symlink() and path.resolve().is_relative_to(ROOT)
    payload = path.read_bytes()
    assert hashlib.sha256(payload).hexdigest().upper() == pin['sha256']
    pins[pin['path']] = pin['sha256']
    return payload


contract = json.loads(read_pin(config['contract']))
manifest = json.loads(read_pin(config['manifest']))
sources = {row['id']: row for row in manifest['rows']}
rows = []
for ident, packet in [('expanded_train:962627', 1), ('expanded_train:962627', 2),
                      ('expanded_train:96436', 4)]:
    assert ident not in contract['restricted_ids']
    source = sources[ident]
    assert source['original']['sha256'] not in contract['restricted_hashes']
    assert source['role'] == 'context_latin' and 1 <= packet <= len(source['reading_parts'])
    part = source['reading_parts'][packet - 1]
    expected = read_pin(part)
    child = subprocess.run(['bash', str(ROOT / 'tmp/hold-l-v1'), ident, str(packet), '--probe'],
                           cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    assert child.returncode == 0, child.stderr.decode('utf-8')
    prefix = b'APPROVED_COMPLETE_PACKET '
    ending = b'\nEND_APPROVED_COMPLETE_PACKET\n'
    assert child.stdout.startswith(prefix) and child.stdout.endswith(ending)
    header, rest = child.stdout.split(b'\n', 1)
    metadata = json.loads(header[len(prefix):])
    payload = rest[:-len(ending)]
    assert payload == expected
    text = payload.decode('utf-8')
    assert metadata['total_characters'] == len(text)
    assert metadata['sha256'] == part['sha256']
    assert metadata['packet_complete'] is True
    assert metadata['source_packet_sequence_complete'] == (packet == len(source['reading_parts']))
    rows.append(dict(id=ident, packet=packet, packets=len(source['reading_parts']),
                     packet_sha256=part['sha256'], actual_payload_characters=[0, len(text)],
                     historical_header_characters=metadata['characters'],
                     historical_header_piece=metadata['piece'], historical_header_pieces=metadata['pieces'],
                     complete_output_equals_entire_pinned_packet=True,
                     source_packet_sequence_complete=metadata['source_packet_sequence_complete'],
                     contains_original_end='=== END ' + ident + ' original ===' in text,
                     contains_candidate_end='=== END ' + ident + ' candidate ===' in text,
                     contains_full_diff_end='=== END ' + ident + ' full_diff ===' in text,
                     purpose='ROOT_VERIFICATION_PROBE_NOT_REVIEW_INPUT'))
for name in ['read_context_latin_birth_root11_packet_v1.py', 'read_context_latin_birth_root11_packet_v2.py',
             'birth_input_delivery_guard_v1.py', 'COMPLETE_PACKET_HEADER_CLARIFICATION_IMPACT_V1.md',
             Path(__file__).name]:
    path = AUDIT / name
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
guide = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_latin/birth_root11_independent_v1/ROOT_COMPLETE_PACKET_HEADER_CLARIFICATION_V1.md'
pins[str(guide.relative_to(ROOT))] = hashlib.sha256(guide.read_bytes()).hexdigest().upper()
result = dict(status='FULL_PACKET_OUTPUT_VERIFIED_INTERNAL_PIECE_HEADER_LIMIT_RECORDED', rows=rows,
              actual_root_probe_calls=3, input_pins=pins, old_reader_or_config_changed=False,
              retrospective_review_emission_claims=0, semantic_passes_granted=0,
              raw_source_access_added=False, protected_body_reads=0, goal_complete=False)
with (AUDIT / 'COMPLETE_PACKET_HEADER_SCOPE_VERIFIED_V1.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(status=result['status'], root_probes=3, full_pinned_packet_bytes_equal=True,
                     old_reader_changed=False, semantic_passes_granted=0), ensure_ascii=False))
