"""Publish prospective v2 entry points; keep v1 readers and source bytes immutable."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
GROUP = 'birth_root11_independent_v1'
module = AUDIT / 'birth_input_delivery_guard_v1.py'
spec = importlib.util.spec_from_file_location('birth_delivery_publication', module)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
module_sha = guard.sha(module.read_bytes())


def pin(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=guard.sha(path.read_bytes()))


def save(path, data):
    require_data = data.encode('utf-8')
    guard.require(len(require_data) < 20_000_000, 'artifact needs another shard')
    with path.open('xb') as stream:
        stream.write(require_data)
    return dict(pin(path), bytes=len(require_data))


contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
manifest_path = BASE / GROUP / 'manifest.json'
manifest = json.loads(manifest_path.read_bytes())
contract = json.loads(contract_path.read_bytes())
guard.require(len(manifest['rows']) == 2707, 'assigned manifest changed')
guard.require(not ({r['id'] for r in manifest['rows']} & set(contract['restricted_ids'])),
              'restricted ID in assignment')
guard.require(not ({r['original']['sha256'] for r in manifest['rows']} &
                   set(contract['restricted_hashes'])), 'restricted original hash in assignment')
config_path = AUDIT / 'BIRTH_INPUT_DELIVERY_CONFIG_V1.json'
receipt_path = AUDIT / 'BIRTH_INPUT_DELIVERY_READERS_VERIFIED_V1.json'
guard.require(not config_path.exists() and not receipt_path.exists(), 'publication is immutable')
roles = {}
for role in ('context_controls', 'context_latin'):
    event_directory = BASE / 'birth_input_delivery_events_v1' / role
    for purpose in ('review_inputs', 'root_probes'):
        (event_directory / purpose).mkdir(parents=True, exist_ok=False)
    reader = AUDIT / f'read_{role}_birth_root11_packet_v1.py'
    registry = AUDIT / f'SCOPED_{role.upper()}_BIRTH_ROOT11_INPUTS_V1.json'
    roles[role] = dict(reader=pin(reader), registry=pin(registry),
                       event_directory=str(event_directory.relative_to(ROOT)))
config = dict(schema='BIRTH_INPUT_DELIVERY_CONFIG_V1', cohort=GROUP,
              contract=pin(contract_path), manifest=pin(manifest_path), roles=roles,
              evidence_limit='Successful output emission is not comprehension or authentication.',
              retrospective_emission_evidence_created=False, cache_admitted=0)
config_pin = save(config_path, json.dumps(config, ensure_ascii=False, indent=2) + chr(10))
publications = {}
for role in roles:
    reader_path = AUDIT / f'read_{role}_birth_root11_packet_v2.py'
    code = chr(10).join([
        '"""Fixed assigned packet emission and prospective delivery journal."""',
        'from pathlib import Path', 'import hashlib, importlib.util',
        'HERE = Path(__file__).resolve().parent', 'ROOT = HERE.parents[2]',
        "MODULE = HERE / 'birth_input_delivery_guard_v1.py'",
        'EXPECTED = ' + repr(module_sha),
        "assert not MODULE.is_symlink() and hashlib.sha256(MODULE.read_bytes()).hexdigest().upper() == EXPECTED",
        "spec = importlib.util.spec_from_file_location('fixed_delivery_reader', MODULE)",
        'guard = importlib.util.module_from_spec(spec)', 'spec.loader.exec_module(guard)',
        'guard.cli(ROOT, ' + repr({k: config_pin[k] for k in ('path', 'sha256')}) +
        ', EXPECTED, ' + repr(role) + ')', ''])
    wrapper_pin = save(reader_path, code)
    directory = BASE / 'agents' / role / GROUP
    plans = []
    role_rows = {r['id']: r for r in manifest['rows'] if r['role'] == role}
    # TASK guides contain only source IDs and already assigned packet commands.
    sys.path.insert(0, str(ROOT))
    from scripts.p106b_hold_resolution_review_safeguards_v3 import explicit_task_ids
    seen = set()
    for task in sorted(directory.glob('TASK_*.md')):
        ids = explicit_task_ids(task.read_text(encoding='utf-8'))
        guard.require(ids and ids <= set(role_rows) and not (seen & ids), 'task assignment differs')
        seen.update(ids)
        lines = ['# 실제 입력 전달 기록이 있는 고정 판독 명령: ' + task.stem, '',
                 '총괄이 지정한 활성화 TASK부터 이 명령을 사용한다. 이전 완료 TASK를 소급 판독하지 않는다.',
                 '한 exec에서 한 패킷만 호출하고 출력 예산을 10000토큰 이상으로 둔다.',
                 '모든 원문·후보·전체 diff 및 패킷 끝을 실제로 읽은 다음 공식 리뷰를 저장한다.',
                 '출력 기록은 이해의 증거가 아니다. 잘린 출력은 실제 판독으로 세지 않는다.',
                 '역할은 --probe를 쓰지 않는다. 이 옵션은 총괄 시험용이며 리뷰 선결로 인정되지 않는다.',
                 '기존 원형·후보·확정본·리뷰는 불변이고 새 draft만 작성 중 편집한다.',
                 '이 고정 도구는 새 코드/시험/해시/Git/웹/모델 권한이 아니다.', '']
        for ident in sorted(ids):
            lines += ['## ' + ident, '```bash']
            lines += [str(Path(sys.executable)) + ' -I -B ' + str(reader_path) +
                      ' --source-id ' + ident + ' --packet ' + str(n)
                      for n in range(1, len(role_rows[ident]['reading_parts']) + 1)]
            lines += ['```', '']
        plans.append(save(directory / ('ROOT_DELIVERY_READER_' + task.stem + '_V1.md'),
                          chr(10).join(lines) + chr(10)))
    guard.require(seen == set(role_rows), 'role task coverage incomplete')
    first = next(iter(role_rows))
    good = subprocess.run([sys.executable, '-I', '-B', str(reader_path), '--source-id', first,
                           '--packet', '1', '--probe'], capture_output=True, cwd=ROOT, timeout=30)
    guard.require(good.returncode == 0, good.stderr.decode('utf-8', errors='replace'))
    expected = guard.expected_event(config, contract, {r['id']: r for r in manifest['rows']},
                                    role, first, 1, config_pin['sha256'], module_sha)
    guard.checked_packet_output(good.stdout, expected, role_rows[first]['reading_parts'][0])
    other = next(r['id'] for r in manifest['rows'] if r['role'] != role)
    bad = subprocess.run([sys.executable, '-I', '-B', str(reader_path), '--source-id', other,
                          '--packet', '1', '--probe'], capture_output=True, cwd=ROOT, timeout=30)
    guard.require(bad.returncode != 0 and not bad.stdout, 'other role input emitted')
    blocked = subprocess.run([sys.executable, '-I', '-B', str(reader_path), '--source-id',
                              contract['restricted_ids'][0], '--packet', '1', '--probe'],
                             capture_output=True, cwd=ROOT, timeout=30)
    guard.require(blocked.returncode != 0 and not blocked.stdout and
                  b'restricted source ID' in blocked.stderr, 'protected input was not denied first')
    events, event_pins = guard.load_events(ROOT, config, role)
    guard.require(not events and not event_pins, 'ROOT probe contaminated role review evidence')
    publications[role] = dict(reader=wrapper_pin, plans=plans, sources=len(role_rows),
                              actual_success_cli=good.returncode,
                              actual_other_role_denied_without_stdout=True,
                              actual_protected_id_denied_without_stdout=True,
                              role_review_emission_events=0)
receipt = dict(status='ACTUAL_CPU_FIXED_READER_EMISSION_AND_DENIAL_VERIFIED',
               config=config_pin, module=pin(module), roles=publications,
               protected_body_reads=0, source_body_writes=0, root_probes_used_as_role_evidence=0,
               comprehension_verified=False, activation='PENDING_EXACT_FUTURE_TASK_BOUNDARIES',
               cache_admitted=0, root_adopted=0, goal_complete=False, training_authorized=False)
save(receipt_path, json.dumps(receipt, ensure_ascii=False, indent=2) + chr(10))
print(json.dumps({k: receipt[k] for k in ('status', 'activation', 'cache_admitted')}, ensure_ascii=False))
