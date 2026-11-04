"""Extend the unchanged stage recorder to an explicit verified-cache chain."""
from pathlib import Path
import hashlib
A=Path(__file__).resolve().parent
frozen=A/'record_hold_stages_v1.py';raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='FFEB2F1FFCF8BA91874CF73F1C3F054C0590BF44981540123A12F3C266BB908B'
code=raw.decode()
begin="previous_cache = read(AUDIT/'CACHE4_PROGRESS_DELTA_INDEPENDENT_VERIFIED_V1.json')"
end="selection = read(ROOT/c['selection'], c['selection_sha256'])"
assert code.count(begin)==code.count(end)==1
lo=code.index(begin);hi=code.index(end)
replacement="""chain=[read(AUDIT/name) for name in c['previous_cache_delta_proofs']]
assert chain and chain[0]['previous_hold_positions']==110173
for before,after in zip(chain,chain[1:]+[cache]):
    assert before['current_hold_positions']==after['previous_hold_positions']
for entry in chain+[cache]:
    assert entry['previous_hold_positions']-entry['current_hold_positions']==entry['resolved_positions']
previous_cache={key:sum(r[key] for r in chain) for key in ['resolved_positions','new_unique_accepted_documents','additional_duplicate_positions_excluded']}
cumulative_reduction=previous_cache['resolved_positions']+cache['resolved_positions']
assert cumulative_reduction==110173-c['official_hold_positions']
"""
code=code[:lo]+replacement+code[hi:]
anchor="source = source.replace('GUARDED_SOURCE_METADATA_CONTRACT_V2', 'GUARDED_SOURCE_METADATA_CONTRACT_V3')"
assert code.count(anchor)==1
extra="source = source.replace(\"('remaining_literal_full_counter_v1','v21')\", \"('remaining_literal_full_counter_v1',\"+repr(c.get('literal_version','v21'))+\")\")\n"
code=code.replace(anchor,extra+anchor,1)
anchor="for path in [frozen, Path(__file__)]:"
assert code.count(anchor)==1
code=code.replace(anchor,"for path in [frozen, Path(__file__), RECORDER_V1_PATH]:",1)
exec(compile(code,str(frozen),'exec'),{'__name__':'hold_stages_chain_v2','__file__':str(Path(__file__)),'RECORDER_V1_PATH':frozen})
