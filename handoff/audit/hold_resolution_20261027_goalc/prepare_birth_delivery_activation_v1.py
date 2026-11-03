"""Record exact acknowledged future TASK boundaries, without retroactive evidence."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
GROUP = 'birth_root11_independent_v1'
sys.path.insert(0, str(ROOT))
from scripts.p106b_hold_resolution_review_safeguards_v3 import explicit_task_ids

module = AUDIT / 'birth_input_delivery_guard_v1.py'
spec = importlib.util.spec_from_file_location('delivery_activation_guard', module)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
parser = argparse.ArgumentParser()
parser.add_argument('--controls-first-task', required=True, type=int)
parser.add_argument('--latin-first-task', required=True, type=int)
args = parser.parse_args()
receipt = json.loads((AUDIT / 'BIRTH_INPUT_DELIVERY_READERS_VERIFIED_V1.json').read_bytes())
config_pin = {k: receipt['config'][k] for k in ('path', 'sha256')}
module_sha = receipt['module']['sha256']
config, contract, rows = guard.load_config(ROOT, config_pin, module_sha)
target = AUDIT / 'BIRTH_INPUT_DELIVERY_ACTIVATION_V1.json'
guard.require(not target.exists(), 'activation is immutable')
roles = {}
for role, first in [('context_controls', args.controls_first_task),
                    ('context_latin', args.latin_first_task)]:
    directory = BASE / 'agents' / role / GROUP
    guard.require(first > 0 and (directory / f'TASK_{first:03}.md').is_file(), 'unknown first TASK')
    historical, activated, task_pins = set(), set(), []
    for task in sorted(directory.glob('TASK_*.md')):
        number = int(task.stem.split('_')[1])
        payload = task.read_bytes()
        ids = explicit_task_ids(payload.decode('utf-8'))
        guard.require(ids and all(i in rows and rows[i]['role'] == role for i in ids),
                      'task source or role changed')
        guard.require(not ids & (historical | activated), 'overlapping TASK IDs')
        (activated if number >= first else historical).update(ids)
        task_pins.append(dict(path=str(task.relative_to(ROOT)), sha256=guard.sha(payload), task=number))
    assigned = {i for i, r in rows.items() if r['role'] == role}
    guard.require(historical | activated == assigned, 'task coverage changed')
    roles[role] = dict(last_v1_task=first - 1, first_v2_task=first,
                       activated_source_ids=sorted(activated),
                       historical_source_ids_without_retrospective_emission_claim=sorted(historical),
                       task_pins=task_pins)
result = dict(status='PROSPECTIVE_EXACT_TASK_BOUNDARIES_ACKNOWLEDGED', cohort=GROUP,
              created_at_ns=time.time_ns(), config=config_pin, module=receipt['module'], roles=roles,
              acknowledgements={
                  'context_controls': 'TASK114 마감 후 다음 미착수TASK115부터 delivery reader 전환 회신',
                  'context_latin': 'v1 마지막085/첫v2 086으로 커서 오기 정정 회신'},
              retroactive_emission_events_created=0, cache_admitted=0, root_adopted=0,
              goal_complete=False, training_authorized=False)
payload = (json.dumps(result, ensure_ascii=False, indent=2) + chr(10)).encode('utf-8')
guard.require(len(payload) < 20_000_000, 'activation needs shards')
with target.open('xb') as stream:
    stream.write(payload)
print(json.dumps(dict(status=result['status'], roles={k:dict(first_v2_task=v['first_v2_task'],
      activated_sources=len(v['activated_source_ids'])) for k,v in roles.items()})))
