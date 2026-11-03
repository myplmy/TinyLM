"""Render literal fixed-reader commands for the remaining already assigned TASKs."""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

manifest_path = inv.BASE / 'remaining_birth_full_counter_v1/manifest.json'
manifest = inv.cache.read(manifest_path)
contract = inv.cache.read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
sources = {r['id']:r for r in manifest['rows'] if r['role'] == 'context_controls'}
assert len(sources) == 547
assert not (set(sources) & set(contract['restricted_ids']))
assert not ({r['original']['sha256'] for r in sources.values()} & set(contract['restricted_hashes']))
directory = inv.BASE / 'agents/context_controls/remaining_birth_full_counter_v1'
reader = AUDIT / 'read_context_controls_birth_packet_v1.py'
records = []
for number in range(94, 111):
    task = directory / ('TASK_' + str(number).zfill(3) + '.md')
    ids = re.findall(r'^## (expanded_train:[0-9]+|validation:[0-9]+|historical_train:[0-9]+)$', task.read_text(encoding='utf-8'), re.M)
    assert ids and set(ids) <= set(sources)
    lines = ['# 정확 고정 reader 명령: ' + task.stem, '',
        '기존 START/ROOT_SCOPED_INPUT_READER의 권한·금지는 유지한다.',
        '아래 명령을 그대로 복사한다. Python 실행파일을 script 인자로 넣거나 경로를 덧붙이지 않는다.',
        '각 출력은2000문자 이하이고 metadata/원문 END까지 실제 읽어야 한다.',
        '이 목록은 입력 경로 안내이며 실제 판독/시험/정제/채택 증거가 아니다.', '']
    for ident in ids:
        lines.extend(['## ' + ident, '```bash'])
        for packet, pin in enumerate(sources[ident]['reading_parts'], 1):
            begin, end = pin['characters']
            for piece in range(1, (end - begin + 1999) // 2000 + 1):
                lines.append('/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B ' + str(reader)
                    + ' --source-id ' + ident + ' --packet ' + str(packet) + ' --piece ' + str(piece))
        lines.extend(['```', ''])
    path = directory / ('ROOT_EXACT_READER_' + task.stem + '_V1.md')
    with path.open('x', encoding='utf-8') as stream:stream.write(chr(10).join(lines) + chr(10))
    records.append(dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path),
        task=str(task.relative_to(ROOT)), task_sha256=inv.file_sha(task), ids=ids))
inv.write_json(AUDIT / 'CONTROLS_EXACT_REMAINING_COMMAND_PLANS_V1.json',
    dict(status='EXACT_PATH_GUIDES_NOT_BODY_READ', rows=records, source_bodies_opened=0,
        manifest_sha256=inv.file_sha(manifest_path), producer_sha256=inv.file_sha(Path(__file__)),
        goal_complete=False, training_authorized=False))
print(json.dumps(dict(task_guides=len(records), source_bodies_opened=0)))
