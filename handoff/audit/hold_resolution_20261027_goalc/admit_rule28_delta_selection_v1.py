"""Reuse the guarded source-class producer for the separately proved rule28 delta."""
from pathlib import Path
import hashlib

frozen=Path(__file__).with_name('admit_rule27_delta_selection_v1.py');raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='60A8F6E21BC76F41FDEE34088B83A21016B2F8C4AA0B8C681AB9CE25B2AD08C2'
code=raw.decode('utf-8')
replacements=[
 ('from scripts import p106b_hold_resolution_policy_v27 as policy','from scripts import p106b_hold_resolution_policy_v28 as policy'),
 ("prior_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V33.json'","prior_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V34.json'"),
 ("prior_sha='9F99AA65B6D42EE78DE4D1C09A13C57BF7E15B3EECAE724BC948B69A33A05DE0'","prior_sha='626B4730A4C17F081BADAD1F2F7155BFAA4565E7E6F78263B6A7B4021608FA69'"),
 ("'ROOT33_SHARDED_SELECTION_INDEPENDENT_VERIFIED_V1.json'","'ROOT34_RULE27_SELECTION_INDEPENDENT_VERIFIED_V1.json'"),
 ("'RULE27_DECLARED_NAME_LIST_CENSUS_V1.json'","'RULE28_DECLARED_NAME_LIST_CENSUS_V1.json'"),
 ('0BBAF7B7B05B9F922ED780BA75A1529018934ADB0B899375E2C760F0194A40C6','0B2705C3B157565424615AF0D09B27C065DCABD048D55DED5208BE6E16910E11'),
 ("'RULE27_LITERAL_DELTA_INDEPENDENT_VERIFIED_V1.json'","'RULE28_LITERAL_DELTA_INDEPENDENT_VERIFIED_V1.json'"),
 ('67CBD366AEE45E82A32495173507F43512259367B381154E0DC659490635F2A6','E7E5FBC30F413441A9A4FDA964CB096E0AD4446725EDA948B75EEFD98449CC4C'),
 ("'RULE27_SAVED_CONTEXT_REVIEW_COMPARISON_V2.json'","'RULE28_SAVED_CONTEXT_REVIEW_COMPARISON_V1.json'"),
 ('66310BEB5DB859D884CDB1059AB659468E3860D13757AE3D7B08F40EA3E2E75E','9F59A2CFDFE2A7F66273A1859A5416876B268D2088F0CFFFA57E81FBD9787F95'),
 ("scope_path=AUDIT/'RULE27_BATCH_ADMISSION_F3_F4_V1.md'","scope_path=AUDIT/'RULE28_BATCH_ADMISSION_F3_F4_V1.md'"),
 ('C5D68659B1CF8E404769D4115E15E6F6F05A9FDF48A30A087C48E6A40B9FAFAC','F46D4C070AC4F9C70C1D015FEF238716B2C54104D7A728ED18CED5200276D1F2'),
 ("'HOLD_110173_STAGNATION_DIAGNOSIS_V13.json'","'HOLD_110173_STAGNATION_DIAGNOSIS_V14.json'"),
 ('6413F2B3D328A0032637C4437259987EFC860D7CD0435584F8CD71B155B0BA30','1B846B55C8801B7995C82D695EE0009A4032C62EEBB690D1152ABBCEEDFE521C'),
 ("out=AUDIT/'ROOT_AUTHORED_SELECTIONS_V34.json'","out=AUDIT/'ROOT_AUTHORED_SELECTIONS_V35.json'"),
 ("storage_path=AUDIT/'ROOT34_SELECTION_STORAGE_V1.json'","storage_path=AUDIT/'ROOT35_SELECTION_STORAGE_V1.json'"),
 ("'rule27_approved_bodies_v1'","'rule28_approved_bodies_v1'"),
 ("'source_class_rule27_declared_name_lists_v1'","'source_class_rule28_declared_name_lists_v1'"),
 ('==478 and selected','==407 and selected'),
 ('independent_saved_full_context_reviews=24','independent_saved_full_context_reviews=21'),
 ("AUDIT/'verify_rule27_literal_delta_v1.py'","AUDIT/'verify_rule28_literal_delta_v1.py'"),
 ("ROOT/'scripts/p106b_hold_resolution_disambiguation_v1.py'","ROOT/'scripts/p106b_hold_resolution_disambiguation_v2.py'"),
 ("ROOT/'scripts/p106b_hold_resolution_policy_v27.py'","ROOT/'scripts/p106b_hold_resolution_policy_v28.py'"),
 ('ROOT_RULE27_SOURCE_CLASS_AND_EVERY_LITERAL_DELTA_APPROVED','ROOT_RULE28_SOURCE_CLASS_AND_EVERY_LITERAL_DELTA_APPROVED'),
]
for before,after in replacements:
    assert code.count(before)==1,before
    code=code.replace(before,after)
before='ROOT34_RULE27_DELTA_CLOSURE_V1'
assert code.count(before)==2
code=code.replace(before,'ROOT35_RULE28_DELTA_CLOSURE_V1')
begin="assert comparison['candidates_with_saved_review']==24 and not any("
end='scope_path='
lo=code.index(begin);hi=code.index(end,lo)
new="""assert comparison['candidates_with_saved_review']==21
context_closure=read(AUDIT/'RULE28_SAVED_CONTEXT_REVIEW_DIFFERENCE_CLOSURE_V1.json',
    '267501C6CF72098952427E1F111B81E2C6865CD729558F52F9675EEE19B97D1B')
assert context_closure['unresolved_differences']==0 and context_closure['closed_exact_ids']==['expanded_train:346999']
different=[r for r in comparison['rows'] if r['outcome']=='DIFFERENT_BODY_REQUIRES_ROOT_CONTEXT_REVIEW']
assert len(different)==1 and different[0]['id']=='expanded_train:346999'
closed=context_closure['closures'][0]
assert all(different[0][key]==closed[key] for key in ['id','original','rule_body_sha256','saved_body_sha256','saved_review'])
assert context_closure['generic_whitespace_or_code_guard_waiver'] is False
assert comparison['counts']=={'ONLY_TERMINAL_LINE_ENDINGS_DIFFER_FROM_SAVED_REVIEW':7,
    'EXACT_BYTES_AGREE_WITH_SAVED_FULL_CONTEXT_REVIEW':13,'DIFFERENT_BODY_REQUIRES_ROOT_CONTEXT_REVIEW':1}
"""
code=code[:lo]+new+code[hi:]
anchor="specs=stage['coverage']+[dict(cohort='root12_independent_admission_counter_v1',version='v39')]"
assert code.count(anchor)==1
code=code.replace(anchor,anchor+"""
overrides={f'remaining_field_title_page_{page:03d}_counter_v1':version
    for page,version in [(12,'v14'),(14,'v9'),(15,'v6'),(16,'v4')]}
specs=[dict(spec,version=overrides.get(spec['cohort'],spec['version'])) for spec in specs]
auxiliary=read(AUDIT/'AUXILIARY_BINDING_FIELD_015_V6_V1.json')
assert auxiliary['only_one_source_free_note_excluded'] is True
assert auxiliary['root_adopted']==auxiliary['cache_admitted']==0
""")
anchor="for path in [Path(__file__),scope_path,"
assert code.count(anchor)==1
code=code.replace(anchor,"for path in [FROZEN_RULE27_PRODUCER,Path(__file__),scope_path,")
exec(compile(code,str(frozen),'exec'),dict(__name__='rule28_exact_source_class_delta_admission',
    __file__=str(Path(__file__)),FROZEN_RULE27_PRODUCER=frozen))
