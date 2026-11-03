"""Add only the exact verified LTER table body whose unusable script is held."""
from contextlib import contextmanager
from pathlib import Path
import sys
from unittest.mock import patch

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
import guarded_reviewed_cache_v3 as previous

ROOT, inv = previous.ROOT, previous.inv
BASE_RUNTIME = previous.runtime
BASE_INPUTS = previous.GuardedInputs
BASE_ENGINE = previous.GuardedResolutionEngine
REGISTRY = AUDIT / 'EXACT_LTER_TABLE_BODY_APPROVAL_1323187_V1.json'


def lter_case():
    case = inv.cache.read(REGISTRY)
    inv.require(case['id'] == 'expanded_train:1323187' and case['root_approved'] is True
        and case['applies_only_to_original_and_body_sha256'] is True
        and case['global_code_guard_waiver'] is False and case['full_held_script_preserved'] is True
        and case['proof']['rows_checked'] == 27 and case['proof']['exact_all_names_and_coordinate_strings'] is True,
        'exact source/table partial-body approval required')
    for name, expected in case['input_pins'].items():
        path = ROOT / name
        inv.require(path.resolve().is_relative_to(ROOT) and not path.is_symlink(), 'LTER input left repository')
        inv.require(inv.file_sha(path) == expected, 'LTER exact evidence changed')
    return case


class GuardedInputs(BASE_INPUTS):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lter_case = lter_case()
        paths = [str(Path(__file__).relative_to(ROOT)), str(REGISTRY.relative_to(ROOT)),
            *self.lter_case['input_pins']]
        self.pins = list(dict.fromkeys(self.pins + paths))
        self.pin_values.update({name:inv.file_sha(ROOT / name) for name in paths})


class GuardedResolutionEngine(BASE_ENGINE):
    def code_guard(self, original, cleaned, manual=None):
        if super().code_guard(original, cleaned, manual): return True
        row, state = self.current
        if state != 3 or row.get('restricted_parent_body_not_decoded') is True: return False
        case = self.guard.lter_case
        return ((manual or {}).get('exact_lter_table_pair_id') == case['id']
            and inv.sha(original) == case['original']['sha256']
            and inv.sha(cleaned) == case['body']['sha256']
            and previous.reviewed.final.engine.policy.unicode_examples_preserved(original, cleaned))


@contextmanager
def runtime(selection):
    with patch.object(previous, 'GuardedInputs', GuardedInputs), \
        patch.object(previous, 'GuardedResolutionEngine', GuardedResolutionEngine):
        with BASE_RUNTIME(selection) as inputs:
            yield inputs


def build(base, adoptions, roster, output_name, proposal_name, selection):
    with runtime(selection):
        return previous.reviewed.build(base, adoptions, roster, output_name, proposal_name)


def verify(base, roster, output_name, selection):
    with patch.object(previous.first, 'runtime', runtime):
        result = previous.BASE_FIRST_VERIFY(base, roster, output_name, selection)
    parent = inv.cache.read(inv.PARENT / 'built.json')
    scope = dict(status='PRESERVATION_BASELINE_IDENTIFIED_NOT_ALL_INTERMEDIATE_BODIES',
        baseline_parent=str(inv.PARENT.relative_to(ROOT)),
        baseline_parent_built_sha256=inv.file_sha(inv.PARENT / 'built.json'),
        preserved_baseline_documents=parent['counts'].get('KEEP',0)+parent['counts'].get('EDIT',0),
        meaning='all_previous_adopted_text_preserved refers to this frozen parent; ROOT10 and later intermediate bodies can have explicitly reviewed corrections or withdrawals.',
        selected_body_approval=dict(path=str(Path(selection).relative_to(ROOT)), sha256=inv.file_sha(selection)),
        goal_complete=False, training_authorized=False)
    inv.write_json(base / output_name / 'baseline_preservation_scope.json', scope)
    return dict(result, baseline_preservation_scope=scope)


def main():
    with patch.object(previous.first, 'build', build), patch.object(previous.first, 'verify', verify):
        return previous.first.main()


if __name__ == '__main__': main()
