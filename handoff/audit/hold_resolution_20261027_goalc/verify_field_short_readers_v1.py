"""Verify real bounded field calls without treating probes as semantic review."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def read_pin(pin):
    path = ROOT / pin['path']
    assert not path.is_symlink() and path.resolve().is_relative_to(ROOT.resolve())
    data = path.read_bytes()
    assert 0 < len(data) < 20_000_000 and sha(data) == pin['sha256']
    return data


def pin(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(data), bytes=len(data))


prepared_path = AUDIT / 'FIELD_SHORT_READERS_PREPARED_V1.json'
prepared = json.loads(prepared_path.read_bytes())
config = json.loads(read_pin(prepared['config']))
contract = json.loads(read_pin(config['contract']))
read_pin(prepared['entry'])
assert prepared['helper'] == config['helper']
read_pin(config['helper'])
registries = {}
for role, pages in config['roles'].items():
    for page, registry_pin in pages.items():
        value = json.loads(read_pin(registry_pin))
        assert value['role'] == role and value['page'] == int(page)
        registries[role, int(page)] = value
assert len(registries) == 108


def invoke(wrapper, page, ident, packet, piece=None):
    args = ['bash', str(ROOT / wrapper['path']), str(page), ident, str(packet)]
    if piece is not None:
        args.append(str(piece))
    return subprocess.run(args, cwd=ROOT, capture_output=True, timeout=30)


def decode_piece(result):
    assert result.returncode == 0, result.stderr.decode('utf-8')
    assert result.stderr == b''
    header, remainder = result.stdout.split(b'\n', 1)
    assert header.startswith(b'APPROVED_PACKET_PIECE ')
    ending = b'\nEND_APPROVED_PACKET_PIECE\n'
    assert remainder.endswith(ending)
    metadata = json.loads(header[len(b'APPROVED_PACKET_PIECE '):])
    text = remainder[:-len(ending)].decode('utf-8')
    return metadata, text


cases = {
    'context_hangul': (6, 'expanded_train:82044'),
    'historical_review': (5, 'expanded_train:56714'),
    'legacy_review': (5, 'expanded_train:59660'),
}
positive = []
wrappers = {}
for output in prepared['outputs']:
    role = output['role']
    read_pin(output['wrapper'])
    read_pin(output['guide'])
    wrappers[role] = output['wrapper']
    page, ident = cases[role]
    registry = registries[role, page]
    source = registry['source_metadata'][ident]
    assert ident not in contract['restricted_ids']
    assert source['original_sha256'] not in contract['restricted_hashes']
    parts = registry['sources'][ident]
    expected = parts[0]
    metadata, text = decode_piece(invoke(output['wrapper'], page, ident, 1))
    pieces, chunks, receipts = metadata['pieces'], [], []
    for number in range(1, pieces + 1):
        if number > 1:
            metadata, text = decode_piece(invoke(output['wrapper'], page, ident, 1, number))
        begin = sum(map(len, chunks))
        assert metadata['source_id'] == ident and metadata['packet'] == 1
        assert metadata['packets'] == len(parts) and metadata['path'] == expected['path']
        assert metadata['sha256'] == expected['sha256']
        assert metadata['piece'] == number and metadata['pieces'] == pieces
        assert 0 < len(text) <= 2000 and metadata['characters'] == [begin, begin + len(text)]
        assert metadata['packet_complete'] == (number == pieces)
        assert metadata['source_packet_sequence_complete'] == (len(parts) == 1 and number == pieces)
        chunks.append(text)
        receipts.append(dict(piece=number, characters=metadata['characters'], text_sha256=sha(text.encode('utf-8'))))
    reconstructed = ''.join(chunks).encode('utf-8')
    assert len(''.join(chunks)) == metadata['total_characters']
    assert sha(reconstructed) == expected['sha256']
    positive.append(dict(role=role, page=page, source_id=ident, packet=1,
                         packet_sha256=sha(reconstructed), pieces=receipts,
                         default_piece_argument_verified=True,
                         exact_packet_reconstruction_verified=True,
                         full_source_semantic_review=False))

negative = []
wrapper = wrappers['context_hangul']
for page, ident, packet, piece, reason in [
    (5, 'expanded_train:60313', 1, None, 'other role source'),
    (5, 'expanded_train:82044', 1, None, 'wrong page source'),
    (6, 'expanded_train:82044', 1000000, None, 'packet outside sequence'),
    (6, 'expanded_train:82044', 1, 0, 'piece outside sequence'),
    (6, 'expanded_train:756966', 1, None, 'restricted source ID'),
]:
    result = invoke(wrapper, page, ident, packet, piece)
    assert result.returncode != 0 and result.stdout == b''
    negative.append(dict(page=page, source_id=ident, packet=packet, piece=piece,
                         reason=reason, exit_code=result.returncode, stdout_bytes=0,
                         stderr_last_line=result.stderr.decode('utf-8').splitlines()[-1]))

paths = [prepared_path, Path(__file__).resolve(),
         AUDIT / 'prepare_field_short_readers_v1.py',
         AUDIT / 'test_field_scoped_packet_entry_v1.py',
         AUDIT / 'test_prepare_field_short_readers_v1.py',
         AUDIT / 'test_scoped_packet_reader_v1.py',
         AUDIT / 'FIELD_SHORT_READER_CPU_TESTS_20261104_V1.log']
result = dict(status='FIELD_SHORT_READERS_ACTUAL_BOUNDED_CALLS_AND_DENIALS_VERIFIED',
              prepared=pin(prepared_path), positive=positive, negative=negative,
              pinned_registry_count=108,
              regression_tests=dict(tool_chunk='1a7566', count=19, failures=0, exit_code=0),
              input_pins=[pin(path) for path in paths],
              unchanged_existing_helper=config['helper'],
              protected_body_reads=0, corpus_or_review_writes=0,
              historical_input_delivery_events_created=False,
              semantic_review_or_OS_authentication_inferred=False,
              source_redecoding=False, root_or_cache_adoptions=0,
              goal_complete=False, training_authorized=False)
target = AUDIT / 'FIELD_SHORT_READERS_RUNTIME_VERIFIED_V1.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(status=result['status'], roles=len(positive), denials=len(negative),
                     pieces=sum(len(row['pieces']) for row in positive), tests=19,
                     protected_body_reads=0, new_semantic_passes=0), ensure_ascii=False))
