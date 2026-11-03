"""Prove a duplicate candidate frame from exact bytes and ordered pinned packets."""
import hashlib

WIDTH = 2000
NO_DIFF = '비교한 전문의 줄 차이 없음'


def digest(data):
    return hashlib.sha256(data).hexdigest().upper()


def frame(ident, kind, text):
    return (f'=== BEGIN {ident} {kind} characters={len(text)} ===' + chr(10)
        + text + chr(10) + f'=== END {ident} {kind} ===' + chr(10))


def prove_identical(ident, original, candidate, original_sha, candidate_sha, packets):
    if digest(original) != original_sha or digest(candidate) != candidate_sha:
        raise ValueError('source bytes differ from exact pins')
    if original != candidate:
        raise ValueError('different candidate requires complete separate reading')
    text = original.decode('utf-8')
    first = frame(ident, 'original', text)
    second = frame(ident, 'candidate', text)
    final = frame(ident, 'full_diff', NO_DIFF)
    whole = first + second + final
    expected_count = (len(whole) + WIDTH - 1) // WIDTH
    if len(packets) != expected_count:
        raise ValueError('packet count differs')
    joined = []
    for index, packet in enumerate(packets):
        payload = packet['payload']
        fragment = payload.decode('utf-8')
        begin = index * WIDTH
        if packet['characters'] != [begin, begin + len(fragment)]:
            raise ValueError('packet offsets differ')
        if digest(payload) != packet['sha256']:
            raise ValueError('packet bytes differ from exact pin')
        if fragment != whole[begin:begin + WIDTH]:
            raise ValueError('ordered packet reconstruction differs')
        joined.append(fragment)
    if ''.join(joined) != whole:
        raise ValueError('full ordered reconstruction differs')
    last_original = (len(first) + WIDTH - 1) // WIDTH
    first_diff = (len(first) + len(second)) // WIDTH + 1
    required = sorted(set(range(1, last_original + 1)) | set(range(first_diff, len(packets) + 1)))
    return dict(protocol='EXACT_IDENTICAL_INPUT_READING_V1', source_characters=len(text),
        original_frame_characters=[0, len(first)],
        candidate_frame_characters=[len(first), len(first) + len(second)],
        full_diff_frame_characters=[len(first) + len(second), len(whole)],
        original_packets=[1, last_original], full_diff_packets=[first_diff, len(packets)],
        required_packets=required,
        duplicate_only_packets=[n for n in range(1, len(packets) + 1) if n not in required],
        original_and_candidate_bytes_equal=True, ordered_packet_reconstruction_equal=True,
        two_independent_readings=False, cache_admitted=False)
