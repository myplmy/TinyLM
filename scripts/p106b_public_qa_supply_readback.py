#!/usr/bin/env python3
"""Independent readback of the immutable QA inventory; JSON wire types only.

The original collector/report/checker remain byte-identical. This reader keeps
every original raw/source/cap/denominator guard and fixes only tuple -> JSON-array
metadata comparison. It never loads a model, tokenizer or teacher.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
import ast
from datetime import datetime, timezone
import json
import re
import subprocess
import time
from scripts import diag_p106b_public_qa_supply as frozen
from scripts.p106b_stage_receipt import pipeline

END = datetime(2026, 10, 20, 8, tzinfo=timezone.utc)
CALLS = ('required', 'safe', 'info', 'load_baseline', 'read_shards', 'detail_summary', 'membership', 'compare_caps')
CODE = ('scripts/p106b_public_qa_supply_readback.py', 'scripts/test_p106b_public_qa_supply_readback.py')
PrerequisitePending = frozen.PrerequisitePending


def wire(value):
    """JSON arrays encode tuples/lists alike; scalar types/content remain exact."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def adapt_source(source):
    if source.count('def check():') != 1 or source.count('report.get(k) != v') != 1:
        raise ValueError('exact single frozen comparison/name edit required')
    source = source.replace('def check():', 'def check_inventory():', 1)
    source = source.replace('report.get(k) != v', 'wire(report.get(k)) != wire(v)', 1)
    for name in CALLS:
        source = re.sub(r'(?<![\w.])' + name + r'(?=\()', 'frozen.' + name, source)
    for name in ('LOCAL', 'EVIDENCE', 'TAG', 'ROOT'):
        source = re.sub(r'\b' + name + r'\b', 'frozen.' + name, source)
    return re.sub(r'(?<![\w.])data(?=\.)', 'frozen.data', source)


def core_equivalence(original=None, candidate=None):
    original = Path(frozen.__file__).read_text(encoding='utf-8') if original is None else original
    candidate = Path(__file__).read_text(encoding='utf-8') if candidate is None else candidate
    def segment(text, name):
        node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == name)
        return ast.get_source_segment(text, node)
    expected = adapt_source(segment(original, 'check')); actual = segment(candidate, 'check_inventory')
    if expected != actual or ast.dump(ast.parse(expected), include_attributes=False) != ast.dump(ast.parse(actual), include_attributes=False):
        raise ValueError('readback changed beyond one JSON wire comparison and explicit frozen namespace/name')
    return dict(ast_and_character_equal_after_declared_edits=True,
        original_source_sha256=frozen.data.sha(segment(original, 'check')),
        reader_core_sha256=frozen.data.sha(actual),
        allowed_difference='check name, explicit immutable module namespace, JSON wire equality only')


def check_inventory():
    report = frozen.required(frozen.EVIDENCE / 'report.json')
    if report.get('status') != 'CPU_PUBLIC_QA_SUPPLY_COMPLETE_NO_TRAINING_CLAIM':
        raise PrerequisitePending('complete public QA supply inventory required')
    if any(wire(report.get(k)) != wire(v) for k, v in frozen.info().items()): raise ValueError('inventory source/code/claim contract changed')
    if (report.get('cuda_initialized') is not False or report.get('source_text_or_qa_copied_to_output') is not False
            or report.get('free_answer_quality') != 'NOT_MEASURED'):
        raise ValueError('CPU-only inventory evidence boundary changed')
    for language, splits in frozen.data.SOURCES.items():
        for _, (relative, expected) in splits.items():
            if frozen.data.digest(frozen.safe(frozen.ROOT / relative)) != expected: raise ValueError('original source changed after inventory')
    baseline, index = frozen.load_baseline()
    if report.get('baseline') != baseline: raise ValueError('source32k report/manifests changed')
    stem = 'baseline'; manifest = report.get('baseline_manifest', {})
    expected_lineage = dict(tag=frozen.TAG, purpose='IDS_AND_ENCODING_COUNTS_ONLY', code_sha256=frozen.info()['code_sha256'])
    if manifest.get('lineage') != expected_lineage: raise ValueError('baseline manifest source/code lineage differs')
    if frozen.data.digest(frozen.safe(frozen.LOCAL / (stem + '_shards_manifest.json'))) != report.get('baseline_manifest_sha256'):
        raise ValueError('baseline ID manifest changed')
    if frozen.read_shards(frozen.LOCAL, manifest, stem) != sorted(index.values(), key=lambda v: v['root']):
        raise ValueError('full baseline ID/signature cohort differs')
    details = {}
    for cap in (2, 4):
        cohort = report['cohorts'][str(cap)]; stem = 'cap' + str(cap)
        if (cohort.get('policy') != ('REFERENCE_CAP2' if cap == 2 else 'HYPOTHETICAL_NOT_ADOPTED')
                or cohort.get('detail_manifest', {}).get('lineage') != expected_lineage):
            raise ValueError('cap policy or detail lineage changed')
        if frozen.data.digest(frozen.safe(frozen.LOCAL / (stem + '_shards_manifest.json'))) != cohort.get('detail_manifest_sha256'):
            raise ValueError('inventory detail manifest changed')
        rows = frozen.read_shards(frozen.LOCAL, cohort['detail_manifest'], stem)
        if any(r.get('cap') != cap for r in rows): raise ValueError('inventory cap label changed')
        if frozen.detail_summary(rows) != cohort.get('summary') or frozen.membership(rows, index, require_all=cap == 2) != cohort.get('source32k_membership'):
            raise ValueError('raw inventory denominator or source32k membership differs')
        details[cap] = rows
    if frozen.compare_caps(details[2], details[4]) != report.get('cap_comparison'):
        raise ValueError('raw cap common/additional/missing recount differs')
    print('[PUBLIC_QA_SUPPLY_CHECK] raw count/ID/source/code matched; no quality or75M claim', flush=True)
    return 0

