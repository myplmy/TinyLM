"""Reuse cache7 engines under guard5 and explicitly bound selection row shards."""
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import sys

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
import guarded_reviewed_cache_v7 as previous
import guarded_reviewed_cache_v6 as guard4_runtime
import active_guard_v5_preflight_v1 as guard5
from selection_metadata_store_v1 import SelectionStore, bound_selection_loads, FORMAT_KEY

assert hashlib.sha256((AUDIT/'guarded_reviewed_cache_v7.py').read_bytes()).hexdigest().upper() == 'C9E90FD6EF21167572C6D54AD1E1567260A010CF1F9B1355ECC6A3729353A21F'
assert hashlib.sha256((AUDIT/'active_guard_v5_preflight_v1.py').read_bytes()).hexdigest().upper() == 'AFEAB668E4717CBA9D5527E429F2866DBDDE31C9FB45DB59767F9F6E565BFAB5'
assert hashlib.sha256((AUDIT/'selection_metadata_store_v1.py').read_bytes()).hexdigest().upper() == 'A5DE169B5493EDB1AD4FF456145BA0BF729754670FF258BADD2AFC67CC89E461'

ROOT, inv, first = previous.ROOT, previous.inv, previous.first
CONTRACT, EXPECTED = guard5.CONTRACT, guard5.EXPECTED
opaque_contract = previous.opaque_contract
BASE_RUNTIME, BASE_INPUTS = previous.runtime, previous.GuardedInputs
SAFE_IDS = {'expanded_train:1250821', 'expanded_train:15695', 'expanded_train:20624'}
ACTIVE_CONTRACT = None


def checked_contract():
    if ACTIVE_CONTRACT is None:
        return guard5.checked_contract()
    inv.require(inv.file_sha(CONTRACT) == EXPECTED, 'active guard5 metadata changed')
    return ACTIVE_CONTRACT


@contextmanager
def active_contract():
    global ACTIVE_CONTRACT
    if ACTIVE_CONTRACT is not None:
        yield checked_contract()
        checked_contract()
        return
    contract = guard5.checked_contract()  # Calls original guard4 before patching it.
    ACTIVE_CONTRACT = contract
    try:
        with patch.object(guard4_runtime, 'CONTRACT', CONTRACT), \
                patch.object(guard4_runtime, 'EXPECTED', EXPECTED), \
                patch.object(guard4_runtime, 'checked_contract', checked_contract), \
                patch.object(previous, 'checked_contract', checked_contract):
            yield contract
            checked_contract()
    finally:
        ACTIVE_CONTRACT = None


def validate_selection(document, prior, contract):
    rows = document['rows']
    prior_rows = {row['id']: row for row in prior['rows']}
    inv.require(len(prior_rows) == len(prior['rows']), 'duplicate prior selection id')
    safe_rows = {row['id']: row for row in rows if row['id'] in SAFE_IDS}
    inv.require(set(safe_rows) == SAFE_IDS, 'exactly three prior safe selections required')
    inv.require(all(row == prior_rows.get(key) for key, row in safe_rows.items()),
                'prior safe derivative selection changed')
    new_hashes = {entry[label]['sha256'] for entry in contract['newly_quarantined_entries']
                  for label in ['original', 'derived_candidate']}
    for row in rows:
        choice = row['selected']
        if (row['id'] in guard5.NEW_IDS or row['original_text_sha256'] in new_hashes
                or choice.get('clean_text_sha256') in new_hashes):
            inv.require(choice['decision'] == 'HOLD' and not choice.get('body')
                and not choice.get('clean_text_sha256'),
                'new quarantined original/candidate cannot enter accepted selection')


def validate_new_aliases(opaque, contract):
    trusted = opaque['trusted_hold_metadata']
    aliases = set()
    for entry in contract['newly_quarantined_entries']:
        for key in entry['parent_alias_ids']:
            expected = contract['trusted_metadata'][key]
            inv.require(key in trusted, 'new quarantined alias missing from opaque HOLD')
            actual = trusted[key]
            inv.require(all(actual.get(name) == value for name, value in expected.items()),
                        'new quarantined alias metadata differs')
            inv.require(actual.get('parent_decision') == 'HOLD', 'quarantined alias not HOLD')
            aliases.add(key)
    inv.require(len(aliases) == 4, 'exactly four new quarantined aliases required')
    return aliases


def selection_binding(selection, contract):
    storage = SelectionStore(AUDIT)
    selection = Path(selection)
    digest = inv.file_sha(selection)
    document = storage.read(selection, digest)
    pin = document['prior_selection']
    prior_path = ROOT/pin['path']
    prior = storage.read(prior_path, pin['sha256'])
    validate_selection(document, prior, contract)
    return [(selection, digest)]


class GuardedInputs(BASE_INPUTS):
    def __init__(self, selection):
        contract = checked_contract()
        inv.require(guard4_runtime.ACTIVE_OPAQUE is not None, 'exact opaque context required')
        validate_new_aliases(guard4_runtime.ACTIVE_OPAQUE[2], contract)
        super().__init__(selection)
        inv.require(self.contract_sha == EXPECTED and self.metadata == contract['trusted_metadata']
            and self.restricted_ids == set(contract['restricted_ids'])
            and self.restricted_hashes == set(contract['restricted_hashes']),
            'guard5 was not installed throughout the reused cache runtime')
        paths = [Path(__file__), CONTRACT, AUDIT/'active_guard_v5_preflight_v1.py',
                 AUDIT/'selection_metadata_store_v1.py', AUDIT/'GUARDED_CACHE_V8_F3_F4_V1.md']
        # Inspect the physical header, not the bound logical dict.
        header = json.JSONDecoder().decode(Path(selection).read_text(encoding='utf-8'))
        if FORMAT_KEY in header:
            storage = SelectionStore(AUDIT)
            paths.extend(storage.shard_path(pin) for pin in header['row_shards'])
        names = [str(path.relative_to(ROOT)) for path in paths]
        self.pins = list(dict.fromkeys(self.pins + names))
        self.pin_values.update({name: inv.file_sha(ROOT/name) for name in names})


@contextmanager
def runtime(selection):
    with active_contract() as contract:
        bindings = selection_binding(selection, contract)
        with bound_selection_loads(bindings, directory=AUDIT), \
                patch.object(previous, 'GuardedInputs', GuardedInputs):
            with BASE_RUNTIME(selection) as inputs:
                yield inputs


def current_pins(selection, opaque_path, opaque_sha):
    with active_contract(), patch.object(previous, 'runtime', runtime):
        return previous.current_pins(selection, opaque_path, opaque_sha)


def verify_configuration(config):
    with active_contract(), patch.object(previous, 'runtime', runtime):
        return previous.verify_configuration(config)


def build(base, adoptions, roster, output_name, proposal_name, selection, opaque_path, opaque_sha):
    with active_contract(), patch.object(previous, 'runtime', runtime):
        return previous.build(base, adoptions, roster, output_name, proposal_name,
                              selection, opaque_path, opaque_sha)


def verify(base, roster, output_name, selection, opaque_path, opaque_sha):
    # Keep EXPECTED=guard5 through previous.verify's final opaque ledger proof.
    with active_contract(), patch.object(previous, 'runtime', runtime):
        return previous.verify(base, roster, output_name, selection, opaque_path, opaque_sha)
