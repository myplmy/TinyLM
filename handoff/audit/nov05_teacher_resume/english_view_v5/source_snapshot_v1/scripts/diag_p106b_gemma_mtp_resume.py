#!/usr/bin/env python3
"""User-only MTP ON fork of the pinned OFF literal producer.

OFF inputs/batches/cursor are immutable read-only ancestors. Only ON batches
are written to a new namespace, starting after the four pinned ancestors.
No new sampler/thinking/context settings, semantic gate, download or coload.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack, contextmanager
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_gemma_literal_recovery as literal
from scripts import diag_p106b_gemma_deficit_production as producer
from scripts import diag_p106b_gemma_budget_resume as budget
from scripts import diag_p106b_gemma_telemetry_resume as telemetry
from scripts.p106b_mixed_scale import digest, safe_repo_path
from scripts.p106b_shards import verify
from scripts.p106b_stage_receipt import pipeline

PARENT = ROOT/'HF/sft_ready/p106b_gemma_deficit_v3'
PARENT_INPUT_SHA = '306C3C4B18DFCA7AC9B8CC0F6823A0B60B631B30583F4ED1358BD2A0B796D025'
PARENT_REPORT_SHAS = (
    'DF9D1E86BD7995905A13580E81C40BACB1A728AAA24B408075C0A9C09C97953A',
    'E51FA4F189A1319E0FEF99C0886B5F97CA59AA902F60F5C9C556D021C855BD1B',
    'C3F088B65D2CF1EA149D0E1EB014D361AFBC62F0A126C922ADD6FB425CAB2DA1',
    '53CF4CF9A4CC96C78D644014EE9A5FF84EFBC10917C0867DA1F0204210A91D59',
)
PAIR = ROOT/'test_result/evidence/p106b_gemma_mtp_production_order_v1_s1337/report.json'
PAIR_SHA = '33C3ADF93B2A6D08F6DF12EC0080E13B3AB33BD9962524E3367D6004776CF9B3'
PATHS = dict(OUTPUT=ROOT/'HF/sft_ready/p106b_gemma_deficit_mtp_v4',
    CORPUS=ROOT/'HF/sft_ready/p106b_capability_gemma_mtp_v5',
    WIRE=ROOT/'HF/sft_ready/p106b_capability_gemma_mtp_wire_v5',
    STUDENT=ROOT/'HF/sft_ready/p106b_capability_gemma_mtp_student_v5',
    EVALUATION=ROOT/'HF/sft_ready/p106b_gemma_mtp_capability_multiaxis_v5')
TAG = 'p106b_s4_gemma_capability300m_chat32_mtponv4_s1337'
VERSION = 'GEMMA_LITERAL_MTP_ON_FORK_V1'
CODE = ('scripts/diag_p106b_gemma_mtp_resume.py',
    'scripts/test_p106b_gemma_mtp_resume.py', *telemetry.CODE_PATHS,
    'scripts/diag_p106b_gemma_budget_resume.py')


def pinned_ancestors():
    if digest(safe_repo_path(PARENT/'inputs.json')) != PARENT_INPUT_SHA:
        raise ValueError('OFF input identity changed')
    found = sorted(PARENT.glob('batch_*'))
    if [p.name for p in found] != [f'batch_{i:06d}' for i in range(4)]:
        raise ValueError('OFF ancestors changed; do not mix concurrent production')
    result = []
    for directory, sha in zip(found, PARENT_REPORT_SHAS):
        path = safe_repo_path(directory/'report.json')
        if digest(path) != sha: raise ValueError('OFF report identity changed')
        report = json.loads(path.read_text(encoding='utf-8'))
        for key in ('raw_manifest', 'candidate_manifest'):
            if key in report: verify(directory, report[key])
        result.append((directory, report))
    return result


def require_pair():
    path = safe_repo_path(PAIR)
    if digest(path) != PAIR_SHA: raise ValueError('paired MTP evidence changed')
    report = json.loads(path.read_text(encoding='utf-8'))
    arms = report.get('arms', [])
    if (report.get('status') != 'MTP_PRODUCTION_COLLECTION_COMPLETE'
            or report.get('protocol') != 'production' or len(arms) != 4
            or any(a.get('accepted') != 6 or a.get('requests') != 6 for a in arms)):
        raise FileNotFoundError('completed ordered production pair required')
    verify(path.parent, report['raw_manifest'])
    return PAIR_SHA


def combined_batches(ancestors, destination):
    yield from ancestors
    directories = sorted(destination.glob('batch_*'))
    for index, directory in enumerate(directories, len(ancestors)):
        if directory.name != f'batch_{index:06d}': raise ValueError('ON batch sequence gap')
        path = safe_repo_path(directory/'report.json')
        if not path.is_file(): raise FileExistsError('unfinished ON batch; inspect before resume')
        report = json.loads(path.read_text(encoding='utf-8'))
        if (report.get('input', {}).get('production_fork') != VERSION
                or report['input'].get('mtp') is not True):
            raise ValueError('non-ON batch in fork')
        yield directory, report


def replay(tok, base):
    control = producer.control
    state = control.Quotas(tok)
    for row in control.base_rows(base):
        if state.admit(row, base=True) is None: raise ValueError('base replay changed')
    if dict(state.tokens) != base['nonpadding_tokens']: raise ValueError('base counts changed')
    cursor = (-1, -1)
    batches = list(control.batch_reports())
    for directory, report in batches:
        if report.get('base_report_sha256') != control.BASE_SHA: raise ValueError('base lineage changed')
        if 'raw_manifest' in report: verify(directory, report['raw_manifest'])
        if 'candidate_manifest' in report:
            for row in control.rows(directory, report['candidate_manifest']):
                if state.admit(row) is None: raise ValueError('saved candidate no longer admissible')
        if dict(state.tokens) != report['nonpadding_tokens']: raise ValueError('saved counter changed')
        cursor = tuple(report['cursor'])
    return state, cursor, len(batches)


@contextmanager
def on_scope():
    with literal.literal_scope(), literal.previous.recovery_scope():
        ancestors = pinned_ancestors()
        pair_sha = require_pair()
        original_require = producer.require_pilots
        original_info = original_require()
        saved = json.loads((PARENT/'inputs.json').read_text(encoding='utf-8'))
        if saved != original_info: raise ValueError('old literal controls changed')
        real_session = producer.teacher.GemmaSession
        original_group = producer.produce_group
        quota_type = producer.control.Quotas
        def info():
            current = original_require()
            return dict(current, mtp=True, production_fork=VERSION, pair_report_sha256=pair_sha,
                off_parent_input_sha256=PARENT_INPUT_SHA, off_parent_reports=list(PARENT_REPORT_SHAS),
                runtime_code_sha256={p:digest(ROOT/p) for p in CODE},
                speculative=dict(type='draft-mtp', n_max=2),
                reasoning_depth='UNMEASURED; identical budgets do not imply identical thinking')
        def group(*args, **kwargs):
            row = original_group(*args, **kwargs)
            if row is not None: row['meta'].update(teacher_mtp=True, production_fork=VERSION)
            return row
        class ForkQuotas(quota_type):
            def report(self):
                return dict(super().report(), teacher_production_fork=VERSION,
                    teacher_profiles=['OFF_PINNED_ANCESTORS', 'ON_NEW_BATCHES'],
                    off_parent_input_sha256=PARENT_INPUT_SHA, off_parent_reports=list(PARENT_REPORT_SHAS))
        with ExitStack() as stack:
            for module, name, value in (
                (producer, 'require_pilots', info), (producer, 'state_from_saved', replay),
                (producer, 'produce_group', group),
                (producer.teacher, 'GemmaSession', lambda _old_flag: real_session(True)),
                (producer.control, 'Quotas', ForkQuotas),
                (producer.control, 'batch_reports', lambda: combined_batches(ancestors, PATHS['OUTPUT'])),
                (producer.control, 'TAG', TAG)):
                stack.enter_context(patch.object(module, name, value))
            for name, path in PATHS.items(): stack.enter_context(patch.object(producer.control, name, path))
            yield


def dispatch(args, execute):
    with on_scope():
        info = producer.require_pilots()
        producer.control.base_report()
        destination = PATHS['OUTPUT']
        if args.mode == 'start' and destination.exists(): raise FileExistsError('ON fork exists; explicit resume only')
        if args.mode == 'resume' and not destination.is_dir(): raise FileNotFoundError('ON fork absent; start first')
        if not execute and args.mode in ('start', 'resume', 'finalize'):
            print('[CHECK_ONLY] '+json.dumps(info, ensure_ascii=False)); return 0
        if args.mode in ('start', 'resume'):
            reader = telemetry.RetryingMemoryReader(telemetry.memory_source.read_memory,
                emit=lambda line: print(line, flush=True))
            evidence = dict(expired=False)
            try:
                with telemetry.telemetry_scope(reader), budget.production_budget_scope(evidence):
                    return producer.production(resume=args.mode == 'resume', max_wall_sec=args.max_wall_sec)
            finally:
                print('[MTP_ON_TELEMETRY] '+json.dumps(dict(telemetry=reader.snapshot(), budget=evidence,
                    safety='GAPPED_OR_SAMPLED_ONLY; not continuous peak/OOM proof'), ensure_ascii=False), flush=True)
        if args.mode == 'finalize':
            saved = json.loads(safe_repo_path(destination/'inputs.json').read_text())
            if saved != info: raise ValueError('ON fork controls changed')
            from tokenizers import Tokenizer
            if digest(producer.TOKENIZER) != producer.TOK_SHA: raise ValueError('tokenizer changed')
            report = producer.control.finalize(Tokenizer.from_file(str(producer.TOKENIZER)))
            print('[FINAL_CORPUS] '+json.dumps(report, ensure_ascii=False)); return 0
        result = (producer.control.evaluate(execute=execute) if args.mode == 'eval' else
            producer.control.learner(args.mode == 'wire', execute=execute))
        if not execute: print('[CHECK_ONLY] '+json.dumps(result)); return 0
        return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=('start','resume','finalize','wire','train','eval'), required=True)
    p.add_argument('--max-wall-sec', type=int, default=21600)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--execute', action='store_true'); g.add_argument('--check-only', action='store_true')
    a = p.parse_args()
    if not 60 <= a.max_wall_sec <= 21600: p.error('bounded production window required')
    def run(command):
        if command[0] in ('PREFLIGHT', 'EXECUTE'):
            try: return dispatch(a, command[0] == 'EXECUTE')
            except (FileNotFoundError, FileExistsError) as exc: print('[HOLD] '+str(exc), flush=True); return 8
            except KeyboardInterrupt: return 130
            except Exception as exc: print('[ERROR] '+type(exc).__name__+': '+str(exc), flush=True); return 9
        return subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL).returncode
    if a.check_only: return run(['PREFLIGHT'])
    return pipeline([('REGRESSION', [sys.executable,'-B','-X','utf8','-m','unittest',
        'scripts.test_p106b_gemma_mtp_resume','scripts.test_p106b_gemma_budget_resume']),
        ('PREFLIGHT',['PREFLIGHT']),('EXECUTE',['EXECUTE'])], run,
        lambda line: print(line, flush=True), experiment=VERSION+'_'+a.mode)['returncode']


if __name__ == '__main__': raise SystemExit(main())
