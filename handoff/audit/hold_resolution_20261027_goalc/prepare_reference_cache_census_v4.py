"""Reuse the metadata-only parent census with the exact cache10 runtime."""
from pathlib import Path
import hashlib

frozen=Path(__file__).with_name('prepare_reference_cache_census_v1.py')
raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='85C73FA7E9BBB431D3B5F4440677B060010514E7B0EBD89E217AA799BFCFAD86'
code=raw.decode('utf-8')
before='from guarded_reviewed_cache_v7 import ROOT, inv, current_pins, checked_contract'
assert code.count(before)==1
code=code.replace(before,'from guarded_reviewed_cache_v10 import ROOT, inv, current_pins, checked_contract')
before='original_or_candidate_payload_files_opened=0,'
assert code.count(before)==1
code=code.replace(before,'parent_census_original_or_candidate_payload_files_opened=0, '
    'exact_adapter_evidence_pin_hashing_may_open_approved_ordinary_payload=True,')
exec(compile(code,str(frozen),'exec'),dict(__name__='guard6_reference_census',__file__=str(Path(__file__))))
