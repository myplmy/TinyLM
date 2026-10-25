#!/usr/bin/env python3
"""Falcon만의 새 문법 평가 창. 기존 공식 계산·자료·모델 실행기는 변경하지 않는다.

기본/--check-only는 표준 라이브러리와 소스 metadata만 사용한다. 실제 prepare와
GPU cost/full은 root가 --execute와 정확 source SHA를 명시할 때만 수행한다.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_babylm_causal as original

TAG = "p106b_babylm_falcon_window_v1_s1337"
SCHEMA = "P106B_BABYLM_FALCON_WINDOW_V1"
OUTPUT = ROOT / "test_result/evidence" / TAG
MODEL = "falcon90m"
DEADLINE_ISO = "2026-10-24T08:40:00+09:00"
LATEST_DEADLINE = datetime.fromisoformat(DEADLINE_ISO).timestamp()
LIMIT = 19_999_999
OWN_FILES = ("scripts/diag_p106b_babylm_window.py", "scripts/test_p106b_babylm_window.py",
             "scripts/diag_p106b_external_core6.py", "scripts/test_p106b_external_core6.py")


def identity(root=ROOT):
    files = dict(original.identity()["files"])
    files.update({name: original.digest(Path(root) / name) for name in OWN_FILES})
    return dict(files=files, sha256=original.object_sha(files))


def finite(value, *, positive=False):
    return type(value) in (int, float) and math.isfinite(value) and (value > 0 if positive else value >= 0)


def window(deadline, max_wall_sec, mode, *, now=None):
    if mode not in ("prepare", "canary", "cost", "full"):
        raise ValueError("등록한 단계만 허용한다")
    parsed = datetime.fromisoformat(deadline)
    if parsed.tzinfo is None or not math.isfinite(parsed.timestamp()) or parsed.timestamp() > LATEST_DEADLINE:
        raise ValueError("시간대가 있는 10월24일08:40 이전 마감이 필요하다")
    upper = 7200 if mode == "full" else 600
    if type(max_wall_sec) is not int or not 60 <= max_wall_sec <= upper:
        raise ValueError("단계별60초 이상/등록된 최대 상한이 필요하다")
    now = time.time() if now is None else now
    remaining = parsed.timestamp() - now - 30
    if not finite(remaining, positive=True) or remaining < 60:
        raise ValueError("정리30초를 남긴 실행 창이 없다")
    return dict(deadline_epoch=parsed.timestamp(), deadline=parsed.isoformat(),
                hard_cap_seconds=min(max_wall_sec, int(remaining)), cleanup_reserve_seconds=30)


def check_time(admission, started, *, now=None, elapsed=None):
    now = time.time() if now is None else now
    elapsed = time.perf_counter() - started if elapsed is None else elapsed
    if (not finite(elapsed) or elapsed >= admission["hard_cap_seconds"] - 20
            or now >= admission["deadline_epoch"] - 20):
        raise TimeoutError("소유 평가의 시간 상한 또는 절대 마감에 도달했다")


def reserve(directory):
    directory = Path(directory)
    if any(p.is_symlink() for p in (directory, *directory.parents)):
        raise ValueError("연결 경로에는 새 평가를 기록하지 않는다")
    directory.mkdir(parents=True, exist_ok=False)
    return directory


def read_report(path):
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file() or path.stat().st_size > LIMIT:
        raise ValueError("명시된20MB 미만의 닫힌 보고서가 필요하다")
    return json.loads(path.read_text(encoding="utf-8"))


def full_admission(cost, signature, admission, *, now=None):
    required = dict(schema=SCHEMA, tag=TAG, model=MODEL, mode="cost", returncode=0,
                    status="BABYLM_WINDOW_COST_COMPLETE", source_identity=signature,
                    policy=original.policy(), inputs_unchanged=True, sources_unchanged=True)
    if any(cost.get(k) != v for k, v in required.items()):
        raise ValueError("새 namespace의 같은 source·정책·Falcon cost가 필요하다")
    if {k: v.get("rows") for k, v in cost.get("group_audits", {}).items()} != {"main": 536, "supplement": 40}:
        raise ValueError("새 cost의 정확한536/40분모가 필요하다")
    if cost.get("raw_independent_recount") is not True or cost.get("numerical_canary_passed") is not True:
        raise ValueError("새 수치 oracle와 원형 재계수가 필요하다")
    times = cost.get("evaluation_seconds", {})
    wall = cost.get("wall_seconds")
    if set(times) != set(original.EXPECTED) or not all(finite(v, positive=True) for v in times.values()) or not finite(wall, positive=True):
        raise ValueError("유한한 양수의 과제별 실측 시간이 필요하다")
    overhead = max(0., wall - math.fsum(times.values()))
    forecast = math.fsum(original.EXPECTED[k]["rows"] * times[k] / cost["group_audits"][k]["rows"]
                         for k in original.EXPECTED) * 1.5 + overhead + 120
    now = time.time() if now is None else now
    if not finite(forecast, positive=True) or forecast > admission["hard_cap_seconds"] or now + forecast + 30 > admission["deadline_epoch"]:
        raise ValueError("같은 계산의 full 외삽이7200초/실제 남은 마감을 넘는다")
    return dict(admission, forecast_seconds=forecast, observed_non_eval_overhead_seconds=overhead,
                forecast_multiplier=1.5, fixed_overhead_reserve_seconds=120)


def recount_pairs(directory, manifest, expected_rows, expected_uids, summary):
    from scripts.p106b_shards import verify
    verify(Path(directory), manifest)
    by_uid = defaultdict(lambda: dict(total=0, correct=0))
    score_sha = hashlib.sha256()
    count = ties = 0
    for shard in manifest["shards"]:
        with (Path(directory) / shard["path"]).open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                scores = row.get("scores", ())
                if (row.get("index") != count or row.get("label") != 0
                        or type(row.get("chosen")) is not int or row["chosen"] not in (0, 1)
                        or len(scores) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in scores)
                        or scores[row["chosen"]] != max(scores) or not isinstance(row.get("uid"), str)
                        or type(row.get("exact_tie")) is not bool or row["exact_tie"] != (scores[0] == scores[1])):
                    raise ValueError("문법 원형의 순서·정답·우도·동점 계약이 다르다")
                by_uid[row["uid"]]["total"] += 1
                by_uid[row["uid"]]["correct"] += int(row["chosen"] == 0)
                ties += int(row["exact_tie"])
                score_sha.update(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8"))
                count += 1
    if count != expected_rows or len(by_uid) != expected_uids:
        raise ValueError("전체 행/UID 분모가 다르다")
    macro = math.fsum(100 * v["correct"] / v["total"] for v in by_uid.values()) / len(by_uid)
    if (summary.get("rows") != count or summary.get("uids") != len(by_uid) or summary.get("by_uid") != dict(by_uid)
            or summary.get("scores_sha256") != score_sha.hexdigest().upper() or summary.get("exact_ties") != ties
            or not math.isclose(summary["uid_macro_percent"], macro, abs_tol=1e-10, rel_tol=1e-12)):
        raise ValueError("저장 원형과 공식 UID macro/관찰 집계가 다르다")
    return dict(rows=count, uids=len(by_uid), uid_macro_percent=macro, raw_sha_verified=True)


def close_partial(writer, report):
    if writer is None:
        return
    try:
        if writer._total_rows:
            report["partial_pair_manifest"] = writer.close(lineage=dict(complete=False))
        else:
            writer._finish()
    except BaseException as exc:
        report["partial_close_error"] = dict(type=type(exc).__name__, message=str(exc)[:1000])


def cleanup_owned(torch, report, idle_fn=None):
    """소유 Python 참조만 정리한다. 다른 PID를 종료하거나 장치를 reset하지 않는다."""
    import gc
    report["owned_cleanup_attempted"] = True
    try:
        gc.collect()
        torch.cuda.empty_cache()
        if idle_fn is not None:
            report["cleanup_gpu_point_query"] = idle_fn()
        report["owned_cleanup_complete"] = True
    except BaseException as exc:
        report["owned_cleanup_complete"] = False
        report["cleanup_error"] = dict(type=type(exc).__name__, message=str(exc)[:1000])
        if report.get("returncode") == 0:
            report.update(status="OWNED_CLEANUP_ERROR", returncode=9)


def finalize(report, directory, started, signature, pins, *, identity_fn=identity, verify_fn=original.verify_pins):
    errors = []
    for name, action in (("inputs_unchanged", lambda: verify_fn(pins)),
                         ("sources_unchanged", lambda: identity_fn() == signature)):
        try:
            if name == "inputs_unchanged" and not pins:
                raise ValueError("입력 pin 검증이 완결되지 않았다")
            result = action()
            if result is False:
                raise ValueError("소유 입력/소스의 전후 값이 다르다")
            report[name] = True
        except BaseException as exc:
            report[name] = False
            errors.append(dict(check=name, type=type(exc).__name__, message=str(exc)[:1000]))
    if errors:
        report["exit_verification_errors"] = errors
        if report.get("returncode") == 0:
            report.update(status="EXIT_VERIFICATION_ERROR", returncode=9)
    report.update(ended_at=datetime.now(timezone.utc).isoformat(), wall_seconds=time.perf_counter() - started)
    from scripts.diag_p106b_external_core6 import close_report
    close_report(Path(directory) / "report.json", report)
    return report


def evaluate_groups(lm, torch, groups, mode, directory, report, check):
    from scripts.p106b_babylm_causal import load_official, TextProcessor, processed_pair, RankAudit
    from scripts.p106b_shards import ShardWriter
    official, proof = load_official(original.SOURCE, torch, device="cuda")
    report["official_source_selection"] = proof
    forward = original.FullLogits(lm, torch, check)
    writer = None
    try:
        processor = TextProcessor(lm.tokenizer, native=False, vocab=forward.vocab)
        pad = lm.tokenizer.pad_token_id
        if type(pad) is not int or not 0 <= pad < forward.vocab:
            raise ValueError("Falcon의 실제 PAD ID가 필요하다")
        report["synthetic_real_model_oracle"] = original.numerical_canary(official, lm, forward, torch, processor, pad)
        report["numerical_canary_passed"] = report["synthetic_real_model_oracle"].get("passed") is True
        if not report["numerical_canary_passed"]:
            raise ValueError("Falcon 수치 oracle 미완료")
        report["tokenizer_policy"] = dict(native=False, pad_id=pad, manual_bos=False,
                                          add_special_tokens="ACTUAL_TOKENIZER_DEFAULT_TRUE")
        args = argparse.Namespace(task="blimp", save_predictions=True, images_path=None)
        collate = official["get_causal_collate_fn"](pad)
        for name, all_rows in groups.items():
            check(); tick = time.perf_counter()
            rows = original.selected_rows(all_rows, mode)
            items, lengths = [], []
            for row in rows:
                check()
                item = processed_pair(official, processor, row["raw"], row["file"])
                items.append(item)
                lengths.append([[int(v) for v in item[1][f"sentence_{j}_tokens"]] for j in range(2)])
            if len({item[4] for item in items}) != original.EXPECTED[name]["files"]:
                raise ValueError("공식 UID를 누락했다")
            writer = ShardWriter(directory, name + "_pairs", limit=LIMIT)
            torch.manual_seed(1337)
            rng_before = torch.get_rng_state().tolist()
            def batches():
                for start in range(0, len(items), 8):
                    check()
                    yield collate(items[start:start + 8])
            with RankAudit(official, torch, sink=writer.append) as audit:
                stats, predictions = official["compute_causal_results"](args, forward, batches(), [1.0])
            accuracies, average = official["process_results"](args, stats)
            summary = audit.summary(average[1.0])
            closing, writer = writer, None
            manifest = closing.close(lineage=dict(model=MODEL, mode=mode, group=name,
                official_commit=proof["commit"], data_admission="EVALUATION_ONLY_NOT_TRAIN"))
            recount = recount_pairs(directory, manifest, len(rows), original.EXPECTED[name]["files"], summary)
            report["group_audits"][name] = dict(summary, pair_manifest=manifest, official_accuracies=accuracies,
                official_macro_percent=average[1.0], input_order_sha256=original.object_sha(rows),
                native_ids_order_sha256=original.object_sha(lengths), cpu_rng_before=rng_before,
                cpu_rng_after=torch.get_rng_state().tolist(), tokenizer_calls=2 * len(rows),
                max_native_tokens=max(len(v) for pair in lengths for v in pair), context_truncated_rows=0,
                independent_raw_recount=recount)
            torch.cuda.synchronize()
            report["evaluation_seconds"][name] = time.perf_counter() - tick
            print("[BABYLM_WINDOW_GROUP] " + json.dumps(dict(model=MODEL, mode=mode, group=name, rows=len(rows))), flush=True)
            del items, lengths, predictions, stats
        report["forward_calls"] = forward.calls
        report["forward_input_tokens"] = forward.input_tokens
        report["raw_independent_recount"] = True
    finally:
        close_partial(writer, report)
        forward = None


def execute(mode, expected_source, deadline, max_wall_sec):
    from scripts.diag_p106b_external_core6 import phase_wall_limit
    started = time.perf_counter()
    admission = window(deadline, max_wall_sec, mode)
    signature = identity()
    if signature["sha256"] != expected_source:
        raise ValueError("실행 source SHA가 현재 동결 소스와 다르다")
    directory = reserve(OUTPUT / ("prepare" if mode == "prepare" else MODEL + "/" + mode))
    report = dict(schema=SCHEMA, tag=TAG, model=MODEL, mode=mode, status="STARTED", returncode=9,
        source_identity=signature, policy=original.policy(), admission=admission, group_audits={},
        evaluation_seconds={}, started_at=datetime.now(timezone.utc).isoformat(), input_pins={},
        sources_unchanged=False, inputs_unchanged=False, full_suite=False, official_cli=False,
        track_eligibility="NOT_CLAIMED", training=False, optimizer_updates=0, checkpoint_writes=0)
    pins = {}
    check = lambda: check_time(admission, started)
    try:
        with phase_wall_limit(admission["hard_cap_seconds"]):
            check()
            pins, groups, counts = original.pins_and_rows()
            report.update(input_pins=pins, actual_counts=counts)
            if mode == "prepare":
                report.update(status="BABYLM_WINDOW_PREPARED", returncode=0, model_loads=0, gpu_calls=0)
            else:
                prep_path = OUTPUT / "prepare/report.json"
                prep = read_report(prep_path)
                if (prep.get("status") != "BABYLM_WINDOW_PREPARED" or prep.get("returncode") != 0
                        or prep.get("source_identity") != signature or prep.get("input_pins") != pins
                        or prep.get("actual_counts") != counts or prep.get("policy") != original.policy()
                        or not prep.get("sources_unchanged") or not prep.get("inputs_unchanged")):
                    raise ValueError("같은 새 소스·입력의 완결 prepare가 필요하다")
                pins[str(prep_path.relative_to(ROOT))] = original.digest(prep_path)
                if mode == "full":
                    cost_path = OUTPUT / MODEL / "cost/report.json"
                    report["admission"] = full_admission(read_report(cost_path), signature, admission)
                    pins[str(cost_path.relative_to(ROOT))] = original.digest(cost_path)
                from scripts.diag_p106b_official_core6 import model_runtime, prerequisites, OFFLINE
                from scripts.interactive_research_infer import require_idle_gpu, state_fingerprint
                from scripts.prepare_p106b_official_eval import configure_hf_cache
                configure_hf_cache()
                import os
                for key, value in OFFLINE.items():
                    os.environ[key] = value
                import torch
                from torch.nn.attention import sdpa_kernel, SDPBackend
                report["strict_runtime_prerequisite"] = prerequisites()
                torch.set_num_threads(4); torch.manual_seed(1337)
                torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
                check()
                with sdpa_kernel(SDPBackend.MATH), torch.no_grad():
                    report["gpu_point_query"] = require_idle_gpu()
                    check()
                    with model_runtime(MODEL, torch) as (lm, proof):
                        report["model_proof"] = proof
                        before = state_fingerprint(lm.model)
                        try:
                            check()
                            evaluate_groups(lm, torch, groups, mode, directory, report, check)
                        finally:
                            after = state_fingerprint(lm.model)
                            report["body_unchanged"] = before == after
                            lm = None
                            if not report["body_unchanged"]:
                                raise ValueError("Falcon 본체가 평가 중 변경됐다")
                check()
                report["cleanup_gpu_point_query"] = require_idle_gpu()
                report.update(status="BABYLM_WINDOW_COST_COMPLETE" if mode == "cost" else "BABYLM_WINDOW_BLIMP_COMPLETE", returncode=0)
            check()
    except BaseException as exc:
        report.update(status="BABYLM_WINDOW_PARTIAL", returncode=130 if isinstance(exc, KeyboardInterrupt) else 9,
            error_type=type(exc).__name__, error=str(exc)[:2000], timed_out=isinstance(exc, TimeoutError))
    finally:
        if "torch" in locals():
            cleanup_owned(torch, report, require_idle_gpu)
        finalize(report, directory, started, signature, pins)
    return {k: report.get(k) for k in ("status", "returncode", "model", "mode", "wall_seconds", "error_type", "error")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check-only", action="store_true")
    action.add_argument("--execute", action="store_true")
    parser.add_argument("--mode", choices=("prepare", "cost", "full"), default="prepare")
    parser.add_argument("--model", choices=(MODEL,), default=MODEL)
    parser.add_argument("--source-sha256")
    parser.add_argument("--deadline", default=DEADLINE_ISO)
    parser.add_argument("--max-wall-sec", type=int, default=600)
    args = parser.parse_args(argv)
    if args.check_only:
        value = dict(status="CHECK_ONLY", source_identity=identity(), policy=original.policy(), tag=TAG,
                     models=[MODEL], model_loading="NOT_RUN", output=str(OUTPUT.relative_to(ROOT)))
    else:
        if not args.source_sha256:
            parser.error("--execute에는 정확한 --source-sha256이 필요하다")
        value = execute(args.mode, args.source_sha256, args.deadline, args.max_wall_sec)
    print("[BABYLM_WINDOW_FINAL] " + json.dumps(value, ensure_ascii=False), flush=True)
    return value.get("returncode", 0)


if __name__ == "__main__":
    raise SystemExit(main())
