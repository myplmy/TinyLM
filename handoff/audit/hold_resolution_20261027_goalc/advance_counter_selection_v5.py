"""Keep strict guard5 admission; store only new selection metadata as row shards."""
from pathlib import Path
import hashlib
import json
import sys

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
from selection_metadata_store_v1 import SelectionStore, bound_selection_loads, encode

adapter = AUDIT / 'advance_counter_selection_v4.py'
raw = adapter.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == '33C8B9BCCE36DAFABB056BC70E2A8557E6FA09D49994875A298C5CB576CAE432'
text = raw.decode('utf-8')
last = "exec(compile(code,str(frozen),'exec'),environment)"
assert text.count(last) == 1
scope = dict(__name__='selection5_transform_guard5_only', __file__=str(Path(__file__)))
exec(compile(text.split(last)[0], str(adapter), 'exec'), scope)
code, environment = scope['code'], scope['environment']
config = scope['config']
prior = AUDIT / ('ROOT_AUTHORED_SELECTIONS_V' + str(config['prior_selection']) + '.json')
assert not config.get('supersession_proof'), 'special unadmitted ROOT30 supersession is already closed'
before = (
    "payload=(json.dumps(document,ensure_ascii=False,indent=2)+chr(10)).encode('utf-8')" + chr(10) +
    "if len(payload)>=20_000_000:payload=(json.dumps(document,ensure_ascii=False,separators=(',',':'))+chr(10)).encode('utf-8')" + chr(10) +
    "assert len(payload)<20_000_000,'selection needs a separately validated sharded schema before creation'" + chr(10) +
    "with out.open('xb') as stream:stream.write(payload)"
)
assert code.count(before) == 1
code = code.replace(before,
    "storage_receipt=SELECTION_STORE.write(out,document,force_sharded=True)" + chr(10) +
    "storage_path=AUDIT/('ROOT'+str(NEXT_SELECTION_NUMBER)+'_SELECTION_STORAGE_V1.json')" + chr(10) +
    "with storage_path.open('xb') as stream:stream.write(ENCODE_METADATA(storage_receipt))")
before = 'pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in input_paths}'
assert code.count(before) == 1
code = code.replace(before,
    "input_paths.extend([ADAPTER_V4_PATH,AUDIT/'selection_metadata_store_v1.py'])" + chr(10) + before)
environment.update(SELECTION_STORE=SelectionStore(AUDIT), ADAPTER_V4_PATH=adapter,
                   NEXT_SELECTION_NUMBER=config['next_selection'], ENCODE_METADATA=encode)
with bound_selection_loads([(prior, config['prior_selection_sha256'])], directory=AUDIT):
    exec(compile(code, str(adapter), 'exec'), environment)
scope['assert_no_protected_opens']()
