"""Reuse saved-row counter7; two exact new rows can only remain opaque HOLD."""
from pathlib import Path
import hashlib
import sys
from unittest.mock import patch

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT));sys.path.insert(0,str(AUDIT.parents[2]))
from active_guard_v5_preflight_v1 import (activate,checked_contract,NEW_IDS,
    validate_new_hold,assert_no_protected_opens,EXPECTED,CONTRACT)
from counter_quarantine_materializer_v1 import materialize as quarantine_materialize
activate()
import collect_exact_cohort_reviews_v5 as frozen
ROOT = AUDIT.parents[2]
manifest_path = ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc/root12_independent_admission_counter_v1/manifest.json'
assert frozen.inv.file_sha(manifest_path) == 'A71B3109889F32F5969298287C7ADA9B1C223130A8603D87B80D2D910A57527D'
sources = {r['id']:r for r in frozen.inv.cache.read(manifest_path)['rows']}
contract = checked_contract()
new_hashes = {r[label]['sha256'] for r in contract['newly_quarantined_entries']
    for label in ['original','derived_candidate']}
assert {key for key,source in sources.items() if key in NEW_IDS or any(
    source[label]['sha256'] in new_hashes for label in ['original','candidate'])} == NEW_IDS
previous_load = frozen.load_reused
previous_shards = frozen.shard_records
previous_write = frozen.write_json_new


def load(path,environment):
    environment = previous_load(path,environment)
    decisions = environment['decisions']
    def protected_decisions(directory,ids):
        rows = decisions(directory,ids)
        for key,row in rows.items():
            if key in NEW_IDS: validate_new_hold(row,sources[key])
        return rows
    environment['decisions'] = protected_decisions
    previous_materialize = environment['materialize']
    environment['materialize'] = lambda row,source,directory: quarantine_materialize(
        row,source,directory,previous_materialize)
    for path in [Path(__file__),CONTRACT,AUDIT/'active_guard_v5_preflight_v1.py',
        AUDIT/'counter_quarantine_materializer_v1.py']:
        environment['input_pins'][str(path.relative_to(ROOT))] = frozen.inv.file_sha(path)
    return environment


def shards(output,records):
    for row in records:
        if row['id'] in NEW_IDS:
            validate_new_hold(row,sources[row['id']])
            row.update(original=sources[row['id']]['original'],
                candidate_metadata=sources[row['id']]['candidate'],metadata_only=True,
                active_quarantine_contract_sha256=EXPECTED,protected_payload_opened=False)
    assert_no_protected_opens()
    return previous_shards(output,records)


def write(path,value):
    if Path(path).name == 'complete.json':
        value.update(active_guard_sha256=EXPECTED,metadata_only_ids=sorted(NEW_IDS &
            set(value['lazy_view_source_ids']+list(sources.keys()-set(value['unreviewed_ids'])))),
            protected_payload_open_attempts=0)
    return previous_write(path,value)


adapter = AUDIT/'collect_root12_counter_v7.py'
raw = adapter.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == '3E934E5B0D6178E720BE52A11D01B4B083A5188A3C2775F46E0D8E83226BE9C6'
with patch.object(frozen,'load_reused',load),patch.object(frozen,'shard_records',shards),patch.object(frozen,'write_json_new',write):
    exec(compile(raw,str(adapter),'exec'),dict(__name__='guard5_counter8_actual_run',__file__=str(Path(__file__))))
assert_no_protected_opens()
