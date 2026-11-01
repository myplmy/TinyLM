#!/usr/bin/env python3
"""Apply exact reviewed literal exceptions through the frozen cache engines.

Partial rosters remain explicitly incomplete. Final rosters must satisfy the
unchanged zero-HOLD conditions. No baseline text, code guard or source file is
modified, and every exception input becomes an immutable runtime input pin.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_cache as final
from scripts import p106b_hold_resolution_partial_cache as partial
from scripts import p106b_hold_resolution_revision_v10 as context_revision
from scripts import p106b_hold_resolution_literal_guard_v1 as literal

ORIGINAL_ENGINE = final.ResolutionEngine


class ReviewedResolutionEngine(ORIGINAL_ENGINE):
    def __init__(self, *args, **kwargs):
        self.literal_cases = literal.load_registry()
        super().__init__(*args, **kwargs)

    def code_guard(self, original, cleaned, manual=None):
        if super().code_guard(original, cleaned, manual):
            return True
        # A new exception can never alter an already admitted baseline body.
        if self.current[1] != 3:
            return False
        ident = (manual or {}).get("literal_guard_case_id")
        return literal.exact_pair_preserved(original, cleaned, ident, self.literal_cases)


def input_pins(cases):
    paths = [literal.REGISTRY, "scripts/p106b_hold_resolution_literal_guard_v1.py",
             "scripts/p106b_hold_resolution_reviewed_cache_v1.py"]
    for row in cases.values():
        paths += [row["original"], row["body"], row["evidence"]["path"]]
        paths += [pin["path"] for pin in row["review_inputs"]]
    return list(dict.fromkeys(partial.EXTRA_CODE + context_revision.CODE + paths))


@contextmanager
def reviewed_inputs():
    cases = literal.load_registry()
    pins = input_pins(cases)
    with patch.object(final, "ResolutionEngine", ReviewedResolutionEngine), \
            patch.object(final, "EXTRA_CODE", pins), patch.object(partial, "EXTRA_CODE", pins):
        yield
    # Evidence cannot silently change while a cache is being built/consumed.
    literal.load_registry()


def selected_adapter(roster):
    schema = final.engine.cache.read(roster).get("schema")
    if schema == partial.SCHEMA:
        return partial
    final.require(schema == final.SCHEMA, "unknown reviewed roster schema")
    return final


def build(base, adoptions, roster, output_name, proposal_name):
    adapter = selected_adapter(roster)
    with reviewed_inputs():
        return adapter.build(base, adoptions, roster, output_name, proposal_name)


def verify(base, roster, output_name):
    adapter = selected_adapter(roster)
    with reviewed_inputs():
        return adapter.verify(base, roster, output_name)


def main():
    os.environ.update(CUDA_VISIBLE_DEVICES="", TOKENIZERS_PARALLELISM="false", RAYON_NUM_THREADS="1",
                      OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "verify"])
    parser.add_argument("--base", type=Path, default=final.BASE)
    parser.add_argument("--roster", type=Path, required=True)
    parser.add_argument("--adoptions", type=Path)
    parser.add_argument("--output-name", required=True)
    parser.add_argument("--proposal-name", default="reviewed_proposals_v1")
    args = parser.parse_args()
    base, roster = final.engine.safe(args.base), final.engine.safe(args.roster)
    if args.command == "build":
        final.require(args.adoptions is not None, "exact reviewed adoptions required")
        result = build(base, final.engine.safe(args.adoptions), roster, args.output_name, args.proposal_name)
    else:
        result = verify(base, roster, args.output_name)
    print(json.dumps({key: value for key, value in result.items()
                      if key in {"status", "counts", "recovery_outcomes", "partial_resolution"}}), flush=True)


if __name__ == "__main__":
    main()
