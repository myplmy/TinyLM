#!/usr/bin/env python3
"""닫힌 Belebele 전량의 읽기 전용 link-cluster 대응 검산; 모델/취득 호출은 없다.

주900/사전 무절단898의 공식 문항 평균을 유지한다. 같은 link 재표집 가중치를
모든 모델·양언어·두 부분집합에 공유하며 지문별 정확도 macro 평균은 만들지 않는다.
실제 런의 프로세스 exit0/외부 hardcap 확인은 root 소유이며 파일 검사로 대신하지 않는다.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import itertools
import math
from pathlib import Path
import re
import resource
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import tinylm  # noqa: F401 -- HF 관련 import보다 프로젝트 캐시 정책을 먼저 적용한다.
from scripts import diag_p106b_belebele as evaluation
from scripts import summarize_p106b_core6_pairs as shared
from scripts.p106b_shards import verify as verify_shards

TAG, SCHEMA = "p106b_belebele_pairs_v1_s1337", "P106B_BELEBELE_CLUSTER_PAIRS_V1"
EVALUATOR_SHA = "2BB7BC8DD6A18465DA8A4B87B4AE3452D43F5E8B26CFD01BAC41482BF9A477FB"
OWN_FILES = ("scripts/summarize_p106b_belebele_pairs.py", "scripts/test_summarize_p106b_belebele_pairs.py")
MODELS, LANGUAGES = evaluation.MODELS, evaluation.LANGUAGES
ROWS, LINKS, COMMON = 900, 488, 898
RESAMPLES, SEED, CHUNK = 100000, 20261024, 512
MAX_BYTES = 20_000_000
SUBSETS = ("main900", "common_untruncated898")
SCOPE = ("고정 완료 모델과 고정900문항의 지문-link 대응 percentile95 CI. 학습 seed·과제 모집단·"
         "자유대화 불확실성이 아니며 다중비교 미보정이다. 양언어 평균의 새 공식점수, 학습/성과/"
         "지능 개선 또는 모델 채택 판정은 만들지 않는다.")
IncompleteFull = shared.IncompleteFull
canonical, digest, read_json = shared.canonical, shared.digest, shared.read_json


def source_identity():
    frozen = evaluation.identity()
    if frozen["sha256"] != EVALUATOR_SHA:
        raise ValueError("동결 Belebele/helper source가 교체됐다")
    files = dict(frozen["files"])
    files.update({name: digest(ROOT / name) for name in OWN_FILES})
    return dict(files=files, sha256=shared.digest_bytes(canonical(files)), evaluator_source=frozen)


class Evidence:
    """읽은 파일만 추적한다. 모델 weight/input_pins 전체를 새로 읽지 않는다."""
    def __init__(self, signature):
        self.inputs, self.signature, self.phases = shared.Inputs(), signature, []

    def json(self, path):
        path = shared.regular(path)
        if path.stat().st_size >= MAX_BYTES:
            raise ValueError("JSON 증거는 해시 전에20MB 미만이어야 한다")
        self.inputs.add(path)
        result = read_json(path)
        canonical(result)  # JSON의 1e309 같은 overflow도 비유한 값으로 거부한다.
        return result

    def closed(self, path, model, mode):
        path = Path(path)
        if not path.is_file():
            raise IncompleteFull("닫힌 " + mode + " 보고서가 없다: " + str(path))
        before = self.json(path)
        closure, _ = evaluation.closure_paths(path.parent)
        self.json(closure)
        result = evaluation.closed_prerequisite(path, self.signature, model, mode, {})
        if result != before:
            raise ValueError("선결 보고서가 읽는 도중 바뀌었다")
        self.phases.append((path, model, mode))
        return result

    def manifest(self, directory, manifest, stem, lineage, rows):
        if (manifest.get("schema") != "P106B_WRITE_ONCE_SHARDS_V1"
                or type(manifest.get("limit_bytes")) is not int
                or not 64 <= manifest["limit_bytes"] < MAX_BYTES
                or manifest.get("rows") != rows or manifest.get("lineage") != lineage
                or not manifest.get("shards")):
            raise ValueError("정확 rows/계보/20MB 미만의 닫힌 원형 manifest가 필요하다")
        if self.json(Path(directory) / (stem + "_shards_manifest.json")) != manifest:
            raise ValueError("보고서와 실제 manifest가 다르다")
        for index, spec in enumerate(manifest["shards"]):
            if (spec.get("path") != f"{stem}_{index:06d}.jsonl"
                    or type(spec.get("bytes")) is not int or not 0 < spec["bytes"] < MAX_BYTES):
                raise ValueError("원형 shard 이름/20MB 상한이 다르다")
            path = shared.regular(Path(directory) / spec["path"])
            if path.stat().st_size != spec["bytes"]:
                raise ValueError("원형 실제 크기가 다르다; 큰 변조 파일을 먼저 해시하지 않는다")
            self.inputs.add(path, spec["sha256"])
        verify_shards(Path(directory), manifest)

    def unchanged(self):
        self.inputs.unchanged()
        for path, model, mode in self.phases:
            evaluation.closed_prerequisite(path, self.signature, model, mode, {})
        return True


def admit_report(report, model, mode):
    expected = dict(schema=evaluation.SCHEMA, tag=evaluation.TAG, model=model, mode=mode,
        status={"prepare": "BELEBELE_PREPARED", "canary": "BELEBELE_CANARY_COMPLETE",
                "cost": "BELEBELE_COST_COMPLETE", "full": "BELEBELE_FULL_COMPLETE"}[mode],
        returncode=0, policy=evaluation.policy(model), training=False, optimizer_updates=0, checkpoint_writes=0,
        sources_unchanged=True, inputs_unchanged=True)
    if any(report.get(key) != value for key, value in expected.items()):
        raise IncompleteFull("완결된 동일 정책/모델/단계만 채택한다: " + str(model) + "/" + mode)
    if (type(report["returncode"]) is not int or report.get("partial_artifacts")
            or report.get("artifact_close_errors") or report.get("exit_verification_errors")):
        raise IncompleteFull("부분/오류 보고서는 완료가 아니다")
    if mode == "prepare":
        if report.get("model_loads") != 0 or report.get("gpu_calls") != 0:
            raise ValueError("출력 전 token-only prepare가 아니다")
        return
    if (report.get("body_unchanged") is not True or report.get("owned_cleanup_complete") is not True
            or not report.get("model_identity") or not report.get("model_proof")):
        raise IncompleteFull("모델 불변/소유 정리/자산 계보가 닫혀야 한다")
    if mode == "canary":
        if report.get("numerical_canary_passed") is not True:
            raise IncompleteFull("동일 모델의 엄격 numerical canary가 필요하다")
    else:
        count = ROWS if mode == "full" else 32
        if (report.get("actual_counts") != dict.fromkeys(LANGUAGES, count)
                or report.get("actual_rows") != 2 * count or report.get("actual_choice_likelihoods") != 8 * count
                or report.get("raw_independent_recount") is not True
                or set(report.get("sample_manifests", {})) != set(LANGUAGES)
                or set(report.get("independent_audits", {})) != set(LANGUAGES)):
            raise IncompleteFull("정확 full1800/7200 또는 cost64/256 양언어 원형이 필요하다")


def baseline(gold):
    counts = Counter(gold)
    if not gold or any(type(value) is not int or value not in range(4) for value in gold):
        raise ValueError("비어 있지 않은 네 라벨의 정답이 필요하다")
    label = max(range(4), key=lambda value: counts[value])
    return dict(rows=len(gold), label_counts=[counts[i] for i in range(4)],
        uniform_random=dict(expected_accuracy=.25, sampled=False),
        majority_label=dict(label="ABCD"[label], accuracy=counts[label] / len(gold),
                            selection="EMPIRICAL_GOLD_MOST_FREQUENT_CONSTANT; EARLIEST_LABEL_TIE"),
        always_A=dict(label="A", accuracy=counts[0] / len(gold)))


def read_correctness(directory, manifest, documents):
    values = {}
    for spec in manifest["shards"]:
        with (Path(directory) / spec["path"]).open(encoding="utf-8") as stream:
            for line in stream:
                row = evaluation.decode(line)
                canonical(row)
                index = len(values)
                if index >= len(documents):
                    raise ValueError("원형의 초과 문항은 허용하지 않는다")
                key = evaluation.key_for(documents[index])
                score = row["metrics"]["acc"]
                if (type(row.get("doc_id")) is not int or row["doc_id"] != index
                        or canonical(row.get("doc")) != canonical(documents[index])
                        or canonical(row["key"]) != canonical(list(key)) or key in values
                        or type(score) not in (bool, int, float) or score not in (0, 1)
                        or row["metrics"]["acc_norm"] != score):
                    raise ValueError("원형의 대응키/이진 정답/acc_norm이 다르다")
                values[key] = int(score)
    if len(values) != ROWS:
        raise ValueError("full900 원형만 통계에 넣는다")
    return values


def sample_means(np, weights, denominators, numerators):
    """복원추출된 모든 질문의 합/실제 질문수; cluster macro가 아니다."""
    den = weights @ denominators
    if (den <= 0).any():
        raise ValueError("재표집의 실제 문항 분모0은 skip/재추출/0점 처리하지 않는다")
    return (weights @ numerators) / den[:, None]


def cluster_intervals(values, keys, common, *, draws=RESAMPLES, seed=SEED, chunk=CHUNK):
    import numpy as np
    if (type(draws) is not int or not 1 <= draws <= RESAMPLES or type(seed) is not int or seed < 0
            or type(chunk) is not int or not 1 <= chunk <= CHUNK or not keys or len(set(keys)) != len(keys)
            or not common or not set(common) <= set(keys) or not values):
        raise ValueError("유일 대응키/비어 있지 않은 교집합/유계 정수 재표집 계약이 필요하다")
    models = tuple(values)
    if len(models) > len(MODELS) or any(set(values[model]) != set(LANGUAGES) for model in models):
        raise ValueError("같은 양언어의 고정 모델 채널만 허용한다")
    channels = [(model, language) for model in models for language in LANGUAGES]
    outcomes = []
    for model, language in channels:
        row = values[model][language]
        if set(row) != set(keys) or any(type(v) not in (bool, int, float) or v not in (0, 1) for v in row.values()):
            raise ValueError("모든 모델/양언어의 동일 대응키와 유한 이진 정답이 필요하다")
        outcomes.append([row[key] for key in keys])
    outcomes = np.asarray(outcomes, dtype=np.int64).T
    links = sorted({key[0] for key in keys})
    link_index = {link: index for index, link in enumerate(links)}
    index = np.asarray([link_index[key[0]] for key in keys])
    subsets = (np.ones(len(keys), dtype=bool), np.asarray([key in common for key in keys]))
    denominators, numerators = [], []
    for selected in subsets:
        den = np.bincount(index[selected], minlength=len(links)).astype(np.int64)
        num = np.zeros((len(links), len(channels)), dtype=np.int64)
        np.add.at(num, index[selected], outcomes[selected])
        denominators.append(den)
        numerators.append(num)
    samples = [np.empty((draws, len(channels)), dtype=np.float64) for _ in subsets]
    rng, weights_sha = np.random.default_rng(seed), hashlib.sha256()
    for start in range(0, draws, chunk):
        stop = min(draws, start + chunk)
        weights = rng.multinomial(len(links), np.full(len(links), 1 / len(links)), size=stop - start)
        weights_sha.update(weights.astype("<i8", copy=False).tobytes())
        for subset in range(2):
            samples[subset][start:stop] = sample_means(np, weights, denominators[subset], numerators[subset])
    result = {}
    for subset, name in enumerate(SUBSETS):
        scores, pairs = {}, {}
        for channel, (model, language) in enumerate(channels):
            scores.setdefault(model, {})[language] = dict(rows=int(denominators[subset].sum()),
                correct=int(numerators[subset][:, channel].sum()),
                accuracy=float(numerators[subset][:, channel].sum() / denominators[subset].sum()),
                ci95=np.quantile(samples[subset][:, channel], [.025, .975], method="linear").tolist())
        for left, right in itertools.combinations(models, 2):
            row = dict(left_model=left, right_model=right, languages={})
            for language in LANGUAGES:
                a, b = channels.index((left, language)), channels.index((right, language))
                row["languages"][language] = dict(left=scores[left][language]["accuracy"],
                    right=scores[right][language]["accuracy"],
                    right_minus_left=scores[right][language]["accuracy"] - scores[left][language]["accuracy"],
                    ci95=np.quantile(samples[subset][:, b] - samples[subset][:, a], [.025, .975], method="linear").tolist())
            pairs[left + "__" + right] = row
        result[name] = dict(rows_per_language=int(denominators[subset].sum()), scores=scores, pairs=pairs)
    return dict(subsets=result, resamples=draws, seed=seed, percentile95_method="linear",
        clusters=len(links), cluster_order_sha256=shared.digest_bytes(canonical(links)),
        shared_draws_sha256=weights_sha.hexdigest().upper(), rng="numpy.default_rng/PCG64",
        numpy_version=np.__version__, max_chunk_rows=min(chunk, draws),
        max_weight_shape=[min(chunk, draws), len(links)],
        sample_array_bytes=sum(sample.nbytes for sample in samples),
        estimator="SUM_CORRECT_OVER_ACTUAL_SELECTED_QUESTIONS; NOT_CLUSTER_MACRO",
        sampling="ONE_LINK_MULTINOMIAL_DRAW_SHARED_BY_ALL_MODELS_LANGUAGES_AND_BOTH_SUBSETS",
        auxiliary_zero_question_cluster_policy="KEEP_ORIGINAL_LINK_DRAWS; ZERO_TOTAL_DENOMINATOR_IS_ERROR",
        bilingual_macro_created=False, multiple_comparisons_corrected=False, interpretation=SCOPE)


def collect(models, *, expected_source, evidence_root=evaluation.OUTPUT):
    if not models or len(set(models)) != len(models) or any(model not in MODELS for model in models):
        raise ValueError("완료 모델을 중복 없이 명시해야 한다; 기본 모델 선택은 없다")
    selected = tuple(model for model in MODELS if model in models)
    source = source_identity()
    if source["sha256"] != expected_source:
        raise ValueError("현재 통계 source pin이 다르다")
    evidence = Evidence(source["evaluator_source"])
    # full 부재/부분은 공식 task·자료 읽기나 통계 전에 중단한다.
    full = {}
    for model in selected:
        path = Path(evidence_root) / model / "full/report.json"
        report = evidence.closed(path, model, "full")
        admit_report(report, model, "full")
        full[model] = report
    prepare_path = Path(evidence_root) / "prepare/report.json"
    prepared = evidence.closed(prepare_path, None, "prepare")
    admit_report(prepared, None, "prepare")
    for model in selected:
        prerequisites = {}
        for mode in ("canary", "cost"):
            path = Path(evidence_root) / model / mode / "report.json"
            prerequisites[mode] = evidence.closed(path, model, mode)
            admit_report(prerequisites[mode], model, mode)
        canary, cost = prerequisites["canary"], prerequisites["cost"]
        for report in (canary, cost, full[model]):
            if (report.get("prepare_report_sha256") != digest(prepare_path)
                    or report.get("model_identity") != canary["model_identity"]):
                raise ValueError("동일 prepare/모델 자산 계보가 아니다")
        canary_sha = digest(Path(evidence_root) / model / "canary/report.json")
        if any(report.get("canary_report_sha256") != canary_sha for report in (cost, full[model])):
            raise ValueError("전량과 cost의 엄격 canary SHA 계보가 다르다")
        cost_path = Path(evidence_root) / model / "cost/report.json"
        recorded_pins = full[model].get("input_pins", {})
        key = str(cost_path.relative_to(ROOT)) if cost_path.is_relative_to(ROOT) else str(cost_path)
        if recorded_pins.get(key) != digest(cost_path):
            raise ValueError("전량의 지명 cost 보고서 SHA가 다르다")
    for spec in evaluation.SPECS.values():
        evidence.inputs.add(evaluation.DATA / spec["filename"])
    documents, assets, data_audit = evaluation.read_assets(allow_download=False)
    tasks, task_proof = evaluation.load_tasks(documents)
    expected = dict(data_assets=assets, data_audit=data_audit, task_contract=task_proof)
    if any(canonical(prepared.get(key)) != canonical(value) for key, value in expected.items()):
        raise ValueError("완료 prepare와 현재 원자료/공식 task가 다르다")
    if data_audit.get("paired_keys") != ROWS or data_audit.get("paired_links") != LINKS:
        raise ValueError("공식900키/488 link 대응이 아니다")
    for item in task_proof["official_definition_sources"].values():
        evidence.inputs.add(item["runtime_path"], item["sha256"])
    frozen = prepared["frozen_tokens"]
    evidence.manifest(prepare_path.parent, frozen["token_manifest"], "token_lengths",
        dict(models=list(MODELS), languages=list(LANGUAGES), forward_calls=0, quality_claim=False), len(MODELS) * 2 * ROWS)
    outcomes, audits, common = {}, {}, None
    for model in selected:
        plans, selected_common = evaluation.read_frozen(prepare_path.parent, frozen, documents, model)
        if len(selected_common) != COMMON or common is not None and common != selected_common:
            raise ValueError("동결된 공통 무절단898 교집합이 다르다")
        common = selected_common
        report, directory = full[model], Path(evidence_root) / model / "full"
        if report.get("auxiliary_common_rows_per_language") != COMMON:
            raise ValueError("완료 보고서의 사전 무절단898 분모가 다르다")
        if any(canonical(report.get(key)) != canonical(value) for key, value in expected.items()):
            raise ValueError("모델 간 원문/정답/공식 요청 정의가 다르다")
        outcomes[model], audits[model] = {}, {}
        for language in LANGUAGES:
            manifest = report["sample_manifests"][language]
            evidence.manifest(directory, manifest, language + "_samples",
                dict(task="belebele_" + language, model=model, mode="full", revision=evaluation.REVISION), ROWS)
            audit = evaluation.recount_raw(tasks[language], documents[language], language, directory,
                manifest, ROWS, plans[language], common)
            if audit != report["independent_audits"][language] or audit["auxiliary_common_untruncated"]["rows"] != COMMON:
                raise ValueError("원형 재계수/원 공식 점수/보조898 집계가 다르다")
            outcomes[model][language] = read_correctness(directory, manifest, documents[language])
            audits[model][language] = audit
    keys = sorted(evaluation.key_for(doc) for doc in documents[LANGUAGES[0]])
    statistics = cluster_intervals(outcomes, keys, common)
    baselines = {}
    for name, subset in zip(SUBSETS, (set(keys), common)):
        baselines[name] = {language: baseline([int(doc["correct_answer_num"]) - 1
            for doc in documents[language] if evaluation.key_for(doc) in subset]) for language in LANGUAGES}
    def final_check():
        if source_identity() != source:
            raise ValueError("통계 실행 중 source가 변경됐다")
        return evidence.unchanged()
    final_check()
    return dict(schema=SCHEMA, tag=TAG, status="CLOSED_FULL_LINK_CLUSTER_CPU_RECOUNT_COMPLETE",
        returncode=0, selected_models=list(selected), unselected_models="NOT_SELECTED_NOT_SCORED",
        statistics=statistics, baselines=baselines, independent_audits=audits,
        evaluator_tag=evaluation.TAG, evaluator_source_sha256=EVALUATOR_SHA,
        source_identity=source, input_files=evidence.inputs.files, inputs_unchanged=True, source_unchanged=True,
        exact_pairing=dict(rows=ROWS, links=LINKS, common_untruncated_rows=COMMON,
            sorted_keys_sha256=shared.digest_bytes(canonical(keys))),
        interpretation=SCOPE, root_actual_exit0_required=True,
        runtime_process_exit0_verification="EXTERNAL_ROOT_PREREQUISITE_NOT_PROVEN_BY_FILE_READER",
        models_loaded=0, gpu_calls=0, optimizer_updates=0, raw_modified=False,
        model_weight_bodies_read=False, quality_claim=False, adoption_decision=False), final_check


def output_path(stamp, root=ROOT):
    if not isinstance(stamp, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_\-]{0,79}", stamp):
        raise ValueError("새 출력의 안전한 ASCII stamp를 명시해야 한다")
    target = Path(root) / "test_result/evidence" / TAG / stamp
    if target.exists() or any(path.is_symlink() for path in (target, *target.parents)):
        raise FileExistsError("기존/부분/연결 출력은 보존한다")
    return target


def write_json(path, value):
    body = canonical(value) + b"\n"
    if len(body) >= MAX_BYTES:
        raise ValueError("통계 출력도20MB 미만이어야 한다")
    with Path(path).open("xb") as stream:
        stream.write(body)
    return shared.digest_bytes(body)


def bounded_run(models, expected_source, *, target=None, max_wall_sec=120, clock=time.perf_counter):
    started = clock()
    started_at = datetime.now(timezone.utc).isoformat()
    def budget():
        elapsed = clock() - started
        if not math.isfinite(elapsed) or elapsed < 0 or elapsed >= max_wall_sec - .1:
            raise TimeoutError("보고서 저장/재읽기를 포함한 유계 CPU 시간이 만료됐다")
        return elapsed
    report = None
    try:
        with shared.cpu_wall_limit(max_wall_sec):
            report, final_check = collect(models, expected_source=expected_source)
            report.update(started_at=started_at, elapsed_seconds=budget(),
                peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                cpu_wall_cap_seconds=max_wall_sec, atomic_process_exit_guarantee=False)
            if target is not None:
                target = Path(target)
                if target.exists() or any(path.is_symlink() for path in (target, *target.parents)):
                    raise FileExistsError("기존 통계 결과는 덮지 않는다")
                target.mkdir(parents=True, exist_ok=False)
                sha = write_json(target / "report.json", report)
                if read_json(target / "report.json") != report:
                    raise ValueError("통계 보고서 저장 후 재읽기가 다르다")
                final_check()
                receipt = dict(schema=SCHEMA + "_OUTPUTS", tag=TAG, report_sha256=sha,
                    source_sha256=expected_source, status="READBACK_CLOSED", report_re_read=True,
                    elapsed_before_receipt=budget(), raw_examples_copied=0,
                    adoption="REQUIRE_REAL_PROCESS_EXIT0_AND_OUTPUTS_RECEIPT_AND_NO_VETO; NO_ATOMIC_EXIT_GUARANTEE")
                write_json(target / "outputs.json", receipt)
                if read_json(target / "outputs.json") != receipt or digest(target / "report.json") != sha:
                    raise ValueError("통계 출력 종결 재읽기/SHA가 다르다")
                final_check()
            budget()
        budget()
    except BaseException as exc:
        if target is not None and Path(target).is_dir() and not isinstance(exc, FileExistsError):
            try:
                write_json(Path(target) / "veto.json", dict(schema=SCHEMA + "_VETO", status="VETO", returncode=9,
                    error_type=type(exc).__name__, error=str(exc)[:1000], source_sha256=expected_source))
            except BaseException:
                pass  # 기존 원형을 덮지 않는다. 실제 CLI 비정상도 독립 채택 금지 사유다.
        raise
    return report, budget


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-only", action="store_true")
    mode.add_argument("--read-only", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--models", nargs="+", choices=MODELS)
    parser.add_argument("--source-sha256")
    parser.add_argument("--output-stamp")
    parser.add_argument("--max-wall-sec", type=int, default=120)
    args = parser.parse_args(argv)
    if args.check_only:
        source = source_identity()
        print(shared.canonical(dict(schema=SCHEMA, tag=TAG, status="SOURCE_ONLY", source_identity=source,
            registered_models=list(MODELS), resamples=RESAMPLES, seed=SEED, models_loaded=0,
            gpu_calls=0, raw_reads=0, evidence_writes=0)).decode())
        return 0
    if not args.models or args.source_sha256 is None:
        parser.error("계산에는 --models와 --source-sha256를 모두 명시해야 한다")
    if args.read_only and args.output_stamp or args.execute and not args.output_stamp:
        parser.error("읽기 전용은 output 없음; execute는 새 --output-stamp 필수")
    target = None
    try:
        target = output_path(args.output_stamp) if args.execute else None
        report, budget = bounded_run(args.models, args.source_sha256, target=target, max_wall_sec=args.max_wall_sec)
        print(canonical(dict(status=report["status"], selected_models=report["selected_models"],
            source_sha256=report["source_identity"]["sha256"], output=None if target is None else str(target),
            resamples=RESAMPLES, seed=SEED, models_loaded=0, gpu_calls=0, quality_claim=False)).decode(), flush=True)
        budget()
        return 0
    except BaseException as exc:
        code = 8 if isinstance(exc, IncompleteFull) else 9
        if target is not None and target.is_dir() and not isinstance(exc, FileExistsError):
            try:
                write_json(target / "veto.json", dict(schema=SCHEMA + "_VETO", status="VETO", returncode=code,
                    error_type=type(exc).__name__, error=str(exc)[:1000]))
            except BaseException:
                pass
        print(canonical(dict(status="INCOMPLETE_FULL_HOLD" if code == 8 else "CPU_RECOUNT_ERROR", returncode=code,
            error_type=type(exc).__name__, error=str(exc)[:1000], models_loaded=0, gpu_calls=0)).decode(), file=sys.stderr)
        return code


if __name__ == "__main__":
    raise SystemExit(main())
