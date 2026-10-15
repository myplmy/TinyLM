"""Exposure-matched epoch views, complete teacher history and known-code replay."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from collections import Counter
import copy
from scripts import p106b_dualqa_sources as source
from scripts import p106b_binding_auxiliary as binding
from scripts import p106b_dualqa_teacher as fields
VERSION='P106B_DUAL_QA_MARGINAL_MATCHED_COURSE_V1'
ARMS=('repeat','contrast')


def text(message):return ''.join(b['text'] for b in message['content'])


def view(student,arm,parity,tok):
    if arm not in ARMS or parity not in (0,1):raise ValueError('registered arm and epoch parity required')
    m=student['meta'];pairs=copy.deepcopy(m.get('original_teacher_content_pairs',m['teacher_content_pairs']))
    if len(pairs)!=2:raise ValueError('exact two teacher pairs required')
    order=[0,1] if parity==0 else [1,0];ordered=[pairs[i] for i in order]
    lo,hi=m['student_reference_range'];ref=text(student['messages'][0])[lo:hi]
    job=dict(root=m['semantic_root_id'],language=m['language'],split=m['source_split'],reference=ref,
        reference_sha256=m['source_reference_sha256'],provenance={k:m[k] for k in ('source_repo','source_revision','source_id','source_family','source_license','source_sha256','rights_status') if k in m})
    parsed=dict(status='QA_FIELDS_COMPLETE',pairs=ordered,note=m['teacher_note'],empty_note_filled_by_code=m.get('teacher_note_defaulted',False))
    result=source.render(job,parsed,tok,repeat_first=arm=='repeat',record_id=m['teacher_record_id'])
    result['meta'].update(original_teacher_content_pairs=pairs,teacher_pair_permutation=order,
        curriculum=VERSION,view_arm=arm,view_parity=parity,
        exposure='each QA4times and each position2times over4epochs in BOTH arms; source4times')
    if text(result['messages'][0])[slice(*result['meta']['student_reference_range'])]!=ref:
        raise ValueError('source changed while choosing QA order')
    return result


def totals(rows,tok,*,token_hist=False):
    from tinylm.train.mtp_sft import encode_record
    result=Counter();languages=Counter();targets=Counter();xs=Counter();ys=Counter()
    for row in rows:
        r=encode_record(row,tok);language=row['meta']['language']
        if r.x_tokens>1024 or not r.targets:raise ValueError('complete context1024/no empty SFT targets')
        result.update(rows=1,x_tokens=r.x_tokens,assistant_targets=r.targets)
        languages[language]+=r.x_tokens;targets[language]+=r.targets
        if token_hist:xs.update(r.x);ys.update(v for v in r.y if v!=-100)
    return dict(result,languages_x=dict(languages),languages_targets=dict(targets)),xs,ys


def marginal_proof(students,tok):
    views={(arm,p):[view(row,arm,p,tok) for row in students] for arm in ARMS for p in (0,1)}
    counts={};hists={}
    for key,rows in views.items():counts[key],x,y=totals(rows,tok,token_hist=True);hists[key]=(x,y)
    summary={};bags={}
    for arm in ARMS:
        a,b=(counts[arm,p] for p in (0,1))
        summary[arm]=dict(epochs=4,source_conversations=4*len(students),
            x_tokens=2*(a['x_tokens']+b['x_tokens']),assistant_targets=2*(a['assistant_targets']+b['assistant_targets']),
            each_original_qa_exposures=4,each_qa_in_first_and_second_position=2,
            languages_x={l:2*(a['languages_x'].get(l,0)+b['languages_x'].get(l,0)) for l in ('ko','en')},
            languages_targets={l:2*(a['languages_targets'].get(l,0)+b['languages_targets'].get(l,0)) for l in ('ko','en')})
        bags[arm]=(hists[arm,0][0]+hists[arm,1][0],hists[arm,0][1]+hists[arm,1][1])
    if summary['repeat']!=summary['contrast'] or bags['repeat']!=bags['contrast']:
        raise ValueError('4epoch token/target/language marginal exposure mismatch; never pad fake true tokens')
    return views,dict(summary=summary,token_id_bags_equal=True,source_and_answer_pairs_unchanged=True,
        scope='marginal information/exposure matched, sequence pairing intentionally differs')


def code_rows(old,tag):
    rows=old['train'];chosen=[]
    for language in ('ko','en'):
        for kind in ('binding_color','binding_department'):
            lane=[r for r in rows if r['meta']['language']==language and r['meta']['kind']==kind]
            roots=sorted({r['meta']['semantic_root_id'] for r in lane},key=lambda r:fields.sha([tag,r]))[:192]
            chosen.extend(copy.deepcopy(r) for r in lane if r['meta']['semantic_root_id'] in roots)
    others=[copy.deepcopy(r) for r in rows if r['meta']['kind'] not in ('public_qa','binding_color','binding_department')]
    if len(chosen)!=3072 or len(others)!=1024:raise ValueError('known3072 binding +1024 rule rows required')
    return chosen+others


def known_contract(rows,tok,approved):
    from tinylm.train.mtp_sft import encode_record
    result={}
    for row in rows:
        bit=binding.binding_bit(row,approved)
        if bit is None:continue
        rec=encode_record(row,tok);first=next(i for i,x in enumerate(rec.y) if x!=-100)
        positions=binding.causal_suffix_positions(row,tok,first)
        result[binding.prior.source.sha(row['messages'])]=dict(bit=bit,root=row['meta']['semantic_root_id'],positions=positions)
    return result
