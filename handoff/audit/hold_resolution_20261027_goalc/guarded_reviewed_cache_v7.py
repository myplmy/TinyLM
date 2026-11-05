"""Keep guard6 payload semantics and reference immutable census metadata once."""
from contextlib import contextmanager
from pathlib import Path
import sys
from unittest.mock import patch

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
import guarded_reviewed_cache_v6 as previous
from referenced_census_metadata_v1 import bind_reference, resolve_reference

ROOT, inv, first = previous.ROOT, previous.inv, previous.first
opaque_contract, checked_contract = previous.opaque_contract, previous.checked_contract
BASE_RUNTIME, BASE_INPUTS = previous.runtime, previous.GuardedInputs


class GuardedInputs(BASE_INPUTS):
    def __init__(self, selection):
        super().__init__(selection)
        paths = [Path(__file__), AUDIT/'referenced_census_metadata_v1.py']
        names = [str(path.relative_to(ROOT)) for path in paths]
        self.pins = list(dict.fromkeys(self.pins + names))
        self.pin_values.update({name: inv.file_sha(ROOT/name) for name in names})


@contextmanager
def runtime(selection):
    with patch.object(previous, 'GuardedInputs', GuardedInputs):
        with BASE_RUNTIME(selection) as inputs:
            yield inputs


def current_pins(selection, opaque_path, opaque_sha):
    from scripts import p106b_hold_resolution_partial_cache as partial
    with opaque_contract(opaque_path, opaque_sha):
        with runtime(selection):
            with first.reviewed.reviewed_inputs():
                with partial.revision():
                    return partial.engine.code_pins()


def verify_configuration(c):
    path = inv.BASE/c['proposal_name']/'complete.json'
    document = inv.cache.read(path)
    expected = current_pins(AUDIT/f"ROOT_AUTHORED_SELECTIONS_V{c['selection_version']}.json",
        AUDIT/c['opaque_contract'], c['opaque_contract_sha256'])
    inv.require(document['pin']['recovery_revision_source_sha256'] == expected,
        'reference census/code fingerprint differs before worker launch')
    source = resolve_reference(ROOT, inv.PARENT, document, inv.cache.read, inv.file_sha)
    inv.verify(source, document['manifest'])
    inv.require(document['remaining_hold'] == c['expected_HOLD_positions'], 'reference HOLD count differs')
    return expected


def build(base, adoptions, roster, output_name, proposal_name, selection, opaque_path, opaque_sha):
    census_path = base/proposal_name/'complete.json'
    document = inv.cache.read(census_path)
    with bind_reference(inv.cache, ROOT, inv.PARENT, census_path, document, inv.file_sha):
        with opaque_contract(opaque_path, opaque_sha) as opaque:
            inv.require(inv.file_sha(roster) == opaque['roster_sha256'], 'opaque roster differs')
            with runtime(selection):
                return first.reviewed.build(base, adoptions, roster, output_name, proposal_name)


def verify(base, roster, output_name, selection, opaque_path, opaque_sha):
    with patch.object(previous, 'runtime', runtime):
        return previous.verify(base, roster, output_name, selection, opaque_path, opaque_sha)
