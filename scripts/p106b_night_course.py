"""Write-once overnight grounded QA + explicit balanced replay contract."""
from __future__ import annotations
from bisect import bisect_left
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_night_qa_data as data
from scripts import p106b_night_learning as learning
from scripts.p106b_shards import ShardWriter, verify

TAG = 'p106b_night_grounded_v2_s1337'
CORPUS = ROOT / 'HF/sft_ready' / TAG / 'corpus'
EVIDENCE = ROOT / 'test_result/evidence' / TAG
SCHEMA = 'P106B_NIGHT_GROUNDED_COURSE_V2'
ARMS = ('ce', 'consistent')
WEIGHTS = dict(ce=0., consistent=.05)
PARENT = ROOT / 'runs/ckpt/m100s10_ko-en_evidencerecovery_dense_chat32_p106b_evidence_recovery_v1_s1337_evidence_recovery.pt'
PARENT_SHA = 'E9707AA2ABB55054DA226A6303A0EEAD8BA0B653029E24AFAD2A63D86E729E42'
DEADLINE = datetime(2026, 10, 17, 1, 0, tzinfo=timezone.utc)
TRAIN_STOP = datetime(2026, 10, 17, 0, 0, tzinfo=timezone.utc)
NATIVE = ROOT / 'data_cache/ko-en_601000000_chat32'
CODE = ('scripts/p106b_night_qa_data.py', 'scripts/test_p106b_night_qa_data.py',
        'scripts/p106b_night_learning.py', 'scripts/test_p106b_night_learning.py',
        'scripts/p106b_night_course.py', 'scripts/test_p106b_night_course.py',
        'scripts/diag_p106b_night_train.py', 'scripts/test_p106b_night_train.py',
        'tinylm/train/mtp_sft.py', 'tinylm/model/transformer.py',
        'tinylm/data/sft.py', 'tinylm/chat/serialize.py',
        'scripts/p106b_relation_fields.py', 'scripts/p106b_native_windows.py',
        'scripts/diag_p101a_sft_mtp.py', 'scripts/diag_p106b_evidence_recovery_course.py')


def write(path, value):
    body = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if len(body.encode('utf-8')) > 20_000_000:
        raise ValueError('20MB evidence limit')
    path = Path(path)
    for parent in (path.parent, *path.parents):
        if parent.is_symlink(): raise ValueError('linked output ancestor')
        if parent == ROOT: break
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream: stream.write(body)


def required(path):
    if not data.regular(path): raise FileNotFoundError(str(path))
    return json.loads(Path(path).read_text(encoding='utf-8'))


def info():
    return dict(schema=SCHEMA, tag=TAG, arms=list(ARMS), weights=WEIGHTS,
        code_sha256={p: data.digest(ROOT / p) for p in CODE}, seed=1337,
        tokenizer_sha256=data.TOK_SHA, parent_sha256=PARENT_SHA,
        micro_bs=8, accum=16, seq=1024, grad_checkpoint=True, compile='default',
        lr=5e-5, muon_lr=2e-4, weight_decay=0., epochs=4, updates=640,
        natural_pairs=8192, natural_ce_rows=16384, replay_rows=4096,
        sft_rows_per_pass=20480, native_targets_per_update=8192,
        binary_aux=False, fact_aux=False, mtp=False, teacher_calls=0,
        comparison='same two-view CE, replay, init/order/optimizer; only SymKL lambda differs',
        native_weight=1., kl_scope='same student, aligned content tokens, EOT excluded',
        checkpoint_policy='one final weight-only checkpoint per arm; cost writes none',
        deadline_utc=DEADLINE.isoformat(), train_stop_utc=TRAIN_STOP.isoformat(),
        formal_train_ready=False, semantic_truth='source spans and code facts; no full semantic review')


