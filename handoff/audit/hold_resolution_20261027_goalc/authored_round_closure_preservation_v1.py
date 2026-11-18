"""Prove closing-parenthesis repairs without claiming raw deletion-only order.

This emits readiness evidence, never ROOT approval. A source-specific review
and ROOT context decision remain mandatory at batch admission.
"""
from authored_empty_section_literal_v2 import preservation as deletion_preservation
from assigned_final_literal_review_v1 import exact_changes
from structural_delimiter_deferrals_v2 import deferrals as delimiter_deferrals
import lossless_review_packet_v3 as core


def preservation(source, body):
    prior = deletion_preservation(source, body)
    failed = [name for name, passed in prior['guards'].items() if not passed]
    if failed != ['ordered']:
        return prior
    changes = exact_changes(source, body, core)
    added = []
    for change in changes:
        a, b = change['source_range']
        c, d = change['candidate_range']
        before, after = source[a:b].strip(), body[c:d].strip()
        if after and before != after:
            added.append(dict(source_range=[a, b], body_range=[c, d], text=after))
    guards = {name: value for name, value in prior['guards'].items() if name != 'ordered'}
    guards.update(all_added_nonwhitespace_characters_are_round_closers=bool(added) and
                      all(set(row['text']) <= {')'} for row in added),
                  source_has_a_real_unclosed_or_crossed_noncode_delimiter=bool(delimiter_deferrals(source)),
                  final_noncode_delimiters_balanced=not delimiter_deferrals(body))
    return dict(guards=guards, eligible_narrow_literal_delta=all(guards.values()),
        comparison_basis='EXACT_ROUND_CLOSURE_ALL_OTHER_LITERAL_GUARDS_SECONDARY_AND_ROOT_CONTEXT_REQUIRED',
        legacy_deletion_only_observations=prior, added_round_closers=added,
        exact_final_reconstruction=True, source_specific_ROOT_review_required=True,
        automatic_root_approval=False)
