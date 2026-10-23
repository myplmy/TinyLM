#!/usr/bin/env python3
"""Thin, explicit V4 experimental consumer. No model on import/check-only.

The pinned original train/evaluate function bodies are called, never copied or
AST-rewritten. Only prepared data_cache V4 is eligible. Preparation is not
quality admission. Real tokenizer/GPU execution belongs to the orchestrator.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter
from contextlib import contextmanager
import copy
from datetime import datetime, timezone
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
SCRIPT = 'scripts/diag_p101a_supervision_v4.py'
TEST = 'scripts/test_p101a_supervision_v4.py'
TAG = 'p101a_sft_mtp_supervision_v4_s1337'
CORPUS = 'data_cache/' + TAG + '/corpus'
BASE = 'test_result/evidence/' + TAG
CONTRACT = BASE + '/cpu_contract/report.json'
REPORT_SHA = '33A7FF08EDEFBAB6C96DA49C52500921D6FF21426364B1803456F263883B0C01'
AUDIT_SHA = 'C91639CDDFD398F20D2F1D52E5BB0DF86AAAAC02FE34A9713E91775CABC11033'
V3_SHA = '7D52695308B0D8122B3ABE42CC7E396BFF3F94E811E5F379FFA85F259ED4EB20'
SCHEMA = 'P101A_SUPERVISION_V4_CONSUMER_V1'
AUTH_SCHEMA = 'P101A_SUPERVISION_V4_EXPERIMENTAL_AUTHORIZATION_V1'
PREPARATION = 'P101A_SUPERVISION_REPAIR_PREPARATION_V4'
ARMS = ('scratch_ntp', 'scratch_mtp', 'parent_ntp', 'parent_mtp')
COUNTS = dict(train=dict(rows=22528, x_tokens=5405444, assistant_targets=552153),
              val=dict(rows=512, x_tokens=127921, assistant_targets=2977))
HARD_STOP = datetime(2026, 10, 22, 8, tzinfo=timezone.utc)
PINS = {
    'scripts/diag_p101a_sft_mtp.py': 'D7AC53E981E957C3C3A38417D19F1F3C01CE38DA736607FB6FC2B60E535A44DC',
    'scripts/diag_p101a_clean_bilingual.py': '4F7C4A3B6D460F72BE20CF8B185660C784F56BF3E14C21ADA5F1E3AE044CD74C',
    'scripts/check_p101a_clean_cost.py': 'C3764052804936411BFBFBF845175A39C41E1BF58D20C79ACD0F21A4A1A33079',
    'scripts/diag_p101a_clean_eval.py': '86BF6AB99F56CFBBE2FF504901E86C56434603A729A13A32FE632EB5C6586D41',
    'scripts/p101a_supervision_repair.py': '77220ECC81C3CD2A09FE9FBD85FD89045FAB1C70635A68737857A5DF7C9EAAAA',
    'scripts/test_p101a_supervision_repair.py': '719F11A45E4BD5F78E05433C8B62D91EB341F38DBE3F73A565A9F3F4AE7D1A6D',
    'scripts/p101a_sft_mtp_data.py': '909B18179F6BDDAD59BA861FF76245DBA99B7912E26CBBBB5E7CBE8CDA2B1F1B',
    'tinylm/train/mtp_sft.py': 'EF508EC83AA16FE37674516A77A3E5B43D69545C05E52E8C6AC34765255BC657',
}
DEPENDENCIES = ('tinylm/config.py', 'tinylm/model/transformer.py', 'tinylm/model/modules.py',
    'tinylm/model/ternary.py', 'tinylm/model/ternary_kernel.py', 'tinylm/infer/generate.py',
    'tinylm/infer/mtp.py', 'tinylm/train/muon.py', 'tinylm/train/optimizer_audit.py',
    'tinylm/chat/canonical.py', 'tinylm/chat/serialize.py', 'tinylm/chat/tokens.py',
    'tinylm/data/sft.py', 'scripts/p106b_shards.py', 'scripts/p106b_source_cleanup.py',
    'scripts/p106b_education_followup.py', 'scripts/p106b_gate_runtime.py',
    'scripts/diag_p101a_mtp_parity.py', 'scripts/p106b_repeat4_gate.py',
    'scripts/train_sft_p090.py', 'scripts/test_p101a_sft_mtp.py',
    'scripts/test_p101a_sft_mtp_data.py', 'scripts/test_p101a_sft_mtp_driver.py',
    'scripts/p101a_sft_mtp_infer.py', 'scripts/test_p101a_clean_eval.py')


class Hold(RuntimeError): pass


def now(): return datetime.now(timezone.utc)
def sha(value): return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()).hexdigest().upper()
def finite(v): return type(v) in (int, float) and math.isfinite(v) and v >= 0


def path(relative):
    item = Path(relative)
    if (item.is_absolute() or not item.parts or '..' in item.parts or '\\' in str(relative)
            or any(p in {'TinyDataset', '.claude', '.codex', '.agents', '.aws'} for p in item.parts)):
        raise ValueError('explicit non-protected relative path required')
    out = ROOT
    for part in item.parts:
        out /= part
        if out.is_symlink(): raise ValueError('linked input/output refused')
    return out


def digest(relative):
    target = path(relative)
    if not target.is_file(): raise FileNotFoundError(relative)
    h = hashlib.sha256()
    with target.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''): h.update(block)
    return h.hexdigest().upper()


def read(relative):
    p = path(relative)
    if not p.is_file(): raise FileNotFoundError(relative)
    if p.stat().st_size >= 20_000_000: raise ValueError('small regular metadata required')
    result = json.loads(p.read_bytes())
    if not isinstance(result, dict): raise ValueError('JSON object required')
    return result


def write(relative, value):
    if not relative.startswith(BASE + '/'): raise ValueError('own V4 evidence only')
    raw = (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
    if len(raw) >= 20_000_000: raise ValueError('small receipt required')
    p = path(relative); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('xb') as f: f.write(raw)


def engine_code():
    """Read literal CODE metadata only; never compile/exec or transform a loop."""
    name = 'scripts/diag_p101a_sft_mtp.py'; raw = path(name).read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != PINS[name]: raise ValueError('original CODE source bytes changed')
    tree = ast.parse(raw.decode('utf-8'))
    values = [node.value for node in tree.body if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == 'CODE' for target in node.targets)]
    if len(values) != 1: raise ValueError('one literal original engine.CODE required')
    names = ast.literal_eval(values[0])
    if not isinstance(names, tuple) or not all(isinstance(p, str) for p in names):
        raise ValueError('literal original CODE path tuple required')
    return names


def sources():
    result = {p: digest(p) for p in PINS}
    if any(result[p] != expected for p, expected in PINS.items()): raise ValueError('pinned original/producer source changed')
    for p in dict.fromkeys((*engine_code(), *DEPENDENCIES, SCRIPT, TEST)):
        result[p] = digest(p)
    if any(result[p] != expected for p, expected in PINS.items()): raise ValueError('pinned source changed during source manifest read')
    return result


def modules():
    manifest = sources()  # verify before importing; modules defer all model imports.
    names = (
        'diag_p101a_sft_mtp', 'diag_p101a_clean_bilingual', 'check_p101a_clean_cost',
        'diag_p101a_clean_eval', 'p101a_supervision_repair')
    loaded = []
    for name in names:
        module = importlib.import_module('scripts.' + name)
        if Path(module.__file__).resolve() != path('scripts/' + name + '.py'):
            raise ValueError('imported module is not the pinned source: ' + name)
        loaded.append(module)
    engine = loaded[0]
    if (Path(engine.data.__file__).resolve() != path('scripts/p101a_sft_mtp_data.py')
            or tuple(engine.CODE) != engine_code() or not set(engine.CODE) <= set(manifest)):
        raise ValueError('imported data/complete original engine.CODE identity differs')
    return tuple(loaded)


def study():
    return dict(schema=SCHEMA, tag=TAG, corpus=CORPUS, corpus_report_sha256=REPORT_SHA,
        supervision_audit_sha256=AUDIT_SHA, code_sha256=sources(), epochs=4, full_updates=704,
        seed=1337, micro_bs=8, accum=16, seq=1024, checkpoint_on=True, compile='default',
        lr=5e-5, muon_lr=2e-4, initializer_policy='ORIGINAL_LOAD_RUNTIME_NO_RESUME',
        supervision='EXPLICIT_ALLOWLIST_TWO_PUBLIC_SOURCES; OTHER_ROWS_NOT_EXHAUSTIVELY_REVIEWED',
        auxiliary='ORIGINAL_COEFFICIENTS_H2_H3_H4_WEIGHT_0.3',
        first_answer='FP32_MATH_TF32_OFF_CACHE_ON_MTP_OFF_GREEDY128_RETRIES0')


def prepared(m):
    engine, _, _, _, producer = m
    if digest(CORPUS + '/report.json') != REPORT_SHA or digest(CORPUS + '/supervision_audit.json') != AUDIT_SHA:
        raise ValueError('exact completed data_cache V4 report/audit required; HF partial is not eligible')
    r, audit = read(CORPUS + '/report.json'), read(CORPUS + '/supervision_audit.json')
    if (r.get('preparation_schema') != PREPARATION or r.get('status') != 'SUPERVISION_REPAIR_PREPARED_NOT_ADMITTED'
            or r.get('tag') != TAG or r.get('counts') != COUNTS or r.get('epochs') != 4
            or r.get('learning_updates') != 704 or set(r.get('manifests', {})) != {'train', 'val'}
            or r.get('tokenizer_sha256') != engine.data.TOK_SHA
            or r.get('actual_unique_train_x_tokens') != COUNTS['train']['x_tokens']
            or r.get('target_processed_x_tokens') != 4 * COUNTS['train']['x_tokens']
            or r.get('training_admission') != 'NOT_ADMITTED'
            or r.get('supervision_audit') != dict(path='supervision_audit.json', sha256=AUDIT_SHA)
            or any(digest(p) != value for p, value in r.get('code_sha256', {}).items())):
        raise ValueError('V4 preparation/producer/count/admission contract differs')
    from scripts.p106b_shards import verify
    for split, manifest in r['manifests'].items():
        if read(CORPUS + '/' + split + '_shards_manifest.json') != manifest: raise ValueError('V4 manifest differs')
        verify(path(CORPUS), manifest)
    if ([v.get('source_id') for v in audit.get('repairs', [])] != [s['source_id'] for s in producer.REPAIRS]
            or r.get('equivalence_audit', {}).get('metadata_changed_rows') != 2):
        raise ValueError('two exact reviewed sources required')
    return r, audit


def encoded_fingerprint(records):
    h = hashlib.sha256()
    for split in ('train', 'val'):
        h.update(split.encode())
        for rec in records[split]: h.update(json.dumps([rec.x, rec.y, rec.segments], separators=(',', ':')).encode())
    return h.hexdigest().upper()


def contract_records(m):
    engine, clean, _, _, producer = m
    r, audit = prepared(m)
    from tokenizers import Tokenizer, __version__ as tokenizer_version
    from tinylm.train import mtp_sft as core
    if digest(str(engine.data.TOKENIZER.relative_to(ROOT))) != engine.data.TOK_SHA: raise ValueError('tokenizer changed')
    tok = Tokenizer.from_file(str(engine.data.TOKENIZER))
    records = clean.encoded(path(CORPUS), r, tok); totals = {}; masses = {}; repairs = {}; row_counts = []
    for split in ('train', 'val'):
        mass = producer.new_mass(); hs = Counter(); rows = list(engine.data.stream_rows(path(CORPUS), r['manifests'][split]))
        if len(rows) != len(records[split]): raise ValueError('actual encoder row count differs')
        for row, rec in zip(rows, records[split]):
            producer.add_mass(mass, row, rec); counts = core.count_record(rec); hs.update(counts)
            if split == 'train': row_counts.append(counts)
            ident = row.get('meta', {}).get('source_id')
            if ident in {s['source_id'] for s in producer.REPAIRS}:
                expected = next(v for v in audit['repairs'] if v['source_id'] == ident)
                if (split != 'train' or ident in repairs or row['meta'].get('supervised_assistant_turns') != [2]
                        or engine.data.conversation_identity(row) != expected['messages_sha256']
                        or producer.turn_audit(rec) != expected['after_turn_h1_to_h4'] or 1 in rec.segments):
                    raise ValueError('actual consumer ignored repaired y/owner/EOT/turn contract')
                repairs[ident] = expected['after_turn_h1_to_h4']
        masses[split] = producer.plain_mass(mass); totals[split] = dict(masses[split]['total'], horizons={str(k): v for k, v in hs.items()})
        if masses[split] != r['after_mass'][split]: raise ValueError('actual language/source/token mass differs')
    if len(repairs) != 2: raise ValueError('both actual repaired records required')
    by_id = {id(rec): count for rec, count in zip(records['train'], row_counts)}
    expected_epochs = []; cost_x = cost_targets = update = 0
    for epoch in range(4):
        valid = Counter()
        for groups in engine.batches(records['train'], epoch):
            weights = core.coefficients(update, 704); active = {1, *(h for h, w in weights.items() if w)}
            for micro in groups:
                for rec in micro:
                    for h in active: valid[h] += by_id[id(rec)][h]
                    if update < 32: cost_x += rec.x_tokens; cost_targets += rec.targets
            update += 1
        expected_epochs.append({str(h): valid[h] for h in (1, 2, 3, 4)})
    if update != 704: raise ValueError('full four-pass704 schedule required')
    summary = dict(records_sha256=encoded_fingerprint(records), totals=totals, mass=masses, repairs=repairs,
        tokenizer_version=tokenizer_version, torch_version=core.torch.__version__,
        python_version=sys.version, expected_mtp_active_epoch_targets=expected_epochs,
        expected_cost=dict(updates=32, actual_processed_x_tokens=cost_x, assistant_targets=cost_targets))
    return records, summary


def cpu_contract(m):
    if path(CONTRACT).exists(): raise FileExistsError('prior CPU consumer contract preserved')
    before = study()
    _, summary = contract_records(m)
    prepared(m)
    if study() != before: raise Hold('consumer source changed during CPU contract; no completion receipt')
    value = dict(status='CPU_V4_CONSUMER_CONTRACT_COMPLETE_NOT_MODEL_QUALITY', study=before,
        study_sha256=sha(before), encoded=summary, model_loads=0, checkpoint_loads=0, gpu_calls=0,
        training_admission='NOT_ADMITTED; separate exact experimental execution approval required')
    write(CONTRACT, value)
    print('[CPU_V4_CONTRACT] ' + json.dumps(dict(path=CONTRACT, sha256=digest(CONTRACT),
        study_sha256=value['study_sha256'], status=value['status'],
        model_loads=0, gpu_calls=0, training_admission='NOT_ADMITTED')), flush=True)
    return value


def load_contract():
    c = read(CONTRACT)
    if (c.get('status') != 'CPU_V4_CONSUMER_CONTRACT_COMPLETE_NOT_MODEL_QUALITY'
            or c.get('study') != study() or c.get('study_sha256') != sha(study())):
        raise Hold('fresh same-source actual CPU tokenizer consumer contract required')
    return c


def stamp(text):
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None: raise ValueError('timezone-aware timestamp required')
    return dt


def checked_authority(a):
    if not a.authorization or not a.authorization.startswith('handoff/audit/') or digest(a.authorization) != a.authorization_sha256:
        raise Hold('explicit root-owned exact execution authority required')
    auth = read(a.authorization); c = load_contract()
    if (auth.get('schema') != AUTH_SCHEMA or auth.get('tag') != TAG or auth.get('allow_experimental_gpu') is not True
            or auth.get('consumer_signature_sha256') != sha(study())
            or auth.get('cpu_contract_sha256') != digest(CONTRACT)
            or auth.get('corpus_report_sha256') != REPORT_SHA or auth.get('supervision_audit_sha256') != AUDIT_SHA
            or type(auth.get('max_worker_seconds')) is not int or not 60 <= a.max_wall_sec <= auth['max_worker_seconds'] <= 21600
            or type(auth.get('max_family_seconds')) is not int or not a.max_wall_sec <= auth['max_family_seconds'] <= 144000
            or auth.get('prior_spend_scope') != 'APPROVED_PRE_V4_FAMILY_ONLY'):
        raise Hold('exact V4/consumer/contract/worker/family experimental approval required')
    arms, modes = auth.get('allowed_arms'), auth.get('allowed_modes')
    if (not isinstance(arms, list) or not arms or len(arms) != len(set(arms)) or not set(arms) <= set(ARMS)
            or a.arm not in arms or not isinstance(modes, list) or not modes
            or len(modes) != len(set(modes)) or not set(modes) <= {'calibrate', 'train', 'evaluate'}
            or a.mode not in modes):
        raise Hold('this exact arm/stage is not authorized')
    remaining = (stamp(auth['expires_at']) - now()).total_seconds()
    if stamp(auth['expires_at']) > HARD_STOP or remaining < a.max_wall_sec:
        raise Hold('whole worker cap must fit current approval and today17:00 KST')
    refs = auth.get('prior_spend_receipts', []); total = 0.; names = set()
    for ref in refs:
        name = ref['path']
        if (not name.startswith(('handoff/audit/', 'test_result/evidence/')) or name.startswith(BASE + '/')
                or name in names or digest(name) != ref['sha256']): raise ValueError('exact distinct pre-V4 spend receipts required')
        value = read(name).get(ref['seconds_field']); names.add(name)
        if not finite(value): raise ValueError('finite prior actual seconds required')
        total += value
    if not refs or not finite(auth.get('prior_spent_seconds')) or abs(total - auth['prior_spent_seconds']) > 1e-6:
        raise ValueError('prior actual spend cannot be silently zeroed for a new tag')
    v3 = auth.get('v3_pair_receipts', [])
    if len(v3) != 2: raise Hold('both original V3 scratch arms must finish before V4 GPU consumption')
    old = []
    for ref, arm in zip(v3, ('scratch_ntp', 'scratch_mtp')):
        expected = 'test_result/evidence/p101a_sft_mtp_cleanbilingual_v3_s1337/' + arm + '/report.json'
        if ref.get('path') != expected or digest(expected) != ref.get('sha256'): raise ValueError('exact original V3 pair receipts required')
        r = read(expected); old.append(r)
        if (r.get('arm') != arm or r.get('status') != 'SFT_MTP_TRAINED_EVAL_PENDING' or r.get('checkpoint_saved') is not True
                or r.get('corpus_sha256') != V3_SHA or r.get('updates') != 704
                or r.get('actual_processed_x_tokens') != 21621776 or r.get('assistant_targets') != 2210436):
            raise Hold('V3 pair must close on unchanged V3, not a mixed partial comparison')
    if old[0]['initial_core_sha256'] != old[1]['initial_core_sha256']: raise ValueError('V3 pair initialization differs')
    return auth, c, remaining


def intent_name(mode, arm): return BASE + '/consumer_intent_' + mode + '_' + arm + '.json'
def activity_name(mode, arm): return BASE + '/consumer_activity_' + mode + '_' + arm + '.json'
def receipt_name(mode, arm): return BASE + '/consumer_' + mode + '_' + arm + '/report.json'


def closed(mode, arm):
    i, a, r = read(intent_name(mode, arm)), read(activity_name(mode, arm)), read(receipt_name(mode, arm))
    auth = i['authorization']
    if (i.get('study_sha256') != sha(study()) or a.get('study_sha256') != sha(study())
            or i.get('mode') != mode or i.get('arm') != arm or r.get('mode') != mode or r.get('arm') != arm
            or auth.get('schema') != AUTH_SCHEMA or auth.get('allow_experimental_gpu') is not True
            or auth.get('consumer_signature_sha256') != sha(study()) or auth.get('tag') != TAG
            or mode not in auth.get('allowed_modes', []) or arm not in auth.get('allowed_arms', [])
            or auth.get('cpu_contract_sha256') != digest(CONTRACT)
            or auth.get('corpus_report_sha256') != REPORT_SHA or auth.get('supervision_audit_sha256') != AUDIT_SHA
            or i.get('authorization_canonical_sha256') != sha(auth)
            or not str(i.get('authorization_path', '')).startswith('handoff/audit/')
            or digest(i['authorization_path']) != i.get('authorization_sha256')
            or a.get('complete') is not True or a.get('returncode') != 0 or a.get('intent_sha256') != digest(intent_name(mode, arm))
            or a.get('receipt_sha256') != digest(receipt_name(mode, arm)) or not finite(a.get('seconds'))
            or type(i.get('max_wall_sec')) is not int or not 60 <= i['max_wall_sec'] <= auth.get('max_worker_seconds', 0)
            or a['seconds'] > i['max_wall_sec'] + 30 or i.get('pid') != i.get('pgid')
            or type(i.get('pid')) is not int or i['pid'] <= 0
            or not stamp(i['started_at']) <= stamp(a['ended_at']) <= stamp(auth['expires_at']) <= HARD_STOP
            or r.get('study_sha256') != sha(study()) or r.get('original_report_sha256') != digest(r['original_report'])
            or r.get('corpus_report_sha256') != REPORT_SHA or r.get('cpu_contract_sha256') != digest(CONTRACT)):
        raise ValueError('closed same-source V4 consumer report/activity required')
    if any(digest(p) != value for p, value in r.get('artifacts', {}).items()):
        raise ValueError('closed checkpoint/raw/review artifact changed')
    return r, read(r['original_report']), auth


def spent(auth):
    total = auth['prior_spent_seconds']
    for mode in ('calibrate', 'train', 'evaluate'):
        for arm in ARMS:
            i, a = intent_name(mode, arm), activity_name(mode, arm)
            if path(i).exists() or path(a).exists():
                _, _, historical = closed(mode, arm)
                if historical['prior_spend_receipts'] != auth['prior_spend_receipts']:
                    raise ValueError('approved pre-V4 spend baseline changed')
                total += read(a)['seconds']
    return total


def metadata(a, m, c):
    value = m[0].info(a)
    value.update(study(), preparation_schema=PREPARATION, family='mtp',
        unique_train_x_target=COUNTS['train']['x_tokens'], processed_x_target_approx=21621776,
        corpus_sha256=REPORT_SHA, supervision_audit_sha256=AUDIT_SHA,
        consumer_signature_sha256=sha(study()), cpu_contract_sha256=digest(CONTRACT),
        encoded_records_sha256=c['encoded']['records_sha256'],
        semantic_quality='TWO_SOURCE_SUPERVISION_REPAIR; OTHER_ROWS_NOT_EXHAUSTIVELY_REVIEWED',
        formal_train_ready=False, experimental_consumption='SEPARATE_EXPLICIT_EXECUTION_AUTHORITY_REQUIRED')
    return value


def validate_training(r, a, m, c):
    engine, _, checker, _, _ = m
    meta = metadata(a, m, c)
    if a.mode == 'calibrate':
        checker.validate(r, meta, REPORT_SHA, a.arm, 704)
        if any(r.get(k) != v for k, v in c['encoded']['expected_cost'].items()): raise ValueError('actual cost32 x/target/update denominator differs')
    else:
        _, cost, _ = closed('calibrate', a.arm)
        if (r.get('status') != 'SFT_MTP_TRAINED_EVAL_PENDING' or r.get('updates') != 704
                or r.get('actual_processed_x_tokens') != 21621776 or r.get('assistant_targets') != 2208612
                or r.get('checkpoint_saved') is not True or len(r.get('history', [])) != 4
                or r.get('checkpoint') != str(engine.checkpoint(TAG, a.arm).relative_to(ROOT))
                or digest(r['checkpoint']) != r.get('checkpoint_sha256')):
            raise ValueError('full704/four-pass/actual targets/unchanged dedicated checkpoint required')
        expected_initializer = 'SCRATCH_NO_WEIGHT_INIT' if a.arm.startswith('scratch_') else 'PINNED_PARENT_WEIGHT_ONLY'
        if r.get('initializer') != expected_initializer or r.get('initial_core_sha256') != cost.get('initial_core_sha256'):
            raise ValueError('main must start fresh from the same declared cost initializer')
        for index, h in enumerate(r['history']):
            expected = c['encoded']['expected_mtp_active_epoch_targets'][index] if a.arm.endswith('_mtp') else dict.fromkeys(('1', '2', '3', '4'), 0)
            if a.arm.endswith('_ntp'): expected['1'] = COUNTS['train']['assistant_targets']
            if (h.get('epoch') != index + 1 or h.get('updates') != 176 * (index + 1)
                    or h.get('processed_x_tokens') != COUNTS['train']['x_tokens']
                    or h.get('assistant_targets') != COUNTS['train']['assistant_targets']
                    or h.get('active_head_target_counts') != expected): raise ValueError('epoch x/target/active horizon exposure differs')
        horizons = ('1', '2', '3', '4') if a.arm.endswith('_mtp') else ('1',)
        for val in [r.get('initial_val', {}), *(h.get('val', {}) for h in r['history'])]:
            if set(val) != set(horizons) or any(val[h].get('targets') != c['encoded']['totals']['val']['horizons'][h] for h in horizons):
                raise ValueError('actual before/epoch DEV horizon denominators differ')
        native_sha = r.get('initial_native_ce', {}).get('val_sha256')
        if not native_sha or native_sha != r.get('final_native_ce', {}).get('val_sha256'):
            raise ValueError('before/after native evaluation source changed')
    if any(r.get(k) != v for k, v in meta.items() if k not in {'max_wall_sec', 'model_loading', 'meaningful_training'}):
        raise ValueError('actual result consumer metadata differs')


@contextmanager
def training_scope(a, m, c, records):
    engine, clean, _, _, _ = m
    factory, writer = engine.optimizers, engine.write
    expected_sha = c['encoded']['records_sha256']; calls = []
    def reader(actual):
        if actual != path(CORPUS): raise ValueError('no V3/HF fallback')
        return prepared(m)[0]
    def encoder(actual, report, tok):
        reader(actual)
        if (tok.get_vocab_size() != 32768 or tok.token_to_id('<|im_end|>') != 4
                or encoded_fingerprint(records) != expected_sha): raise ValueError('runtime encoder/tokenizer contract differs')
        calls.append(True); return records
    def optimizers(model):
        adam, muon = factory(model)
        for g in adam.param_groups: g['lr'] = 5e-5
        for g in muon.param_groups: g['lr'] = 2e-4
        return adam, muon
    def checked_write(target, value):
        if target == engine.report_path(path(BASE), a.arm, a.mode == 'calibrate'):
            if len(calls) != 1 or encoded_fingerprint(records) != expected_sha: raise ValueError('actual consumer invocation/mutation differs')
            validate_training(value, a, m, c)
        writer(target, value)
    with patch.object(engine, 'corpus_report', reader), patch.object(engine, 'encoded', encoder), \
         patch.object(engine, 'optimizers', optimizers), patch.object(engine, 'write', checked_write):
        yield calls


def evaluate(a, m, c):
    engine, _, _, ev, _ = m
    _, trained, _ = closed('train', a.arm)
    if trained['corpus_sha256'] != REPORT_SHA: raise ValueError('same V4 student required')
    output = path(BASE + '/first_answer_' + a.arm)
    if output.exists(): raise FileExistsError('old first answers preserved')
    def preconditions(selector, arm):
        if selector != TAG or arm != a.arm: raise ValueError('explicit versioned output selector required')
        r, _ = prepared(m)
        if (digest(str(engine.checkpoint(TAG, arm).relative_to(ROOT))) != trained['checkpoint_sha256']
                or digest(str(engine.data.TOKENIZER.relative_to(ROOT))) != engine.data.TOK_SHA):
            raise ValueError('exact saved student/tokenizer required before evaluation model loading')
        info = dict(metadata(a, m, c), schema=SCHEMA, arm=arm, corpus_sha256=REPORT_SHA,
            checkpoint_sha256=trained['checkpoint_sha256'], trained_report_sha256=digest(BASE + '/' + arm + '/report.json'),
            family='mtp', output_selector=TAG, split='val', expected_rows=512,
            precision='FP32_MATH_TF32_OFF', cache=True, mtp_inference=False, temperature=0, top_k=1,
            max_new=128, retries=0, learning_updates=0, test_independence='DEV_USED_BY_TRAINING_VALIDATION')
        return path(CORPUS), r, 'val', engine.checkpoint(TAG, arm), output, info
    args = copy.copy(a); args.family = TAG  # namespace only; canonical family remains mtp in receipt.
    with patch.object(ev, 'prerequisites', preconditions): code = ev.execute(args)
    if code: raise Hold('first-answer worker failed; raw partials preserved')
    r = read(BASE + '/first_answer_' + a.arm + '/report.json')
    if (r.get('status') != 'FIRST_ANSWER_COLLECTION_COMPLETE' or r.get('returncode') != 0
            or r.get('counts', {}).get('total') != 512 or r.get('corpus_sha256') != REPORT_SHA
            or r.get('output_selector') != TAG or r.get('checkpoint_sha256') != trained['checkpoint_sha256']
            or r.get('first_answer_only') is not True or r.get('training_feedback') != 0 or r.get('checkpoint_writes') != 0):
        raise ValueError('complete same-V4 DEV512 first-answer receipt required')
    expected_review = 'review_request/20261021_' + TAG + '_' + a.arm + '_실제첫답.md'
    if r.get('readable_review') != expected_review or not path(expected_review).is_file():
        raise ValueError('versioned review output must not collide with V3')
    from scripts.p106b_shards import verify
    verify(output, r['raw_manifest'])
    cases = engine.data.stream_rows(output, r['raw_manifest'])
    expected_rows = engine.data.stream_rows(path(CORPUS), prepared(m)[0]['manifests']['val'])
    counts = Counter()
    from itertools import zip_longest
    for index, (case, source) in enumerate(zip_longest(cases, expected_rows)):
        if case is None or source is None or case.get('index') != index or case.get('source') != source:
            raise ValueError('all actual DEV first answers/source order required')
        grading = ev.score(source, case['answer'], case['grading'].get('extraction_ok') is True)
        if grading != case['grading']: raise ValueError('raw first-answer grading differs')
        counts.update(total=1, primary_correct=int(grading['primary_correct']),
            extraction_failed=int(not grading.get('extraction_ok')),
            ended=int(case['generation']['finish_reason'] in ('STOP_SEQUENCE', 'EOS')))
    if dict(counts) != r['counts']: raise ValueError('independent first-answer raw recount differs')
    return BASE + '/first_answer_' + a.arm + '/report.json'


def gpu_worker(a, m):
    began = now(); tick = time.perf_counter()
    if os.getpgrp() != os.getpid(): raise Hold('owned isolated process group required')
    auth, c, _ = checked_authority(a)
    if spent(auth) + a.max_wall_sec > auth['max_family_seconds']: raise Hold('actual prior+V4 whole worker budget does not fit')
    for name in (intent_name(a.mode, a.arm), activity_name(a.mode, a.arm), receipt_name(a.mode, a.arm)):
        if path(name).exists(): raise FileExistsError('prior consumer stage preserved')
    if a.mode == 'train':
        _, cost, _ = closed('calibrate', a.arm)
        m[2].validate(cost, metadata(a, m, c), REPORT_SHA, a.arm, 704)
    if a.mode == 'evaluate': closed('train', a.arm)
    code = 9; error = None; original = None
    write(intent_name(a.mode, a.arm), dict(study_sha256=sha(study()), mode=a.mode, arm=a.arm,
        max_wall_sec=a.max_wall_sec, started_at=began.isoformat(), pid=os.getpid(), pgid=os.getpgrp(),
        authorization=auth, authorization_path=a.authorization,
        authorization_canonical_sha256=sha(auth), authorization_sha256=a.authorization_sha256))
    try:
        args = copy.copy(a); args.tag = TAG
        if a.mode in ('calibrate', 'train'):
            records, summary = contract_records(m)
            if summary != c['encoded']: raise ValueError('actual current CPU encoder differs from admitted contract')
            if study() != c['study']: raise Hold('consumer source changed before model loading')
            args.max_wall_sec = int(min(a.max_wall_sec - (time.perf_counter() - tick), (stamp(auth['expires_at']) - now()).total_seconds()))
            if args.max_wall_sec < 60: raise Hold('no full bounded model window remains')
            with training_scope(args, m, c, records) as calls:
                rc = m[0].train_arm(args, path(CORPUS), path(BASE), metadata(args, m, c), calibrate=a.mode == 'calibrate')
            if rc or len(calls) != 1 or encoded_fingerprint(records) != c['encoded']['records_sha256']:
                raise Hold('original training did not complete unchanged actual V4 consumption')
            original = str(m[0].report_path(path(BASE), a.arm, a.mode == 'calibrate').relative_to(ROOT))
            validate_training(read(original), args, m, c)
        else: original = evaluate(args, m, c)
        if now() >= stamp(auth['expires_at']) or study() != c['study']: raise Hold('deadline/source changed; no consumer completion')
        prepared(m)
        result = read(original); artifacts = {}
        if a.mode == 'train': artifacts[result['checkpoint']] = result['checkpoint_sha256']
        if a.mode == 'evaluate':
            artifacts[result['readable_review']] = digest(result['readable_review'])
            for shard in result['raw_manifest']['shards']:
                artifacts[str(Path(original).parent / shard['path'])] = shard['sha256']
        write(receipt_name(a.mode, a.arm), dict(status='V4_EXPERIMENTAL_CONSUMPTION_VERIFIED_NO_QUALITY_ADOPTION',
            mode=a.mode, arm=a.arm, study_sha256=sha(study()), corpus_report_sha256=REPORT_SHA,
            supervision_audit_sha256=AUDIT_SHA, cpu_contract_sha256=digest(CONTRACT),
            original_report=original, original_report_sha256=digest(original),
            artifacts=artifacts,
            timing_scope='consumer_activity.seconds includes GPU-worker prechecks/CPU encoding/engine/postchecks; module import and parent setup excluded; original engine timer excludes CPU record preflight',
            experimental_authority_sha256=a.authorization_sha256,
            scope='Two explicit supervision repairs; unreviewed row accuracy/general intelligence not established'))
        code = 0
    except KeyboardInterrupt: code, error = 130, 'KeyboardInterrupt'
    except Hold as exc: code, error = 8, str(exc)
    except Exception as exc: code, error = 9, type(exc).__name__ + ': ' + str(exc)
    finally:
        write(activity_name(a.mode, a.arm), dict(study_sha256=sha(c['study']), complete=code == 0,
            returncode=code, error=error, ended_at=now().isoformat(), seconds=time.perf_counter() - tick,
            intent_sha256=digest(intent_name(a.mode, a.arm)),
            receipt_sha256=digest(receipt_name(a.mode, a.arm)) if path(receipt_name(a.mode, a.arm)).exists() else None))
    if error: print('[V4_CONSUMER_ERROR] ' + error, flush=True)
    return code


def pair_readback(a):
    arms = (a.initializer + '_ntp', a.initializer + '_mtp'); result = {}
    for arm in arms:
        _, train, _ = closed('train', arm); _, evaluation, _ = closed('evaluate', arm)
        result[arm] = dict(train=train, first_answers=evaluation)
    for key in ('initial_core_sha256', 'corpus_sha256', 'actual_processed_x_tokens', 'assistant_targets', 'updates', 'code_sha256'):
        if result[arms[0]]['train'][key] != result[arms[1]]['train'][key]: raise ValueError('paired initializer/input/exposure differs: ' + key)
    completed = [arm for arm in ARMS if path(receipt_name('train', arm)).exists() and closed('train', arm)]
    value = dict(status='V4_INITIALIZER_PAIR_READBACK_NO_ADOPTION', selected_pair=list(arms),
        selected_complete=2, original_total=4, completed_training_arms=completed,
        pending_training_arms=[arm for arm in ARMS if arm not in completed], results=result,
        original_four_arm_compare='NOT_RUN; original ARMS unchanged',
        quality='DEV annotation match and raw answers; not independent TEST or general intelligence')
    write(BASE + '/pair_' + a.initializer + '/report.json', value)
    return value


def launch(argv, seconds):
    process = subprocess.Popen([sys.executable, '-B', '-X', 'utf8', str(path(SCRIPT)), *argv, '--worker'],
        cwd=ROOT, stdin=subprocess.DEVNULL, start_new_session=True)
    try: return process.wait(timeout=seconds)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        try: os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError: pass
        try: process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait()
        return 130


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('check-only', 'cpu-contract', 'calibrate', 'train', 'evaluate', 'pair-readback'), required=True)
    parser.add_argument('--arm', choices=ARMS, default='parent_ntp')
    parser.add_argument('--initializer', choices=('parent', 'scratch'), default='parent')
    parser.add_argument('--max-wall-sec', type=int)
    parser.add_argument('--authorization'); parser.add_argument('--authorization-sha256')
    parser.add_argument('--execute', action='store_true'); parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    a = parser.parse_args(argv); a.tag = TAG
    try:
        if a.mode == 'check-only':
            print('[STATIC_ONLY] ' + json.dumps(dict(study_sha256=sha(study()), tag=TAG,
                corpus=CORPUS, corpus_report_sha256=REPORT_SHA, supervision_audit_sha256=AUDIT_SHA,
                arms=list(ARMS), model_loads=0, asset_reads=0, training_admission='NOT_ADMITTED')), flush=True)
            return 0
        if a.max_wall_sec is None:
            if a.mode in ('train', 'evaluate'): raise Hold('explicit whole train/evaluate wall cap required; no short-course default')
            a.max_wall_sec = 1200
        if not a.execute or not 60 <= a.max_wall_sec <= 21600: raise Hold('explicit bounded execution required')
        if a.mode == 'pair-readback': pair_readback(a); return 0
        m = modules()
        if a.mode != 'cpu-contract':
            auth, _, remaining = checked_authority(a)
            if spent(auth) + a.max_wall_sec > auth['max_family_seconds']: raise Hold('whole family budget does not fit')
        if not a.worker: return launch(argv, a.max_wall_sec)
        if os.getpgrp() != os.getpid(): raise Hold('owned process group required')
        signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
        if a.mode == 'cpu-contract': cpu_contract(m); return 0
        return gpu_worker(a, m)
    except (Hold, FileExistsError, FileNotFoundError) as exc:
        print('[HOLD] ' + str(exc), file=sys.stderr, flush=True); return 8
    except Exception as exc:
        print('[V4_ERROR] ' + type(exc).__name__ + ': ' + str(exc), file=sys.stderr, flush=True); return 9


if __name__ == '__main__': raise SystemExit(main())
