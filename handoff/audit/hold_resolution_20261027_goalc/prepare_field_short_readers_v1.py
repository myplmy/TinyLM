"""Prepare role-bound field registries from existing metadata, without body IO."""
from pathlib import Path
import hashlib
import json
import re
import shlex
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
PYTHON = Path('/home/uranus/miniforge3/envs/tlm_torch/bin/python')
HELPER_SHA = 'DCEB4BD2CB9ABD8681ACEE9F2604B69D55625B20D28BCB1956C7B99E3E1D96A6'


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def pin(path):
    data = path.read_bytes()
    require(not path.is_symlink() and 0 < len(data) < 20_000_000, 'invalid local tool or metadata file')
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(data), bytes=len(data))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def write_new(path, value):
    data = ((json.dumps(value, ensure_ascii=False, indent=2) + chr(10))
            if isinstance(value, dict) else value).encode('utf-8')
    require(0 < len(data) < 20_000_000, 'output must be split')
    with path.open('xb') as stream:
        stream.write(data)
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(data), bytes=len(data))


def launcher(role, config_pin, entry_pin):
    source = chr(10).join([
        'from pathlib import Path', 'import hashlib, importlib.util, sys',
        'root = Path(' + repr(str(ROOT)) + ')',
        'path = root / ' + repr(entry_pin['path']),
        'expected = ' + repr(entry_pin['sha256']),
        "if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest().upper() != expected:",
        "    raise SystemExit('fixed field entry bytes changed; no packet read')",
        'values = sys.argv[1:]',
        "sys.argv = [str(path), '--page', values[0], '--source-id', values[1], '--packet', values[2], '--piece', values[3] if len(values) == 4 else '1']",
        "spec = importlib.util.spec_from_file_location('fixed_field_entry', path)",
        'entry = importlib.util.module_from_spec(spec)', 'spec.loader.exec_module(entry)',
        'entry.cli(root, ' + repr(role) + ', ' + repr({k: config_pin[k] for k in ('path', 'sha256')}) + ')'])
    return chr(10).join(['#!/bin/bash', 'set -eu',
        'if [ "$#" -ne 3 ] && [ "$#" -ne 4 ]; then',
        "  echo 'usage: shortcut PAGE SOURCE_ID PACKET_NUMBER [PIECE_NUMBER]' >&2", '  exit 64', 'fi',
        'exec ' + shlex.quote(str(PYTHON)) + ' -I -B -c ' + shlex.quote(source) + ' "$@"', ''])


