"""Reuse the independent literal stream proof for every new rule28 candidate."""
from pathlib import Path
import hashlib

frozen=Path(__file__).with_name('verify_rule27_literal_delta_v1.py');raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='ECF8B7F4F3B325FAFDB67AAC87C9D7DE5FACE18BCF34B4E55A4599759778B331'
code=raw.decode('utf-8')
for before,after in [
 ('from scripts import p106b_hold_resolution_policy_v27 as policy','from scripts import p106b_hold_resolution_policy_v28 as policy'),
 ("'RULE27_DECLARED_NAME_LIST_CENSUS_V1.json'","'RULE28_DECLARED_NAME_LIST_CENSUS_V1.json'"),
 ('0BBAF7B7B05B9F922ED780BA75A1529018934ADB0B899375E2C760F0194A40C6','0B2705C3B157565424615AF0D09B27C065DCABD048D55DED5208BE6E16910E11'),
 ('assert len(rows)==478','assert len(rows)==407'),
 ('RULE27_ALL_CANDIDATE_LITERAL_DELTA_AUDIT_NOT_ADMISSION','RULE28_ALL_CANDIDATE_LITERAL_DELTA_AUDIT_NOT_ADMISSION'),
 ("'RULE27_LITERAL_DELTA_INDEPENDENT_VERIFIED_V1.json'","'RULE28_LITERAL_DELTA_INDEPENDENT_VERIFIED_V1.json'"),
]:
    assert code.count(before)==1,before
    code=code.replace(before,after)
exec(compile(code,str(frozen),'exec'),dict(__name__='__main__',__file__=str(Path(__file__))))
