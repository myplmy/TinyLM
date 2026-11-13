#!/usr/bin/env python3
"""Read-only real replay/asset preflight; only a fresh small audit is written.

Usage: python -m scripts.diag_p106b_nov05_supported_ready OUTPUT_JSON
The published production tree, STOP markers and public sources are read-only.
No GemmaSession, server, GPU, optimizer or downloads are invoked.
"""
from pathlib import Path
import hashlib
import json
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import diag_p106b_supported_production8h as supported


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest().upper()


def snapshot(destination):
    result = {}
    for directory in sorted(destination.glob('batch_*')):
        for path in sorted(directory.iterdir()):
            if path.is_symlink() or not path.is_file():
                raise ValueError('unexpected published batch path')
            result[str(path.relative_to(ROOT))] = sha(path)
    return result


def preflight():
    from tokenizers import Tokenizer
    from scripts.p106b_mixed_scale import TOKENIZER, TOK_SHA
    destination = supported.OUTPUT
    before = snapshot(destination)
    with supported.scope(destination) as (producer, info):
        saved = json.loads((destination / 'inputs.json').read_text(encoding='utf-8'))
        if saved != info:
            raise ValueError('saved V3 source/prompt/pilot controls differ')
        pilot = supported.require_pilot(info)
        base = producer.control.base_report()
        public = {}
        for item in base['sources']:
            path = (ROOT / item['path']).resolve()
            if path.is_symlink() or path.parts[len(ROOT.parts):len(ROOT.parts) + 2] != ('HF', 'sft_sources'):
                raise ValueError('only exact pinned public source files permitted')
            actual = sha(path)
            if actual != item['sha256']:
                raise ValueError('pinned public source changed')
            public[item['path']] = actual
        if sha(TOKENIZER) != TOK_SHA:
            raise ValueError('student tokenizer changed')
        tok = Tokenizer.from_file(str(TOKENIZER))
        quota, cursor, count = producer.state_from_saved(tok, base)
        closed = list(producer.control.batch_reports())
        if count != len(closed) or not closed or list(cursor) != closed[-1][1]['cursor']:
            raise ValueError('real replay count/cursor differs')
        if quota.report()['nonpadding_tokens'] != closed[-1][1]['nonpadding_tokens']:
            raise ValueError('real replay token quotas differ')
        assets = producer.teacher.assets(True)
        role = producer.gate.read_report(producer.gate.previous.role_gate.OUTPUT / 'role/report.json', producer.gate.ROLE_SHA)
        for key in ('model_sha256', 'draft_sha256'):
            if assets[key] != role['input']['asset_identity'][key]:
                raise ValueError('exact current MTP teacher differs')
        after = snapshot(destination)
        if before != after:
            raise ValueError('published batch bytes changed during read-only preflight')
        return dict(schema='P106B_NOV05_READ_ONLY_READY_V1', authority_directive=109,
            status='TECHNICAL_INPUTS_READY_NOT_SEMANTIC_APPROVAL', original_batches=count,
            original_file_count=len(before), original_files=before, original_files_unchanged=True,
            cursor=list(cursor), quotas=quota.report(), public_source_sha256=public,
            inputs_sha256=sha(destination / 'inputs.json'), visible_source_contract=supported.VERSION,
            pilot_accepted_groups=pilot['accepted_groups'], mtp=info['mtp'],
            model_sha256=assets['model_sha256'], draft_sha256=assets['draft_sha256'],
            model_loading=False, server_started=False, production_started=False,
            source_code_sha256=info['code_sha256'], source_rights_status='UNCHANGED_NOT_NEW_APPROVAL',
            semantic_quality='NOT_REVIEWED', formal_train_ready=False)


def main():
    if len(sys.argv) != 2:
        raise SystemExit('one fresh repository audit JSON path required')
    target = (ROOT / sys.argv[1]).resolve()
    if ROOT not in target.parents or target.exists() or target.is_symlink():
        raise ValueError('fresh repository audit path required')
    started = time.monotonic()
    failed = None
    try:
        report = preflight()
    except BaseException as exc:
        failed = exc
        report = dict(schema='P106B_NOV05_READ_ONLY_READY_V1', status='ERROR',
                      error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc(),
                      model_loading=False, server_started=False, production_started=False)
    report['whole_wall_seconds'] = time.monotonic() - started
    raw = (json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + chr(10)).encode('utf-8')
    if len(raw) >= 4_000_000:
        raise ValueError('small readiness report exceeds limit')
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as f:
        f.write(raw)
    print('[READY_CHECK] ' + json.dumps({k: report.get(k) for k in
          ('status', 'original_batches', 'original_file_count', 'cursor', 'whole_wall_seconds')}), flush=True)
    if failed is not None:
        raise failed


if __name__ == '__main__':
    main()