def main():
    contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
    contract = json.loads(contract_path.read_bytes())
    helper_path = AUDIT / 'scoped_packet_reader_v1.py'
    require(pin(helper_path)['sha256'] == HELPER_SHA, 'existing scoped helper changed')
    entry_path = AUDIT / 'field_scoped_packet_entry_v1.py'
    roles = {'context_hangul': 'h', 'historical_review': 'j', 'legacy_review': 'g'}
    directory = AUDIT / 'field_short_reader_registries_v1'
    directory.mkdir(exist_ok=False)
    config = dict(schema='FIELD_SCOPED_SHORT_ENTRY_V1', contract=pin(contract_path), helper=pin(helper_path),
                  roles={role: {} for role in roles}, manifest_pins=[], excluded_restricted_metadata=[])
    counts = {role: dict(sources=0, packets=0) for role in roles}
    for page in range(1, 37):
        cohort = f'remaining_field_title_page_{page:03}_counter_v1'
        manifest_path = BASE / cohort / 'manifest.json'
        manifest = json.loads(manifest_path.read_bytes())
        config['manifest_pins'].append(pin(manifest_path))
        sources = {row['id']: row for row in manifest['rows']}
        for role in roles:
            ids = manifest['assignments'][role]
            ids = ids['ids'] if isinstance(ids, dict) else ids
            require(len(ids) == len(set(ids)), 'duplicate source in role assignment')
            registry = dict(role=role, page=page,
                            allowed_packet_directory=str((BASE / cohort / 'reading_packets_v1').relative_to(ROOT)),
                            sources={}, source_metadata={})
            for ident in ids:
                source = sources[ident]
                require(source['role'] == role, 'source role differs from manifest assignment')
                original_sha = source['original']['sha256']
                if ident in contract['restricted_ids'] or original_sha in contract['restricted_hashes']:
                    config['excluded_restricted_metadata'].append(dict(id=ident, role=role, page=page,
                                                                       original_sha256=original_sha, body_opened=False))
                    continue
                parts = source['reading_parts']
                require(parts, 'assigned source lacks reading parts')
                for number, part in enumerate(parts, 1):
                    path = Path(part['path'])
                    require(path.parent == Path(registry['allowed_packet_directory']), 'packet left exact page namespace')
                    require(path.name == ident.replace(':', '_') + '_' + str(number).zfill(4) + '.txt',
                            'packet order/source identity changed')
                    require(re.fullmatch('[0-9A-F]{64}', part['sha256']) is not None, 'packet SHA missing')
                registry['sources'][ident] = parts
                registry['source_metadata'][ident] = dict(role=role, original_sha256=original_sha)
                counts[role]['sources'] += 1
                counts[role]['packets'] += len(parts)
            config['roles'][role][str(page)] = write_new(directory / f'{role}_page_{page:03}.json', registry)
    config_path = AUDIT / 'FIELD_SHORT_READER_CONFIG_V1.json'
    config_pin = write_new(config_path, config)
    entry_pin = pin(entry_path)
    outputs = []
    for role, short in roles.items():
        wrapper = ROOT / 'tmp' / ('hold-' + short + '-field-v1')
        wrapper_pin = write_new(wrapper, launcher(role, config_pin, entry_pin))
        guide = BASE / 'agents' / role / 'ROOT_FIELD_SHORT_READER_ENTRY_V1.md'
        text = '# 기존 분할 판독기의 field 전용 짧은 호출' + chr(10)*2
        text += '자기 역할의 field36페이지 명단만 읽는다. 명령 시작은 `bash ' + str(wrapper) + '`이고 뒤에 페이지숫자, 정확원문ID, 정확패킷번호, 조각번호(생략하면1)를 순서대로 붙인다.' + chr(10)*2
        text += '기존TASK/READING_VIEWS와 ROOT_IDENTITY_TASK의 지정 읽기·동일후보 생략계획은 그대로다. 한exec 한조각, 출력한도10000토큰 이상으로 읽고 pieces/characters/packet_complete/source_packet_sequence_complete와 실제원문/후보/full_diff의 논리END·EOF를 모두 확인한다. 첫조각이 packet_complete=false이면 다음조각을 읽는다. 파일명/0채움/부모경로는 직접조합하지 않는다.' + chr(10)*2
        text += '보호ID와원형SHA는본문보다먼저검사하며 기존helper의2000자분할/SHA/역할명단/순서검사를 재사용한다. 시간journal·이해/인증·의미PASS를 새로 제공하지 않는다. 완료한원문은도구때문에재독하지않고 현재입력을마친뒤정확다음미착수부터사용한다. source가없거나거부/잘림이면판독으로세지않고정확지정값을확인한다. 다른역할·other유형은이진입점범위가아니다.' + chr(10)
        outputs.append(dict(role=role, wrapper=wrapper_pin, guide=write_new(guide, text), counts=counts[role]))
    result = dict(status='FIELD_ROLE_SCOPED_REGISTRIES_AND_SHORT_ENTRIES_PREPARED_NOT_REVIEWED',
                  config=config_pin, entry=entry_pin, helper=pin(helper_path), outputs=outputs,
                  excluded_restricted_metadata=config['excluded_restricted_metadata'],
                  preparation_original_candidate_packet_body_reads=0, source_redecoded=False,
                  previous_inputs_or_reviews_changed=False, new_semantic_passes=0, goal_complete=False)
    write_new(AUDIT / 'FIELD_SHORT_READERS_PREPARED_V1.json', result)
    print(json.dumps(dict(status=result['status'], counts=counts,
                         excluded_metadata=len(config['excluded_restricted_metadata']), body_reads=0), ensure_ascii=False))


if __name__ == '__main__':
    main()
