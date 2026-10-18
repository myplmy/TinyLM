#!/usr/bin/env python3
"""Write-once context intervention evaluation; never a training corpus.

prepare/check-only/help do not load learned weights or initialize CUDA.
evaluate is a separately authorized GPU action after the complete original A
readback. Only two role values in the queried subject's fact sentences change.
Original view0 answers are reused; exactly256 additional answers/model are made.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_relation_bind as original
from scripts import p106b_relation_bind_data as data
from scripts.p106b_shards import ShardWriter, verify

TAG = 'p106b_relation_cf_eval_v1_s1337'
SCHEMA = 'P106B_RELATION_CF_EVAL_V1'
CASE_SCHEMA = 'P106B_RELATION_CF_CASE_V1'
LOCAL = ROOT / 'test_result/evidence/local' / TAG
CORPUS = LOCAL / 'corpus'
EVIDENCE = ROOT / 'test_result/evidence' / TAG
ENDPOINTS = ('parent', 'ce', 'contrast')
EXPECTED_BUNDLES = 128
EXPECTED_RESPONSES = 256
GENERATION_BUDGET = 128
CONTEXT = 1024
CODE = ('scripts/p106b_relation_cf_eval.py', 'scripts/test_p106b_relation_cf_eval.py',
        'scripts/p106b_relation_cf_entry.py', 'scripts/test_p106b_relation_cf_entry.py',
        'tinylm/chat/canonical.py', 'tinylm/chat/serialize.py',
        'tinylm/train/mtp_sft.py', 'scripts/diag_p101a_sft_mtp.py')
Pending = original.PrerequisitePending


def safe(path):
    path = Path(path).absolute()
    if '..' in path.parts:
        raise ValueError('unresolved research path')
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError('research path must stay inside repository') from exc
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError('linked research path')
        if parent == ROOT:
            break
    return path


def digest(path):
    return original.original.digest(safe(path))


def write(path, value):
    path = safe(path)
    body = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode('utf-8')
    if len(body) >= 20_000_000:
        raise ValueError('split research output before20MB')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(body)


def required(path):
    path = safe(path)
    if not path.exists() or (path.is_file() and path.stat().st_size == 0):
        raise Pending('required complete stage not run: ' + str(path))
    if not path.is_file():
        raise ValueError('regular source file required')
    return json.loads(path.read_text(encoding='utf-8'))


def info():
    source = original.info()
    paths = sorted(set(CODE) | set(source['code_sha256']))
    return dict(schema=SCHEMA, tag=TAG, code_sha256={p: digest(ROOT / p) for p in paths},
        original_tag=original.TAG, original_code_sha256=source['code_sha256'],
        source_split='test', inherited_split=True, original_bundles=EXPECTED_BUNDLES,
        independent_fact_graphs=64, additional_responses_per_model=EXPECTED_RESPONSES,
        reused_original_view0_responses_per_model=EXPECTED_RESPONSES,
        context=CONTEXT, generation_budget=GENERATION_BUDGET,
        precision='FP32_MATH', temperature=0., top_k=1, use_cache=True, mtp=False,
        intervention='swap only queried subject role0/role1 values in two exact fact lines',
        training=False, teacher_calls=0, optimizer_updates=0, checkpoint_writes=0,
        adoption='NOT_DECIDED', scope='fixed familiar names/roles; conditional context dependence only')


def canonical_row(messages, gold):
    """Derivative provenance lives outside canonical; no new transform enum."""
    from tinylm.chat.canonical import normalize, validate
    return validate(normalize(dict(messages=copy.deepcopy(messages) + [dict(role='assistant', content=gold)],
                                   meta=dict(supervised_assistant_turns=[1]))))


def original_case(bundle, qi):
    row = data.render(bundle, qi, view=0)
    return dict(id=data.sha(['RELATION', bundle['bundle_id'], 0, qi]), lane='relation',
        language=bundle['language'], family=bundle['family'], group_id=bundle['group_id'],
        bundle_id=bundle['bundle_id'], view=0, question_index=qi,
        messages=row['messages'][:1], gold=bundle['answers'][qi])


def build_case(bundle, qi):
    """Validate the original, then create a different schema without forging it."""
    data.validate_bundle(bundle)
    if bundle['split'] != 'test' or type(qi) is not int or qi not in (0, 1):
        raise ValueError('only original TEST questions0/1 may become evaluation derivatives')
    source = original_case(bundle, qi)
    prompt = original.original.text(source['messages'][0])
    subject = bundle['subject']; language = bundle['language']; family = bundle['family']
    facts = copy.deepcopy(bundle['facts'])
    table = {(s, r): a for s, r, a in facts}
    if len(table) != len(facts) or len(facts) != 4:
        raise ValueError('unique four-row fact lookup required')
    old_values = {r: table[subject, r] for r in (0, 1)}
    for fact in facts:
        if fact[0] == subject:
            fact[2] = old_values[1 - fact[1]]
    changed = [(old, new) for old, new in zip(bundle['facts'], facts) if old != new]
    if len(changed) != 2 or any(a[:2] != b[:2] or a[0] != subject for a, b in changed):
        raise ValueError('only two queried-subject value cells may change')
    names_before = {entity for s, _, a in bundle['facts'] for entity in (s, a)}
    names_after = {entity for s, _, a in facts for entity in (s, a)}
    if names_before != names_after:
        raise ValueError('intervention changed the entity set')
    lines = prompt.split('\n'); rewritten = list(lines); edits = []
    for before, after in changed:
        old_line = data._sentence(family, before, language)
        new_line = data._sentence(family, after, language)
        positions = [i for i, line in enumerate(lines) if line == old_line]
        if len(positions) != 1 or old_line == new_line or new_line in lines:
            raise ValueError('each original fact sentence must occur exactly once')
        index = positions[0]; rewritten[index] = new_line
        edits.append(dict(line=index, original=old_line, derivative=new_line))
    changed_lines = [i for i, (a, b) in enumerate(zip(lines, rewritten)) if a != b]
    if sorted(changed_lines) != sorted(e['line'] for e in edits):
        raise ValueError('question/instructions/distractor or fact ordering changed')
    for fact_index in bundle['fact_order']:
        before = data._sentence(family, bundle['facts'][fact_index], language)
        after = data._sentence(family, facts[fact_index], language)
        if rewritten[lines.index(before)] != after:
            raise ValueError('fact position or unqueried-subject value changed')
    derivative_prompt = '\n'.join(rewritten)
    new_table = {(s, r): a for s, r, a in facts}
    role = bundle['query_order'][qi]
    matches = [a for s, r, a in facts if s == subject and r == role]
    if len(matches) != 1 or new_table[subject, role] != matches[0]:
        raise ValueError('derivative gold is not a unique lookup')
    gold = data.NAMES[language][matches[0]]
    if gold != bundle['answers'][1 - qi] or gold == source['gold']:
        raise ValueError('swapped gold must be the other original role value')
    messages = canonical_row([dict(role='user', content=derivative_prompt)], gold)['messages'][:1]
    result = dict(schema=CASE_SCHEMA, id=data.sha([CASE_SCHEMA, bundle['bundle_id'], qi]),
        lane='relation_cf', language=language, family=family, parent_group_id=bundle['group_id'],
        parent_bundle_id=bundle['bundle_id'], parent_bundle_sha256=bundle['bundle_sha256'],
        inherited_source_split=bundle['split'], split_policy='inherit_parent_TEST_not_rehash',
        derivative_fact_graph_sha256=data.sha([data.SCHEMA, family, sorted(facts)]),
        derivative_facts=facts, fact_order=list(bundle['fact_order']),
        query_order=list(bundle['query_order']), question_index=qi, original_case_id=source['id'],
        original_case=source, original_gold=source['gold'], gold=gold, messages=messages,
        prompt_sha256=data.sha(derivative_prompt), original_prompt_sha256=data.sha(prompt),
        fact_sentence_edits=sorted(edits, key=lambda e: e['line']),
        transformation='queried_subject_two_role_value_swap', training_example=False)
    result['derivative_case_sha256'] = data.sha(result)
    return result


def construct_cases(relations, source_cases, *, expected_bundles=EXPECTED_BUNDLES):
    data.validate_splits(relations)
    bundles = relations['test']
    if len(bundles) != expected_bundles or expected_bundles <= 0:
        raise ValueError('exact nonempty original TEST cohort required')
    source = {c['id']: c for c in source_cases}
    if len(source) != len(source_cases):
        raise ValueError('duplicate original evaluation ID')
    expected_original = [original_case(b, qi) for b in bundles for qi in (0, 1)]
    selected = [c for c in source_cases if c.get('lane') == 'relation' and c.get('view') == 0]
    if ({c['id']: c for c in selected} != {c['id']: c for c in expected_original}
            or any(source.get(c['id']) != c for c in expected_original)):
        raise ValueError('original view0 question IDs/prompts/golds do not match frozen evaluation_cases')
    cases = [build_case(b, qi) for b in bundles for qi in (0, 1)]
    training_graphs = {b['group_id'] for b in relations['train']}
    if training_graphs & {c['derivative_fact_graph_sha256'] for c in cases}:
        raise ValueError('derivative full fact graph overlaps original TRAIN')
    test_graphs = {b['group_id'] for b in bundles}
    if test_graphs & {c['derivative_fact_graph_sha256'] for c in cases}:
        raise ValueError('derivative full fact graph overlaps original TEST; intervention pairs are not independent')
    groups = defaultdict(list); derivatives = defaultdict(set)
    for case in cases:
        groups[case['parent_group_id']].append((case['language'], case['question_index']))
        derivatives[case['derivative_fact_graph_sha256']].add(case['parent_group_id'])
    if (len(groups) != expected_bundles // 2 or len(derivatives) != len(groups)
            or any(sorted(v) != [('en', 0), ('en', 1), ('ko', 0), ('ko', 1)] for v in groups.values())
            or any(len(v) != 1 for v in derivatives.values())
            or len({c['id'] for c in cases}) != len(cases)):
        raise ValueError('complete bilingual independent parent/derivative graphs required')
    return cases


def encoding_proof(cases, tok):
    from tinylm.chat.serialize import serialize
    entries = []
    for case in cases:
        if [m['role'] for m in case['messages']] != ['user']:
            raise ValueError('candidate-free single-user generation input required')
        row = canonical_row(case['messages'], case['gold'])
        rec = data.complete_record(row, tok)
        old = case['original_case']
        old_rec = data.complete_record(canonical_row(old['messages'], old['gold']), tok)
        prompt = serialize(dict(messages=case['messages']), 'chatml', add_generation_prompt=True)
        prefix = tok.encode(prompt).ids
        if not prefix or len(prefix) + GENERATION_BUDGET > CONTEXT:
            raise ValueError('complete generation prefix plus128 exceeds1024')
        entries.append(dict(id=case['id'], original_case_id=case['original_case_id'],
            prompt_sha256=data.sha(prompt), prompt_ids_sha256=data.sha(prefix),
            prompt_tokens=len(prefix), derivative_record_sha256=original.record_identity(rec),
            original_record_sha256=original.record_identity(old_rec)))
    if not entries:
        raise ValueError('empty intervention cohort forbidden')
    return dict(cases_sha256=data.sha(cases), entries=entries, entries_sha256=data.sha(entries),
        responses=len(entries), max_prompt_tokens=max(e['prompt_tokens'] for e in entries),
        generation_budget=GENERATION_BUDGET, context=CONTEXT, candidates_in_generation=False,
        complete_content_and_eot_coverage=True)


def source_context():
    """Source/tokenizer only; callable before A finishes and never opens weights."""
    from tokenizers import Tokenizer
    frozen, rows, relations = original.read_prepared()
    if digest(original.original.TOKENIZER) != original.original.TOK_SHA:
        raise ValueError('original tokenizer changed')
    tok = Tokenizer.from_file(str(original.original.TOKENIZER))
    source_cases = original.evaluation_cases(rows, relations)
    if len(source_cases) != 990:
        raise ValueError('original990-response evaluation contract changed')
    if original.evaluation_input_proof(source_cases, tok) != frozen['evaluation_input_proof']:
        raise ValueError('original prompt/token proof differs')
    cases = construct_cases(relations, source_cases)
    proof = encoding_proof(cases, tok)
    source = dict(original_corpus_report_sha256=digest(original.CORPUS / 'report.json'),
        original_cpu_contract_sha256=digest(original.EVIDENCE / 'cpu_contract.json'),
        original_cases_sha256=data.sha(source_cases), original_code_sha256=original.info()['code_sha256'],
        original_test_bundles_sha256=data.sha(relations['test']),
        original_train_graphs_sha256=data.sha(sorted({b['group_id'] for b in relations['train']})),
        tokenizer_sha256=original.original.TOK_SHA)
    return dict(frozen=frozen, relations=relations, source_cases=source_cases,
                cases=cases, proof=proof, source=source, tok=tok)


def read_shards(directory, manifest, stem, expected_rows):
    directory = safe(directory)
    if not isinstance(manifest, dict):
        raise ValueError('source-bound shard manifest required')
    count = manifest.get('rows')
    if type(count) is not int:
        raise ValueError('integer shard row count required')
    if count < expected_rows:
        raise Pending('empty/partial raw cohort; never fill missing answers with zeros')
    if count != expected_rows or expected_rows <= 0:
        raise ValueError('unexpected raw cohort row count')
    shards = manifest.get('shards')
    if not isinstance(shards, list) or not shards:
        raise ValueError('nonempty shard list required')
    for i, spec in enumerate(shards):
        if spec.get('path') != f'{stem}_{i:06d}.jsonl' or spec.get('bytes', 20_000_000) >= 20_000_000:
            raise ValueError('exact shard stem/order and less-than20MB required')
        safe(directory / spec['path'])
    verify(directory, manifest)
    output = []
    for spec in shards:
        with (directory / spec['path']).open(encoding='utf-8') as stream:
            output.extend(json.loads(line) for line in stream)
    if len(output) != expected_rows:
        raise ValueError('decoded shard rows differ')
    return output


def prepare():
    for path in (LOCAL, EVIDENCE):
        safe(path)
        if path.exists():
            raise FileExistsError('old intervention namespace preserved: ' + str(path))
    context = source_context(); metadata = info()
    import torch
    if torch.cuda.is_initialized():
        raise ValueError('source-only preparation must not initialize CUDA')
    CORPUS.mkdir(parents=True, exist_ok=False)
    writer = ShardWriter(CORPUS, 'cases', limit=19_999_999)
    for case in context['cases']:
        writer.append(case)
    lineage = dict(tag=TAG, source=context['source'], purpose='EVALUATION_ONLY_NO_TRAIN')
    manifest = writer.close(lineage=lineage); verify(CORPUS, manifest)
    report = dict(metadata, status='CPU_CF_PREPARED_MODEL_NOT_RUN', source=context['source'],
        case_manifest=manifest, case_manifest_sha256=digest(CORPUS / 'cases_shards_manifest.json'),
        encoding_proof=context['proof'], expected_additional_responses=EXPECTED_RESPONSES,
        train_full_graph_overlap=0, model_loaded=False, model_forward=False, cuda_initialized=False,
        source_immutable=True, prepared_at=datetime.now(timezone.utc).isoformat())
    write(CORPUS / 'report.json', report)
    write(EVIDENCE / 'cpu_contract.json', public_contract(report))
    print('[RELATION_CF_PREPARED] evaluation-only256 additional cases/model; model/GPU NOT_RUN', flush=True)
    return 0


def public_contract(report):
    summary = {k: v for k, v in report.items() if k not in ('case_manifest', 'encoding_proof')}
    summary.update(corpus_report_sha256=digest(CORPUS / 'report.json'),
                   cases_sha256=report['encoding_proof']['cases_sha256'],
                   encoding_proof_sha256=data.sha(report['encoding_proof']))
    return summary


def read_prepared():
    report = required(CORPUS / 'report.json')
    if report.get('status') != 'CPU_CF_PREPARED_MODEL_NOT_RUN':
        raise Pending('complete CPU intervention preparation required')
    if any(report.get(k) != v for k, v in info().items()):
        raise ValueError('prepared intervention code/contract differs')
    context = source_context()
    if report.get('source') != context['source'] or report.get('encoding_proof') != context['proof']:
        raise ValueError('frozen original/derivative source or actual token coverage changed')
    path = CORPUS / 'cases_shards_manifest.json'
    if digest(path) != report.get('case_manifest_sha256') or required(path) != report.get('case_manifest'):
        raise ValueError('prepared case manifest changed')
    expected_lineage = dict(tag=TAG, source=context['source'], purpose='EVALUATION_ONLY_NO_TRAIN')
    if report['case_manifest'].get('lineage') != expected_lineage:
        raise ValueError('prepared source/split lineage changed')
    if read_shards(CORPUS, report['case_manifest'], 'cases', EXPECTED_RESPONSES) != context['cases']:
        raise ValueError('derivative prompt/gold/source case changed')
    if required(EVIDENCE / 'cpu_contract.json') != public_contract(report):
        raise ValueError('public CPU proof differs from private frozen corpus')
    context['prepared_report_sha256'] = digest(CORPUS / 'report.json')
    return context


def validate_generation(answer, meta, messages, tok):
    from tinylm.chat.serialize import serialize
    if not isinstance(answer, str) or not isinstance(meta, dict):
        raise ValueError('actual answer and generation metadata required')
    prompt = serialize(dict(messages=messages), 'chatml', add_generation_prompt=True)
    ids = tok.encode(prompt).ids
    expected = dict(precision='FP32_MATH', temperature=0., top_k=1, use_cache=True, mtp=False,
        prompt_sha256=data.sha(prompt), prompt_ids_sha256=data.sha(ids), prompt_tokens=len(ids),
        candidate_answers_supplied=False, max_new=GENERATION_BUDGET,
        stop_token_sequences=[[tok.token_to_id('<|im_end|>')]])
    if (any(meta.get(k) != v for k, v in expected.items())
            or type(meta.get('generated_tokens')) is not int
            or not 1 <= meta['generated_tokens'] <= GENERATION_BUDGET
            or len(ids) + GENERATION_BUDGET > CONTEXT
            or meta.get('finish_reason') not in ('EOS', 'STOP_SEQUENCE', 'MAX_NEW',
                                                'MAX_NEW_EOS_DISABLED', 'EOS_UNAVAILABLE')
            or not isinstance(meta.get('generated_ids_sha256'), str)
            or re.fullmatch(r'[0-9A-F]{64}', meta['generated_ids_sha256']) is None):
        raise ValueError('exact candidate-free FP32 greedy prompt/termination receipt required')
    if ((meta['finish_reason'] == 'STOP_SEQUENCE')
            != (meta.get('matched_stop_sequence') == [tok.token_to_id('<|im_end|>')])):
        raise ValueError('terminal EOT receipt and finish reason differ')
    if (meta['finish_reason'] in ('MAX_NEW', 'MAX_NEW_EOS_DISABLED', 'EOS_UNAVAILABLE')
            and meta['generated_tokens'] != GENERATION_BUDGET):
        raise ValueError('generation-budget exhaustion receipt differs')


def original_results(context):
    """Revalidate all original raw/manifests/readback before any GPU admission."""
    path = original.EVIDENCE / 'readback.json'; readback = required(path)
    if readback.get('status') != 'RAW_READBACK_COMPLETE_NO_AUTOMATIC_ADOPTION':
        raise Pending('original A raw readback has not completed')
    source_cases = context['source_cases']; cases_sha = data.sha(source_cases)
    code = context['source']['original_code_sha256']; corpus = context['source']['original_corpus_report_sha256']
    if (readback.get('tag') != original.TAG or readback.get('errors') != 0
            or readback.get('code_sha256') != code or readback.get('cases_sha256') != cases_sha
            or readback.get('learning_seeds') != 1 or readback.get('model_training') is not False
            or set(readback.get('source_reports_sha256', {})) != set(ENDPOINTS)):
        raise ValueError('original readback source/code or endpoint set differs')
    identities = {}; reports = {}; outputs = {}; report_hashes = {}; answer_hashes = {}; rank_hashes = {}
    for label in ENDPOINTS:
        identity = original.endpoint_identity(label)
        report_path = original.EVIDENCE / ('evaluate_' + label) / 'report.json'
        report = required(report_path)
        if report.get('status') != 'ACTUAL_FIRST_ANSWERS_RECORDED':
            raise Pending('original endpoint evaluation incomplete: ' + label)
        original.validate_evaluation_report(report, identity, cases_sha, corpus, code)
        if (report.get('model_training') is not False or report.get('weights_changed') is not False
                or report.get('checkpoints_written') != 0):
            raise ValueError('original evaluation mutation receipt differs')
        local = original.LOCAL / ('evaluate_' + label)
        for stem, field in (('answers', 'answer'), ('rank', 'rank')):
            manifest_path = local / (stem + '_shards_manifest.json')
            if (digest(manifest_path) != report.get(field + '_manifest_sha256')
                    or required(manifest_path) != report[field + '_manifest']):
                raise ValueError('original raw manifest/report hash differs')
        answers = read_shards(local, report['answer_manifest'], 'answers', len(source_cases))
        for event in answers:
            if not isinstance(event.get('case'), dict):
                raise ValueError('original case binding absent')
            validate_generation(event.get('answer'), event.get('generation'), event['case']['messages'], context['tok'])
        summary = original.summarize_answers(answers, source_cases)
        rank = read_shards(local, report['rank_manifest'], 'rank', len(context['relations']['test']))
        rank_summary = original.summarize_ranks(rank, context['relations']['test'],
            original.rank_specifications(context['relations']['test'], context['tok']))
        if summary != report.get('summary') or rank_summary != report.get('rank_summary'):
            raise ValueError('original raw answer/rank recount differs')
        report_hashes[label] = digest(report_path)
        if report_hashes[label] != readback['source_reports_sha256'][label]:
            raise ValueError('original readback references different endpoint report')
        identities[label] = identity; reports[label] = report; outputs[label] = answers
        answer_hashes[label] = report['answer_manifest_sha256']; rank_hashes[label] = report['rank_manifest_sha256']
    if ({k: reports[k]['summary'] for k in ENDPOINTS} != readback.get('summaries')
            or original.paired_relation(outputs['ce'], outputs['contrast'], source_cases) != readback.get('contrast_minus_ce')):
        raise ValueError('original readback summary or paired graph recount changed')
    binding = dict(original_readback_sha256=digest(path), original_source=context['source'],
        source_reports_sha256=report_hashes, answer_manifest_sha256=answer_hashes,
        rank_manifest_sha256=rank_hashes, endpoint_identities=identities)
    return dict(binding=binding, outputs=outputs, identities=identities)


def lineage(context, originals, label):
    if label not in ENDPOINTS:
        raise ValueError('explicit registered endpoint required')
    return dict(tag=TAG, **originals['identities'][label],
        prepared_report_sha256=context['prepared_report_sha256'],
        source_binding_sha256=data.sha(originals['binding']))


def summarize(events, cases, original_events, expected_lineage, tok):
    expected = {c['id']: c for c in cases}; seen = set()
    source = {e['id']: e for e in original_events}
    if not expected or len(expected) != len(cases) or len(source) != len(original_events):
        raise ValueError('nonempty unique intervention/original IDs required')
    counts = defaultdict(Counter); endings = defaultdict(Counter); graphs = defaultdict(list); bilingual = defaultdict(list)
    for event in events:
        ident = event.get('id'); case = expected.get(ident)
        if case is None or ident in seen or event.get('case') != case or event.get('lineage') != expected_lineage:
            raise ValueError('unknown/duplicate/tampered/other-endpoint intervention answer')
        old = source.get(case['original_case_id'])
        if old is None:
            raise Pending('original same-question view0 answer missing')
        if old.get('case') != case['original_case']:
            raise ValueError('original question/prompt/gold mapping changed')
        validate_generation(event.get('answer'), event.get('generation'), case['messages'], tok)
        validate_generation(old.get('answer'), old.get('generation'), old['case']['messages'], tok)
        old_answer = data.exact_answer(old['answer']); answer = data.exact_answer(event['answer'])
        correct_old = old_answer == data.exact_answer(case['original_gold'])
        correct_new = answer == data.exact_answer(case['gold'])
        stop_old = old['generation']['finish_reason'] == 'STOP_SEQUENCE'
        stop_new = event['generation']['finish_reason'] == 'STOP_SEQUENCE'
        metrics = dict(questions=1, original_exact=int(correct_old), swapped_exact=int(correct_new),
            original_and_swapped_exact=int(correct_old and correct_new),
            answer_changed=int(old_answer != answer),
            retained_original_gold=int(answer == data.exact_answer(case['original_gold'])),
            repeated_actual_original_answer=int(answer == old_answer),
            original_stopped=int(stop_old), swapped_stopped=int(stop_new),
            original_and_swapped_exact_and_stopped=int(correct_old and correct_new and stop_old and stop_new),
            swapped_empty=int(not answer), swapped_generated_tokens=event['generation']['generated_tokens'])
        for key in (case['language'], case['language'] + '|' + case['family']):
            counts[key].update(metrics)
        endings[case['language'] + '|' + old['generation']['finish_reason'] + '|' + event['generation']['finish_reason']].update(metrics)
        values = (case['question_index'], correct_old, correct_new, old_answer != answer)
        graphs[case['language'], case['parent_group_id']].append(values)
        bilingual[case['parent_group_id']].append((case['language'], *values))
        seen.add(ident)
    if seen != set(expected):
        raise Pending('empty/partial intervention evaluation; no zero imputation')
    graph_counts = defaultdict(Counter)
    for (language, _), values in graphs.items():
        if sorted(v[0] for v in values) != [0, 1]:
            raise ValueError('both same-graph questions required')
        graph_counts[language].update(graphs=1, original_both_exact=int(all(v[1] for v in values)),
            swapped_both_exact=int(all(v[2] for v in values)),
            original_and_swapped_all_four_exact=int(all(v[1] and v[2] for v in values)),
            both_answers_changed=int(all(v[3] for v in values)))
    bilingual_all = 0
    for values in bilingual.values():
        if sorted((v[0], v[1]) for v in values) != [('en', 0), ('en', 1), ('ko', 0), ('ko', 1)]:
            raise ValueError('complete bilingual graph responses required')
        bilingual_all += int(all(v[2] and v[3] for v in values))
    return dict(additional_responses=len(seen), reused_original_responses=len(seen),
        counts={k: dict(v) for k, v in sorted(counts.items())},
        by_original_and_swapped_finish={k: dict(v) for k, v in sorted(endings.items())},
        paired_graphs={k: dict(v) for k, v in sorted(graph_counts.items())},
        independent_fact_graphs=len(bilingual), bilingual_all_eight_exact=bilingual_all,
        primary='original and swapped answers both exact; change alone is not success',
        original_and_swapped_are_not_independent=True, learning_seeds=1, adoption='NOT_DECIDED')


def validate_report(report, context, originals, label):
    if report.get('status') != 'ACTUAL_CF_FIRST_ANSWERS_RECORDED':
        raise Pending('complete intervention evaluation required: ' + label)
    expected = lineage(context, originals, label)
    if (any(report.get(k) != v for k, v in info().items())
            or report.get('endpoint') != label or report.get('lineage') != expected
            or report.get('source_binding') != originals['binding']
            or report.get('cases_sha256') != data.sha(context['cases'])
            or report.get('core_before') != expected['expected_core_sha256']
            or report.get('core_after') != expected['expected_core_sha256']
            or report.get('answer_manifest', {}).get('lineage') != expected
            or report.get('model_training') is not False or report.get('weights_changed') is not False
            or report.get('checkpoints_written') != 0):
        raise ValueError('intervention source/code/endpoint/body/raw lineage differs')


def evaluate(seconds, model=None):
    context = read_prepared(); originals = original_results(context)
    selected = (model,) if model is not None else ENDPOINTS
    targets = []
    for label in selected:
        if label not in ENDPOINTS:
            raise ValueError('registered model required')
        target = safe(EVIDENCE / ('evaluate_' + label)); local = safe(LOCAL / ('evaluate_' + label))
        if target.exists() or local.exists():
            raise FileExistsError('old intervention evaluation output preserved')
        targets.append((label, target, local))
    # No GPU admission or weight loading is reachable before the complete A check.
    import gc
    import torch
    from tinylm.infer.generate import _strip
    from scripts import diag_p101a_sft_mtp as runtime
    from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
    idle_before_gpu(); began = time.perf_counter()
    with wall_limit(seconds):
        for label, target, local in targets:
            target.mkdir(parents=True, exist_ok=False); local.mkdir(parents=True, exist_ok=False)
            writer = ShardWriter(local, 'answers', limit=19_999_999); events = []; base = None
            try:
                torch, base, cfg, tok, _ = original.load_parent()
                identity = originals['identities'][label]
                if label != 'parent':
                    saved = torch.load(safe(ROOT / identity['checkpoint']), map_location='cpu', weights_only=True)
                    if (saved.get('relation_course') != dict(tag=original.TAG, arm=label, epoch=4,
                                                            weight=original.WEIGHTS[label])
                            or saved.get('tokenizer_sha256') != original.original.TOK_SHA):
                        raise ValueError('original child checkpoint lineage changed')
                    base.load_state_dict(_strip(saved['model']), strict=True); del saved
                if encoding_proof(context['cases'], tok) != context['proof']:
                    raise ValueError('runtime tokenizer/prefix/coverage differs from CPU contract')
                before = runtime.state_fingerprint(base)
                if before != identity['expected_core_sha256']:
                    raise ValueError('actual body differs from original endpoint')
                if cfg.max_seq_len != CONTEXT:
                    raise ValueError('original1024 context required')
                base = base.cuda(); base.eval(); base.freeze_quant()
                torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
                bound = lineage(context, originals, label)
                with torch.no_grad():
                    for i, case in enumerate(context['cases']):
                        answer, meta = original.emit_answer(base, cfg, tok, case['messages'])
                        validate_generation(answer, meta, case['messages'], tok)
                        event = dict(id=case['id'], case=case, answer=answer, generation=meta, lineage=bound)
                        writer.append(event); events.append(event)
                        if (i + 1) % 64 == 0:
                            print('[RELATION_CF_PROGRESS] ' + json.dumps(dict(endpoint=label,
                                additional_responses=i + 1, expected=EXPECTED_RESPONSES)), flush=True)
                base.clear_quant(); after = runtime.state_fingerprint(base)
                if before != after:
                    raise ValueError('intervention evaluation changed original weights')
                summary = summarize(events, context['cases'], originals['outputs'][label], bound, tok)
                manifest = writer.close(lineage=bound); verify(local, manifest)
                report = dict(info(), status='ACTUAL_CF_FIRST_ANSWERS_RECORDED', endpoint=label,
                    lineage=bound, source_binding=originals['binding'], cases_sha256=data.sha(context['cases']),
                    core_before=before, core_after=after, summary=summary, answer_manifest=manifest,
                    answer_manifest_sha256=digest(local / 'answers_shards_manifest.json'),
                    model_training=False, weights_changed=False, checkpoints_written=0,
                    whole_seconds_since_start=time.perf_counter() - began)
                validate_report(report, context, originals, label); write(target / 'report.json', report)
            except BaseException as exc:
                status, code = original.failure_status(exc)
                write(target / 'error.json', dict(status=status, exit_code=code, endpoint=label,
                    exception=type(exc).__name__, message=str(exc), partial_raw_preserved=True))
                raise
            finally:
                del base
                gc.collect(); torch.cuda.empty_cache()
    print('[RELATION_CF_FINAL] additional first answers saved; readback required; no automatic adoption', flush=True)
    return 0


def readback(model=None):
    context = read_prepared(); originals = original_results(context)
    selected = (model,) if model is not None else ENDPOINTS
    summaries = {}; hashes = {}
    for label in selected:
        if label not in ENDPOINTS:
            raise ValueError('registered endpoint required')
        path = EVIDENCE / ('evaluate_' + label) / 'report.json'; report = required(path)
        validate_report(report, context, originals, label)
        local = LOCAL / ('evaluate_' + label); manifest_path = local / 'answers_shards_manifest.json'
        if digest(manifest_path) != report.get('answer_manifest_sha256') or required(manifest_path) != report.get('answer_manifest'):
            raise ValueError('intervention manifest/report changed')
        events = read_shards(local, report['answer_manifest'], 'answers', EXPECTED_RESPONSES)
        summary = summarize(events, context['cases'], originals['outputs'][label],
                            lineage(context, originals, label), context['tok'])
        if summary != report.get('summary'):
            raise ValueError('raw intervention/original paired recount differs')
        summaries[label] = summary; hashes[label] = digest(path)
    result = dict(info(), status='CF_RAW_READBACK_COMPLETE_NO_AUTOMATIC_ADOPTION',
        source_binding=originals['binding'], cases_sha256=data.sha(context['cases']),
        source_reports_sha256=hashes, summaries=summaries, errors=0,
        model_loaded=False, model_training=False, semantic_adoption='USER_REVIEW_REQUIRED')
    write(EVIDENCE / ('readback' + (('_' + model) if model else '') + '.json'), result)
    print('[RELATION_CF_READBACK] ' + json.dumps(result, ensure_ascii=False), flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('prepare', 'evaluate', 'readback'), required=True)
    parser.add_argument('--model', choices=ENDPOINTS)
    parser.add_argument('--max-wall-sec', type=int, default=3600)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true'); action.add_argument('--check-only', action='store_true')
    args = parser.parse_args(argv)
    if not 60 <= args.max_wall_sec <= 21600:
        parser.error('bounded60..21600 wall seconds required')
    if args.mode == 'prepare' and args.model is not None:
        parser.error('preparation fixes all source-only cases before endpoint selection')
    if args.check_only:
        print('[RELATION_CF_CHECK_ONLY] ' + json.dumps(info(), ensure_ascii=False)); return 0
    try:
        if args.mode == 'prepare':
            return prepare()
        if args.mode == 'readback':
            return readback(args.model)
        return evaluate(args.max_wall_sec, args.model)
    except KeyboardInterrupt:
        print('[RELATION_CF_FINAL] INTERRUPTED130; partial evidence preserved', flush=True); return 130
    except Exception as exc:
        status, code = original.failure_status(exc)
        if code == 9:
            import traceback
            traceback.print_exc()
        print('[RELATION_CF_FINAL] ' + status + str(code) + ': ' + str(exc), flush=True)
        return code


if __name__ == '__main__':
    raise SystemExit(main())
