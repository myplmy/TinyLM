"""Reproduce the existing census fingerprint context before an expensive build."""
from pathlib import Path
from guarded_reviewed_cache_v6 import ROOT, inv, opaque_contract, runtime, first
from scripts import p106b_hold_resolution_partial_cache as partial

AUDIT = Path(__file__).resolve().parent


def current_pins(selection, opaque_path, opaque_sha):
    with opaque_contract(opaque_path, opaque_sha):
        with runtime(selection):
            with first.reviewed.reviewed_inputs():
                with partial.revision():
                    return partial.engine.code_pins()


def verify_configuration(c):
    name = c.get('proposal_name', f"guarded_partial_proposals_v{c['roster_version']}")
    path = inv.BASE/name/'complete.json'
    census = inv.cache.read(path)
    expected = current_pins(AUDIT/f"ROOT_AUTHORED_SELECTIONS_V{c['selection_version']}.json",
        AUDIT/c['opaque_contract'], c['opaque_contract_sha256'])
    inv.require(census['pin']['recovery_revision_source_sha256'] == expected,
        'full enumeration census/code fingerprint differs before worker launch')
    inv.require(census['unprocessed'] == 0 and census['counts'] ==
        {'documents':460695, 'input_ids':462874291}, 'full enumeration coverage differs')
    inv.verify(path.parent/'ledger', census['manifest'])
    inv.require(census['remaining_hold'] == c['expected_HOLD_positions'], 'census current HOLD count differs')
    return expected
