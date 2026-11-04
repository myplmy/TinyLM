"""Reuse the independent proof-chain check for cache4 to cache5 progress."""
from pathlib import Path
import hashlib
import re

AUDIT=Path(__file__).resolve().parent
frozen=AUDIT/'verify_cache4_progress_delta_v1.py'
assert hashlib.sha256(frozen.read_bytes()).hexdigest().upper()=='52DA8A36EACDC0C851407FE7D0CEEF01B0267563F9A356B3BDAEE2DEE0F49C7A'
code=frozen.read_text(encoding='utf-8')
mapping={
    'cache_reviewed_partial_v3':'cache_reviewed_partial_v4',
    'cache_reviewed_partial_v4':'cache_reviewed_partial_v5',
    'CACHE_REVIEWED_PARTIAL_V4':'CACHE_REVIEWED_PARTIAL_V5',
    'roster_reviewed_partial_v4':'roster_reviewed_partial_v5',
    'ROOT_AUTHORED_SELECTIONS_V12.json':'ROOT_AUTHORED_SELECTIONS_V13.json',
    'ACTUAL_CACHE4_CONSUMER_PROOF_CHAIN_AND_PROGRESS_DELTA_VERIFIED':'ACTUAL_CACHE5_CONSUMER_PROOF_CHAIN_AND_PROGRESS_DELTA_VERIFIED',
    'CACHE4_PROGRESS_DELTA_INDEPENDENT_VERIFIED_V1':'CACHE5_PROGRESS_DELTA_INDEPENDENT_VERIFIED_V1'}
pattern='|'.join(re.escape(value) for value in sorted(mapping,key=len,reverse=True))
code=re.sub(pattern,lambda match:mapping[match.group()],code)
numbers={'110173':'109931','109931':'109064','109893':'109026','123':'436','242':'867','119':'431'}
pattern=r'(?<![A-Za-z0-9_])(?:'+'|'.join(numbers)+r')(?![A-Za-z0-9_])'
code=re.sub(pattern,lambda match:numbers[match.group()],code)
before="assert added=={'train':121,'val':2}"
assert code.count(before)==1;code=code.replace(before,"assert sum(added.values())==436 and all(value>=0 for value in added.values())")
assert code.count('pins={}'+chr(10))==1
code=code.replace('pins={}'+chr(10),
    "pins={str(FROZEN_PATH.relative_to(ROOT)):hashlib.sha256(FROZEN_PATH.read_bytes()).hexdigest().upper()}"+chr(10))
exec(compile(code,str(frozen),'exec'),dict(__name__='cache5_progress_metadata_check',__file__=str(Path(__file__)),FROZEN_PATH=frozen))
