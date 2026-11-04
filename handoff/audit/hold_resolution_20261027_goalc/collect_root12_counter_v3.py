"""Archive one exact superseded bad draft; keep strict TASK and body checks."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
adapter = AUDIT / 'collect_root12_counter_v2.py'
raw = adapter.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == 'BEA65EF538DC170652C99151BB1040CC11D6838CD4D5032200F401CE308BCA93'
history_path = AUDIT / 'ROOT12_COUNTER_REVIEW143_HISTORY_INDEPENDENT_VERIFIED_V1.json'
history_raw = history_path.read_bytes()
assert hashlib.sha256(history_raw).hexdigest().upper() == '84EABFF54AB6F5CFC168AE1D4B49A25267B1B667100E084A437EDF240B913853'
history = json.loads(history_raw)
assert history['historical_bad_rows_selected'] == 0
assert history['corrected_TASK143_rows_selected'] == 5
assert history['correct_TASK142_rows_preserved'] == 4
for name, expected in history['input_pins'].items():
    path = ROOT / name
    assert not path.is_symlink()
    assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == expected, name
directory = 'data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_latin/root12_independent_admission_counter_v1/'
extra = dict(path=directory+'review_143.md',
    sha256='6D26C4705AA6FB723D4B6501B24D213376A65E882338C4273F2BFD3F5F73B576',
    canonical_review=directory+'review_143_v2.md',
    canonical_review_sha256='4839845DEDCEC8363B7C0C2170560E275EB1B878E23C978AFAED994BD8A232D8',
    root_approved=True,original_auxiliary_preserved=True,
    kind='SUPERSEDED_BAD_DRAFT_NONDECISION_HISTORY',
    reason='TASK143의 지정5행은 정정본에서 보존했고 다른 TASK의 혼입4행은 엄격 검사로 제외했다. 옛9행 초안은 별도 판정으로 재사용하지 않고 원형과 content-addressed archive에 보존한다.',
    exact_root_evidence=dict(path=str(history_path.relative_to(ROOT)),sha256='84EABFF54AB6F5CFC168AE1D4B49A25267B1B667100E084A437EDF240B913853'))
source = raw.decode('utf-8')
before = "code=frozen.read_text(encoding='utf-8')"
assert source.count(before) == 1
source = source.replace(before,"document['rows'].append(EXTRA_NONDECISION_HISTORY)\n"+before,1)
before = 'for path in [HISTORY_PATH,FROZEN_COLLECTOR,manifest_path,'
assert source.count(before) == 1
source = source.replace(before,'for path in [EXTRA_HISTORY_PATH,ADAPTER_V2_PATH,HISTORY_PATH,FROZEN_COLLECTOR,manifest_path,',1)
before = "exec(compile(code,str(frozen),'exec'),environment)"
assert source.count(before) == 1
source = source.replace(before,"environment.update(EXTRA_HISTORY_PATH=EXTRA_HISTORY_PATH,ADAPTER_V2_PATH=ADAPTER_V2_PATH)\n"+before,1)
exec(compile(source,str(adapter),'exec'),dict(__name__='counter_v3_exact_history_run',
    __file__=str(Path(__file__)),EXTRA_NONDECISION_HISTORY=extra,
    EXTRA_HISTORY_PATH=history_path,ADAPTER_V2_PATH=adapter))
