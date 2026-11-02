"""Reuse frozen cache engines while restricted original bodies remain opaque."""
from contextlib import contextmanager
from pathlib import Path
import argparse
import json
import os
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUDIT))
from scripts import p106b_hold_resolution_reviewed_cache_v2 as reviewed
from scripts import p106b_hold_resolution_inventory as inv
from guarded_scan_metadata_v1 import guarded_row

CONTRACT = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
SAFE_IDS = {'expanded_train:1250821', 'expanded_train:15695', 'expanded_train:20624'}
ACTIVE = None


def validate_outcome(row, decision, text, safe):
    """A projected original can never become a source slice or unreviewed body."""
    inv.require(row.get('restricted_parent_body_not_decoded') is True and row['text'] == '',
                'restricted outcome requires an explicit absent-body projection')
    inv.require(decision in {'EDIT', 'EXCLUDE', 'HOLD'}, 'restricted KEEP/source slice is forbidden')
    if decision == 'EDIT':
        key = row['original_text_sha256']
        inv.require(key in safe and text and inv.sha(text) == safe[key]['clean_text_sha256'],
                    'restricted EDIT lacks an exact approved safe-view body')


class GuardedInputs:
    def __init__(self, selection):
        self.selection_path = Path(selection)
        self.document = inv.cache.read(CONTRACT)
        self.contract_sha = inv.file_sha(CONTRACT)
        for name, expected in self.document['input_pins'].items():
            inv.require(inv.file_sha(ROOT/name) == expected, 'trusted metadata input changed')
        self.metadata = self.document['trusted_metadata']
        self.restricted_ids = set(self.document['restricted_ids'])
        self.restricted_hashes = set(self.document['restricted_hashes'])
        self.safe, self.safe_texts = {}, {}
        self.pins = [str(CONTRACT.relative_to(ROOT)), str(self.selection_path.relative_to(ROOT)),
                     str(Path(__file__).relative_to(ROOT)),
                     str((AUDIT/'guarded_scan_metadata_v1.py').relative_to(ROOT))]
        selections = inv.cache.read(self.selection_path)
        inv.require(selections['unresolved_sources'] == 0, 'safe view requires closed exact selections')
        for row in selections['rows']:
            if row['id'] not in SAFE_IDS:
                continue
            choice = row['selected']
            inv.require(row.get('root_approved') is True and choice['decision'] == 'EDIT',
                        'safe body must have explicit exact root approval')
            key = row['original_text_sha256']
            inv.require(key in self.restricted_hashes and choice.get('compare_source'),
                        'restricted safe body lacks an original-linked safe source view')
            view = choice['compare_source']
            inv.require(inv.file_sha(ROOT/view['path']) == view['sha256'] and
                        inv.file_sha(ROOT/choice['body']) == choice['clean_text_sha256'], 'safe view/body changed')
            original = (ROOT/view['path']).read_text(encoding='utf-8')
            clean = (ROOT/choice['body']).read_text(encoding='utf-8')
            inv.require(reviewed.final.engine.policy.unicode_examples_preserved(original, clean) and
                        reviewed.final.engine.policy.code_preserved(original, clean),
                        'safe view code or Unicode identity changed')
            self.safe[key] = dict(id=row['id'], view=view, body=choice['body'],
                                  clean_text_sha256=choice['clean_text_sha256'])
            self.safe_texts[key] = (original, clean)
            self.pins += [view['path'], choice['body']]
        inv.require({row['id'] for row in self.safe.values()} == SAFE_IDS, 'exactly three approved safe views required')
        self.pin_values = {name:inv.file_sha(ROOT/name) for name in self.pins}

    def check(self):
        for name, expected in self.pin_values.items():
            inv.require(inv.file_sha(ROOT/name) == expected, 'guarded runtime input changed')

    def iter_scan(self, _base, source=None):
        # The old recovery adapter passes its parent explicitly. Read that same
        # frozen source directly, never fall back to a text-decoding iterator.
        base = reviewed.final.engine.recovery.PARENT
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
                            yield guarded_row(line, restricted_ids=self.restricted_ids,
                                              restricted_hashes=self.restricted_hashes,
                                              trusted_metadata=self.metadata)


