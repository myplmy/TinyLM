"""Reuse the all-source census for rule28, retaining only small delta metadata."""
from pathlib import Path
import hashlib
import json

AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2]
prior_path=AUDIT/'RULE27_DECLARED_NAME_LIST_CENSUS_V1.json';prior_raw=prior_path.read_bytes()
assert hashlib.sha256(prior_raw).hexdigest().upper()=='0BBAF7B7B05B9F922ED780BA75A1529018934ADB0B899375E2C760F0194A40C6'
prior=json.loads(prior_raw)
frozen=AUDIT/'census_rule27_declared_name_lists_v1.py';raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()==prior['input_pins'][str(frozen.relative_to(ROOT))]
code=raw.decode('utf-8')
replacements=[
 ('from scripts import p106b_hold_resolution_policy_v27 as policy','from scripts import p106b_hold_resolution_policy_v28 as policy'),
 ("selection_path = AUDIT/'ROOT_AUTHORED_SELECTIONS_V32.json'","selection_path = AUDIT/'ROOT_AUTHORED_SELECTIONS_V34.json'"),
 ("'67A77EA21E4F98FE5FF5F27D906B0C8E08C0B702C2B852750A9C0825281DA5A8'","'626B4730A4C17F081BADAD1F2F7155BFAA4565E7E6F78263B6A7B4021608FA69'"),
 ("individual_hashes = {row['original_text_sha256']", "hold_hashes -= {r['original_text_sha256'] for r in selection['rows'] if r['selected']['decision'] != 'HOLD'}\nassert len(hold_hashes)==66790\nindividual_hashes = {row['original_text_sha256']"),
 ("stage_path = AUDIT/'HOLD_110173_STAGNATION_DIAGNOSIS_V12.json'","stage_path = AUDIT/'HOLD_110173_STAGNATION_DIAGNOSIS_V14.json'"),
 ("'3E7EE29411E8B00791D040FAA48E90F466B0E2013BC0A347DF959403E3CA7516'","'1B846B55C8801B7995C82D695EE0009A4032C62EEBB690D1152ABBCEEDFE521C'"),
 ("version='v38'","version='v39'"),
 ("ROOT/'scripts/p106b_hold_resolution_disambiguation_v1.py'","ROOT/'scripts/p106b_hold_resolution_disambiguation_v2.py'"),
 ("ROOT/'scripts/p106b_hold_resolution_policy_v27.py'","ROOT/'scripts/p106b_hold_resolution_policy_v28.py'"),
 ("ROOT/'scripts/test_p106b_hold_resolution_policy_v27.py'","ROOT/'scripts/test_p106b_hold_resolution_policy_v28.py'"),
 ("AUDIT/'V27_SOURCE_DISAMBIGUATION_ALIAS_SCOPE_V1.md'","AUDIT/'V28_DECLARED_NAME_VARIANTS_F3_F4_V1.md'"),
 ("AUDIT/'POLICY_V27_REGRESSION_RUN_V2.log'","AUDIT/'POLICY_V28_REGRESSION_RUN_V2.log'"),
 ("out = inv.BASE/'rule27_declared_name_list_census_v1'","out = inv.BASE/'rule28_declared_name_list_census_v1'"),
 ("len(seen)==66411 and len(hold_hashes-seen)==914","len(seen)==len(hold_hashes)-914 and len(hold_hashes-seen)==914"),
 ("'V27_WHOLE_REMAINING_QUEUE_CENSUS_AND_NARROW_DELTA_CANDIDATES_NOT_ADMISSION'","'V28_WHOLE_REMAINING_QUEUE_CENSUS_AND_NARROW_DELTA_CANDIDATES_NOT_ADMISSION'"),
 ("'ROOT32_ROSTER23_EXPECTED_REMAINING_HOLD'","'ROOT34_ROSTER24_EXPECTED_REMAINING_HOLD'"),
 ("'RULE27_DECLARED_NAME_LIST_CENSUS_V1.json'","'RULE28_DECLARED_NAME_LIST_CENSUS_V1.json'"),
 ("phase='RULE27_CENSUS'","phase='RULE28_CENSUS'"),
]
for before,after in replacements:
    assert code.count(before)==1,before
    code=code.replace(before,after)
anchor='started = time.monotonic()'
assert code.count(anchor)==1
extra="""for name,expected in PRIOR_CENSUS['input_pins'].items():
    assert inv.file_sha(ROOT/name)==expected,name
    pins[name]=expected
pins[str(PRIOR_CENSUS_PATH.relative_to(ROOT))]=inv.file_sha(PRIOR_CENSUS_PATH)
pins[str(FROZEN_CENSUS_PATH.relative_to(ROOT))]=inv.file_sha(FROZEN_CENSUS_PATH)
"""
code=code.replace(anchor,extra+anchor)
exec(compile(code,str(frozen),'exec'),dict(__name__='rule28_whole_remaining_delta_census',
    __file__=str(Path(__file__)),PRIOR_CENSUS=prior,PRIOR_CENSUS_PATH=prior_path,FROZEN_CENSUS_PATH=frozen))
