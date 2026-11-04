"""Independently compare all canonical rows using the frozen separate verifier."""
from pathlib import Path
import argparse
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);args=parser.parse_args()
config_path=(ROOT/args.config).resolve();assert config_path.is_relative_to(AUDIT)
c=json.loads(config_path.read_bytes());old_version,new_version=c['prior_roster'],c['next_roster']
frozen=AUDIT/'verify_reviewed_partial_roster_v4_v1.py'
assert hashlib.sha256(frozen.read_bytes()).hexdigest().upper()=='92B28B649DE749241C4660A26F741F0C3E32AF350B981507A8EA8BBB26B04BED'
selection_path=AUDIT/f"ROOT_AUTHORED_SELECTIONS_V{c['next_selection']}.json"
assert hashlib.sha256(selection_path.read_bytes()).hexdigest().upper()==c['selection_sha256']
selection=json.loads(selection_path.read_bytes())
prior=json.loads((AUDIT/f"ROOT_AUTHORED_SELECTIONS_V{c['prior_selection']}.json").read_bytes())
added=len(selection['rows'])-len(prior['rows']);assert added>0
code=frozen.read_text(encoding='utf-8')


def once(before,after):
    global code
    assert code.count(before)==1,('frozen independent verifier anchor changed',before)
    code=code.replace(before,after)


once("old_path=inv.BASE/'roster_reviewed_partial_v3/complete.json'",f"old_path=inv.BASE/'roster_reviewed_partial_v{old_version}/complete.json'")
once("new_path=inv.BASE/'roster_reviewed_partial_v4/complete.json'",f"new_path=inv.BASE/'roster_reviewed_partial_v{new_version}/complete.json'")
once("selection_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V12.json'",f"selection_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V{c['next_selection']}.json'")
once("'C93C6A8B29D5FB3EF9769346C1B37383FEE8F45557139324757793F42DD0759A'",repr(c['selection_sha256']))
once("prior=inv.cache.read(AUDIT/'ROOT_AUTHORED_SELECTIONS_V11.json')",f"prior=inv.cache.read(AUDIT/'ROOT_AUTHORED_SELECTIONS_V{c['prior_selection']}.json')")
code=code.replace('==123','=='+str(added)).replace('==297416','=='+str(297539-added))
code=code.replace('==70107','=='+str(selection['expected_roster_HOLD_unique']))
code=code.replace('109931',str(selection['expected_roster_HOLD_positions']))
code=code.replace('109893',str(selection['expected_roster_HOLD_positions']-38))
code=code.replace('changed_sources=123','changed_sources='+str(added))
code=code.replace('ALL_ROSTER4_CANONICAL_ROWS_AND_EXACT_ROOT12_DELTA',f"ALL_ROSTER{new_version}_CANONICAL_ROWS_AND_EXACT_ROOT{c['next_selection']}_DELTA")
code=code.replace('ROOT12_ROSTER_V4_INDEPENDENT_VERIFIED_V1',c['new_roster_proof_stem'])
once('input_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in [old_path,new_path,selection_path,Path(__file__)]}',
    'input_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in [CONFIG_PATH,FROZEN_PATH,old_path,new_path,selection_path,Path(__file__)]}')
exec(compile(code,str(frozen),'exec'),dict(__name__='actual_independent_versioned_roster_check',__file__=str(Path(__file__)),CONFIG_PATH=config_path,FROZEN_PATH=frozen))
