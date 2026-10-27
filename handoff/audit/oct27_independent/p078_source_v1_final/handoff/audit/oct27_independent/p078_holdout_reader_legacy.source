#!/usr/bin/env python3
"""V2 CPU-only router holdout from unused official TRAIN, never teacher/eval gold.

Original V3 TRAIN/VAL and original sources are read-only. Fixed seed1337,
connected groups and128 rows per language/split; insufficient supply is HOLD.
No model/CP/GPU/download path. Metadata-only inventory imports no torch.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts import p078_prefix_router as router
from scripts import diag_p078_route_training as base
SCHEMA = 'P078_ROUTER_HOLDOUT_DATA_V2'
DIRECTORY = 'data_cache/p078_router_holdout_bootstrap_v3_s1337'
SEED = 1337
TARGET = 128
END = datetime.fromisoformat('2026-10-21T14:00:00+00:00')
CODE = tuple(dict.fromkeys(('scripts/p078_router_holdout_data.py', 'scripts/p078_prefix_router.py',
    'scripts/p106b_night_qa_data.py', *base.CODE)))
sha = router.route.sha


def source_tools():
    path = base.path('scripts/p106b_night_qa_data.py'); tree = ast.parse(path.read_text(encoding='utf-8'))
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ('SOURCES', 'VERSION'): values[target.id] = ast.literal_eval(node.value)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in ('_paragraphs', '_user', '_balanced_candidates')]
    if len(functions) != 3 or set(values) != {'SOURCES', 'VERSION'}: raise ValueError('original pinned QA source contract changed')
    namespace = dict(sha=sha, defaultdict=defaultdict, deque=deque)
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'), namespace)
    return values, namespace


def evidence_keys(row):
    meta = row.get('meta', {}); keys = set()
    for field in ('article_id', 'context_id'):
        if isinstance(meta.get(field), str) and meta[field]: keys.add(field + ':' + meta[field])
    for field in ('parent_concept_id', 'semantic_root_id', 'root_id', 'root'):
        if isinstance(meta.get(field), str) and meta[field]: keys.add('root:' + meta[field])
    if isinstance(meta.get('context_original'), str): keys.add('context_text:' + sha(router.normalized(meta['context_original'])))
    if isinstance(meta.get('question_original'), str): keys.add('raw_question:' + sha(router.normalized(meta['question_original'])))
    for message in row.get('messages', []):
        if message.get('role') == 'user': keys.add('raw_question:' + sha(router.normalized(router.text_content(message['content']))))
    return keys


def existing(args):
    from scripts.p101a_sft_mtp_data import stream_rows
    report = base.inputs(SimpleNamespace(corpus=base.CLEAN_CORPUS, corpus_sha256=args.corpus_sha256))
    keys = set(); counts = {}; coverage = Counter()
    for split in ('train', 'val'):
        for spec in report['manifests'][split]['shards']: base.path(base.CLEAN_CORPUS + '/' + spec['path'])
        n = 0
        for row in stream_rows(base.path(base.CLEAN_CORPUS), report['manifests'][split]):
            row_keys = evidence_keys(row); keys.update(row_keys); n += 1
            for kind in ('article_id', 'context_id', 'root', 'context_text', 'raw_question'):
                coverage[kind] += any(k.startswith(kind + ':') for k in row_keys)
        if n != report['manifests'][split]['rows']: raise ValueError('original V3 complete denominator differs')
        counts[split] = n
    if counts != dict(train=22528, val=512): raise ValueError('complete original V3 22528/512 required')
    return keys, dict(corpus_report_sha256=args.corpus_sha256, corpus_manifests=report['manifests'], rows=counts,
        key_coverage=dict(coverage), exclusion_keys=len(keys), exclusion_keys_sha256=sha(sorted(keys)))


def row_from_pair(pair, user):
    meta = {k: pair[k] for k in ('root', 'language', 'article_id', 'context_id', 'article_title', 'qa_id',
        'source_path', 'source_sha256', 'answers')}
    meta.update(parent_concept_id=pair['root'], semantic_root_id=pair['root'], question_original=pair['question'],
        context_original=pair['context'], aliases=list(dict.fromkeys(a['text'] for a in pair['answers'])),
        supervised_assistant_turns=[1], source_original_split='train', wrapper_view=2,
        source='unused_official_train_router_holdout', teacher_calls=0, label_status='ORIGINAL_SPAN_ANNOTATION_CHAR_VERIFIED')
    return dict(messages=[dict(role='user', content=user(pair['context'], pair['question'], pair['language'], 2)),
        dict(role='assistant', content=pair['answers'][0]['text'])], meta=meta)


def candidates(documents, blocked, tools, original_version):
    result = []; rejection = Counter()
    for language in ('ko', 'en'):
        descriptor = documents[language]
        for title, context, qas in tools['_paragraphs'](descriptor['document']):
            aid = sha([language, router.normalized(title)]); cid = sha([language, router.normalized(context)])
            for qa in qas:
                question = qa['question']; answers = qa.get('answers', [])
                early = ('used_article' if 'article_id:' + aid in blocked else
                    'used_context' if 'context_id:' + cid in blocked or 'context_text:' + sha(router.normalized(context)) in blocked else
                    'used_question' if 'raw_question:' + sha(router.normalized(question)) in blocked else None)
                if early: rejection[language + ':' + early] += 1; continue
                if not isinstance(question, str) or not question.strip() or not answers or qa.get('is_impossible') is True:
                    rejection[language + ':unanswerable_or_empty'] += 1; continue
                if any(not isinstance(a.get('text'), str) or not a['text'] or type(a.get('answer_start')) is not int
                        or a['answer_start'] < 0 or context[a['answer_start']:a['answer_start'] + len(a['text'])] != a['text'] for a in answers):
                    rejection[language + ':span_mismatch'] += 1; continue
                root = sha([original_version, language, descriptor['sha256'], title, context, question, answers])
                pair = dict(root=root, language=language, article_id=aid, context_id=cid, article_title=title,
                    qa_id=qa['id'], question=question, context=context, answers=answers,
                    source_path=descriptor['path'], source_sha256=descriptor['sha256'])
                pair['row'] = row_from_pair(pair, tools['_user']); pair['keys'] = sorted(evidence_keys(pair['row']))
                if set(pair['keys']) & blocked: rejection[language + ':used_other_alias'] += 1; continue
                result.append(pair)
    return result, dict(rejection)


def group_inventory(pairs):
    parent = list(range(len(pairs))); owner = {}
    def find(i):
        while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for i, pair in enumerate(pairs):
        for key in pair['keys']:
            if key in owner: parent[find(i)] = find(owner[key])
            else: owner[key] = i
    components = defaultdict(list)
    for i in range(len(pairs)): components[find(i)].append(i)
    counts = {s: Counter() for s in ('dev', 'test')}; groups = {s: Counter() for s in counts}
    for members in components.values():
        group = sha(sorted({key for i in members for key in pairs[i]['keys']}))
        split = 'dev' if int(sha([SCHEMA, SEED, group])[:16], 16) % 2 == 0 else 'test'
        languages = set()
        for i in members:
            pairs[i]['group_sha256'] = group; pairs[i]['split'] = split
            counts[split][pairs[i]['language']] += 1; languages.add(pairs[i]['language'])
        groups[split].update(languages)
    return dict(components=len(components), rows=len(pairs), buckets={s:dict(rows=sum(counts[s].values()),
        languages=dict(counts[s]), groups=dict(groups[s])) for s in counts}, seed=SEED, target_per_language_split=TARGET)


def load_inventory(args):
    started = time.perf_counter(); values, tools = source_tools(); blocked, original = existing(args); documents = {}
    for language in ('ko', 'en'):
        relative, expected = values['SOURCES'][language]['train']; path = base.path(relative)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest().upper() != expected: raise ValueError('pinned original TRAIN SHA differs')
        documents[language] = dict(path=relative, sha256=expected, document=json.loads(raw))
    pairs, rejected = candidates(documents, blocked, tools, values['VERSION']); inventory = group_inventory(pairs)
    inventory.update(original=original, rejections=rejected, sources={k:{f:v[f] for f in ('path','sha256')} for k,v in documents.items()},
        elapsed_seconds=time.perf_counter() - started, official_eval_files_read=0, teacher_calls=0, model_loads=0,
        checkpoint_tensor_loads=0, full_pretraining_contamination='NOT_AUDITED', fully_pipeline_blind=False)
    return pairs, inventory, blocked, tools


def select(pairs, blocked, tools, admit, *, target=TARGET):
    selected = {s: [] for s in ('dev', 'test')}; rejected = Counter()
    for split in ('dev', 'test'):
        for language in ('ko', 'en'):
            pool = [p for p in pairs if p['split'] == split and p['language'] == language]
            contexts = set(); questions = set(); chosen = []
            for pair in tools['_balanced_candidates'](pool, SEED):
                question = router.normalized(pair['question'])
                if pair['context_id'] in contexts or question in questions: continue
                row, reason = admit(pair['row'])
                if reason: rejected[language + ':' + split + ':' + reason] += 1; continue
                if evidence_keys(row) & blocked: raise ValueError('selected original TRAIN/VAL overlap')
                chosen.append((pair, row)); contexts.add(pair['context_id']); questions.add(question)
                if len(chosen) == target: break
            if len(chosen) != target: raise ValueError('HOLD_SUPPLY: fixed seed/bucket/quota shortage ' + language + '/' + split + ':' + str(len(chosen)))
            selected[split].extend(chosen)
    for a,b in (('dev','test'),):
        if {k for pair,row in selected[a] for k in pair['keys']} & {k for pair,row in selected[b] for k in pair['keys']}:
            raise ValueError('new DEV/TEST article/context/root/normalized-question overlap')
    return selected, dict(rejected)


def prepare(args):
    source_before={p:base.digest(base.path(p)) for p in CODE}
    pairs, inventory, blocked, tools = load_inventory(args)
    router.route.import_guard()
    from tokenizers import Tokenizer
    from tinylm.chat.canonical import normalize, validate
    from tinylm.chat.serialize import serialize
    from scripts.diag_p101a_clean_bilingual import masked_record
    from scripts.p106b_shards import ShardWriter, verify
    raw = base.path(base.TOKENIZER).read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != base.TOK_SHA: raise ValueError('pinned tokenizer bytes differ')
    tok = Tokenizer.from_str(raw.decode())
    if tok.get_vocab_size()!=32768 or [tok.token_to_id(k) for k in ('<|im_start|>','<|im_end|>','<eos>')] != [3,4,2]: raise ValueError('pinned chat32 vocab differs')
    def admit(row):
        row = validate(normalize(row))
        prompt=serialize(dict(messages=row['messages'][:1]),'chatml',add_generation_prompt=True)
        if len(tok.encode(prompt).ids)+128>1024 or len(tok.encode(serialize(row,'chatml')).ids)-1>1024:
            return None,'full_context_generation_budget'
        record = masked_record(row, tok)
        p = router.validate_prefix(row, record, tok)  # Any boundary mismatch HOLD; never filter such rows.
        if len(p.token_ids) + 128 > 1024 or record.x_tokens > 1024: return None, 'full_context_generation_budget'
        if record.targets > 128 or [v for v in record.y if v!=-100][-1] != 4: return None, 'complete_answer_eot'
        return row, None
    selected, rejected = select(pairs, blocked, tools, admit)
    directory = base.path(DIRECTORY)
    if directory.exists(): raise FileExistsError('V2 holdout namespace preserved')
    manifests = {}; counts = {}; entries = {'dev': [], 'test': []}; ordered = []; complete = False; writer=None
    try:
        for split in ('dev','test'):
            writer = ShardWriter(directory, split, limit=19_999_999); tally = Counter()
            values = sorted(selected[split], key=lambda v: (router.case_order_sha(v[1]), v[0]['root']))
            for pair,row in values:
                record = masked_record(row,tok); index=len(ordered); ordered.append(row)
                writer.append(row); tally.update(rows=1,x_tokens=record.x_tokens,assistant_targets=record.targets,
                    ko_rows=row['meta']['language']=='ko',en_rows=row['meta']['language']=='en')
                entries[split].append(dict(index=index,row_sha256=router.row_sha(row),language=row['meta']['language'],
                    group_sha256=pair['group_sha256'],keys=pair['keys'],case_order_sha256=router.case_order_sha(row)))
            manifests[split]=writer.close(lineage=dict(schema=SCHEMA,complete=True,source_original_split='train',teacher_calls=0)); writer=None
            verify(directory,manifests[split]); counts[split]=dict(tally)
        split_manifest=dict(schema=router.SCHEMA,seed=SEED,min_rows=128,min_language=64,rows=len(ordered),
            splits=entries,counts={s:dict(rows=counts[s]['rows'],languages=dict(ko=counts[s]['ko_rows'],en=counts[s]['en_rows'])) for s in counts},
            groups=inventory['components'],body_validation_reused=False,fully_pipeline_blind=False,
            claim='unused official TRAIN groups; original body VAL unchanged; pretraining/paraphrase contamination not audited')
        if len(ordered)!=512 or any(counts[s]['rows']!=256 or counts[s]['ko_rows']!=128 or counts[s]['en_rows']!=128 for s in counts): raise ValueError('fixed512 quota differs')
        split_manifest['manifest_sha256']=sha(split_manifest)
        selected_groups={p['group_sha256'] for split in selected.values() for p,row in split}
        group_keys={g:sorted({key for pair in pairs if pair['group_sha256']==g for key in pair['keys']}) for g in selected_groups}
        if source_before!={p:base.digest(base.path(p)) for p in CODE}: raise ValueError('producer source changed during CPU preparation')
        report=dict(schema=SCHEMA,status='ROUTER_HOLDOUT_READY',inventory=inventory,counts=counts,manifests=manifests,
            split_manifest=split_manifest,rows_sha256=sha([router.row_sha(r) for r in ordered]),tokenizer_sha256=base.TOK_SHA,
            admission_rejections=rejected,source_sha256=source_before,selected_component_keys=group_keys,
            teacher_calls=0,model_loads=0,checkpoint_tensor_loads=0,fully_pipeline_blind=False,
            official_train_annotation_gold_inputs='KorQuAD/SQuAD official TRAIN annotated spans are labels',official_eval_gold_inputs=0)
        if __import__('torch').cuda.is_initialized(): raise ValueError('CPU-only source preparation unexpectedly initialized CUDA')
        destination=base.path(DIRECTORY+'/report.json')
        serialized=(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
        if len(serialized)>=20_000_000: raise ValueError('CPU metadata below20MB required')
        with destination.open('xb') as stream: stream.write(serialized)
        complete=True; return report
    finally:
        # Never remove partial files. A missing final report is NOT_READY.
        if writer is not None and writer._total_rows: writer.close(lineage=dict(schema=SCHEMA,complete=False,partial=True))
        if not complete: print('[HOLD_PARTIAL_SOURCE_PRESERVED]',flush=True)


def read_prepared(expected_sha, corpus_sha):
    from scripts.p101a_sft_mtp_data import stream_rows
    path=base.path(DIRECTORY+'/report.json')
    if base.digest(path)!=expected_sha: raise ValueError('independent holdout report byte pin differs')
    if path.stat().st_size>=20_000_000: raise ValueError('small metadata limit')
    report=json.loads(path.read_text())
    activity=base.read(DIRECTORY+'/activity.json')
    begin,end=(datetime.fromisoformat(activity[k]) for k in ('started_at','ended_at'))
    seconds=activity.get('seconds'); cap=activity.get('max_wall_sec')
    if (report.get('schema')!=SCHEMA or report.get('status')!='ROUTER_HOLDOUT_READY' or report.get('tokenizer_sha256')!=base.TOK_SHA
            or report['inventory']['original']['corpus_report_sha256']!=corpus_sha
            or report['source_sha256']!={p:base.digest(base.path(p)) for p in CODE}
            or activity.get('complete') is not True or activity.get('returncode')!=0
            or activity.get('report_sha256')!=expected_sha or activity.get('corpus_sha256')!=corpus_sha
            or activity.get('source_sha256')!=report['source_sha256']
            or type(seconds) not in (int,float) or not math.isfinite(seconds) or seconds<0
            or type(cap) is not int or not 1<=cap<=1200 or seconds>cap+30
            or begin.tzinfo is None or end.tzinfo is None or begin>end or end>END
            or activity.get('expires_at')!=END.isoformat() or activity.get('model_loads')!=0
            or activity.get('checkpoint_tensor_loads')!=0): raise ValueError('frozen V2 producer/original corpus/time differs')
    rows=[]
    for split in ('dev','test'):
        for part in report['manifests'][split]['shards']: base.path(DIRECTORY+'/'+part['path'])
        values=list(stream_rows(base.path(DIRECTORY),report['manifests'][split])); rows.extend(values)
        if len(values)!=256 or Counter(r['meta']['language'] for r in values)!=dict(ko=128,en=128): raise ValueError('fixed V2 bilingual quota differs')
    if len(rows)!=512 or sha([router.row_sha(r) for r in rows])!=report['rows_sha256']: raise ValueError('frozen row identity differs')
    blocked,original=existing(SimpleNamespace(corpus_sha256=corpus_sha))
    if original!=report['inventory']['original']: raise ValueError('original frozen exclusion set changed')
    split_keys={s:set() for s in ('dev','test')}
    manifest=report['split_manifest']; check=dict(manifest); expected_manifest=check.pop('manifest_sha256')
    if (sha(check)!=expected_manifest or manifest.get('seed')!=1337 or manifest.get('min_rows')!=128 or manifest.get('min_language')!=64): raise ValueError('fixed source split schema/minima differ')
    for split in ('dev','test'):
        entries=manifest['splits'][split]; offset=0 if split=='dev' else 256
        if (len(entries)!=256 or [e['index'] for e in entries]!=list(range(offset,offset+256))
                or Counter(e['language'] for e in entries)!=dict(ko=128,en=128)):
            raise ValueError('all512 source entries exactly once in fixed256/256 order required')
        for entry in entries:
            row=rows[entry['index']]; keys=evidence_keys(row); full=report['selected_component_keys'][entry['group_sha256']]
            assigned='dev' if int(sha([SCHEMA,SEED,entry['group_sha256']])[:16],16)%2==0 else 'test'
            if (entry['row_sha256']!=router.row_sha(row) or entry['language']!=row['meta']['language']
                    or sorted(keys)!=entry['keys'] or not keys<=set(full) or sha(full)!=entry['group_sha256']
                    or entry['case_order_sha256']!=router.case_order_sha(row)
                    or assigned!=split or set(full)&blocked): raise ValueError('independent frozen group/row/exclusion mismatch')
            split_keys[split].update(full)
    if split_keys['dev']&split_keys['test']: raise ValueError('independent complete group cross-split overlap')
    return report,rows


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--mode',choices=('inventory','prepare'),required=True)
    p.add_argument('--corpus-sha256'); p.add_argument('--max-wall-sec',type=int,default=600)
    action=p.add_mutually_exclusive_group(required=True); action.add_argument('--check-only',action='store_true'); action.add_argument('--execute',action='store_true'); args=p.parse_args(argv)
    started=time.perf_counter(); began=datetime.now(timezone.utc); owned=False; code=8; error=None
    try:
        if args.check_only: print(json.dumps(dict(status='STATIC_ONLY',source_sha256={x:base.digest(base.path(x)) for x in CODE},model_loads=0,corpus_reads=0))); return 0
        if not isinstance(args.corpus_sha256,str) or len(args.corpus_sha256)!=64: raise ValueError('root-pinned original V3 report SHA required')
        remaining=(END-datetime.now(timezone.utc)).total_seconds()
        if not 1<=args.max_wall_sec<=1200 or args.max_wall_sec>remaining: raise ValueError('CPU task current UTC/full bounded cap admission required')
        if args.mode=='prepare':
            if base.path(DIRECTORY).exists(): raise FileExistsError('prior source namespace preserved')
            owned=True
        with base.wall(args.max_wall_sec):
            result=load_inventory(args)[1] if args.mode=='inventory' else prepare(args)
        print(json.dumps(dict(status='INVENTORY_ONLY' if args.mode=='inventory' else result['status'],
            inventory=result if args.mode=='inventory' else result['inventory'],counts=result.get('counts'),model_loads=0,checkpoint_tensor_loads=0),ensure_ascii=False,sort_keys=True)); code=0; return code
    except KeyboardInterrupt: code=130; error='KeyboardInterrupt'; return code
    except Exception as exc: error=type(exc).__name__+': '+str(exc); print('[HOLD] '+error,flush=True); return code
    finally:
        if owned and base.path(DIRECTORY).is_dir():
            ended=datetime.now(timezone.utc); path=base.path(DIRECTORY+'/report.json')
            receipt=dict(schema=SCHEMA,complete=code==0,returncode=code,error=error,started_at=began.isoformat(),ended_at=ended.isoformat(),
                seconds=time.perf_counter()-started,max_wall_sec=args.max_wall_sec,expires_at=END.isoformat(),pid=os.getpid(),pgid=os.getpgrp(),
                source_sha256={p:base.digest(base.path(p)) for p in CODE},corpus_sha256=args.corpus_sha256,
                report_sha256=base.digest(path) if path.is_file() else None,invocation=list(sys.argv),model_loads=0,checkpoint_tensor_loads=0)
            with base.path(DIRECTORY+'/activity.json').open('x',encoding='utf-8') as stream: json.dump(receipt,stream,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False); stream.write('\n')


if __name__=='__main__': raise SystemExit(main())
