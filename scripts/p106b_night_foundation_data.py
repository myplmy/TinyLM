"""Pure native-CPT exposure contract for the same-P090B QA comparison.

This module performs no file I/O, model construction, tensor operation or GPU
work. Supplied asset identities are declarations; the parent driver verifies
the actual cache, QA report, initializer and frozen artifact before execution.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
TAG = 'p106b_night_foundation_v1_s1337'
CORPUS = ROOT / 'HF/sft_ready' / TAG / 'corpus'
EVIDENCE = ROOT / 'test_result/evidence' / TAG
VERSION = 'P106B_NIGHT_FOUNDATION_CONTRACT_V1'
NATIVE_TRAIN = 'data_cache/ko-en_601000000_chat32/train.bin'
NATIVE_VAL = 'data_cache/ko-en_601000000_chat32/val.bin'
NATIVE_TRAIN_TOKENS = 597995000
NATIVE_VAL_TOKENS = 3005000
TRAIN_SHA = 'DBD12235B4A1478177246B4BD5214C8B8BBF10D077CBA80304690AD12A8E59A2'
VAL_SHA = 'AD7EFB0DBD0D830A216B4D21A91C8ACB3FC41DAE2B23A3A55999AE8727AA374C'
QA_REPORT = 'HF/sft_ready/p106b_night_grounded_v2_s1337/corpus/report.json'
LOCKED_QA_SHA = 'E340BCE35E0B5FA6CC0EE2F08694E584A711231BC6443C5D599D55F95D5D122B'
PARENT = ROOT / 'runs/ckpt/m100s10_ko-en_300M_dense_chat32_p090b_s1337.pt'
PARENT_SHA = '12E18658CDCD0AFEBE5A87073DC8977304C0D490A03A8471779D514FBB0D9950'
MICRO_BS, ACCUM, SEQ = 8, 16, 1024
WINDOW_WIDTH = SEQ + 1
UPDATE_WINDOWS = MICRO_BS * ACCUM
UPDATE_TARGETS = UPDATE_WINDOWS * SEQ
MAX_STEPS = 2289


def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest().upper()


def _locked_sha(value, expected, label):
    if not isinstance(value, str) or value.upper() != expected:
        raise ValueError('locked ' + label + ' SHA differs')
    return expected


def _qa_followup():
    return dict(report=QA_REPORT, report_sha256=LOCKED_QA_SHA,
                updates=640, passes=4, natural_views=[0, 1], replay_rows_per_pass=4096,
                native_rows_per_update=8, native_x_tokens=640 * 8 * 1024,
                adam_lr=5e-5, muon_lr=2e-4, consistency_weight=0.,
                fresh_optimizer_moments=True, grad_checkpoint=True,
                compile='default', mtp=False,
                parent_policy='explicit original P090B or completed CPT checkpoint argument; never mutate module PARENT',
                comparison='same locked QA rows, targets, replay, native offsets,640 updates and fresh optimizer in both arms')


def _check_offsets(offsets, native_tokens, expected_count):
    if not isinstance(offsets, list) or len(offsets) != expected_count:
        raise ValueError('exact planned native-window count required')
    if any(type(offset) is not int or offset < 0
           or offset + WINDOW_WIDTH > native_tokens
           or offset % WINDOW_WIDTH != 0 for offset in offsets):
        raise ValueError('native windows must be integer, stride1025 and entirely in TRAIN bounds')
    ordered = sorted(offsets)
    if any(right - left < WINDOW_WIDTH for left, right in zip(ordered, ordered[1:])):
        raise ValueError('native windows overlap, including their next-token target boundary')


def make_contract(native_tokens, train_sha, val_sha, qa_sha=LOCKED_QA_SHA,
                  seed=1337, max_steps=MAX_STEPS):
    """Plan a >=2x source pool and shuffled, mutually disjoint1025-token windows.

    Actual learning targets are1024/window; the extra source token is retained
    in the nonoverlap and bounds checks. This is a declaration, not a cache
    content/length verification or evidence of previously unseen source text.
    """
    if type(native_tokens) is not int or native_tokens < 1:
        raise ValueError('positive declared native TRAIN token count required')
    if type(seed) is not int:
        raise ValueError('integer native window seed required')
    if type(max_steps) is not int or not 1 <= max_steps <= MAX_STEPS:
        raise ValueError('max_steps must be an explicit1..2289 native budget')
    train_sha = _locked_sha(train_sha, TRAIN_SHA, 'native TRAIN')
    val_sha = _locked_sha(val_sha, VAL_SHA, 'native VAL')
    qa_sha = _locked_sha(qa_sha, LOCKED_QA_SHA, 'V2 QA report')
    steps = min(max_steps, native_tokens // (2 * UPDATE_TARGETS))
    if not steps:
        raise ValueError('TRAIN pool cannot supply even one update at a2x target-token ratio')
    windows = steps * UPDATE_WINDOWS
    candidates = list(range(0, native_tokens - WINDOW_WIDTH + 1, WINDOW_WIDTH))
    if len(candidates) < windows:
        raise ValueError('not enough mutually disjoint1025-token source windows')
    random.Random(seed).shuffle(candidates)
    offsets = candidates[:windows]
    _check_offsets(offsets, native_tokens, windows)
    actual = steps * UPDATE_TARGETS
    contract = dict(schema=VERSION, tag=TAG, status='DECLARED_NATIVE_CPT_CONTRACT',
        native_access='INDEXED_TRAIN_ONLY', native_train_file=NATIVE_TRAIN,
        native_val_file=NATIVE_VAL, native_train_tokens=native_tokens,
        expected_native_train_tokens=NATIVE_TRAIN_TOKENS,
        native_val_tokens=NATIVE_VAL_TOKENS, native_train_sha256=train_sha,
        native_val_sha256=val_sha, qa_report=QA_REPORT, qa_report_sha256=qa_sha,
        parent=str(PARENT.relative_to(ROOT)), parent_sha256=PARENT_SHA,
        steps=steps, max_steps=max_steps, micro_bs=MICRO_BS, accum=ACCUM, seq=SEQ,
        actual_pool_tokens=native_tokens, actual_draw_tokens=actual,
        pool_ratio=native_tokens / actual, native_windows=windows,
        native_window_width=WINDOW_WIDTH, native_candidate_stride=WINDOW_WIDTH,
        native_candidate_windows=len(candidates), native_train_offsets=offsets,
        native_train_offsets_sha256=_sha(offsets), native_seed=seed,
        selected_raw_window_tokens=windows * WINDOW_WIDTH,
        sampling='shuffle all stride1025 TRAIN candidates with local Random(seed), then select without replacement',
        pool_ratio_basis='declared TRAIN token count / actual next-token targets;1025-token physical windows checked separately',
        grad_checkpoint=True, compile='default', optimizer='fresh AdamW plus Muon',
        adam_lr=1e-4, muon_lr=4e-4, scheduler='constant', quant_anneal=1.,
        fresh_optimizer_moments=True, mtp=False, qa_followup=_qa_followup(),
        parent_source_overlap='NOT_AUDITED_AGAINST_ORIGINAL_PARENT_TRAINING',
        new_unique_source_tokens_claim=False,
        asset_verification='NOT_RUN_BY_PURE_CONTRACT; parent driver verifies actual files and initializer',
        model_loaded=False, optimizer_updates=0, corpus_written=False)
    validate_contract(contract)
    return contract


def validate_contract(contract):
    """Validate declared counts, exact recipe and every selected offset in CPU."""
    expected = dict(schema=VERSION, tag=TAG, status='DECLARED_NATIVE_CPT_CONTRACT',
        native_access='INDEXED_TRAIN_ONLY', native_train_file=NATIVE_TRAIN,
        native_val_file=NATIVE_VAL, expected_native_train_tokens=NATIVE_TRAIN_TOKENS,
        native_val_tokens=NATIVE_VAL_TOKENS, native_train_sha256=TRAIN_SHA,
        native_val_sha256=VAL_SHA, qa_report=QA_REPORT, qa_report_sha256=LOCKED_QA_SHA,
        parent=str(PARENT.relative_to(ROOT)), parent_sha256=PARENT_SHA,
        micro_bs=MICRO_BS, accum=ACCUM, seq=SEQ, native_window_width=WINDOW_WIDTH,
        native_candidate_stride=WINDOW_WIDTH, grad_checkpoint=True, compile='default',
        optimizer='fresh AdamW plus Muon', adam_lr=1e-4, muon_lr=4e-4,
        scheduler='constant', quant_anneal=1., fresh_optimizer_moments=True,
        mtp=False, qa_followup=_qa_followup(),
        parent_source_overlap='NOT_AUDITED_AGAINST_ORIGINAL_PARENT_TRAINING',
        new_unique_source_tokens_claim=False)
    if not isinstance(contract, dict) or any(contract.get(k) != v for k, v in expected.items()):
        raise ValueError('fixed native/QA recipe, source or original parent declaration differs')
    native_tokens, max_steps, steps = (contract.get(k) for k in ('native_train_tokens', 'max_steps', 'steps'))
    if (type(native_tokens) is not int or native_tokens < 1 or type(max_steps) is not int
            or not 1 <= max_steps <= MAX_STEPS or type(steps) is not int
            or steps != min(max_steps, native_tokens // (2 * UPDATE_TARGETS)) or steps < 1):
        raise ValueError('steps must match the declared2x-pool integer calculation')
    actual, windows = steps * UPDATE_TARGETS, steps * UPDATE_WINDOWS
    if (contract.get('actual_pool_tokens') != native_tokens
            or contract.get('actual_draw_tokens') != actual
            or contract.get('pool_ratio') != native_tokens / actual
            or contract['pool_ratio'] < 2.
            or contract.get('native_windows') != windows
            or contract.get('native_candidate_windows') != native_tokens // WINDOW_WIDTH
            or contract.get('selected_raw_window_tokens') != windows * WINDOW_WIDTH
            or type(contract.get('native_seed')) is not int):
        raise ValueError('native exposure/count/ratio declaration differs')
    offsets = contract.get('native_train_offsets')
    _check_offsets(offsets, native_tokens, windows)
    if contract.get('native_train_offsets_sha256') != _sha(offsets):
        raise ValueError('native offset ordering/hash changed')
    return dict(status='CPU_DECLARATION_AND_OFFSETS_VALID', steps=steps,
                windows=windows, actual_draw_tokens=actual,
                pool_ratio=contract['pool_ratio'], file_content_verification=False,
                model_loaded=False, optimizer_updates=0)


def native_groups(contract, start_update=0):
    """Yield16 micros of8 OFFSET-LIST INDICES per update, without reading tokens.

    A driver obtains the actual source position with
    contract['native_train_offsets'][index]. start_update selects a suffix of
    this already-frozen order; it does not recreate weights or optimizer state.
    """
    validate_contract(contract)
    if type(start_update) is not int or not 0 <= start_update <= contract['steps']:
        raise ValueError('start_update must name a boundary in this fixed contract')
    for update in range(start_update, contract['steps']):
        start = update * UPDATE_WINDOWS
        yield [list(range(start + micro * MICRO_BS, start + (micro + 1) * MICRO_BS))
               for micro in range(ACCUM)]
