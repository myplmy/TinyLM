#!/usr/bin/env python3
"""Reuse unchanged cache engines with ten exact reviewed literal pairs.

Both approval registries and every original/body/review are runtime pins. The
partial/final distinction and preserved-baseline priority are unchanged.
"""
from contextlib import contextmanager
from unittest.mock import patch
from scripts import p106b_hold_resolution_reviewed_cache_v1 as previous
from scripts import p106b_hold_resolution_literal_guard_v2 as literal
from scripts import p106b_hold_resolution_revision_v13 as context_revision

final, partial = previous.final, previous.partial
ORIGINAL_ENGINE = previous.ORIGINAL_ENGINE
ORIGINAL_INPUT_PINS = previous.input_pins
ORIGINAL_REVIEWED_INPUTS = previous.reviewed_inputs
selected_adapter = previous.selected_adapter


class ReviewedResolutionEngine(previous.ReviewedResolutionEngine):
    def __init__(self, *args, **kwargs):
        self.literal_cases = literal.load_registry()
        ORIGINAL_ENGINE.__init__(self, *args, **kwargs)


def input_pins(cases):
    return list(dict.fromkeys(ORIGINAL_INPUT_PINS(cases) + context_revision.CODE +
                [literal.ADDITIONAL_REGISTRY, "scripts/p106b_hold_resolution_literal_guard_v2.py",
                 "scripts/p106b_hold_resolution_reviewed_cache_v2.py"]))


@contextmanager
def reviewed_inputs():
    with patch.object(previous, "literal", literal), \
            patch.object(previous, "ReviewedResolutionEngine", ReviewedResolutionEngine), \
            patch.object(previous, "input_pins", input_pins):
        with ORIGINAL_REVIEWED_INPUTS():
            yield


def build(base, adoptions, roster, output_name, proposal_name):
    with patch.object(previous, "reviewed_inputs", reviewed_inputs):
        return previous.build(base, adoptions, roster, output_name, proposal_name)


def verify(base, roster, output_name):
    with patch.object(previous, "reviewed_inputs", reviewed_inputs):
        return previous.verify(base, roster, output_name)


def main():
    with patch.object(previous, "reviewed_inputs", reviewed_inputs):
        return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
