"""Reuse the frozen independent context comparator with explicit batch parameters."""
from pathlib import Path
import hashlib
import json
import sys

AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parents[2]
sys.path.insert(0,str(ROOT))
config_path=Path(sys.argv[sys.argv.index('--config')+1]).resolve()
assert config_path.parent==AUDIT and not config_path.is_symlink()
config=json.loads(config_path.read_bytes())
frozen=AUDIT/'compare_rule27_with_saved_context_reviews_v1.py'
raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='DC93F076773257A28E72224C69958F2CC5A1AEE24AEEE0317662EF40679717CB'
code=raw.decode('utf-8')
replacements=[
    ('from scripts import p106b_hold_resolution_policy_v27 as policy',
     'from '+config['policy'].rsplit('.',1)[0]+' import '+config['policy'].rsplit('.',1)[1]+' as policy'),
    ("census=read(AUDIT/'RULE27_DECLARED_NAME_LIST_CENSUS_V1.json')",
     'census=read(AUDIT/'+repr(config['census'])+','+repr(config['census_sha256'])+')'),
    ("assert len(candidates)==census['counts']['new_terminal_rule_candidates']==478",
     "assert len(candidates)==census['counts']['new_terminal_candidates']=="+str(config['expected_candidates'])),
    ("stage=read(AUDIT/'HOLD_110173_STAGNATION_DIAGNOSIS_V12.json')",
     'stage=read(AUDIT/'+repr(config['stage'])+','+repr(config['stage_sha256'])+')'),
    ("overrides={12:'v12',14:'v7',16:'v2'}",'overrides='+repr({int(k):v for k,v in config['overrides'].items()})),
    ('RULE27_VS_INDEPENDENT_SAVED_FULL_CONTEXT_REVIEW_COMPARISON_NOT_ADMISSION',
     config['label']+'_VS_INDEPENDENT_SAVED_FULL_CONTEXT_REVIEW_COMPARISON_NOT_ADMISSION'),
    ("AUDIT/'RULE27_SAVED_CONTEXT_REVIEW_COMPARISON_V1.json'",'AUDIT/'+repr(config['output'])),
]
for before,after in replacements:
    assert code.count(before)==1,before
    code=code.replace(before,after)
before="pins[str(Path(__file__).relative_to(ROOT))]=inv.file_sha(Path(__file__))"
assert code.count(before)==1
code=code.replace(before,before+chr(10)+
    "pins[str(CONFIG_PATH.relative_to(ROOT))]=inv.file_sha(CONFIG_PATH)"+chr(10)+
    "pins[str(FROZEN_PATH.relative_to(ROOT))]=inv.file_sha(FROZEN_PATH)")
exec(compile(code,str(frozen),'exec'),dict(__name__='source_class_saved_context_comparison',
    __file__=str(Path(__file__)),CONFIG_PATH=config_path,FROZEN_PATH=frozen))
