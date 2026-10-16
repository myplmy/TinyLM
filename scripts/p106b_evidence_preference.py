"""Code-owned answer-versus-clarification preference, not a free-text classifier."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
from scripts import p106b_evidence_recovery as previous
from scripts import p106b_conditional_orpo as odds
from tinylm.chat.canonical import normalize,validate
VERSION='P106B_QUERY_EVIDENCE_PREFERENCE_V1'
ARMS={'sft_only':0.,'orpo010':.1}


def make_pair(g,language,condition,style,tok):
    row=previous.make(g,language,condition,True,style,tok);meta=row['meta']
    if g['split']!='train':raise ValueError('preference training requires original TRAIN graph only')
    first=row['messages'][:2];wanted=meta['requested_fields'][0]
    if meta['query_sufficient']:
        denied=previous.mask_key(g,wanted)
        if denied not in meta['first_available_keys']:raise ValueError('negative clarification must deny a present dependency')
        rejected=previous.clarification(denied,language);mode='UNNECESSARY_CLARIFICATION'
    else:
        if meta['omitted_key'] not in previous.dependencies(wanted):raise ValueError('missing query dependency required')
        rejected=previous.base.values(g,language)[wanted];mode='UNSUPPORTED_ASSERTION'
    chosen=previous.wrap.text(first[1])
    if not chosen or not rejected or chosen==rejected:raise ValueError('distinct complete preference responses required')
    newmeta=dict(kind='evidence_preference',source='project_authored_query_preference',language=language,
        semantic_root_id=previous.wrap.sha([VERSION,meta['neutral_root'],language,condition,style]),
        neutral_root=meta['neutral_root'],family=g['family'],condition=condition,question_style=style,
        query_sufficient=meta['query_sufficient'],source_split='train',preference_version=VERSION,
        first_required_keys=meta['first_required_keys'],first_available_keys=meta['first_available_keys'],
        omitted_key=meta['omitted_key'],requested_field=wanted,source_license='project_authored_fictional',
        known_output_contract='CODE_QUERY_SUFFICIENCY_ONLY',semantic_truth='GIVEN_FICTIONAL_RECORD_AND_NO_GUESS_INSTRUCTION_ONLY',
        supervised_assistant_turns=[1],teacher_calls=0)
    positive=validate(normalize(dict(messages=copy.deepcopy(first),meta=newmeta)))
    negative=copy.deepcopy(positive);negative['messages'][-1]['content']=[dict(type='text',text=rejected)]
    return dict(chosen=positive,rejected=negative,mode=mode,root=newmeta['semantic_root_id'],neutral_root=meta['neutral_root'],
        language=language,source_signature=previous.wrap.sha(positive['messages']),producer_graph=copy.deepcopy(g),
        scope='Known fictional dependency/explicit no-guess contract; not natural-world truth, repetition ban or online quality classifier')


def select_graphs(graphs,count,tag):
    if count%4 or count<=0:raise ValueError('balanced four-family sample required')
    selected=[]
    for family in previous.base.FAMILIES:
        lane=[g for g in graphs if g['family']==family]
        ranked=sorted(lane,key=lambda g:previous.wrap.sha([tag,'TRAIN_PAIR',previous.neutral(g)]))
        if len(ranked)<count//4:raise ValueError('original train graph supply short')
        selected.extend(ranked[:count//4])
    return selected


def fresh_test(previous_test,tag):
    excluded={previous.neutral(g) for g in previous_test}
    excluded.update(previous.neutral(g) for g in previous.base.graphs(128,'test'))
    out=previous.graphs(128,'test',exclude=excluded)
    if {previous.neutral(g) for g in out}&excluded:raise ValueError('old visible facts reused as new test')
    return out


def index_pairs(pairs):
    """Different hidden worlds can share a visible prompt/chosen clarification.

    Keep distinct producer-owned rejected examples instead of overwriting one
    by a chosen-message hash. This is indexing sealed producer data, not a
    permissive semantic admission function for arbitrary preferences.
    """
    out={}
    for p in pairs:
        if p['root'] in out:raise ValueError('duplicate full producer pair identity')
        if p['chosen']['meta']['semantic_root_id']!=p['root'] or p['rejected']['meta']['semantic_root_id']!=p['root']:
            raise ValueError('pair identity differs from canonical metadata')
        if p['chosen']['messages'][0]!=p['rejected']['messages'][0]:raise ValueError('same pair prompt required')
        out[p['root']]=p
    return out
