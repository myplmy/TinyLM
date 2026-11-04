"""Reuse full cache engines with cumulative guard4 and opaque unadopted HOLD."""
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
import sys
from unittest.mock import patch

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
import guarded_reviewed_cache_v4 as previous
from opaque_hold_metadata_v1 import guarded_or_opaque_row, validate_hold_outcome

ROOT, inv = previous.ROOT, previous.inv
first = previous.previous.first
BASE_RUNTIME = previous.runtime
BASE_INPUTS = previous.GuardedInputs
BASE_ENGINE = previous.GuardedResolutionEngine
CONTRACT = AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V4.json'
EXPECTED = '59CA9419990CD1D6968EA9B1E7EF4416D418C8C460EDD8074E98DA9BF5FCEF7D'
ACTIVE_OPAQUE = None


def checked_contract():
    inv.require(inv.file_sha(CONTRACT) == EXPECTED, 'cumulative metadata contract changed')
    data = inv.cache.read(CONTRACT)
    inv.require(len(data['restricted_ids']) == 9 and len(data['restricted_hashes']) == 10
        and len(data['trusted_metadata']) == 15, 'cumulative protection count differs')
    inv.require(data['new_restricted_entry']['parent_alias_ids'] ==
        ['expanded_train:267902', 'historical_train:267904'], 'new protected aliases differ')
    inv.require(all(data['trusted_metadata'][key]['parent_decision'] == 'HOLD'
        for key in data['new_restricted_entry']['parent_alias_ids']), 'new source was already admitted')
    return data


@contextmanager
def opaque_contract(path, expected_sha):
    global ACTIVE_OPAQUE
    inv.require(ACTIVE_OPAQUE is None, 'opaque runtime cannot nest')
    path = Path(path).resolve()
    inv.require(path.is_relative_to(AUDIT) and not path.is_symlink(), 'opaque contract escaped audit')
    inv.require(inv.file_sha(path) == expected_sha, 'opaque contract changed')
    document = inv.cache.read(path)
    inv.require(document['schema'] == 'OPAQUE_UNADOPTED_HOLD_METADATA_V1', 'unknown opaque contract')
    inv.require(document['body_fields_decoded'] == 0 and
        document['ordinary_HOLD_is_not_reclassified_as_sensitive'] is True, 'opaque scope differs')
    directory = (ROOT/document['hold_metadata_directory']).resolve()
    inv.require(directory.is_relative_to(inv.BASE) and not directory.is_symlink(), 'opaque metadata escaped data scope')
    manifest = document['hold_metadata_manifest']
    inv.require(all(shard['bytes'] < 20_000_000 for shard in manifest['shards']), 'opaque metadata shard is oversized')
    inv.verify(directory, manifest)
    trusted = {}
    for row in inv.cache.rows(directory, manifest):
        inv.require(row['id'] not in trusted, 'duplicate opaque metadata position')
        trusted[row['id']] = row
    document['trusted_hold_metadata'] = trusted
    hashes = set(document['hold_hashes'])
    inv.require(len(trusted) == document['counts']['positions'] and
        len(hashes) == document['unique_sources'] and
        all(row['parent_decision'] == 'HOLD' and row['original_text_sha256'] in hashes
            for row in trusted.values()) and
        sum(row['input_ids'] for row in trusted.values()) == document['counts']['input_ids'],
        'opaque metadata census differs')
    for name, pin in document['input_pins'].items():
        inv.require(inv.file_sha(ROOT/name) == pin, 'opaque input pin changed')
    ACTIVE_OPAQUE = (path, expected_sha, document)
    try:
        yield document
        inv.require(inv.file_sha(path) == expected_sha, 'opaque contract changed during use')
    finally:
        ACTIVE_OPAQUE = None


class GuardedInputs(BASE_INPUTS):
    def __init__(self, selection):
        inv.require(ACTIVE_OPAQUE is not None, 'an exact opaque contract is required')
        super().__init__(selection)
        path, digest, document = ACTIVE_OPAQUE
        inv.require(str(Path(selection).relative_to(ROOT)) == document['selection'] and
            inv.file_sha(Path(selection)) == document['selection_sha256'], 'opaque selection differs')
        self.opaque = document
        self.opaque_sha = digest
        self.hold_metadata = document['trusted_hold_metadata']
        self.hold_hashes = set(document['hold_hashes'])
        paths = [Path(__file__), CONTRACT, path, AUDIT/'GUARDED_CACHE_V6_SCOPE_V1.md',
            AUDIT/'opaque_hold_metadata_v1.py', AUDIT/'OPAQUE_UNADOPTED_HOLD_CACHE_F3_F4_V1.md']
        names = [str(item.relative_to(ROOT)) for item in paths]
        self.pins = list(dict.fromkeys(self.pins + names + list(document['input_pins'])))
        directory = ROOT/document['hold_metadata_directory']
        self.pins += [str((directory/shard['path']).relative_to(ROOT))
            for shard in document['hold_metadata_manifest']['shards']]
        self.pin_values.update({name: inv.file_sha(ROOT/name) for name in self.pins})

    def iter_scan(self, _base, source=None):
        base = first.reviewed.final.engine.recovery.PARENT
        scope = inv.cache.read(base/'scope.json')
        for spec in scope['inputs']:
            if source and spec['name'] != source:
                continue
            for stamp in sorted((base/'scan'/spec['name']).glob('unit_*/complete.json')):
                info = inv.cache.read(stamp)
                inv.verify(stamp.parent/'records', info['manifest'])
                for shard in info['manifest']['shards']:
                    with (stamp.parent/'records'/shard['path']).open('rb') as stream:
                        for line in stream:
                            yield guarded_or_opaque_row(line,
                                restricted_ids=self.restricted_ids,
                                restricted_hashes=self.restricted_hashes,
                                restricted_metadata=self.metadata,
                                hold_metadata=self.hold_metadata, hold_hashes=self.hold_hashes)


