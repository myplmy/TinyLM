"""Add exact reviewed runtime pairs and the already verified typed-alias proof."""
from contextlib import contextmanager
from pathlib import Path
import sys
from unittest.mock import patch

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
import guarded_reviewed_cache_v1 as previous
import exact_runtime_pair_guard_v1 as exact
from scripts import p106b_hold_resolution_policy_v22 as aliases

CASES=None
ROOT=previous.ROOT
inv=previous.inv
ORIGINAL_RUNTIME=previous.runtime


class GuardedInputs(previous.GuardedInputs):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        paths=[str(Path(__file__).relative_to(ROOT)),str(Path(exact.__file__).relative_to(ROOT)),
               str(exact.REGISTRY.relative_to(ROOT)),'scripts/p106b_hold_resolution_policy_v22.py']
        draft_path=inv.BASE/'draft_proposals_v26_delta_v1/complete.json'
        frozen=inv.cache.read(draft_path)['lineage']['source_code_sha256']
        inv.require(len(frozen)==66,'all frozen policy dependencies must be pinned')
        for name,expected in frozen.items():
            inv.require(inv.file_sha(ROOT/name)==expected,'frozen policy dependency changed')
        paths += list(frozen) + [str(draft_path.relative_to(ROOT))]
        self.pins=list(dict.fromkeys(self.pins+paths))
        self.pin_values.update({name:inv.file_sha(ROOT/name) for name in paths})


class GuardedResolutionEngine(previous.GuardedResolutionEngine):
    def __init__(self,*args,**kwargs):
        inv.require(CASES is not None,'exact pair runtime is required')
        self.exact_cases=CASES
        super().__init__(*args,**kwargs)

    def code_guard(self,original,cleaned,manual=None):
        if super().code_guard(original,cleaned,manual):
            return True
        row,state=self.current
        if state!=3 or row.get('restricted_parent_body_not_decoded') is True:
            return False
        # The frozen V22 rule proves only the first explicit named definition's
        # optional alias. All other actual code/Unicode remains under the old
        # guard, including real calls elsewhere in the same document.
        prepared,proof=aliases.typed_initial_alias(original)
        if proof and previous.reviewed.final.engine.policy.code_preserved(prepared,cleaned) and \
                previous.reviewed.final.engine.policy.unicode_examples_preserved(original,cleaned):
            return True
        return exact.exact_pair_preserved(original,cleaned,(manual or {}).get('exact_runtime_pair_id'),self.exact_cases)


@contextmanager
def runtime(selection):
    global CASES
    inv.require(CASES is None,'exact runtime cannot nest')
    CASES=exact.load_registry()
    try:
        with patch.object(previous,'GuardedInputs',GuardedInputs), \
                patch.object(previous,'GuardedResolutionEngine',GuardedResolutionEngine):
            with ORIGINAL_RUNTIME(selection) as inputs:
                yield inputs
        exact.load_registry()
    finally:
        CASES=None


def build(base,adoptions,roster,output_name,proposal_name,selection):
    with runtime(selection):
        return previous.reviewed.build(base,adoptions,roster,output_name,proposal_name)


def verify(base,roster,output_name,selection):
    # Preserve the full consumer plus the V1 restricted metadata ledger check.
    with patch.object(previous,'runtime',runtime):
        return previous.verify(base,roster,output_name,selection)


def main():
    with patch.object(previous,'build',build),patch.object(previous,'verify',verify):
        return previous.main()


if __name__=='__main__':
    main()
