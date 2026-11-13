"""Strict native top-k records and one-shift prefix alignment for ACTD.

Raw teacher edges are never dropped, fabricated or renormalized on a subset.
This module does not admit a corpus, load a model or perform optimizer updates.
"""
from collections import Counter
import math
from scripts import p106b_actd_anchor as actd


POLICIES=('nearest_monotonic','causal_left_variant')


def prefix_candidates(stream):
    """Predict target j from native prefix index j-1; preserve target ownership."""
    candidates=[];holds=[]
    for target in stream.tokens:
        if not target.supervised:continue
        if target.raw_index==0:
            holds.append(dict(target_raw_index=0,reason='NO_NATIVE_PREFIX'));continue
        previous=stream.tokens[target.raw_index-1]
        try:char=actd.character_boundaries(stream.text_utf8.decode('utf-8'),[previous.byte_end])[0]
        except actd.AnchorMappingHold:
            holds.append(dict(target_raw_index=target.raw_index,reason='PREFIX_INSIDE_UTF8_CHARACTER'));continue
        if target.turn_id<1:raise ValueError('supervised target must have a semantic owner')
        candidates.append(dict(prefix_raw_index=previous.raw_index,target_raw_index=target.raw_index,
            target_id=target.token_id,owner=target.turn_id,character_end=char,
            prefix_byte_end=previous.byte_end,target_special_kind=target.special_kind))
    return candidates,holds


def align_positions(student,teacher,*,policy):
    if policy not in POLICIES:raise ValueError('explicit ACTD alignment policy required')
    previous=-1;rows=[];holds=[]
    teacher_by_index={r['prefix_raw_index']:r for r in teacher}
    if len(teacher_by_index)!=len(teacher):raise ValueError('unique teacher predictor positions required')
    for s in student:
        available=[(t['character_end'],t['owner'],t['prefix_raw_index']) for t in teacher
                   if t['owner']==s['owner'] and t['prefix_raw_index']>=previous]
        try:
            match=actd.align_prefix_boundaries([(s['character_end'],s['owner'],s['prefix_raw_index'])],
                available,policy=policy)[0]
        except actd.AnchorMappingHold:
            holds.append(dict(student_target_raw_index=s['target_raw_index'],reason='NO_SAME_OWNER_MONOTONIC_PREFIX',policy=policy));continue
        t=teacher_by_index[match['teacher_prefix_raw_index']];previous=t['prefix_raw_index']
        rows.append(dict(match,student_target_raw_index=s['target_raw_index'],student_target_id=s['target_id'],
            teacher_target_raw_index=t['target_raw_index'],teacher_target_id=t['target_id']))
    return rows,holds


def literal_added_overrides(raw_teacher,decode_single,mapper,base_anchors):
    """New policy: added special=False literal bytes; special=True stays explicit."""
    added=raw_teacher['added_tokens'];result=[]
    if len({r['id'] for r in added})!=len(added):raise ValueError('duplicate added native ID')
    for row in added:
        if row['special']is not False:continue
        token_id=row['id'];text=row['content']
        if (type(token_id)is not int or not 0<=token_id<len(base_anchors)
                or not isinstance(text,str) or not text or base_anchors[token_id]is not None
                or decode_single(token_id)!=text):
            raise ValueError('literal added token provenance/old HOLD/decode differs')
        mapped=mapper.map([token_id],[text.encode('utf-8',errors='strict')])[0]
        result.append(dict(mapped,literal=text,source_policy='HF_SPECIAL_FALSE_LITERAL_UTF8'))
    return result


def native_topk(logits,*,k):
    import torch
    if (not isinstance(logits,torch.Tensor) or logits.ndim!=2 or logits.dtype!=torch.float32
            or type(k)is not int or not 1<=k<=logits.shape[1] or not bool(torch.isfinite(logits).all())):
        raise ValueError('finite FP32 positions by full native vocabulary required')
    scores,ids=torch.topk(logits,k=k,dim=-1,largest=True,sorted=True)
    normalizers=torch.logsumexp(logits,dim=-1)
    return ids,scores,normalizers


def distribution(ids,scores,full_logsumexp,*,anchor_lookup,student_vocab,k):
    if (not isinstance(ids,list) or not isinstance(scores,list) or len(ids)!=k or len(scores)!=k
            or len(set(ids))!=k or any(type(i)is not int or not 0<=i<len(anchor_lookup) for i in ids)
            or any(type(s)not in(int,float) or not math.isfinite(s) for s in scores)
            or any(a<b for a,b in zip(scores,scores[1:]))
            or type(full_logsumexp)not in(int,float) or not math.isfinite(full_logsumexp)
            or type(student_vocab)is not int or student_vocab<2):
        raise ValueError('complete unique ordered native top-k with finite full normalizer required')
    maximum=max(scores);conditional_z=maximum+math.log(sum(math.exp(s-maximum) for s in scores))
    logmass=conditional_z-full_logsumexp
    if logmass>1e-5:raise ValueError('retained top-k mass exceeds full native probability')
    anchors=[anchor_lookup[i] for i in ids]
    missing=[i for i,a in zip(ids,anchors) if a is None]
    if any(a is not None and (type(a)is not int or not 0<=a<student_vocab) for a in anchors):
        raise ValueError('mapped anchor outside native student vocabulary')
    return dict(native_ids=list(ids),native_logits=list(scores),full_logsumexp=float(full_logsumexp),
        retained_probability_mass=math.exp(logmass),accepted=not missing,unmapped_native_ids=missing,
        anchor_ids=None if missing else anchors,
        duplicate_anchor_edges=None if missing else k-len(set(anchors)),
        student_denominator='FULL_NATIVE_VOCAB',teacher_denominator='COMPLETE_NATIVE_TOPK',
        rejection_reason='UNMAPPED_EDGE_WHOLE_POSITION_HOLD' if missing else None)


def accepted_positions(prepared,distributions,*,policy,k,anchor_lookup,student_vocab):
    if policy not in POLICIES:raise ValueError('explicit cache position policy required')
    expected=set(prepared['teacher_prefix_union'])
    if set(distributions)!=expected:raise ValueError('every declared teacher predictor must have exactly one distribution')
    verified={}
    for index,row in distributions.items():
        verified[index]=distribution(row['native_ids'],row['native_logits'],row['full_logsumexp'],
            anchor_lookup=anchor_lookup,student_vocab=student_vocab,k=k)
        if row!=verified[index]:raise ValueError('derived top-k acceptance/anchors/mass changed')
    out=[];holds=list(prepared['student_boundary_holds'])+list(prepared['alignment_holds'][policy])
    for position in prepared['alignments'][policy]:
        row=verified[position['teacher_prefix_raw_index']]
        if row['accepted']:out.append(dict(position,distribution=row))
        else:holds.append(dict(student_target_raw_index=position['student_target_raw_index'],
            reason=row['rejection_reason'],unmapped_native_ids=row['unmapped_native_ids']))
    if len(out)+len(holds)!=prepared['ce_targets']:raise ValueError('ACTD acceptance/HOLD must account for all original CE targets')
    return out,holds
