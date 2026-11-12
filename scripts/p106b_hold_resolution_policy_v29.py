"""Preserve literal start/end event metadata while removing only proved empty footers."""
from scripts import p106b_hold_resolution_policy_v28 as previous
from scripts import p106b_hold_resolution_metadata_v3 as metadata

RULES = 'RESIDUAL_CONTEXT_RECOVERY_DRAFT_V29_EXPLICIT_START_END_METADATA_BOUNDARY'


def __getattr__(name):
    return getattr(previous, name)


def versioned(value):
    return dict(value, rules=RULES)


def propose(row, individual_hold=False):
    value = previous.propose(row, individual_hold)
    if (value['decision'] == 'PENDING'
            and 'APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT' in value['reasons']
            and any(change['reason'] == previous.QUARANTINE for change in value['changes'])
            and previous.separate_metadata_suffix(value.get('candidate',value['text']))[2]):
        value = dict(value, reasons=sorted(set(value['reasons']) | {
            'PARTIAL_QUARANTINE_CANNOT_BORROW_A_METADATA_BOUNDARY_RELEASE'}))
    if (individual_hold or row.get('previous_holds') or not row['complete_eos']
            or row['id'] == 'validation:0' or value['decision'] != 'PENDING'
            or 'APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT' not in value['reasons']):
        return versioned(value)
    if any(change['reason'] == previous.QUARANTINE for change in value['changes']):
        return versioned(value)
    original = row['text']
    proof = metadata.prove(value.get('candidate',value['text']))
    if proof is None or proof['metadata_original'] not in original:
        return versioned(value)
    clean = proof['candidate']
    reasons = set(value['reasons']) - {'APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT'}
    reasons.update(previous.literal_holes(clean))
    if not previous.code_preserved(original,clean) or not previous.unicode_examples_preserved(original,clean):
        reasons.add('CODE_OR_UNICODE_GUARD')
    if not previous.semantic_style_preserved(original,clean):
        reasons.add('SOURCE_STYLE_VALUE_REQUIRES_LITERAL_OR_AUTHORED_PRESERVATION')
    if not previous.ordered_deletion(original,clean):
        reasons.add('NONWHITESPACE_ADDITION_OR_REORDER_REQUIRES_AUTHORED_REVIEW')
    result = dict(value, changes=value['changes']+proof['changes'], metadata_boundary_proof=proof['proof'])
    if reasons:
        return versioned(dict(result, decision='PENDING', text=original, candidate=clean, reasons=sorted(reasons)))
    return dict(result, decision='EDIT' if original != clean else 'KEEP', text=clean,
                reasons=['EXPLICIT_START_END_METADATA_AND_ALL_SOURCE_VALUE_GUARDS_PRESERVED'], rules=RULES)
