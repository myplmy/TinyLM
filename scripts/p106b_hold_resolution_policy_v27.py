"""Continue v26 with proved name-list aliases; all ordinary guards remain."""
from scripts import p106b_hold_resolution_policy_v26 as previous
from scripts import p106b_hold_resolution_disambiguation_v1 as disambiguation

RULES = 'RESIDUAL_CONTEXT_RECOVERY_DRAFT_V27_DECLARED_NAME_LIST_OPTIONAL_ALIASES'


def __getattr__(name):
    return getattr(previous, name)


def versioned(value):
    # Preserve the same explicit boundary even when a caller supplies a frozen
    # previous-proposal fixture instead of running all older policy layers.
    if (value['decision'] == 'PENDING'
            and 'APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT' in value['reasons']
            and any(change['reason'] == previous.QUARANTINE for change in value['changes'])
            and previous.separate_metadata_suffix(value.get('candidate', value['text']))[2]):
        value = dict(value, reasons=sorted(set(value['reasons']) | {
            'PARTIAL_QUARANTINE_CANNOT_BORROW_A_METADATA_BOUNDARY_RELEASE'}))
    return dict(value, rules=RULES)


def propose(row, individual_hold=False):
    original = row['text']
    if individual_hold or row.get('previous_holds') or not row['complete_eos'] or row['id'] == 'validation:0':
        return versioned(previous.propose(row, individual_hold))
    prepared, source_proofs = disambiguation.source_named_aliases(original)
    if not source_proofs:
        return versioned(previous.propose(row, False))
    value = previous.propose(dict(row, text=prepared), False)
    clean = value.get('candidate', value['text'])
    reasons = set(value['reasons']) if value['decision'] == 'PENDING' else set()
    reasons.update(previous.literal_holes(clean))
    if not previous.code_preserved(original, clean) or not previous.unicode_examples_preserved(original, clean):
        reasons.add('CODE_OR_UNICODE_GUARD')
    if not previous.semantic_style_preserved(original, clean):
        reasons.add('SOURCE_STYLE_VALUE_REQUIRES_LITERAL_OR_AUTHORED_PRESERVATION')
    if not previous.ordered_deletion(original, clean):
        reasons.add('NONWHITESPACE_ADDITION_OR_REORDER_REQUIRES_AUTHORED_REVIEW')
    changes = source_proofs + value['changes']
    if reasons:
        return versioned(dict(value, decision='PENDING', text=original, candidate=clean,
                              reasons=sorted(reasons), changes=changes))
    return dict(decision='EDIT' if original != clean else 'KEEP', text=clean,
        reasons=['SOURCE_DECLARED_NAME_LIST_VALUES_AND_ALL_V26_GUARDS_PRESERVED'],
        changes=changes, source_list_proof=disambiguation.declared_name_list(original), rules=RULES)