def metadata():
    return dict(schema='P106B_PUBLIC_QA_SUPPLY_READBACK_V1', tag=frozen.TAG,
        reader_code_sha256={p: frozen.data.digest(ROOT / p) for p in CODE},
        frozen_code_sha256=frozen.info()['code_sha256'], model_loaded=False,
        tokenizer_loaded=False, gpu_initialized=False, training=False,
        quality='NOT_MEASURED', no_additive75m_claim=True)


def run_check():
    began = time.perf_counter()
    if (END - datetime.now(timezone.utc)).total_seconds() < 3600:
        raise frozen.PrerequisitePending('one-hour final record reserve required')
    proof = core_equivalence()
    check_inventory()
    report = frozen.required(frozen.EVIDENCE / 'report.json')
    result = dict(metadata(), status='FROZEN_INVENTORY_RAW_READBACK_COMPLETE',
        source_report_sha256=frozen.data.digest(frozen.EVIDENCE / 'report.json'),
        core_equivalence=proof, errors=0, whole_seconds=time.perf_counter() - began,
        summary={cap: value['summary'] for cap, value in report['cohorts'].items()},
        cap_comparison=report['cap_comparison'], source_text_or_qa_copied_to_output=False,
        existing29m_overlap='NOT_MEASURED', new75m_quota_integration='NOT_MEASURED',
        training_policy_adopted=False)
    frozen.write(frozen.EVIDENCE / 'raw_readback_v1.json', result)
    print('[PUBLIC_QA_SUPPLY_READBACK] complete exact raw/source/ID/count recount; quality/quota not adopted', flush=True)
    return 0


def phase_commands():
    py = [sys.executable, '-B', '-X', 'utf8']
    driver = py + ['scripts/p106b_public_qa_supply_readback.py', '--mode', 'check']
    return [('REGRESSION', py + ['-m', 'unittest', 'scripts.test_p106b_public_qa_supply_readback', '-v']),
            ('PREFLIGHT', driver + ['--check-only']), ('EXECUTE', driver + ['--execute'])]


def run_pipeline():
    def launch(command):
        print('[PHASE_COMMAND] ' + json.dumps(command), flush=True)
        try:
            return subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL, timeout=300).returncode
        except (subprocess.TimeoutExpired, OSError):
            return 9
        except KeyboardInterrupt:
            return 130
    return pipeline(phase_commands(), launch, lambda line: print(line, flush=True),
                    experiment='P106B_PUBLIC_QA_SUPPLY_RAW_READBACK')['returncode']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('check', 'pipeline'), default='check')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true')
    action.add_argument('--check-only', action='store_true')
    args = parser.parse_args(argv)
    if args.check_only:
        print('[PUBLIC_QA_READBACK_CHECK_ONLY] ' + json.dumps(dict(metadata(), core_equivalence=core_equivalence())))
        return 0
    try:
        return run_pipeline() if args.mode == 'pipeline' else run_check()
    except frozen.PrerequisitePending as exc:
        print('[PUBLIC_QA_READBACK_NOT_RUN8] ' + str(exc), flush=True); return 8
    except KeyboardInterrupt:
        print('[PUBLIC_QA_READBACK_INTERRUPTED130]', flush=True); return 130
    except Exception as exc:
        print('[PUBLIC_QA_READBACK_TOOL_ERROR9] ' + type(exc).__name__ + ': ' + str(exc), flush=True); return 9


if __name__ == '__main__':
    raise SystemExit(main())