def stratified(rows, count, fields):
    """Deterministic equal allocation; insufficient cells do not repeat rows."""
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row['meta'][f] for f in fields)].append(row)
    if not groups or count % len(groups): raise ValueError('whole balanced cells required')
    n = count // len(groups); result = []
    for key in sorted(groups, key=repr):
        values = sorted(groups[key], key=lambda row: data.sha([1337, row]))
        if len(values) < n: raise ValueError('insufficient replay cell: ' + repr(key))
        result.extend(values[:n])
    if len({data.sha(row) for row in result}) != count:
        raise ValueError('replay duplicate row')
    return result


def choose_replay(recovery, role):
    role_rows = [x for x in role if x['meta']['kind'] == 'role_bridge']
    evidence = [x for x in recovery if x['meta']['kind'] == 'evidence_recovery']
    fiction = [x for x in recovery if x['meta']['kind'] == 'fictional_relation_fields']
    code = [x for x in recovery if x['meta']['kind'] not in
            ('public_qa', 'fictional_relation_fields', 'role_bridge', 'evidence_recovery')]
    result = (stratified(role_rows, 2048, ('language', 'view'))
              + stratified(evidence, 1024, ('language', 'family', 'condition'))
              + stratified(code, 768, ('language', 'kind'))
              + stratified(fiction, 256, ('language', 'scenario')))
    if Counter(x['meta']['language'] for x in result) != {'ko': 2048, 'en': 2048}:
        raise ValueError('balanced replay languages required')
    return result


def choose_native(length, count, excluded):
    """New disjoint train windows, also nonoverlapping all declared old windows."""
    previous = sorted(set(excluded))
    def clear(offset):
        i = bisect_left(previous, offset)
        return all(abs(p - offset) >= 1025 for p in previous[max(0, i - 1):i + 1])
    offsets = [i for i in range(0, length - 1024, 1025) if clear(i)]
    random.Random(20261016).shuffle(offsets)
    if len(offsets) < count: raise ValueError('new native train supply exhausted')
    return offsets[:count]


def stream(manifest):
    verify(CORPUS, manifest)
    for spec in manifest['shards']:
        for line in (CORPUS / spec['path']).read_text(encoding='utf-8').splitlines():
            yield json.loads(line)


def put(stem, rows):
    writer = ShardWriter(CORPUS, stem)
    for row in rows: writer.append(row)
    manifest = writer.close(lineage=dict(tag=TAG, schema=SCHEMA, teacher_calls=0))
    verify(CORPUS, manifest)
    return manifest


def records(pairs, replay, tok):
    from tinylm.train.mtp_sft import encode_record
    from scripts.p106b_relation_fields import encode
    natural = [[encode_record(p['views'][str(v)], tok) for v in (0, 1)] for p in pairs]
    controls = [encode(row, tok)[0] for row in replay]
    for pair, pair_records in zip(pairs, natural):
        learning.paired_positions(pair_records, tok.token_to_id('<|im_end|>'))
        for view, rec in enumerate(pair_records):
            e = pair['encoding'][str(view)]
            if rec.x_tokens != e['x_tokens'] or rec.targets != e['assistant_targets']:
                raise ValueError('frozen natural actual consumer differs')
            positions = [i for i, y in enumerate(rec.y) if y != -100]
            if positions[0] != e['prompt_tokens'] - 1:
                raise ValueError('first causal predictor shifted incorrectly')
    return natural, controls


def counts(pairs, replay, tok):
    natural, controls = records(pairs, replay, tok)
    lanes = defaultdict(Counter)
    for values in natural:
        for rec in values:
            lanes['natural'].update(rows=1, x_tokens=rec.x_tokens, assistant_targets=rec.targets)
    for row, rec in zip(replay, controls):
        lanes[row['meta']['kind']].update(rows=1, x_tokens=rec.x_tokens, assistant_targets=rec.targets)
    total = Counter()
    for value in lanes.values(): total.update(value)
    return dict(lanes=dict(lanes), per_pass=dict(total),
        natural_content_targets=sum(pair[0].targets - 1 for pair in natural),
        expected_four_pass={k: 4 * v for k, v in total.items()},
        native_targets_four_pass=640 * 8192, padded_sft_slots_four_pass=640 * 8 * 16 * 1024)


