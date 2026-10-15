#!/usr/bin/env python3
"""CPU inventory on old TRAIN roots; only a small report, no dataset/model writes."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter,defaultdict
from datetime import datetime,timezone
import json
import time
from scripts import diag_p106b_relation_course as dependency
from scripts import p106b_public_qa_roles as method
from scripts.p106b_gate_runtime import GateNegative
TAG='p106b_public_three_qa_inventory_v1_s1337'
EVIDENCE=ROOT/'test_result/evidence'/TAG
CODE=('scripts/p106b_public_qa_roles.py','scripts/test_p106b_public_qa_roles.py','scripts/diag_p106b_public_qa_role_inventory.py')


def info():
    return dict(schema=method.VERSION,tag=TAG,code_sha256={p:dependency.training.data.digest(ROOT/p) for p in CODE},
        operation='READ_ONLY_ORIGINAL_TRAIN_INVENTORY',expected_original_train_roots=2048,
        teacher_calls=0,model_loading='NOT_RUN',dataset_saved=False,new_facts_claimed=False,
        source_truth='ORIGINAL_PUBLIC_UNVERIFIED',semantic_truth='NOT_REVIEWED',max_student_sequence=1024,
        deadline_utc=dependency.prior.producer.legacy.source.DEADLINE.isoformat())


def run():
    from tokenizers import Tokenizer
    from tinylm.train import mtp_sft as core
    dependency.prior.producer.legacy.source.deadline();began=time.perf_counter()
    if EVIDENCE.exists():raise GateNegative('old inventory preserved')
    source=dependency.prior.producer.data.source;old,rows,_=source.read_course()
    wanted={x['meta']['parent_concept_id'] for x in rows['train'] if x['meta']['kind']=='natural_first_qa'}
    if len(wanted)!=2048:raise ValueError('complete old source TRAIN2048 roots required')
    if dependency.training.data.digest(dependency.training.data.PUBLIC/'report.json')!=dependency.training.data.PUBLIC_SHA:raise ValueError('pinned public source changed')
    tok=Tokenizer.from_file(str(dependency.training.data.TOKENIZER));totals=defaultdict(Counter);seen={};accepted=[];reasons=Counter()
    for split in ('train','val'):
        manifest=json.loads((dependency.training.data.PUBLIC/(split+'_shards_manifest.json')).read_text())
        for row in dependency.training.data.stream_rows(dependency.training.data.PUBLIC,manifest):
            m=row['meta'];identity=m.get('parent_concept_id')
            if m.get('selection_family')!='Flan-Coqa' or identity not in wanted:continue
            digest=method.source.sha(row['messages'][:2]);lang=m['language']
            if identity in seen:
                if seen[identity]!=digest:raise ValueError('same parent ID has different original messages')
                totals[lang]['duplicate_same_original']+=1;continue
            seen[identity]=digest;totals[lang]['original_roots']+=1
            try:child,parsed=method.wrap(row)
            except ValueError as exc:totals[lang]['strict_parse_rejected']+=1;reasons[lang+':'+str(exc)]+=1;continue
            totals[lang]['three_qa_parseable']+=1
            for pair in parsed['pairs']:
                totals[lang]['original_qa_items']+=1
                totals[lang]['unique_literal_answer_in_reference']+=int(parsed['reference'].count(pair['answer'])==1)
            try:rec=core.encode_record(child,tok)
            except ValueError as exc:totals[lang]['serialization_rejected']+=1;reasons[lang+':'+str(exc)]+=1;continue
            if rec.x_tokens>1024:
                totals[lang]['over1024']+=1;continue
            first=dict(messages=child['messages'][:2],meta=child['meta']);one=core.encode_record(first,tok)
            totals[lang].update(usable1024_roots=1,three_turn_x=rec.x_tokens,three_turn_targets=rec.targets,first_turn_x=one.x_tokens,first_turn_targets=one.targets)
            accepted.append(identity)
    missing=sorted(wanted-set(seen))
    if missing:raise ValueError('old TRAIN originals missing from pinned train/val: '+str(len(missing)))
    result=dict(info(),status='PUBLIC_QA_ROLE_INVENTORY_COMPLETED',languages={k:dict(v) for k,v in totals.items()},rejections=dict(reasons),
        old_source_corpus_sha256=dependency.training.data.digest(source.CORPUS/'report.json'),
        public_report_sha256=dependency.training.data.PUBLIC_SHA,source_train_ids_sha256=method.source.sha(sorted(wanted)),
        accepted_ids_sha256=method.source.sha(sorted(accepted)),fresh_relation_test_accessed=False,
        whole_sec=time.perf_counter()-began,
        interpretation='strict original numbered pairs; source answer quality/translation/context resolution not reviewed; no new corpus or training')
    dependency.training.write(EVIDENCE/'report.json',result)
    print('[PUBLIC_QA_ROLE_INVENTORY] '+json.dumps(dict(languages=result['languages'],rejections=dict(reasons),whole_sec=result['whole_sec'])),flush=True);return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if a.check_only:print('[PUBLIC_QA_ROLES_CHECK_ONLY] '+json.dumps(info()));return 0
    try:return run()
    except GateNegative as exc:print('[PUBLIC_QA_ROLES_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[PUBLIC_QA_ROLES_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
