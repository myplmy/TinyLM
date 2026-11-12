"""Publish the final event-metadata text without its obsolete pending candidate."""
from scripts import p106b_hold_resolution_policy_v29 as previous

RULES='RESIDUAL_CONTEXT_RECOVERY_DRAFT_V30_EVENT_METADATA_TERMINAL_BODY_CONTRACT'


def __getattr__(name):
    return getattr(previous,name)


def versioned(value):
    return dict(value,rules=RULES)


def propose(row,individual_hold=False):
    value=previous.propose(row,individual_hold)
    if (value['decision']=='PENDING'
            and 'APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT' in value['reasons']
            and any(change['reason']==previous.QUARANTINE for change in value['changes'])
            and previous.separate_metadata_suffix(value.get('candidate',value['text']))[2]):
        value=dict(value,reasons=sorted(set(value['reasons']) | {
            'PARTIAL_QUARANTINE_CANNOT_BORROW_A_METADATA_BOUNDARY_RELEASE'}))
    if (value['decision'] in {'KEEP','EDIT'}
            and value['reasons']==['EXPLICIT_START_END_METADATA_AND_ALL_SOURCE_VALUE_GUARDS_PRESERVED']):
        # Inherited PENDING had text=original,candidate=old_draft. Rule29
        # publishes its finished text; terminal consumers must see that text.
        value=dict(value)
        value.pop('candidate',None)
    return versioned(value)
