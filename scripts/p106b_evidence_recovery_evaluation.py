"""Query-specific evidence traces; free clarification semantics stays posthoc."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from collections import defaultdict
from scripts import p106b_original_qa3_evaluation as source
from scripts.p106b_repair_role_evaluation import paired


def collect(row,emit):
    events=source.collect(row,emit);m=row['meta']
    if m.get('kind')!='evidence_recovery':raise ValueError('declared evidence producer required')
    for e in events:
        e.update(neutral_root=m['neutral_root'],family=m['family'],condition=m['condition'],question_style=m['question_style'],
            first_query_sufficient=m['query_sufficient'],omitted_key=m['omitted_key'],requested_field=m['requested_fields'][e['turn']-1],
            expected_response_intent=m['first_response_intent'] if e['turn']==1 else 'ANSWER',
            source_truth='GIVEN_FICTIONAL_FIELDS_AND_CONFIRMED_USER_SUPPLEMENT_ONLY')
    return events


def counts(events):
    out=source.counts(events);groups=defaultdict(list)
    for e in events:
        for key in ('family','condition','expected_response_intent','first_query_sufficient'):
            groups[key+'='+str(e[key])].append(e)
    return dict(base=out,producer_slices={k:source.counts(v) for k,v in sorted(groups.items())},
        clarification_exact_match_is_not_semantic_judgment=True,clarification_semantics='PENDING_POSTHOC_REVIEW')
