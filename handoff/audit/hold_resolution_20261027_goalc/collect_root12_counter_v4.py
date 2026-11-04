"""Reuse strict V3 collection with one exact English header compatibility map."""
from pathlib import Path
import hashlib

AUDIT=Path(__file__).resolve().parent
frozen=AUDIT/'collect_root12_counter_v3.py'
raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='9EAC02B374715468FE8CD7B3BE66A3E9F21AF9119A02E5D94FC634CA8EF181AB'
last="exec(compile(source,str(adapter),'exec'),dict("
text=raw.decode('utf-8');assert text.count(last)==1
scope=dict(__name__='counter_v4_transform_only',__file__=str(Path(__file__)))
exec(compile(text.split(last)[0],str(frozen),'exec'),scope)
source=scope['source']
before="code=frozen.read_text(encoding='utf-8')"
assert source.count(before)==1
source=source.replace(before,before+"\ncode=code.replace('exact_review_header_alias_v2','exact_review_header_alias_v3')",1)
before='for path in [EXTRA_HISTORY_PATH,ADAPTER_V2_PATH,HISTORY_PATH,'
assert source.count(before)==1
source=source.replace(before,'for path in [ADAPTER_V3_PATH,EXTRA_HISTORY_PATH,ADAPTER_V2_PATH,HISTORY_PATH,',1)
before='environment.update(EXTRA_HISTORY_PATH=EXTRA_HISTORY_PATH,ADAPTER_V2_PATH=ADAPTER_V2_PATH)'
assert source.count(before)==1
source=source.replace(before,'environment.update(EXTRA_HISTORY_PATH=EXTRA_HISTORY_PATH,ADAPTER_V2_PATH=ADAPTER_V2_PATH,ADAPTER_V3_PATH=ADAPTER_V3_PATH)',1)
exec(compile(source,str(scope['adapter']),'exec'),dict(__name__='counter_v4_actual_run',
    __file__=str(Path(__file__)),EXTRA_NONDECISION_HISTORY=scope['extra'],
    EXTRA_HISTORY_PATH=scope['history_path'],ADAPTER_V2_PATH=scope['adapter'],ADAPTER_V3_PATH=frozen))
