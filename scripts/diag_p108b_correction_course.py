#!/usr/bin/env python3
"""CPU-only paired-view/label exposure preflight, never corpus admission."""
import argparse
import hashlib
import json
from tokenizers import Tokenizer
from tinylm.chat.serialize import serialize
from scripts import p108b_correction_course as course
from scripts import p108b_correction as masks
from scripts import diag_p108b_correction as teacher
from scripts import diag_p108b_value_library as library
from scripts import diag_p108b_geometry as atlas
from scripts import interactive_research_infer as manual
from scripts.p106b_shards import verify

SOURCE=atlas.BASE/'correction_reviewed_v2'
OUT=atlas.BASE/'correction_course_v1'

def build():
    manifest=json.loads((SOURCE/'candidates_shards_manifest.json').read_text());verify(SOURCE,manifest)
    root_review=json.loads((SOURCE/'ROOT_REVIEW_v1.json').read_text())
    if root_review['final_candidate_views']!=56:raise ValueError('closed ROOT-reviewed56 candidates required')
    rows=[]
    for shard in manifest['shards']:
        rows.extend(json.loads(line)for line in(SOURCE/shard['path']).read_text().splitlines())
    if len(rows)!=56:raise ValueError('no added or silently excluded candidate views')
    if manual.file_sha(teacher.TOKENIZER)!='9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E':
        raise ValueError('same chat32 tokenizer required')
    tok=Tokenizer.from_file(str(teacher.TOKENIZER));cohort=course.pairs(rows);encoded={};audits=[]
    for identifier,pair in cohort.items():
        target_ids={};lengths={}
        for view,row in pair.items():
            full=tok.encode(serialize(row,'chatml')).ids
            if len(full)-1>1024:raise ValueError('paired cohort must reject full source instead of truncating')
            record=masks.masked_record(row,tok)
            if len(record.x)!=len(full)-1:raise ValueError('serialized input prefix differs')
            target_ids[view]=[v for v in record.y if v!=-100];lengths[view]=len(record.x)
            owners={o for o,t in zip(record.segments,record.y)if t!=-100}
            if owners!=({1}if view=='single'else{2}):raise ValueError('first wrong assistant receives supervision')
            encoded[(identifier,view)]=record
        if target_ids['single']!=target_ids['correction']:raise ValueError('same case must have exact same target IDs/EOT')
        audits.append(dict(case_id=identifier,input_tokens=lengths,target_ids=target_ids['single'],
            source_group_id=pair['single']['meta']['source_group_id'],language=pair['single']['meta']['language']))
    arms={}
    for arm in course.ARMS:
        epochs=[]
        for epoch in range(4):
            plan=course.epoch_plan(cohort,arm,epoch);records=[encoded[(r['case_id'],r['view'])]for r in plan]
            groups=[]
            for start in range(0,len(records),128):
                targets=[v for record in records[start:start+128]for v in record.y if v!=-100]
                groups.append(dict(targets=len(targets),sha256=hashlib.sha256(json.dumps(targets,separators=(',',':')).encode()).hexdigest().upper()))
            epochs.append(dict(epoch=epoch+1,plan=plan,input_tokens=sum(len(r.x)for r in records),
                supervised_tokens=sum(r.targets for r in records),update_denominators=groups))
        arms[arm]=dict(epochs=epochs,total_input_tokens=sum(e['input_tokens']for e in epochs),
            total_supervised_tokens=sum(e['supervised_tokens']for e in epochs))
    reference=arms['SINGLE_ONLY']['epochs']
    for arm,data in arms.items():
        for expected,actual in zip(reference,data['epochs']):
            if actual['update_denominators']!=expected['update_denominators']:raise ValueError('per-update target ID/denominator mismatch')
            if [r['case_id']for r in actual['plan']]!=[r['case_id']for r in expected['plan']]:raise ValueError('same case order required')
    return dict(schema='P108B_CORRECTION_COURSE_CPU_V1',status='RESEARCH_FIXTURE_CONTRACT_COMPLETE_NOT_TRAINING',
        sources={n:manual.file_sha(atlas.ROOT/n)for n in('scripts/p108b_correction_course.py','scripts/test_p108b_correction_course.py',
            'scripts/diag_p108b_correction_course.py','scripts/diag_p101a_clean_bilingual.py','tinylm/train/mtp_sft.py')},
        source_manifest_sha256=manual.file_sha(SOURCE/'candidates_shards_manifest.json'),root_review_sha256=manual.file_sha(SOURCE/'ROOT_REVIEW_v1.json'),
        initial_plan_sha256=manual.file_sha(atlas.ROOT/library.PLAN),cases=len(cohort),source_groups=len({a['source_group_id']for a in audits}),
        pair_token_audits=audits,arms=arms,microbatch=8,accumulation=16,context=1024,mtp=False,
        new_training_updates=0,model_loads=0,corpus75m_admitted=False,production_ready=False,
        required_before_full_training=['independently admitted complete source cohort and split','fixed parent/training budget/schedule',
            'independent final evaluation','separate equal-input/time panel if making efficiency claims'])

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check-only',action='store_true');a=parser.parse_args();report=build()
    if not a.check_only:library.write_new(OUT/'report.json',report)
    print(json.dumps(dict(status=report['status'],cases=report['cases'],
        arms={name:{k:v for k,v in data.items()if k!='epochs'}for name,data in report['arms'].items()},
        model_loads=0,new_training_updates=0,production_ready=False)))

if __name__=='__main__':main()
