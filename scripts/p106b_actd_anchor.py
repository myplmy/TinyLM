"""ACTD Eq7/8 primitives and explicit cross-tokenizer mapping policies.

No teacher/model/I/O is opened. This is not a complete training consumer.
Literal ordered anchor edges are retained; residual support is unique.
Boundary inputs are PREFIX endpoints and NEXT-target owners, not raw labels.
"""
import math
import torch


class AnchorContractError(ValueError):
    pass


class AnchorMappingHold(AnchorContractError):
    """Missing/ambiguous native mapping; never silently discard and renormalize."""


def actd_sums(student_logits, anchor_ids, teacher_scores, *, residual_weight):
    if (not isinstance(student_logits,torch.Tensor) or student_logits.ndim!=2
            or student_logits.shape[1]<2 or student_logits.dtype not in
            (torch.float16,torch.bfloat16,torch.float32,torch.float64)):
        raise AnchorContractError('finite N*full_vocabulary floating student logits required')
    n,vocab=student_logits.shape
    if (not isinstance(anchor_ids,torch.Tensor) or anchor_ids.dtype!=torch.long or anchor_ids.ndim!=2
            or anchor_ids.shape[0]!=n or (n and anchor_ids.shape[1]<1)
            or anchor_ids.device!=student_logits.device or bool((anchor_ids<0).any())
            or bool((anchor_ids>=vocab).any())):
        raise AnchorContractError('native mapped N*K anchor IDs required; duplicate student anchors allowed')
    if (not isinstance(teacher_scores,torch.Tensor) or teacher_scores.shape!=anchor_ids.shape
            or teacher_scores.dtype not in (torch.float16,torch.bfloat16,torch.float32,torch.float64)
            or teacher_scores.device!=student_logits.device or teacher_scores.requires_grad
            or not bool(torch.isfinite(teacher_scores).all()) or not bool(torch.isfinite(student_logits).all())):
        raise AnchorContractError('matching finite frozen teacher top-k scores required')
    if type(residual_weight)not in(int,float) or not math.isfinite(residual_weight) or residual_weight<0:
        raise AnchorContractError('explicit finite nonnegative residual weight required')
    work=student_logits if student_logits.dtype==torch.float64 else student_logits.float()
    if not n:
        zero=work.sum()*0
        return dict(loss_sum=zero,anchor_sum=zero,residual_sum=zero,positions=0,
                    anchor_probabilities=work.new_empty(anchor_ids.shape),residual_probabilities=work.new_empty((0,)),
                    unique_anchor_count=anchor_ids.new_empty((0,)),duplicate_anchor_edges=anchor_ids.new_empty((0,)))
    logz=torch.logsumexp(work,dim=-1)
    student=(work.gather(1,anchor_ids)-logz[:,None]).exp()
    teacher=torch.softmax(teacher_scores.to(work),dim=-1)
    anchor=(teacher-student).abs().sum(dim=-1)
    support=torch.zeros_like(work,dtype=torch.bool).scatter_(1,anchor_ids,True)
    unique=support.sum(dim=-1)
    # Avoid both cancellation in 1-sum(pA) and NaN gradient of all-minus-inf LSE.
    residual=logz*0
    active=torch.nonzero(unique.lt(vocab),as_tuple=False).flatten()
    if active.numel():
        scores=work.index_select(0,active).masked_fill(support.index_select(0,active),float('-inf'))
        mass=(torch.logsumexp(scores,dim=-1)-logz.index_select(0,active)).exp()
        residual=residual.index_copy(0,active,mass)
    a,r=anchor.sum(),residual.sum()
    return dict(loss_sum=a+float(residual_weight)*r,anchor_sum=a,residual_sum=r,positions=n,
                anchor_probabilities=student,residual_probabilities=residual,unique_anchor_count=unique,
                duplicate_anchor_edges=anchor_ids.shape[1]-unique)