def freeze():
    from tokenizers import Tokenizer
    from scripts import diag_p106b_evidence_recovery_course as old
    import numpy as np
    import torch
    if CORPUS.parent.exists() or EVIDENCE.exists(): raise FileExistsError('preserve old namespace')
    if datetime.now(timezone.utc) >= TRAIN_STOP: raise ValueError('overnight preparation deadline')
    if data.digest(PARENT) != PARENT_SHA: raise ValueError('E970 parent changed')
    tok = Tokenizer.from_file(str(data.TOKENIZER))
    pairs, source = data.collect_natural(tok)
    prior, rows, _ = old.read_course(); old_report, role_rows, _ = old.old.read_course()
    replay = choose_replay(rows['evidence_recovery_train0'], role_rows['raw_role_train0'])
    exposure = counts(pairs['train'], replay, tok)
    if exposure['per_pass']['rows'] != 20480: raise ValueError('exact planned pass rows')
    steps = len(learning.schedule(len(pairs['train']), len(replay), 0))
    if steps != 160: raise ValueError('exact planned160 updates per pass')
    excluded = set(prior['native_train_offsets']) | set(old_report['native_train_offsets'])
    prior_refs = []
    for desc in prior['native_exclusion_reports'] + old_report['native_exclusion_reports']:
        path = ROOT / desc['path']
        if data.digest(path) != desc['sha256']: raise ValueError('native prior contract changed')
        previous = required(path); excluded.update(previous['native_train_offsets'])
        prior_refs.append(desc)
    tokens = np.memmap(NATIVE / 'train.bin', dtype=np.uint16, mode='r')
    native = dict(native_access='INDEXED_TRAIN_ONLY', native_train_file='data_cache/ko-en_601000000_chat32/train.bin',
        native_train_offsets=choose_native(len(tokens), 640 * 8, excluded),
        native_train_sha256=prior['native_train_sha256'], native_val_sha256=prior['native_val_sha256'])
    if torch.cuda.is_initialized(): raise ValueError('CPU-only source freeze initialized CUDA')
    CORPUS.mkdir(parents=True, exist_ok=False)
    manifests = {s: put('natural_' + s, values) for s, values in pairs.items()}
    manifests['replay'] = put('replay', replay)
    result = dict(info(), status='FROZEN', manifests=manifests, source_contract=source,
        exposure=exposure, native_exclusion_reports=prior_refs, **native,
        upstream_course=dict(path=str(old.CORPUS.relative_to(ROOT)), sha256=data.digest(old.CORPUS / 'report.json')),
        role_course=dict(path=str(old.old.CORPUS.relative_to(ROOT)), sha256=data.digest(old.old.CORPUS / 'report.json')),
        replay_literal_sha256=data.sha(replay), teacher_generation=False, model_loaded=False,
        cuda_initialized=torch.cuda.is_initialized(), updated_at=datetime.now(timezone.utc).isoformat())
    write(CORPUS / 'report.json', result); write(EVIDENCE / 'corpus_report.json', result)
    print('[NIGHT_CORPUS] ' + json.dumps(dict(status='FROZEN', counts=exposure,
        selected_sha256=source['selected_roots_sha256']), ensure_ascii=False), flush=True)
    return 0


def read_night_course():
    r = required(CORPUS / 'report.json')
    if r['status'] != 'FROZEN' or r['code_sha256'] != info()['code_sha256']:
        raise ValueError('frozen course/source-code contract changed')
    for path, digest in ((PARENT, PARENT_SHA), (data.TOKENIZER, data.TOK_SHA),
                         (NATIVE / 'train.bin', r['native_train_sha256']),
                         (NATIVE / 'val.bin', r['native_val_sha256'])):
        if data.digest(path) != digest: raise ValueError('read-only parent/token/cache identity differs')
    rows = {s: list(stream(m)) for s, m in r['manifests'].items()}
    return r, rows
