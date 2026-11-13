#!/usr/bin/env python3
"""CPU-only native vocabulary mapping and frozen TRAIN scalar-cache inventory."""
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import time
from scripts import p106b_actd_anchor as actd
from scripts.p106b_alm_bytes import student_piece_bytes
from scripts import diag_p106b_qwen35_text_core6 as q

ROOT=Path(__file__).resolve().parents[1]
TAG='p106b_actd_anchor_v1_20261113'
BASE=ROOT/'test_result/evidence'/TAG
ROWS=ROOT/'test_result/evidence/p106b_gsq_coordinates_v2_20261113/training_rows.json'
GSQ_PROFILE=ROOT/'test_result/evidence/p106b_gsq_logtail_v1_20261113/profile.json'
QUALIFIED=ROOT/'test_result/evidence/p106b_qwen35_fixedshape_v1_20261113'
TOKENIZER=ROOT/'data_cache/tok-ko-en-32768-chat32.json'
TOKENIZER_SHA='9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E'
DEADLINE=datetime(2026,11,13,8,tzinfo=timezone.utc)
SOURCES=('scripts/p106b_actd_anchor.py','scripts/test_p106b_actd_anchor.py',
 'scripts/diag_p106b_actd_anchor.py','scripts/test_p106b_actd_inventory.py',
 'scripts/p106b_alm_bytes.py','scripts/diag_p106b_qwen35_text_core6.py')


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def object_sha(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest().upper()


def write_new(path,obj,*,limit=3_000_000):
    raw=json.dumps(obj,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()+bytes([10])
    if len(raw)>limit:raise ValueError('bounded artifact size exceeded')
    with Path(path).open('xb') as stream:stream.write(raw)
    return dict(path=Path(path).name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest().upper())


def native_special_map(student_specials,teacher_vocab,metadata):
    if ({k:student_specials.get(k) for k in ['<eos>','<|im_start|>','<|im_end|>']}
            !={'<eos>':2,'<|im_start|>':3,'<|im_end|>':4}
            or metadata.get('eos_token')!='<|endoftext|>'
            or {k:teacher_vocab.get(k) for k in ['<|endoftext|>','<|im_start|>','<|im_end|>']}
            !={'<|endoftext|>':248044,'<|im_start|>':248045,'<|im_end|>':248046}):
        raise ValueError('declared native EOS2 vs ChatML EOT4 correspondence changed')
    return {248044:2,248045:3,248046:4}


def inventory(rows):
    languages=Counter();actual_x=ce=chunks=teacher_targets=topk_positions=0
    for row in rows:
        record=row['record']
        if (set(record)!={'x','y','segments'} or not len(record['x'])==len(record['y'])==len(record['segments'])
                or object_sha(record)!=row['record_sha256']):
            raise ValueError('frozen actual one-shift student record changed')
        count=sum(i!=-100 for i in record['y'])
        if count!=row['ce_targets']:raise ValueError('original CE target count changed')
        languages[row['language']]+=1;actual_x+=len(record['x']);ce+=count
        for chunk in row['chunks']:
            chunks+=1;teacher_targets+=chunk['teacher_target_count']
            topk_positions+=int(any(name in chunk for name in ['topk','top_log_probs','top_token_ids','anchor_ids']))
    return dict(rows=len(rows),language_counts=dict(languages),actual_x_tokens=actual_x,ce_targets=ce,
        scalar_alm_chunks=chunks,teacher_targets_in_chunks=teacher_targets,export_topk_positions=topk_positions,
        actd_cache_ready=bool(topk_positions) and topk_positions==chunks,
        scope='This frozen TRAIN export only; scalar target probabilities are not top-k distributions')


def run():
    start=time.perf_counter()
    if BASE.exists():raise FileExistsError('fresh ACTD CPU namespace required')
    def check():
        if time.perf_counter()-start>600 or (DEADLINE-datetime.now(timezone.utc)).total_seconds()<900:
            raise TimeoutError('CPU vocabulary mapping phase/authority reserve')
    check()
    profile=json.loads((QUALIFIED/'profile.json').read_text());canary=json.loads((QUALIFIED/'canary/report.json').read_text())
    exit_receipt=json.loads((QUALIFIED/'ROOT_CANARY_EXIT_v1.json').read_text())
    if (not canary['fixed_numerical_passed'] or not canary['sources_assets_unchanged']
            or exit_receipt['actual_process_exit_code']!=0
            or exit_receipt['report_sha256']!=digest(QUALIFIED/'canary/report.json')
            or exit_receipt['profile_sha256']!=digest(QUALIFIED/'profile.json')):
        raise ValueError('closed qualified teacher numerical provenance required')
    paths=[TOKENIZER,ROWS,GSQ_PROFILE,QUALIFIED/'profile.json',QUALIFIED/'canary/report.json',QUALIFIED/'ROOT_CANARY_EXIT_v1.json']
    for name in ['tokenizer.json','tokenizer_config.json']:
        item=profile['assets']['files'][name];path=Path(item['resolved_path'])
        if not path.resolve().is_relative_to(ROOT/'HF') or digest(path)!=item['sha256']:raise ValueError('teacher metadata pin changed')
        paths.append(path)
    if digest(TOKENIZER)!=TOKENIZER_SHA:raise ValueError('student tokenizer changed')
    sources={str(path.relative_to(ROOT)):digest(path) for path in [*paths,*[ROOT/n for n in SOURCES]]}
    gsq=json.loads(GSQ_PROFILE.read_text());expected=gsq['references'].get(str(ROWS.relative_to(ROOT)))
    if expected is None or digest(ROWS)!=expected:raise ValueError('same frozen GSQ TRAIN128 identity required')
    rows=json.loads(ROWS.read_text())['rows'];cache=inventory(rows)
    if cache['rows']!=128 or cache['language_counts']!={'ko':64,'en':64}:raise ValueError('same bilingual TRAIN128 required')
    student=json.loads(TOKENIZER.read_text());teacher=json.loads(paths[-2].read_text());metadata=json.loads(paths[-1].read_text())
    if (student['model']['type']!='BPE' or teacher['model']['type']!='BPE'
            or student['decoder']['type']!='ByteLevel' or teacher['decoder']['type']!='ByteLevel'
            or student['normalizer']is not None or student['pre_tokenizer'].get('add_prefix_space')is not False):
        raise ValueError('inspected native ByteLevel student/teacher declarations required')
    from tokenizers import Tokenizer
    tok=Tokenizer.from_file(str(TOKENIZER))
    specials={a['content']:a['id'] for a in student['added_tokens'] if a['special']}
    ordinary={token_id:student_piece_bytes(piece) for piece,token_id in student['model']['vocab'].items()
              if token_id not in set(specials.values())}
    declarations=q.tokenizer_declarations(teacher,metadata);tv=declarations['vocabulary']
    teacher_specials=set(declarations['decoder'])|{tv[t] for t in declarations['extras']}|{tv[t] for t in declarations['named'].values()}
    special_map=native_special_map(specials,tv,metadata)
    mapper=actd.AnchorMapper(ordinary,32768,lambda text:tok.encode(text,add_special_tokens=False).ids,
        teacher_special_ids=teacher_specials,special_map=special_map)
    by_id={i:piece for piece,i in teacher['model']['vocab'].items()}
    head_vocab=profile['vocab'];anchors=[None]*head_vocab;modes=[0]*head_vocab;counts=Counter();holds=Counter();examples=[]
    for token_id in range(head_vocab):
        if token_id%1024==0:check()
        if token_id not in by_id and token_id not in teacher_specials:
            counts['UNDECLARED_HEAD_ID']+=1;continue
        piece=None if token_id in teacher_specials else student_piece_bytes(by_id[token_id])
        try:
            row=mapper.map([token_id],[piece])[0];anchors[token_id]=row['anchor_id']
            mode={'EXACT_SHARED_BYTES':1,'FIRST_STUDENT_SUBTOKEN':2,'EXPLICIT_SPECIAL':3}[row['mode']]
            modes[token_id]=mode;counts[row['mode']]+=1
        except actd.AnchorMappingHold as exc:
            counts['HOLD']+=1;holds[str(exc)]+=1
            if len(examples)<32:examples.append(dict(teacher_id=token_id,reason=str(exc),piece_hex=None if token_id in teacher_specials else piece.hex()))
    BASE.mkdir(parents=True)
    pinned=dict(schema='P106B_ACTD_ANCHOR_CPU_PROFILE_V1',tag=TAG,authority_directive=115,
        deadline=DEADLINE.isoformat(),sources=sources,teacher=q.MODEL,teacher_revision=q.REVISION,
        teacher_head_vocab=head_vocab,student_head_vocab=32768,teacher_special_map=special_map,
        eos_contract='NATIVE_SEQUENCE_EOS_TO_TINY_EOS2; CHATML_EOT_TO_TINY_EOT4; no EOS/EOT collapse',
        objective='LITERAL_EQ7_ORDERED_EDGES_PLUS_EQ8_UNIQUE_COMPLEMENT_FULL_STUDENT_NORMALIZER',
        default_training_enabled=False,new_models=0,gpu_calls=0,optimizer_updates=0,checkpoint_writes=0)
    write_new(BASE/'profile.json',pinned)
    artifacts=[write_new(BASE/'teacher_to_student_anchors.json',anchors),write_new(BASE/'teacher_mapping_modes.json',modes)]
    for name,sha in sources.items():
        if digest(ROOT/name)!=sha:raise ValueError('CPU mapping source changed: '+name)
    import torch
    if torch.cuda.is_initialized():raise RuntimeError('CPU-only stage initialized CUDA')
    result=dict(schema='P106B_ACTD_ANCHOR_CPU_INVENTORY_V1',tag=TAG,status='CPU_MAPPING_AND_CACHE_INVENTORY_COMPLETE_NOT_TRAINING_READY',
        profile_sha256=digest(BASE/'profile.json'),cache_inventory=cache,head_vocab=head_vocab,
        declared_teacher_vocab=len(tv),student_ordinary_vocab=len(ordinary),mapping_counts=dict(counts),
        hold_reasons=dict(holds),hold_examples=examples,artifacts=artifacts,seconds=time.perf_counter()-start,
        sources_unchanged=True,cuda_initialized=False,training_ready=False,quality_claim=False,
        limitation='Static vocabulary support is not top-k probability/position coverage; no model, train, source admission or quality claim')
    write_new(BASE/'report.json',result)
    print('[ACTD_CPU_COMPLETE] '+json.dumps({k:result[k] for k in ['status','seconds','cache_inventory','mapping_counts','hold_reasons','training_ready']}),flush=True)


if __name__=='__main__':run()