class AnchorMapper:
    """Exact shared bytes, then strict decoded text's first student subtoken.

    Caller supplies native ordinary byte vocabulary and an encode-without-BOS
    callback. Special-token IDs require declared native correspondences.
    A partial byte token is valid when shared exactly; otherwise it is HOLD.
    """
    def __init__(self,student_id_to_bytes,student_vocab_size,encode_without_specials,*,teacher_special_ids,special_map):
        if (type(student_vocab_size)is not int or student_vocab_size<2 or not callable(encode_without_specials)
                or not isinstance(student_id_to_bytes,dict) or not student_id_to_bytes):
            raise AnchorContractError('explicit ordinary student byte vocabulary and encoder required')
        self.vocab=student_vocab_size;self.encode=encode_without_specials;self.pieces=dict(student_id_to_bytes)
        self.shared={}
        for token_id,piece in self.pieces.items():
            if type(token_id)is not int or not 0<=token_id<self.vocab or type(piece)is not bytes or not piece:
                raise AnchorContractError('ordinary vocabulary requires bounded native IDs and nonempty raw bytes')
            self.shared.setdefault(piece,[]).append(token_id)
        self.specials=set(teacher_special_ids);self.special_map=dict(special_map)
        if (any(type(i)is not int or i<0 for i in self.specials) or not set(self.special_map)<=self.specials
                or any(type(i)is not int or not 0<=i<self.vocab for i in self.special_map.values())):
            raise AnchorContractError('special mappings must bind declared teacher IDs to bounded student IDs')

    def map(self,teacher_ids,teacher_pieces):
        ids=list(teacher_ids);pieces=list(teacher_pieces)
        if (not ids or len(ids)!=len(pieces) or any(type(i)is not int or i<0 for i in ids)
                or len(set(ids))!=len(ids)):
            raise AnchorContractError('unique ordered native teacher top-k IDs and exact pieces required')
        result=[]
        for token_id,piece in zip(ids,pieces):
            if token_id in self.specials:
                if token_id not in self.special_map:raise AnchorMappingHold('teacher special lacks explicit student correspondence')
                result.append(dict(teacher_id=token_id,anchor_id=self.special_map[token_id],mode='EXPLICIT_SPECIAL'))
                continue
            if type(piece)is not bytes or not piece:raise AnchorMappingHold('ordinary teacher token requires nonempty raw bytes')
            shared=self.shared.get(piece,[])
            if shared:
                if len(shared)!=1:raise AnchorMappingHold('ambiguous shared byte token; no arbitrary ID choice')
                result.append(dict(teacher_id=token_id,anchor_id=shared[0],mode='EXACT_SHARED_BYTES'))
                continue
            try:text=piece.decode('utf-8',errors='strict')
            except UnicodeDecodeError as exc:raise AnchorMappingHold('unshared partial UTF-8 token') from exc
            encoded=self.encode(text)
            if (not isinstance(encoded,(list,tuple)) or not encoded
                    or any(type(i)is not int or i not in self.pieces for i in encoded)):
                raise AnchorMappingHold('fallback encoder returned invalid/automatic-special token IDs')
            if b''.join(self.pieces[i] for i in encoded)!=piece:
                raise AnchorMappingHold('fallback tokenizer changed source bytes; no normalization repair')
            result.append(dict(teacher_id=token_id,anchor_id=encoded[0],mode='FIRST_STUDENT_SUBTOKEN',
                               retokenized_ids=list(encoded)))
        return result


def character_boundaries(text,byte_endpoints):
    if not isinstance(text,str):raise AnchorContractError('unaltered Unicode source text required')
    lookup={0:0};position=0
    for i,char in enumerate(text):
        try:position+=len(char.encode('utf-8',errors='strict'))
        except UnicodeEncodeError as exc:raise AnchorContractError('invalid Unicode source') from exc
        lookup[position]=i+1
    result=[];previous=0
    for endpoint in byte_endpoints:
        if type(endpoint)is not int or not previous<=endpoint<=position:
            raise AnchorContractError('monotonic bounded native byte endpoints required')
        if endpoint not in lookup:raise AnchorMappingHold('prefix ends inside UTF-8 character; no fabricated offset')
        result.append(lookup[endpoint]);previous=endpoint
    return result


def _boundaries(rows):
    output=[];last_char=last_owner=last_index=-1
    for row in rows:
        if (not isinstance(row,(list,tuple)) or len(row)!=3
                or any(type(i)is not int for i in row)):
            raise AnchorContractError('boundary triple is (character_end, next_target_owner, prefix_raw_index)')
        char,owner,index=row
        if char<last_char or char<0 or owner<1 or owner<last_owner or index<=last_index:
            raise AnchorContractError('monotonic character/owner and strictly increasing native prefix indices required')
        output.append((char,owner,index));last_char,last_owner,last_index=row
    return output


def align_prefix_boundaries(student,teacher,*,policy):
    """Explicit nearest-monotonic or separately named causal-left variant.

    This helper never shifts labels. The caller must bind next-target owners
    and verified native prefix endpoints BEFORE invoking it.
    """
    if policy not in ('nearest_monotonic','causal_left_variant'):
        raise AnchorContractError('explicit alignment policy required')
    students,teachers=_boundaries(student),_boundaries(teacher)
    grouped={}
    for t in teachers:grouped.setdefault(t[1],[]).append(t)
    result=[];previous=-1
    for char,owner,index in students:
        available=[t for t in grouped.get(owner,[]) if t[2]>=previous]
        if policy=='causal_left_variant':available=[t for t in available if t[0]<=char]
        if not available:raise AnchorMappingHold('same-owner monotonic teacher prefix unavailable')
        chosen=min(available,key=lambda t:(abs(t[0]-char),t[0],t[2]))
        previous=chosen[2]
        result.append(dict(student_prefix_raw_index=index,teacher_prefix_raw_index=chosen[2],
            student_character_end=char,teacher_character_end=chosen[0],owner=owner,
            lookahead_characters=max(0,chosen[0]-char),backtrack_characters=max(0,char-chosen[0]),policy=policy))
    return result
