"""Create short role-bound calls; keep the existing v2 reader and journals."""
from pathlib import Path
import hashlib
import json
import shlex
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
PYTHON = Path('/home/uranus/miniforge3/envs/tlm_torch/bin/python')


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def shortcut_text(python, reader, expected_sha):
    assert len(expected_sha) == 64 and set(expected_sha) <= set('0123456789ABCDEF')
    source = chr(10).join([
        'from pathlib import Path', 'import hashlib, runpy, sys',
        'path = Path(' + repr(str(reader)) + ')',
        'expected = ' + repr(expected_sha),
        "if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest().upper() != expected:",
        "    raise SystemExit('fixed reader bytes changed; no packet read')",
        'arguments = sys.argv[1:]',
        "sys.argv = [str(path), '--source-id', arguments[0], '--packet', arguments[1]] + arguments[2:]",
        "runpy.run_path(str(path), run_name='__main__')"])
    return chr(10).join([
        '#!/bin/bash', 'set -eu',
        'if [ "$#" -eq 2 ]; then :',
        'elif [ "$#" -eq 3 ] && [ "$3" = "--probe" ]; then :',
        'else',
        "  echo 'usage: shortcut SOURCE_ID PACKET_NUMBER [--probe]' >&2",
        '  exit 64', 'fi',
        'exec ' + shlex.quote(str(python)) + ' -I -B -c ' + shlex.quote(source) + ' "$@"', ''])


def write_new(path, text):
    data = text.encode('utf-8')
    assert 0 < len(data) < 20_000_000
    with path.open('xb') as stream:
        stream.write(data)
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(data), bytes=len(data))


def main():
    assert PYTHON.is_file()
    rows = []
    for short, role in [('c', 'context_controls'), ('l', 'context_latin')]:
        reader = AUDIT / ('read_' + role + '_birth_root11_packet_v2.py')
        assert not reader.is_symlink() and reader.is_file()
        reader_pin = dict(path=str(reader.relative_to(ROOT)), sha256=sha(reader.read_bytes()))
        shortcut = ROOT / 'tmp' / ('hold-' + short + '-v1')
        wrapper_pin = write_new(shortcut, shortcut_text(PYTHON, reader, reader_pin['sha256']))
        directory = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc/agents' / role / 'birth_root11_independent_v1'
        guide = directory / 'ROOT_SHORT_READER_ENTRY_V1.md'
        text = '# 동일한 v2 판독기의 짧은 호출 경로' + chr(10)*2
        text += '자기 역할만 사용한다. 기존 ROOT_DELIVERY_READER_TASK의 원문ID와 정확 패킷번호를 두 위치 인자로 전달한다. 명령의 시작은 `bash ' + str(shortcut) + '`이다. 뒤에 원문ID, 숫자 패킷번호를 순서대로 적는다.' + chr(10)*2
        text += '한 exec에서 지정 패킷 하나만 읽고 출력 한도는 10000토큰 이상을 준다. 기존 v2의 metadata와 END, 최종 original/candidate/full_diff 논리 END 및 EOF를 확인한다. 다른 packet이나 경로를 추정하지 않는다. 실제 wrapper SHA는 ' + wrapper_pin['sha256'] + ', 기존 v2 SHA는 ' + reader_pin['sha256'] + '이다.' + chr(10)*2
        text += '기존 guard/config/registry/journal과 역할·ID·SHA·순서 검사는 그대로다. 완료한 입력을 이 도구 때문에 다시 읽지 말고 자기 최신 완료 TASK 다음 미착수부터 쓴다. --probe는 총괄 시험 전용이며 Luna 정식 판독에는 붙이지 않는다. 실패/잘림은 판독에 세지 않고 정확 명령의 성공 출력만 사용한다.' + chr(10)
        guide_pin = write_new(guide, text)
        rows.append(dict(role=role, reader=reader_pin, shortcut=wrapper_pin, guide=guide_pin))
    result = dict(status='SHORT_ROLE_BOUND_ENTRY_POINTS_CREATED_NOT_INPUT_DELIVERY_OR_SEMANTIC_PASS',
                  rows=rows, existing_v2_bytes_changed=False, past_reviews_replayed=False,
                  root_or_cache_adoptions=0, protected_body_reads=0, goal_complete=False)
    write_new(AUDIT / 'BIRTH_READER_SHORTCUTS_PREPARED_V1.json', json.dumps(result, ensure_ascii=False, indent=2) + chr(10))
    print(json.dumps(dict(status=result['status'], roles=len(rows), corpus_or_review_writes=0), ensure_ascii=False))


if __name__ == '__main__':
    main()