class GuardedResolutionEngine(reviewed.ReviewedResolutionEngine):
    def __init__(self, *args, **kwargs):
        inv.require(ACTIVE is not None, 'guarded runtime context is required')
        self.guard = ACTIVE
        super().__init__(*args, **kwargs)

    def pick(self, row, overrides, known=False):
        blocked = row.get('restricted_parent_body_not_decoded') is True
        if blocked:
            inv.require(self.index.state(row) in {3,4,5}, 'restricted body cannot replace an admitted baseline')
            if self.index.state(row) == 3:
                proposal = self.roster[row['original_text_sha256']]
                text = proposal.get('text', '') if proposal['decision'] == 'EDIT' else ''
                validate_outcome(row, proposal['decision'], text, self.guard.safe)
        value = super().pick(row, overrides, known)
        if blocked:
            validate_outcome(row, value[0], value[1], self.guard.safe)
        return value

    def code_guard(self, original, cleaned, manual=None):
        row, state = self.current
        if row.get('restricted_parent_body_not_decoded') is not True:
            return super().code_guard(original, cleaned, manual)
        inv.require(state == 3 and original == '', 'restricted safe view is only for new residual edits')
        validate_outcome(row, 'EDIT', cleaned, self.guard.safe)
        safe_original, safe_clean = self.guard.safe_texts[row['original_text_sha256']]
        return cleaned == safe_clean and reviewed.final.engine.policy.code_preserved(safe_original, cleaned) and \
            reviewed.final.engine.policy.unicode_examples_preserved(safe_original, cleaned)

    def annotate(self, row, *, ledger=False):
        result = super().annotate(row, ledger=ledger)
        if row['id'] in self.guard.metadata:
            result.update(restricted_parent_body_not_decoded=True,
                          restricted_metadata_contract_sha256=self.guard.contract_sha)
            if row['decision'] in {'KEEP','EDIT'}:
                inv.require(row['decision'] == 'EDIT' and row['serialization_mode'] == 'ENCODE_CLEAN_TEXT',
                            'restricted accepted body cannot use a source slice')
                safe = self.guard.safe[row['original_text_sha256']]
                inv.require(row['clean_text_sha256'] == safe['clean_text_sha256'], 'restricted accepted body differs')
                result['restricted_safe_source_view'] = safe['view']
        return result


@contextmanager
def runtime(selection):
    global ACTIVE
    inv.require(ACTIVE is None, 'guarded runtime cannot nest')
    inputs = GuardedInputs(selection)
    original_pins = reviewed.input_pins

    def pins(cases):
        return list(dict.fromkeys(original_pins(cases) + inputs.pins))

    ACTIVE = inputs
    try:
        with patch.object(reviewed, 'ReviewedResolutionEngine', GuardedResolutionEngine), \
                patch.object(reviewed, 'input_pins', pins), \
                patch.object(inv.corpus, 'iter_scan', inputs.iter_scan):
            yield inputs
        inputs.check()
    finally:
        ACTIVE = None


def build(base, adoptions, roster, output_name, proposal_name, selection):
    with runtime(selection):
        return reviewed.build(base, adoptions, roster, output_name, proposal_name)


def verify(base, roster, output_name, selection):
    with runtime(selection) as inputs:
        result = reviewed.verify(base, roster, output_name)
        report = inv.cache.read(base/output_name/'built.json')
        checked = set()
        for row in inv.cache.rows(base/output_name/'ledger', report['manifests']['ledger']):
            if row['id'] not in inputs.metadata:
                continue
            inv.require(row.get('restricted_parent_body_not_decoded') is True and
                        row.get('restricted_metadata_contract_sha256') == inputs.contract_sha,
                        'restricted ledger lacks guarded metadata provenance')
            if row['decision'] in {'KEEP','EDIT'}:
                safe = inputs.safe[row['original_text_sha256']]
                inv.require(row['decision'] == 'EDIT' and row['serialization_mode'] == 'ENCODE_CLEAN_TEXT' and
                            row['clean_text_sha256'] == safe['clean_text_sha256'] and
                            row['restricted_safe_source_view'] == safe['view'], 'restricted admitted body differs')
            checked.add(row['id'])
        inv.require(checked == set(inputs.metadata), 'restricted alias coverage differs')
        proof = dict(status='RESTRICTED_METADATA_AND_EXACT_SAFE_VIEW_CACHE_LEDGER_VERIFIED',
                     restricted_sources=len(inputs.restricted_ids), alias_positions=len(checked),
                     original_parent_bodies_decoded=False, contract_sha256=inputs.contract_sha,
                     goal_complete=False, training_authorized=False)
        inv.write_json(base/output_name/'restricted_metadata_verified.json', proof)
        return dict(result, restricted_metadata=proof)


def main():
    os.environ.update(CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                      MKL_NUM_THREADS='1', RAYON_NUM_THREADS='1', TOKENIZERS_PARALLELISM='false')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build','verify'])
    parser.add_argument('--roster', type=Path, required=True)
    parser.add_argument('--adoptions', type=Path)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--output-name', required=True)
    parser.add_argument('--proposal-name', default='guarded_partial_proposals_v2')
    args = parser.parse_args()
    if args.command == 'build':
        inv.require(args.adoptions is not None, 'exact root adoptions required')
        result = build(inv.BASE, args.adoptions.resolve(), args.roster.resolve(), args.output_name,
                       args.proposal_name, args.selection.resolve())
    else:
        result = verify(inv.BASE, args.roster.resolve(), args.output_name, args.selection.resolve())
    print(json.dumps({key:value for key,value in result.items() if key in
                      {'status','counts','recovery_outcomes','partial_resolution','restricted_metadata'}}))


if __name__ == '__main__':
    main()
