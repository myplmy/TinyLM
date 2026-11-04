#!/usr/bin/env python3
"""P108 float control; reuse the strict loader, capture, scoring and rollback.

Float latent/effective additions are the same matrix operation. Search only
one realization, rather than paying twice for a known equivalent treatment.
"""
import argparse
import json
import time

from scripts import diag_p108_weight_space as common
from scripts import interactive_research_infer as manual
from scripts import p108_weight_space as repair
from scripts.p106b_shards import ShardWriter, verify as verify_shards

TAG, MODEL = 'p108w_v3_20261104', 'new595-broad-f'
SELF = 'scripts/diag_p108_float_pair.py'
TEST = 'scripts/test_p108_float_projection.py'


def prepare():
    common.prepare(TAG, MODEL)
    base, _ = common.locations(TAG, MODEL)
    common.write_json(base/'float_profile.json', dict(schema='P108_FLOAT_PAIR_V1',
        source_sha256=manual.file_sha(common.ROOT/SELF), test_sha256=manual.file_sha(common.ROOT/TEST),
        base_profile_sha256=manual.file_sha(base/'profile.json'),
        authority_directive=107, deadline=common.DEADLINE.isoformat(),
        realizations=['effective'], equivalence='FLOAT_EFFECTIVE_EQUALS_LATENT_ADDITION_CPU_VERIFIED',
        gate='AT_LEAST_FOUR_NATURAL_REPAIR_LOOPS',
        q_vs_f_claim='DESCRIPTIVE_ONLY_INDEPENDENTLY_TRAINED_MODELS'))


def check(base):
    common.verify_profile(base)
    extra=common.read_json(base/'float_profile.json')
    if (extra['schema']!='P108_FLOAT_PAIR_V1' or extra['authority_directive']!=107
            or extra['deadline']!=common.DEADLINE.isoformat()
            or extra['source_sha256']!=manual.file_sha(common.ROOT/SELF)
            or extra['test_sha256']!=manual.file_sha(common.ROOT/TEST)
            or extra['base_profile_sha256']!=manual.file_sha(base/'profile.json')
            or extra['realizations']!=['effective']):
        raise ValueError('float profile/source contract differs')
    return extra


def search():
    base,runtime=common.locations(TAG,MODEL)
    extra=check(base)
    profile=common.verify_profile(base)
    previous=common.read_json(base/'baseline'/'report.json')
    if previous['direction_report']['protocol']!='OBSERVED_LOOP_ORDER_CONTROL':
        print('[HOLD] natural loop cases fewer than four; no forced-loop repair claim',flush=True)
        return 8
    budget=common.Budget(profile)
    budget.check()
    if (base/'search').exists():
        raise FileExistsError('float search already exists')
    writer=ShardWriter(base/'search','answers',limit=3_000_000)
    final=dict(schema=common.SCHEMA,phase='search',variants=[],training_tokens=0,optimizer_updates=0,
               float_profile_sha256=manual.file_sha(base/'float_profile.json'),
               duplicate_float_realization_avoided=True)
    items=[r for r in common.read_json(base/'data.json')['rows'] if r['split']=='dev']
    with manual.selected_runtime(manual.resolve_model(MODEL)) as active:
        active['torch'].set_num_threads(4)
        active['torch'].cuda.reset_peak_memory_stats()
        vectors=common.load_vectors(runtime,active['torch'],previous)
        _,summary=common.evaluate(active,items,writer,'original_dev',budget,profile['max_new'])
        final['variants'].append(dict(name='original_dev',**summary))
        for gain in profile['gains']:
            name=f'effective_g{gain}'
            edits,specs=common.make_edits(active,vectors,previous['direction_report'],profile,gain,'effective')
            with repair.edit_weights(active['model'],active['route'],edits,'effective') as receipts:
                _,summary=common.evaluate(active,items,writer,name,budget,profile['max_new'])
            final['variants'].append(dict(name=name,**summary,realization='effective',gain=gain,
                                         specs=specs,receipts=receipts))
        def score(row):
            return (row['exact'],row['protected_exact'],-row['empty'],-row['question_echoes'],
                    -row['loop_indicators'],-sum(r['effective_delta_norm'] for r in row['receipts']))
        winner=max(final['variants'][1:],key=score)
        final['selected']=dict(name=winner['name'],realization='effective',gain=winner['gain'],
                               selection_split='DEV_ONLY',criterion='EXACT_PROTECTED_EMPTY_ECHO_LOOP_DELTA')
        final['origin']={key:active[key] for key in ('name','checkpoint_sha256','core_sha256','tokenizer_sha256')}
    check(base)
    manifest=writer.close(lineage=dict(float_profile_sha256=final['float_profile_sha256'],
                                      checkpoint_sha256=final['origin']['checkpoint_sha256']))
    verify_shards(base/'search',manifest)
    final.update(original_registered_core_unchanged=True,wall_seconds=time.monotonic()-budget.start,
                 status='TECHNICAL_COMPLETE_QUALITY_SEPARATE')
    common.write_json(base/'search'/'report.json',final)
    print('[FINAL] '+json.dumps(dict(selected=final['selected'],variants=[{k:r[k] for k in
        ('name','exact','scored','loop_indicators')} for r in final['variants']]),ensure_ascii=False),flush=True)
    return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('prepare','baseline','search','confirm'))
    args=parser.parse_args()
    if args.phase=='prepare':
        prepare()
        return 0
    base,_=common.locations(TAG,MODEL)
    check(base)
    if args.phase=='search':
        return search()
    common.run(args.phase,TAG,MODEL)
    check(base)
    return 0


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except TimeoutError as exc:
        print('[HOLD] '+str(exc),flush=True)
        raise SystemExit(8)
