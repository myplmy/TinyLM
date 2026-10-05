#!/usr/bin/env python3
"""Bounded Qwen role + real chat32 micro8/accum16 coload, no checkpoint writes.

--check-only does not load a model or query GPU. Execution creates a new evidence
JSON only. The four teacher answers are a small workload, not corpus approval.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import json
import math
from pathlib import Path
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_qwen_teacher as profile
from scripts.diag_p106b_mtp_teacher import Session, owned_rss
from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit, disposition, GateNegative
from scripts.p106b_education_followup import arm_inputs
from scripts.p106b_teacher_format import parse_reply
from scripts.p106b_mtp_teacher import response_metrics

NAME = 'P106B_Stage6aW_qwen_chat32_coload_role'
OUTPUT = ROOT / 'test_result/evidence/101_P106B_Stage6aW_qwen_chat32_coload_role.json'


class QwenSession(Session):
    def __enter__(self):
        from scripts.diag_p106_vram_sample import read_memory
        from scripts.diag_p106b_online_rate5 import capture_server_line
        self.baseline_used, self.baseline_free = read_memory()
        before = time.perf_counter()
        try:
            self.process = subprocess.Popen(profile.command(self.port, self.key), cwd=ROOT,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', errors='replace', bufsize=1, start_new_session=True)
            def drain():
                for line in self.process.stdout:
                    capture_server_line(line, self.signals, self.tail, self.key)
            def sample():
                while not self.stop.is_set():
                    try:
                        used, free = read_memory()
                        rss = owned_rss(self.process.pid)
                        if rss is not None: self.samples.append(dict(used=used, free=free, rss_mib=rss))
                        if free < 512: self.errors.append('FREE_LT_512'); return
                    except Exception as exc: self.errors.append(type(exc).__name__); return
                    self.stop.wait(.2)
            for fn in (drain, sample):
                worker = threading.Thread(target=fn, daemon=True)
                worker.start(); self.workers.append(worker)
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                self.check()
                try: self.request('/health', timeout=3); break
                except (OSError, ValueError): time.sleep(.25)
            else: raise TimeoutError('owned teacher health deadline')
            self.props = self.request('/props')
            if self.props.get('total_slots') != 1: raise ValueError('one slot not confirmed')
            self.startup_sec = time.perf_counter() - before
            return self
        except BaseException:
            self.__exit__(); raise

    def __exit__(self, *_):
        super().__exit__()
        if self.process is not None and self.process.stdout is not None:
            self.process.stdout.close()


def check():
    if OUTPUT.exists() or OUTPUT.is_symlink(): raise FileExistsError('preserve prior output, use new stage/version')
    spec = arm_inputs('b')
    return dict(profile.assets(True), schema='P106B_QWEN_COLOAD_ROLE_V1',
        parent=spec['parent'], parent_sha256=spec['sha'], tokenizer_sha256=spec['tok_sha'],
        micro_bs=8, accum=16, seq=1024, grad_checkpoint=True, compile='default',
        optimizer_updates=1, padded_slots=131072, meaningful_training='NOT_RUN',
        source='four code-authored benign role questions plus synthetic full-width resource input',
        max_wall_sec=1200, gpu_layers='all', output=str(OUTPUT.relative_to(ROOT)),
        code_sha256={p: profile.digest(ROOT / p) for p in (
            'scripts/p106b_qwen_teacher.py', 'scripts/diag_p106b_qwen_coload.py',
            'scripts/p106b_education_followup.py', 'scripts/train_sft_p090.py')})


def request_case(session, case, seed):
    before = time.perf_counter()
    reply = session.request('/v1/chat/completions', profile.payload(case, seed), timeout=180)
    session.check()
    metric = response_metrics(reply, time.perf_counter() - before)
    parsed = parse_reply(reply, language=case['language'])
    print('[TEACHER_ANSWER] ' + json.dumps(dict(id=case['id'], question=case['question'],
        final=metric['final_text'], finish_reason=metric['finish_reason'],
        wire_status=parsed['format_status'], wall_sec=metric['request_wall_sec']), ensure_ascii=False), flush=True)
    return dict(case=case, seed=seed, reply=reply, metrics=metric, parsed=parsed,
                semantic_truth='NOT_REVIEWED')


def student_update(session, report):
    from scripts.p106b_education_followup import load_student
    from scripts.train_sft_p090 import encode_records, loss_sum
    torch, model, base, cfg, tok, adam, muon = load_student('b', training=True)
    report['student_loaded'] = True
    print('[STUDENT_READY] chat32 dense14 micro8 accum16 checkpoint ON compile default seq1024', flush=True)
    rows = [{'messages': [{'role': 'user', 'content': '2 더하기 3은 얼마인가요?'},
                          {'role': 'assistant', 'content': '5'}], 'meta': {}}]
    encoded = encode_records(rows, tok, 1024, cfg.vocab_size)
    x, y, targets = encoded[0]
    pad_id = tok.token_to_id('<|pad|>')
    if pad_id is None: pad_id = 0
    # Padding to full1024 is intentional: short true conversations underestimate VRAM.
    batch = [(x + [pad_id] * (1024-len(x)), y + [-100] * (1024-len(y)), targets)] * 8
    adam.zero_grad(set_to_none=True); muon.zero_grad(set_to_none=True)
    torch.cuda.reset_peak_memory_stats()
    model.train(); times = []; losses = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        concurrent_answer = pool.submit(request_case, session, profile.cases()[0], 1441)
        begin = time.perf_counter()
        for index in range(16):
            session.check(); t = time.perf_counter()
            ce = loss_sum(model, batch, pad_id, 'cuda', cfg.vocab_size, 2048) / (targets * 128)
            if not torch.isfinite(ce): raise ValueError('nonfinite resource CE')
            ce.backward(); torch.cuda.synchronize()
            times.append(time.perf_counter()-t); losses.append(float(ce.detach()))
            print(f'[STUDENT_MICRO] {index+1}/16 sec={times[-1]:.3f}', flush=True)
        grad = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        if not torch.isfinite(grad): raise ValueError('nonfinite resource gradient')
        adam.step(); muon.step(); torch.cuda.synchronize()
        report['student'] = dict(optimizer_updates=1, microbatch_seconds=times,
            total_sec=time.perf_counter()-begin, loss_sum_normalized=sum(losses), grad_norm=float(grad),
            torch_peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
            torch_peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,
            scope='synthetic assistant-masked resource update only; repeated one QA, padded fullwidth1024',
            padded_slots=131072, nonpadding_tokens=len(x)*128, assistant_targets=targets*128,
            checkpoint_saved=False)
        report['concurrent_teacher'] = concurrent_answer.result(timeout=185)
    session.check()


def execute(info):
    report = dict(input=info, schema=info['schema'], status='STARTED', returncode=None,
        teacher_answers=[], student_loaded=False, student_oom=False, checkpoint_saved=False,
        formal_sft='NOT_RUN', teacher_default_adoption='NOT_RUN')
    start = time.perf_counter(); session = None
    try:
        idle_before_gpu()
        with wall_limit(1200), QwenSession('qwen') as session:
            report['teacher_startup_sec'] = session.startup_sec
            report['server_props'] = session.props
            for index, case in enumerate(profile.cases()):
                report['teacher_answers'].append(request_case(session, case, 1337+index))
            report['teacher_only_memory'] = session.memory()
            student_update(session, report)
            report['memory'] = session.memory()
            ok = all(r['parsed']['format_status']=='TAGGED_COMPLETE' for r in report['teacher_answers'])
            report.update(status='RESOURCE_AND_ROLE_WIRE_PASSED' if ok else 'RESOURCE_PASS_ROLE_WIRE_NEGATIVE',
                          returncode=0 if ok else 8)
    except BaseException as exc:
        status, rc = disposition(exc)
        report.update(status=status, returncode=rc, error_type=type(exc).__name__, error=str(exc)[:1600],
                      student_oom=type(exc).__name__=='OutOfMemoryError')
        # Backend allocation failure and low-free margin are not a PyTorch student OOM.
        if session is not None and session.samples:
            report['partial_memory'] = dict(sample_count=len(session.samples),
                sampled_gpu_global_peak_mib=max(s['used'] for s in session.samples),
                sampled_gpu_min_free_mib=min(s['free'] for s in session.samples),
                telemetry_errors=list(session.errors))
    finally:
        if session is not None:
            report.update(server_signals=session.signals, server_tail=session.tail)
        report['wall_sec'] = time.perf_counter()-start
        with OUTPUT.open('x', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2); f.write('\n')
        print('[QWEN_GATE_FINAL] '+json.dumps({k: report.get(k) for k in
            ('status','returncode','student_loaded','student_oom','wall_sec')}, ensure_ascii=False), flush=True)
        print('[EVIDENCE] '+str(OUTPUT.relative_to(ROOT)), flush=True)
    return report['returncode']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    a = p.add_mutually_exclusive_group(required=True)
    a.add_argument('--execute', action='store_true'); a.add_argument('--check-only', action='store_true')
    args = p.parse_args()
    try:
        info = check()
        if args.check_only:
            print('[CHECK_ONLY] '+json.dumps(info, ensure_ascii=False)); return 0
        return execute(info)
    except (ValueError, FileNotFoundError, FileExistsError) as exc:
        print('[PRECHECK_ERROR] '+str(exc), file=sys.stderr); return 9


if __name__=='__main__': raise SystemExit(main())
