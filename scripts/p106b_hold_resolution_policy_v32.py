"""Release repeated records only after every occurrence has a narrow typed role."""
from scripts import p106b_hold_resolution_policy_v31 as previous
from scripts import p106b_hold_resolution_repeat_context_v2 as repeated_records

RULES='RESIDUAL_CONTEXT_RECOVERY_DRAFT_V32_TYPED_REPEATED_RECORDS'


def __getattr__(name):
    return getattr(previous,name)


def propose(row,individual_hold=False):
    value=previous.propose(row,individual_hold)
    if (value['decision']=='PENDING'
            and 'APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT' in value['reasons']
            and any(item['reason']==previous.QUARANTINE for item in value['changes'])):
        value=dict(value,reasons=sorted(set(value['reasons'])|{
            'PARTIAL_QUARANTINE_CANNOT_BORROW_A_METADATA_BOUNDARY_RELEASE'}))
    if (individual_hold or row.get('previous_holds') or not row['complete_eos'] or row['id']=='validation:0'
            or value['decision'] not in {'PENDING','KEEP','EDIT'}
            or (value['decision']=='PENDING' and 'MAIN_BODY_REPETITION_REQUIRES_CONTEXT' not in value['reasons'])
            or any(item['reason']==previous.QUARANTINE for item in value['changes'])):
        return dict(value,rules=RULES)
    proof=repeated_records.prove(value.get('candidate',value['text']))
    if proof is None:
        return dict(value,rules=RULES)
    clean=proof['candidate'];original=row['text']
    reasons=(set(value['reasons'])-{'MAIN_BODY_REPETITION_REQUIRES_CONTEXT'}
             if value['decision']=='PENDING' else set())
    reasons.update(previous.literal_holes(clean))
    if not previous.code_preserved(original,clean) or not previous.unicode_examples_preserved(original,clean):
        reasons.add('CODE_OR_UNICODE_GUARD')
    if not previous.semantic_style_preserved(original,clean):
        reasons.add('SOURCE_STYLE_VALUE_REQUIRES_LITERAL_OR_AUTHORED_PRESERVATION')
    if not previous.ordered_deletion(original,clean):
        reasons.add('NONWHITESPACE_ADDITION_OR_REORDER_REQUIRES_AUTHORED_REVIEW')
    result=dict(value,changes=value['changes']+proof['changes'],repeated_record_proof=proof['proof'],rules=RULES)
    if reasons:
        return dict(result,decision='PENDING',text=original,candidate=clean,reasons=sorted(reasons))
    result.pop('candidate',None)
    return dict(result,decision='EDIT' if original!=clean else 'KEEP',text=clean,
                reasons=['ALL_REPEATED_OCCURRENCES_HAVE_PROVED_RECORD_ROLES'])
