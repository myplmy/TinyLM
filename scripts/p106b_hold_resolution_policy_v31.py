"""Resolve only a separately proven literal category boundary; retain other HOLDs."""
from scripts import p106b_hold_resolution_policy_v30 as previous
from scripts import p106b_hold_resolution_metadata_v4 as metadata

RULES='RESIDUAL_CONTEXT_RECOVERY_DRAFT_V31_MULTIPLE_TYPED_LITERAL_CATEGORY_ANCHORS'


def __getattr__(name):
    return getattr(previous,name)


def propose(row,individual_hold=False):
    value=previous.propose(row,individual_hold)
    if (value['decision']=='PENDING'
            and 'APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT' in value['reasons']
            and any(c['reason']==previous.QUARANTINE for c in value['changes'])):
        value=dict(value,reasons=sorted(set(value['reasons'])|{
            'PARTIAL_QUARANTINE_CANNOT_BORROW_A_METADATA_BOUNDARY_RELEASE'}))
    if (individual_hold or row.get('previous_holds') or not row['complete_eos']
            or row['id']=='validation:0' or value['decision']!='PENDING'
            or 'APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT' not in value['reasons']
            or any(c['reason']==previous.QUARANTINE for c in value['changes'])):
        return dict(value,rules=RULES)
    original=row['text']
    proof=metadata.prove(value.get('candidate',value['text']))
    if proof is None or proof['metadata_original'] not in original:
        return dict(value,rules=RULES)
    clean=proof['candidate']
    reasons=set(value['reasons'])-{'APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT'}
    reasons.update(previous.literal_holes(clean))
    if not previous.code_preserved(original,clean) or not previous.unicode_examples_preserved(original,clean):
        reasons.add('CODE_OR_UNICODE_GUARD')
    if not previous.semantic_style_preserved(original,clean):
        reasons.add('SOURCE_STYLE_VALUE_REQUIRES_LITERAL_OR_AUTHORED_PRESERVATION')
    if not previous.ordered_deletion(original,clean):
        reasons.add('NONWHITESPACE_ADDITION_OR_REORDER_REQUIRES_AUTHORED_REVIEW')
    result=dict(value,changes=value['changes']+proof['changes'],metadata_boundary_proof=proof['proof'],rules=RULES)
    if reasons:
        return dict(result,decision='PENDING',text=original,candidate=clean,reasons=sorted(reasons))
    result.pop('candidate',None)
    return dict(result,decision='EDIT' if original!=clean else 'KEEP',text=clean,
        reasons=['MULTIPLE_TYPED_LITERAL_CATEGORY_ANCHORS_AND_ALL_SOURCE_VALUE_GUARDS_PRESERVED'])
