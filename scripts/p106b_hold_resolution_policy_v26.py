"""Preserve complete ordinal football categories while proving empty footers."""
from scripts import p106b_hold_resolution_policy_v25 as previous
from scripts import p106b_hold_resolution_metadata_v2 as metadata

RULES = 'RESIDUAL_CONTEXT_RECOVERY_DRAFT_V26_TYPED_ORDINAL_CATEGORY_PUNCTUATION'


def __getattr__(name):
    return getattr(previous, name)


def propose(row, individual_hold=False):
    value = previous.propose(row, individual_hold)
    # This boundary guard remains explicit even when a previous proposal is
    # supplied by a frozen selector or an independent counter fixture.
    if (value['decision'] == 'PENDING'
            and 'APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT' in value['reasons']
            and any(change['reason'] == previous.QUARANTINE for change in value['changes'])
            and previous.separate_metadata_suffix(value.get('candidate', value['text']))[2]):
        value = dict(value, reasons=sorted(set(value['reasons']) | {
            'PARTIAL_QUARANTINE_CANNOT_BORROW_A_METADATA_BOUNDARY_RELEASE'}))
    if (individual_hold or row.get('previous_holds') or not row['complete_eos']
            or row['id'] == 'validation:0' or value['decision'] != 'PENDING'
            or 'APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT' not in value['reasons']):
        return dict(value, rules=RULES)
    clean = value.get('candidate', value['text'])
    proof = metadata.prove(clean)
    if proof is None:
        return dict(value, rules=RULES)
    if any(change['reason'] == previous.QUARANTINE for change in value['changes']):
        return dict(value, reasons=sorted(set(value['reasons']) | {
            'PARTIAL_QUARANTINE_CANNOT_BORROW_A_METADATA_BOUNDARY_RELEASE'}), rules=RULES)
    original = row['text']
    if proof['metadata_original'] not in original:
        return dict(value, rules=RULES)
    clean = proof['candidate']
    reasons = set(value['reasons'])
    reasons.discard('APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT')
    reasons.update(previous.literal_holes(clean))
    if not previous.code_preserved(original, clean) or not previous.unicode_examples_preserved(original, clean):
        reasons.add('CODE_OR_UNICODE_GUARD')
    if not previous.semantic_style_preserved(original, clean):
        reasons.add('SOURCE_STYLE_VALUE_REQUIRES_LITERAL_OR_AUTHORED_PRESERVATION')
    if not previous.ordered_deletion(original, clean):
        reasons.add('NONWHITESPACE_ADDITION_OR_REORDER_REQUIRES_AUTHORED_REVIEW')
    changes = value['changes'] + proof['changes']
    if reasons:
        return dict(value, decision='PENDING', text=original, candidate=clean, reasons=sorted(reasons),
                    changes=changes, metadata_boundary_proof=proof['proof'], rules=RULES)
    return dict(decision='EDIT' if original != clean else 'KEEP', text=clean,
        reasons=['TYPED_ORDINAL_METADATA_VALUES_AND_ALL_OTHER_SOURCE_GUARDS_PRESERVED'],
        changes=changes, metadata_boundary_proof=proof['proof'], rules=RULES)