class GuardedResolutionEngine(BASE_ENGINE):
    def pick(self, row, overrides, known=False):
        if row.get('unadopted_hold_body_not_decoded') is True:
            validate_hold_outcome(row, self.index.state(row),
                                  self.roster[row['original_text_sha256']])
        value = super().pick(row, overrides, known)
        if row.get('unadopted_hold_body_not_decoded') is True:
            validate_hold_outcome(row, self.index.state(row),
                                  self.roster[row['original_text_sha256']], value)
        return value

    def code_guard(self, original, cleaned, manual=None):
        inv.require(self.current[0].get('unadopted_hold_body_not_decoded') is not True,
                    'an opaque HOLD cannot enter an adoption code guard')
        return super().code_guard(original, cleaned, manual)

    def annotate(self, row, *, ledger=False):
        result = super().annotate(row, ledger=ledger)
        if row['id'] in self.guard.hold_metadata:
            inv.require(row['decision'] == 'HOLD' and not row.get('clean_text_sha256')
                and not row.get('cache'), 'opaque HOLD appeared in accepted output')
            result.update(unadopted_hold_body_not_decoded=True,
                          opaque_hold_metadata_contract_sha256=self.guard.opaque_sha)
        return result


@contextmanager
def runtime(selection):
    contract = checked_contract()
    with patch.object(first, 'CONTRACT', CONTRACT), \
        patch.object(previous, 'GuardedInputs', GuardedInputs), \
        patch.object(previous, 'GuardedResolutionEngine', GuardedResolutionEngine):
        with BASE_RUNTIME(selection) as inputs:
            inv.require(inputs.contract_sha == EXPECTED and
                inputs.metadata == contract['trusted_metadata'], 'active guard4 was not loaded')
            yield inputs


def build(base, adoptions, roster, output_name, proposal_name, selection, opaque_path, opaque_sha):
    with opaque_contract(opaque_path, opaque_sha) as document:
        inv.require(inv.file_sha(roster) == document['roster_sha256'], 'opaque roster differs')
        with runtime(selection):
            return first.reviewed.build(base, adoptions, roster, output_name, proposal_name)


def verify(base, roster, output_name, selection, opaque_path, opaque_sha):
    with opaque_contract(opaque_path, opaque_sha) as document:
        inv.require(inv.file_sha(roster) == document['roster_sha256'], 'opaque roster differs')
        with patch.object(previous, 'runtime', runtime):
            result = previous.verify(base, roster, output_name, selection)
        report = inv.cache.read(base/output_name/'built.json')
        checked, counts = set(), Counter()
        for row in inv.cache.rows(base/output_name/'ledger', report['manifests']['ledger']):
            if row['id'] not in document['trusted_hold_metadata']:
                inv.require(not row.get('unadopted_hold_body_not_decoded'), 'outside opaque annotation')
                continue
            expected = document['trusted_hold_metadata'][row['id']]
            inv.require(row['id'] not in checked and row['decision'] == 'HOLD'
                and row.get('unadopted_hold_body_not_decoded') is True
                and row.get('opaque_hold_metadata_contract_sha256') == ACTIVE_OPAQUE[1]
                and not row.get('clean_text_sha256') and not row.get('cache'), 'opaque ledger differs')
            for name in ['original_text_sha256', 'source_ids', 'source_ids_sha256', 'input_ids']:
                inv.require(row[name] == expected[name], 'opaque interval identity changed')
            checked.add(row['id']); counts.update(positions=1, input_ids=row['input_ids'])
        inv.require(checked == set(document['trusted_hold_metadata']) and
            dict(counts) == document['counts'], 'opaque full consumer coverage differs')
        proof = dict(status='FULL_UNADOPTED_HOLD_METADATA_CONSUMER_VERIFIED',
            counts=dict(counts), unique_sources=document['unique_sources'],
            contract_sha256=ACTIVE_OPAQUE[1], active_restricted_contract_sha256=EXPECTED,
            ordinary_HOLD_is_not_reclassified_as_sensitive=True,
            goal_complete=False, training_authorized=False)
        inv.write_json(base/output_name/'opaque_hold_verified.json', proof)
        return dict(result, opaque_hold=proof)
