"""Extend declared-name grammar; preserve all inherited policy boundaries."""
from scripts import p106b_hold_resolution_policy_v27 as previous
from scripts import p106b_hold_resolution_disambiguation_v2 as disambiguation

RULES='RESIDUAL_CONTEXT_RECOVERY_DRAFT_V28_EXPLICIT_NAME_DECLARATION_VARIANTS'


def __getattr__(name):return getattr(previous,name)


def versioned(value):return dict(previous.versioned(value),rules=RULES)


def propose(row,individual_hold=False):
    original=row['text']
    if individual_hold or row.get('previous_holds') or not row['complete_eos'] or row['id']=='validation:0':
        return versioned(previous.propose(row,individual_hold))
    # Existing declarations retain the exact earlier result and provenance.
    if disambiguation.ORIGINAL_DECLARATION(original) is not None:
        return versioned(previous.propose(row,False))
    prepared,proof=disambiguation.source_named_aliases(original)
    if not proof:return versioned(previous.propose(row,False))
    value=previous.propose(dict(row,text=prepared),False)
    clean=value.get('candidate',value['text'])
    reasons=set(value['reasons']) if value['decision']=='PENDING' else set()
    reasons.update(previous.literal_holes(clean))
    if not previous.code_preserved(original,clean) or not previous.unicode_examples_preserved(original,clean):
        reasons.add('CODE_OR_UNICODE_GUARD')
    if not previous.semantic_style_preserved(original,clean):
        reasons.add('SOURCE_STYLE_VALUE_REQUIRES_LITERAL_OR_AUTHORED_PRESERVATION')
    if not previous.ordered_deletion(original,clean):
        reasons.add('NONWHITESPACE_ADDITION_OR_REORDER_REQUIRES_AUTHORED_REVIEW')
    if not disambiguation.balanced_prose_parentheses(clean):
        reasons.add('UNBALANCED_PROSE_PARENTHESES_REQUIRE_CONTEXT')
    changes=proof+value['changes']
    if reasons:
        return versioned(dict(value,decision='PENDING',text=original,candidate=clean,
            reasons=sorted(reasons),changes=changes))
    return dict(decision='EDIT' if original!=clean else 'KEEP',text=clean,
        reasons=['EXPLICIT_NAME_LIST_VARIANT_AND_ALL_SOURCE_VALUE_GUARDS_PRESERVED'],
        changes=changes,source_list_proof=disambiguation.declared_name_list(original),rules=RULES)
