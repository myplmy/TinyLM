"""Enter only the metadata runtime and check restoration; no cache/model run."""
from pathlib import Path
import sys

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
import guarded_reviewed_cache_v5 as adapter

ROOT,inv=adapter.ROOT,adapter.inv
before=adapter.first.CONTRACT
assert inv.file_sha(AUDIT/'guarded_reviewed_cache_v4.py')=='28A6122F02EBABF6DB4D1393CCD7390343E9E01962670E4DB22676F445F59F09'
with adapter.runtime(AUDIT/'ROOT_AUTHORED_SELECTIONS_V11.json') as inputs:
    assert adapter.first.CONTRACT==adapter.CONTRACT
    assert inputs.contract_sha==adapter.EXPECTED
    assert len(inputs.metadata)==13 and set(inputs.safe)==set(inputs.safe_texts)
    assert len(inputs.safe)==3
    assert all(key in inputs.metadata for key in ['expanded_train:28876','historical_train:28876'])
    assert str(Path(adapter.__file__).relative_to(ROOT)) in inputs.pins
assert adapter.first.CONTRACT==before and adapter.first.ACTIVE is None
out=AUDIT/'GUARDED_CACHE_V5_METADATA_PREFLIGHT_V1.json'
assert not out.exists()
inv.write_json(out,dict(status='CUMULATIVE_METADATA_RUNTIME_ENTER_EXIT_VERIFIED_NO_CACHE_BUILD',
    contract_sha256=adapter.EXPECTED,restricted_sources=8,restricted_hashes=9,
    alias_positions=13,existing_safe_views_preserved=3,original_contract_restored=True,
    runtime_active_cleared=True,native_scan_calls=0,cache_builds=0,consumer_runs=0,
    actual_model_or_GPU_runs=0,protected_original_or_candidate_TXT_opens=0,
    input_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in [Path(__file__),
        Path(adapter.__file__),adapter.CONTRACT,AUDIT/'ROOT_AUTHORED_SELECTIONS_V11.json']},
    root_adopted=0,cache_admitted=0,goal_complete=False,training_authorized=False))
print(out.name,inv.file_sha(out))
