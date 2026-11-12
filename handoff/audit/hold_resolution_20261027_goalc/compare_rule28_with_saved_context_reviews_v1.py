"""Blindly compare rule28 with already saved independent source-context work."""
from pathlib import Path
import hashlib

frozen=Path(__file__).with_name('compare_rule27_with_saved_context_reviews_v1.py');raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='DC93F076773257A28E72224C69958F2CC5A1AEE24AEEE0317662EF40679717CB'
code=raw.decode('utf-8')
for before,after in [
 ('from scripts import p106b_hold_resolution_policy_v27 as policy','from scripts import p106b_hold_resolution_policy_v28 as policy'),
 ("'RULE27_DECLARED_NAME_LIST_CENSUS_V1.json'","'RULE28_DECLARED_NAME_LIST_CENSUS_V1.json'"),
 ("==478","==407"),
 ("'HOLD_110173_STAGNATION_DIAGNOSIS_V12.json'","'HOLD_110173_STAGNATION_DIAGNOSIS_V14.json'"),
 ("overrides={12:'v12',14:'v7',16:'v2'}","overrides={12:'v14',14:'v9',15:'v4',16:'v4'}"),
 ('RULE27_VS_INDEPENDENT_SAVED_FULL_CONTEXT_REVIEW_COMPARISON_NOT_ADMISSION','RULE28_VS_INDEPENDENT_SAVED_FULL_CONTEXT_REVIEW_COMPARISON_NOT_ADMISSION'),
 ("'RULE27_SAVED_CONTEXT_REVIEW_COMPARISON_V1.json'","'RULE28_SAVED_CONTEXT_REVIEW_COMPARISON_V1.json'"),
]:
    assert code.count(before)==1,before
    code=code.replace(before,after)
exec(compile(code,str(frozen),'exec'),dict(__name__='rule28_blind_existing_context_comparison',__file__=str(Path(__file__))))
