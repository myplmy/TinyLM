"""Independently reconstruct ROOT35 and recount every source-linked rule28 delta."""
from pathlib import Path
import hashlib
import json

AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2]
proof_path=AUDIT/'ROOT34_RULE27_SELECTION_INDEPENDENT_VERIFIED_V1.json'
assert hashlib.sha256(proof_path.read_bytes()).hexdigest().upper()=='8CE45C6B150270BBF2775DA2DDC8119F7727FD1330B82AA5783D97BAA5DD5817'
proof=json.loads(proof_path.read_bytes())
frozen=AUDIT/'verify_rule27_selection_metadata_v1.py';raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()==proof['input_pins'][str(frozen.relative_to(ROOT))]
assert hashlib.sha256((AUDIT/'ROOT_AUTHORED_SELECTIONS_V35.json').read_bytes()).hexdigest().upper()=='DF7AA25488D2F8694588E98F866DCA61FDA66A62E8D8BB0395159B0287559BC3'
code=raw.decode('utf-8')
for before,after in [
 ("path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V34.json'","path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V35.json'"),
 ("=='ROOT_AUTHORED_SELECTIONS_V33.json'","=='ROOT_AUTHORED_SELECTIONS_V34.json'"),
 ('9F99AA65B6D42EE78DE4D1C09A13C57BF7E15B3EECAE724BC948B69A33A05DE0','626B4730A4C17F081BADAD1F2F7155BFAA4565E7E6F78263B6A7B4021608FA69'),
 ("'RULE27_DECLARED_NAME_LIST_CENSUS_V1.json'","'RULE28_DECLARED_NAME_LIST_CENSUS_V1.json'"),
 ('0BBAF7B7B05B9F922ED780BA75A1529018934ADB0B899375E2C760F0194A40C6','0B2705C3B157565424615AF0D09B27C065DCABD048D55DED5208BE6E16910E11'),
 ('assert len(candidates)==478','assert len(candidates)==407'),
 ("'RULE27_LITERAL_DELTA_INDEPENDENT_VERIFIED_V1.json'","'RULE28_LITERAL_DELTA_INDEPENDENT_VERIFIED_V1.json'"),
 ('67CBD366AEE45E82A32495173507F43512259367B381154E0DC659490635F2A6','E7E5FBC30F413441A9A4FDA964CB096E0AD4446725EDA948B75EEFD98449CC4C'),
 ("'/RULE27_BATCH_ADMISSION_F3_F4_V1.md'","'/RULE28_BATCH_ADMISSION_F3_F4_V1.md'"),
 ("ROOT/'scripts/p106b_hold_resolution_disambiguation_v1.py'","ROOT/'scripts/p106b_hold_resolution_disambiguation_v2.py'"),
 ("ROOT/'scripts/p106b_hold_resolution_policy_v27.py'","ROOT/'scripts/p106b_hold_resolution_policy_v28.py'"),
 ('RULE27_SHARDED_SELECTION_INDEPENDENTLY_RECONSTRUCTED_AND_RECOUNTED','RULE28_SHARDED_SELECTION_INDEPENDENTLY_RECONSTRUCTED_AND_RECOUNTED'),
 ("'ROOT34_RULE27_SELECTION_INDEPENDENT_VERIFIED_V1.json'","'ROOT35_RULE28_SELECTION_INDEPENDENT_VERIFIED_V1.json'"),
]:
    assert code.count(before)==1,before
    code=code.replace(before,after)
exec(compile(code,str(frozen),'exec'),dict(__name__='independent_rule28_native_metadata_verification',
    __file__=str(Path(__file__))))
