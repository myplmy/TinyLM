"""Preserve an exact prior audit under the handoff checker's filename contract."""
import hashlib
import json
from pathlib import Path

base=Path('handoff/audit/nov04_p107_cli')
source=base/'STATIC_AUDIT_v3.json'
target=base/'SOURCE_STATIC_AUDIT.json'
receipt=base/'STATIC_AUDIT_ALIAS_v1.json'
if target.exists() or receipt.exists():raise FileExistsError('audit alias already exists')
raw=source.read_bytes()
with target.open('xb') as stream:stream.write(raw)
value=dict(schema='EXACT_STATIC_AUDIT_FILENAME_ALIAS_V1',source=str(source),alias=str(target),
    bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest().upper(),exact_bytes=True,
    new_validation_execution=False,original_audit_overwrite=False,
    reason='Handoff checker requires the linked basename to end with _STATIC_AUDIT.json.')
with receipt.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2);stream.write(chr(10))
print(json.dumps(value))
