#!/usr/bin/env python3
"""완료된 형식 Muon/NorMuon 공식 전량의 별도 CPU 통계 접점.

원 모델명·스키마·원답·문턱을 바꾸지 않는다. 두 새 공식 full의 실제
종결이 없으면 HOLD다. CP 본문과 학습 캐시는 열거나 해시하지 않는다.
원 재계수·문항 대응·pointwise95 구간·정확 검정을 재사용하고 지정한
5쌍×6과제의30검정만 하나의 Holm 가족으로 표시한다. 자동 채택은 없다.
"""
from __future__ import annotations
import time
STARTED = time.monotonic()
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_native_format_official as official
from scripts import diag_p106b_native_format_dialogue as dialogue
from scripts.eval_bench_suite import mcnemar_exact_p

training, supervisor = official.training, official.supervisor
Hold = training.Hold
SCHEMA = "P106B_NATIVE_FORMAT_PAIR_STATS_V1"
INPUTS_SCHEMA = "P106B_NATIVE_FORMAT_PAIR_STATS_INPUTS_V1"
PREFIX = "p106b_native_format_pair_stats_v1_20261026_"
TRAINING_SHA = "9EA74842B672407044FB52B668B56EC8AD2C4390229409C7E12EE5F9B002F90C"
OFFICIAL_SHA = "9841ACF491E1CCD156FB060C2194773CCD6B02186F86F55ADA549FF8C5D4BB71"
DIALOGUE_SHA = "E059BA2DE73D14053021932ACD37B83505D3ABD5523488809392D66F91164E9B"
SHARED_SHA = "085A18CF0382C31F98BA4B9BC4C4B598DEFAF2D1BD0ECB6A9E911196C7B3485D"
NEW_MODELS = ("format_muon", "format_normuon")
PEERS = ("native595-q", "falcon90m")
PAIRS = (("format_muon", "format_normuon"), ("native595-q", "format_muon"),
    ("native595-q", "format_normuon"), ("falcon90m", "format_muon"), ("falcon90m", "format_normuon"))
PRIMARY = dict(piqa="acc", arc_easy="acc_norm", arc_challenge="acc_norm", hellaswag="acc_norm",
    winogrande="acc", boolq="acc")
COUNTS = dict(official.official.TASK_COUNTS)
ITEMS, REQUESTS, RESAMPLES, SEED, FAMILY = 19965, 67106, 100000, 20261024, 30
MAX_BYTES = 20_000_000
OWN = ("scripts/summarize_p106b_native_format_pair.py", "scripts/test_p106b_native_format_pair_stats.py")
SCOPE = ("고정6과제 안 문항쌍의 pointwise95 구간이며 동시 신뢰구간이 아니다. "
    "학습seed·과제 모집단 불확실성을 포함하지 않는다. 30개 정확검정의 p값만 하나의 Holm 가족으로 보정한다. "
    "사후최빈라벨은 진단값이며 학습된 기준선이 아니다. 자동 승자·모델 채택·한국어·대화·일반 지능 판정은 하지 않는다. "
    "기존 Native595-Q/Falcon 비교는 학습량·원천·구조를 맞춘 optimizer 인과 비교가 아니다.")
require, canonical, sha = official.require, official.canonical, official.sha
read_official_closed = official.read_closed


def shared_api():
    # 기존 paths의 mkdir가 새 디렉터리를 만들기 전에 원 환경을 검사한다.
    dialogue.interactive.validate_import_environment(ROOT)
    from scripts import summarize_p106b_core6_pairs as shared
    return shared


def checked(path):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(p.is_symlink() for p in (path, *path.parents)), "명시한 비링크 경로가 필요하다")
    require(not any(part in {"TinyDataset", ".claude", "CLAUDE.md", ".codex", ".agents", ".aws"} for part in path.parts),
        "보호 환경과 데이터는 통계 입력이 아니다")
    require(path.suffix.lower() not in {".pt", ".pth", ".bin", ".safetensors", ".gguf"}
        and not any(path.parts[i:i+2] == ("runs", "ckpt") for i in range(len(path.parts)-1)),
        "CP 본문과 token bin은 열거나 해시하지 않는다")
    if path.is_relative_to(ROOT):
        require(path.relative_to(ROOT).parts[0] != "ai_dev_tool", "환경 원천은 통계 입력이 아니다")
    return path


def relative(name, root=None):
    root = ROOT if root is None else root
    name = Path(name)
    require(name.parts and not name.is_absolute() and ".." not in name.parts, "저장소 상대 경로가 필요하다")
    return checked(Path(root) / name)


def source_identity():
    shared = shared_api()
    frozen = dict(training=training.source_identity()["sha256"], official=official.source_identity()["sha256"],
        dialogue=dialogue.source_identity()["sha256"], shared=shared.source_identity()["sha256"])
    require(frozen == dict(training=TRAINING_SHA, official=OFFICIAL_SHA, dialogue=DIALOGUE_SHA, shared=SHARED_SHA),
        "기존47/58/70 또는 원 통계 소스가 달라졌다")
    names = sorted(set((*dialogue.CODE, *shared.SOURCES, *OWN, "scripts/eval_bench_suite.py")))
    files = {name: official.digest(relative(name)) for name in names}
    payload = dict(files=files, frozen=frozen)
    return dict(**payload, sha256=sha(payload))


class Inputs:
    """원 Inputs를 감싸 CP 경로를 먼저 거부한다. 원 helper 전역은 안 바꾼다."""
    def __init__(self, shared):
        self.owner = shared.Inputs()
        self.files = self.owner.files
    def add(self, path, expected=None):
        return self.owner.add(checked(path), expected)
    def unchanged(self):
        return self.owner.unchanged()


class Evidence:
    def __init__(self, shared, *, root=None):
        root = ROOT if root is None else root
        self.shared, self.root, self.inputs = shared, Path(root), Inputs(shared)
    def path(self, name):
        return relative(name, self.root)
    def json(self, path, expected=None):
        path = checked(path)
        if not path.is_file():
            raise Hold("정확한 종결 또는 metadata가 아직 없다: " + str(path))
        require(path.stat().st_size < MAX_BYTES, "metadata JSON은20MB 미만이어야 한다")
        self.inputs.add(path, expected)
        value = self.shared.read_json(path)
        canonical(value)
        self.inputs.add(path, expected)
        return value
    def ref(self, ref):
        require(isinstance(ref, dict) and re.fullmatch("[0-9A-F]{64}", str(ref.get("sha256", ""))), "경로와 정확한 원 SHA가 필요하다")
        return self.json(self.path(ref["path"]), ref["sha256"])
    def terminal(self, directory, wanted):
        path = checked(directory / "terminal.jsonl")
        require(path.is_file() and path.stat().st_size < MAX_BYTES, "완결 종결 원장이 필요하다")
        self.inputs.add(path, wanted)
        events = [self.shared.decode(line) for line in path.read_bytes().splitlines()]
        require(events == [dict(event="OBSERVATION", returncode=0)], "후행 거부 또는 미완 종결 원장이 있다")
    def manifest(self, directory, stem, value, lineage, *, rows=None, bodies=False):
        require(value.get("schema") == "P106B_WRITE_ONCE_SHARDS_V1" and value.get("lineage") == lineage
            and type(value.get("limit_bytes")) is int and 0 < value["limit_bytes"] < MAX_BYTES
            and (rows is None or value.get("rows") == rows), "새 raw manifest의 원 계보·분모가 다르다")
        path = checked(directory / (stem + "_shards_manifest.json"))
        require(self.json(path) == value, "실제 disk manifest와 worker 내 원형이 다르다")
        for index, spec in enumerate(value["shards"]):
            require(spec["path"] == stem + "_" + str(index).zfill(6) + ".jsonl"
                and type(spec.get("bytes")) is int and 0 < spec["bytes"] < MAX_BYTES,
                "원 shard 이름·20MB 미만 계약이 다르다")
            raw = checked(directory / spec["path"])
            require(raw.is_file() and raw.stat().st_size == spec["bytes"], "원 raw shard 크기가 다르다")
            if bodies:
                self.inputs.add(raw, spec["sha256"])


def code_receipt(value, expected):
    files = value.get("files")
    require(isinstance(files, dict) and files and value.get("sha256") == expected and sha(files) == expected
        and all(isinstance(name, str) and not Path(name).is_absolute() and ".." not in Path(name).parts
            and re.fullmatch("[0-9A-F]{64}", str(digest)) for name, digest in files.items()), "보존된 원 source 영수증이 다르다")


def parent_receipt(spec, report, evidence, *, schema, mode, source, arm, profile_sha):
    if type(spec.get("actual_supervisor_exit")) is not int or spec["actual_supervisor_exit"] != 0:
        raise Hold("총괄이 회수한 실제 부모 종료0이 없다")
    if type(report.get("returncode")) is not int or report["returncode"] != 0:
        raise Hold("정상 완료 부모가 아니다")
    require(report.get("schema") == schema and report.get("mode") == mode and report.get("arm") == arm
        and report.get("source_sha256") == source and report.get("profile_sha256") == profile_sha
        and training.supervision_ok(report.get("supervision", {})), "원 부모·소스·팔·자연 정리가 다르다")
    wall = spec.get("actual_parent_wall_sec")
    require(type(wall) in (int, float) and math.isfinite(wall) and wall > 0
        and type(report.get("whole_parent_seconds")) in (int, float) and math.isfinite(report["whole_parent_seconds"])
        and 0 < report["whole_parent_seconds"] <= wall, "실제 부모 전체 시간 영수증이 다르다")
    directory = evidence.path(spec["path"]).parent
    require(evidence.path(spec["path"]).name == "report.json", "원 report.json 경로가 필요하다")
    evidence.terminal(directory, spec["terminal_sha256"])
    worker = evidence.json(directory / "worker.json", report["worker_sha256"])
    require(canonical(report.get("worker")) == canonical(worker), "실제 worker와 부모에 보존된 원형이 다르다")
    code_receipt(evidence.json(directory / "source.json"), source)
    return worker, directory


def new_metadata(model, entry, root_spec, evidence):
    profile = evidence.ref(entry["profile"])
    profile_sha = entry["profile"]["sha256"]
    require(profile.get("schema") == official.PROFILE and profile.get("root_approved") is True
        and profile.get("arm") == model and profile.get("source_sha256") == OFFICIAL_SHA
        and profile.get("training_source_sha256") == TRAINING_SHA
        and canonical(profile.get("official_policy")) == canonical(official.policy())
        and canonical(profile.get("numerical_contract")) == canonical(official.CONTRACT)
        and profile.get("deadline") == official.END.isoformat(), "새 모델의 원 공식 profile이 다르다")
    train_profile = evidence.ref(profile["training_profile"])
    f4 = evidence.ref(profile["training_f4"])
    require(train_profile.get("schema") == training.PROFILE and train_profile.get("recipe") == training.RECIPE
        and f4.get("schema") == "P106B_NATIVE_FORMAT_F4_V1" and f4.get("root_approved") is True
        and f4.get("source_sha256") == TRAINING_SHA and f4.get("profile_sha256") == profile["training_profile"]["sha256"]
        and "train" in f4.get("allowed_modes", []), "원 학습 profile/F4 계보가 다르다")
    arm = training.arm_for(dict(profile=train_profile), model)
    require(arm["corpus"] == "format" and arm["optimizer"] == ("muon" if model == NEW_MODELS[0] else "normuon")
        and arm["required"] is True, "필수 형식 두 팔의 정확한 optimizer가 필요하다")
    require(train_profile.get("normuon") == dict(beta2=.95, eps=1e-10, implementation="TINYLM_ADAPTED_POST_NS_ROW_EMA"),
        "선택한 NorMuon의 원 설정이 다르다")
    train_spec = profile["closed_train"]
    train_report = evidence.ref(train_spec)
    train, train_directory = parent_receipt(train_spec, train_report, evidence, schema=training.SCHEMA, mode="train",
        source=TRAINING_SHA, arm=model, profile_sha=profile["training_profile"]["sha256"])
    require(train_report.get("f4_sha256") == profile["training_f4"]["sha256"]
        and train_report.get("pair_complete_sha256") == train_profile["pair_complete"]["sha256"]
        and train.get("schema") == training.SCHEMA and train.get("status") == "TRAIN2289_COMPLETE"
        and train.get("mode") == "train" and train.get("arm") == model and train.get("corpus") == "format"
        and train.get("optimizer") == arm["optimizer"] and train.get("synthetic") is False
        and type(train.get("updates")) is int and train["updates"] == 2289
        and canonical(train.get("totals")) == canonical(dict(targets=300023808, x_tokens=300023808))
        and train.get("scratch_core_sha256") == training.CORE and train.get("original_weights_copied") is False
        and train.get("source_sha256") == TRAINING_SHA
        and train.get("profile_sha256") == profile["training_profile"]["sha256"]
        and train.get("pair_complete_sha256") == train_profile["pair_complete"]["sha256"]
        and train.get("quantization_route") == official.ROUTE and isinstance(train.get("cfg"), dict)
        and type(train.get("training_completed_epoch")) in (float, int)
        and math.isfinite(train["training_completed_epoch"]) and train["training_completed_epoch"] < training.TRAIN_END.timestamp()
        and all(re.fullmatch("[0-9A-F]{64}", str(train.get(key, ""))) for key in ("checkpoint_sha256", "final_core_sha256")),
        "실제 전체2289와 새 CP metadata가 필요하다")
    # CP 경로는 문자열 계보로만 남긴다. is_file/stat/digest도 호출하지 않는다.
    cp = Path(train["checkpoint"])
    require(cp.parts[:2] == ("runs", "ckpt") and len(cp.parts) == 3 and cp.suffix == ".pt", "원 CP 경로 표기가 다르다")
    report = evidence.ref(root_spec)
    worker, directory = parent_receipt(root_spec, report, evidence, schema=official.SCHEMA, mode="full",
        source=OFFICIAL_SHA, arm=model, profile_sha=profile_sha)
    if worker.get("status") != "OFFICIAL_CORE6_FULL_COMPLETE":
        raise Hold("새 공식 전량이 닫히지 않았다")
    require(worker.get("mode") == "full" and worker.get("actual_counts") == COUNTS
        and worker.get("token_lengths_summary", {}).get("requests") == REQUESTS
        and worker.get("source_sha256") == OFFICIAL_SHA and worker.get("profile_sha256") == profile_sha
        and worker.get("training_report_sha256") == train_spec["sha256"]
        and worker.get("checkpoint_sha256") == train["checkpoint_sha256"]
        and worker.get("framework_commit") == official.assets.COMMIT
        and worker.get("data_manifest_sha256") == official.assets.MANIFEST_SHA
        and report.get("authority_end") == official.END.isoformat(), "새 공식19965/67106·CP·과제 계보가 다르다")
    state = dict(source_identity=evidence.json(directory / "source.json"), profile=profile,
        profile_sha256=profile_sha, train=train, train_spec=train_spec, task_specs=worker["task_specs"])
    return dict(model=model, root_spec=root_spec, root_ref=entry["full_root_ref"], profile_ref=entry["profile"],
        report=report, worker=worker, state=state, directory=directory, train_report=train_report,
        train_directory=train_directory, train_profile=train_profile)


def prepare(ref, expected_source, budget, *, root=None):
    root = ROOT if root is None else root
    shared = shared_api()
    signature = source_identity()
    require(expected_source == signature["sha256"], "동결한 새 통계 source pin이 다르다")
    evidence = Evidence(shared, root=root)
    input_spec = evidence.ref(ref)
    require(input_spec.get("schema") == INPUTS_SCHEMA and input_spec.get("root_approved") is True
        and input_spec.get("statistics_source_sha256") == expected_source
        and input_spec.get("official_source_sha256") == OFFICIAL_SHA
        and input_spec.get("training_source_sha256") == TRAINING_SHA
        and input_spec.get("dialogue_source_sha256") == DIALOGUE_SHA
        and set(input_spec.get("new_models", {})) == set(NEW_MODELS), "사전에 고정한 두 새 모델의 입력 계약이 필요하다")
    specs = {}
    # 둘 다 실제 root0일 때만 어느 새 보고서의 수치도 읽는다.
    for model in NEW_MODELS:
        entry = input_spec["new_models"][model]
        require(set(entry) == {"profile", "full_root_ref"}, "새 모델명·스키마 치환을 허용하지 않는다")
        spec = evidence.ref(entry["full_root_ref"])
        if type(spec.get("actual_supervisor_exit")) is not int or spec["actual_supervisor_exit"] != 0:
            raise Hold("두 공식 full의 실제 부모0이 아직 없다")
        specs[model] = spec
    models = {model: new_metadata(model, input_spec["new_models"][model], specs[model], evidence) for model in NEW_MODELS}
    left, right = (models[name]["state"]["train"] for name in NEW_MODELS)
    for key in ("cfg", "offsets", "source_sha256", "profile_sha256", "pair_complete_sha256", "scratch_core_sha256"):
        require(canonical(left[key]) == canonical(right[key]), "두 format 학습의 원 조건이 다르다: " + key)
    for name in PEERS:
        path = checked(shared.report_path(name, root))
        report = evidence.json(path)
        shared.admit_report(name, report)
        models[name] = dict(model=name, path=path, report=report)
    budget.check("두 공식 전량 metadata 입장 후")
    return dict(source=signature, config_ref=ref, evidence=evidence, models=models)


def new_manifests(bundle, evidence, *, bodies):
    worker, directory = bundle["worker"], bundle["directory"]
    require(set(worker["sample_manifests"]) == set(PRIMARY), "6과제 manifest가 모두 있어야 한다")
    for name in PRIMARY:
        evidence.manifest(directory, name + "_samples", worker["sample_manifests"][name],
            dict(schema=official.SCHEMA, checkpoint_sha256=worker["checkpoint_sha256"], task=name, mode="full"),
            rows=COUNTS[name], bodies=bodies)
    evidence.manifest(directory, "token_lengths", worker["lengths_manifest"],
        dict(schema=official.SCHEMA, mode="full", checkpoint_sha256=worker["checkpoint_sha256"]), rows=REQUESTS, bodies=bodies)
    evidence.manifest(directory / "stdout", "stdout", bundle["report"]["supervision"]["stdout_manifest"],
        dict(schema=training.SCHEMA), bodies=bodies)


def new_recount(bundle, tasks, contracts, request_builder, evidence, budget):
    shared, worker = evidence.shared, bundle["worker"]
    values, per_task, correspondence, choices = {}, {}, {}, 0
    for name in PRIMARY:
        rows = list(official.manifests_rows(bundle["directory"], worker["sample_manifests"][name], budget))
        counted = shared.recount_task(name, tasks[name], rows, expected=COUNTS[name], request_builder=request_builder,
            contracts=contracts[name])
        shared.verify_audit(counted["audit"], worker["independent_audits"][name])
        scores = worker["official_results"][name]["results"][name]
        require(PRIMARY[name] + ",none" in scores, "원 주지표가 없다")
        for metric, key in (("acc", "correct"), ("acc_norm", "correct_norm")):
            if metric + ",none" in scores:
                require(math.isclose(scores[metric + ",none"], counted["audit"][key] / COUNTS[name],
                    abs_tol=1e-12, rel_tol=1e-12), "원 공식 집계와 재계수가 다르다")
        audit = counted["audit"]
        values[name] = counted["values"]; correspondence[name] = counted["correspondence"]
        per_task[name] = dict(rows=COUNTS[name], primary_metric=PRIMARY[name], primary_correct=sum(values[name]),
            primary_score=sum(values[name]) / COUNTS[name], acc=audit["correct"] / COUNTS[name],
            acc_norm=audit["correct_norm"] / COUNTS[name],
            baseline=dict(random_expectation=audit["random_expected_correct"] / COUNTS[name],
                posthoc_label_majority=audit["posthoc_majority_correct"] / COUNTS[name],
                posthoc_label_counts={str(k): v for k, v in audit["posthoc_label_counts"].items()},
                shortest=audit["shortest_correct"] / COUNTS[name], longest=audit["longest_correct"] / COUNTS[name],
                baseline_policy=audit["baseline_policy"], trained_baseline=False),
            raw_concat_sha256=worker["sample_manifests"][name]["concat_sha256"],
            choice_likelihoods=counted["choice_likelihoods"], correspondence=counted["correspondence"])
        choices += counted["choice_likelihoods"]
        budget.check("새 공식 과제 원형 재계수 후")
    require(sum(map(len, values.values())) == ITEMS and choices == REQUESTS, "3269 교집합이나 부분 전량은 허용하지 않는다")
    return dict(model=bundle["model"], rows=ITEMS, choice_likelihoods=choices, values=values, per_task=per_task,
        correspondence=correspondence, mean6=sum(row["primary_score"] for row in per_task.values()) / 6)


def family_ids():
    return [left + "__" + right + "__" + name for left, right in PAIRS for name in PRIMARY]


def holm(tests):
    """지정한30개 p값의 step-down adjusted p만 반환하며 승자를 정하지 않는다."""
    require(len(tests) == FAMILY and [row["id"] for row in tests] == family_ids()
        and len({row["id"] for row in tests}) == FAMILY, "5쌍×6과제의 하나인30검정 가족이 필요하다")
    require(all(type(row.get("raw_p")) in (int, float) and math.isfinite(row["raw_p"])
        and 0 <= row["raw_p"] <= 1 for row in tests), "유한한 양측 p값이 필요하다")
    adjusted, previous = {}, 0.
    for rank, index in enumerate(sorted(range(FAMILY), key=lambda i: (tests[i]["raw_p"], i))):
        previous = min(1., max(previous, (FAMILY - rank) * tests[index]["raw_p"]))
        adjusted[index] = dict(holm_adjusted_p=previous, holm_rank=rank + 1)
    return [dict(row, **adjusted[i]) for i, row in enumerate(tests)]


def comparisons(models, *, paired=None, exact=None):
    shared = shared_api()
    paired = shared.paired_intervals if paired is None else paired
    exact = mcnemar_exact_p if exact is None else exact
    require(set(models) == set((*NEW_MODELS, *PEERS)), "사전 고정4모델만 통계에 넣는다")
    reference = models[NEW_MODELS[0]]["correspondence"]
    require(set(reference) == set(PRIMARY) and all(set(row) == {key + "_ordered_sha256" for key in
        ("docs", "arguments", "gold_choices", "cases")} and all(re.fullmatch("[0-9A-F]{64}", str(v)) for v in row.values())
        for row in reference.values()), "과제별 원 순서4SHA가 필요하다")
    for model in models.values():
        require(model["correspondence"] == reference and set(model["values"]) == set(PRIMARY)
            and model["rows"] == ITEMS and model["choice_likelihoods"] == REQUESTS, "4개 원 문항 대응 SHA 또는 전량 분모가 다르다")
        for name in PRIMARY:
            require(len(model["values"][name]) == COUNTS[name]
                and all(type(value) is int and value in (0, 1) for value in model["values"][name]),
                "공식 분모의 원 binary 정답만 허용한다")
    result, tests = {}, []
    for left, right in PAIRS:
        interval = paired(models[left]["values"], models[right]["values"], draws=RESAMPLES, seed=SEED)
        key = left + "__" + right
        require(set(interval["per_task"]) == set(PRIMARY), "기존 구간의6과제가 다르다")
        for name in PRIMARY:
            row = interval["per_task"][name]
            worse, better, same = row["discordant_right_worse"], row["discordant_right_better"], row["same_correctness"]
            require(row["n"] == COUNTS[name] and all(type(v) is int and v >= 0 for v in (worse, better, same))
                and worse + better + same == COUNTS[name], "정확 검정에 전달할 전량 불일치 정수가 다르다")
            p = exact(worse, better)
            tests.append(dict(id=key + "__" + name, left_model=left, right_model=right, task=name,
                n=COUNTS[name], primary_metric=PRIMARY[name], left_only_correct=worse, right_only_correct=better,
                raw_p=p, method="EXISTING_TWO_SIDED_EXACT_MCNEMAR", float_zero_may_underflow=(p == 0.)))
        result[key] = dict(left_model=left, right_model=right, difference="RIGHT_MINUS_LEFT", pointwise95=interval)
    adjusted = holm(tests)
    return dict(pairs=result, exact_tests=adjusted,
        holm_family=dict(method="HOLM_STEP_DOWN", size=FAMILY, ids=family_ids(), families=1,
            all_planned_tests_included=True, adjusted_p_only=True, automatic_rejection=False),
        intervals=dict(level=.95, pointwise=True, simultaneous=False, multiplicity_adjusted=False,
            training_seed_uncertainty=False, task_population_uncertainty=False, resamples=RESAMPLES, seed=SEED))


def collect(prepared, budget):
    evidence, models = prepared["evidence"], prepared["models"]
    shared = evidence.shared
    for name in NEW_MODELS:
        bundle = models[name]
        new_manifests(bundle, evidence, bodies=True)
        closed = read_official_closed(bundle["root_spec"], bundle["state"], "full", budget)
        require(canonical(closed) == canonical(bundle["report"]), "새 공식 종결 검산 중 원형이 달라졌다")
    tasks, proof = shared.load_readonly_tasks(evidence.inputs)
    from scripts.p106b_official_tasks import task_requests
    contracts = {name: shared.CaseContracts(tasks[name], COUNTS[name], task_requests) for name in PRIMARY}
    counted = {name: new_recount(models[name], tasks, contracts, task_requests, evidence, budget) for name in NEW_MODELS}
    for name in PEERS:
        bundle = models[name]
        counted[name] = shared.recount_model(name, bundle["path"], bundle["report"], tasks, evidence.inputs, task_requests, contracts)
    stats = comparisons(counted)
    summaries = {}
    for name, model in counted.items():
        summaries[name] = {key: model[key] for key in ("model", "rows", "choice_likelihoods", "per_task", "mean6", "correspondence")}
        if name in NEW_MODELS:
            bundle = models[name]
            summaries[name]["lineage"] = dict(full_root_ref=bundle["root_ref"], report=bundle["root_spec"],
                profile=bundle["profile_ref"], training_report=bundle["state"]["train_spec"],
                checkpoint_path=bundle["state"]["train"]["checkpoint"], checkpoint_sha256=bundle["worker"]["checkpoint_sha256"],
                core_sha256=bundle["state"]["train"]["final_core_sha256"])
        else:
            summaries[name]["lineage"] = dict(report_path=str(models[name]["path"]),
                report_sha256=evidence.inputs.files[str(models[name]["path"])]["sha256"])
    final_check(prepared, budget)
    return dict(models=summaries, **stats, primary_metrics=PRIMARY, task_counts=COUNTS,
        task_source_sha256=proof["task_source_sha256"], framework_revision=official.assets.COMMIT,
        data_manifest_sha256=official.assets.MANIFEST_SHA, input_files=evidence.inputs.files,
        interpretation=SCOPE, raw_arrays_copied=False, raw_examples_copied=0, model_weight_bodies_read=False,
        models_loaded=0, gpu_calls=0, adoption_decision=False, posthoc_majority_is_trained_baseline=False,
        preregistration_stages=["Stage10g0W", "Stage10gW"])


def final_check(prepared, budget):
    require(source_identity() == prepared["source"], "원형 통계·모델 source가 실행 중 달라졌다")
    prepared["evidence"].inputs.unchanged()
    budget.check("통계 원형 최종 재검산 후")


def output_path(name):
    path = Path(name)
    require(path.parts[:2] == ("test_result", "evidence") and len(path.parts) == 3
        and re.fullmatch(PREFIX + "[A-Za-z0-9_]+", path.name), "새 통계 증거 이름공간이 필요하다")
    target = relative(name)
    require(not target.exists(), "이전 완결·부분 통계를 보존한다")
    return target


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    group = value.add_mutually_exclusive_group(required=True)
    group.add_argument("--source-only", action="store_true")
    group.add_argument("--check-only", action="store_true")
    group.add_argument("--execute", action="store_true")
    value.add_argument("--inputs"); value.add_argument("--inputs-sha256")
    value.add_argument("--source-sha256"); value.add_argument("--output")
    value.add_argument("--max-wall-sec", type=int, default=120)
    value.add_argument("--deadline", default=official.END.isoformat())
    return value


def main(argv=None):
    args = parser().parse_args(argv)
    target, owned = None, False
    try:
        if args.source_only:
            print(json.dumps(dict(schema=SCHEMA, status="SOURCE_ONLY", source_identity=source_identity(),
                pairs=PAIRS, exact_test_family_size=FAMILY, model_weight_bodies_read=False, raw_reads=0,
                models_loaded=0, gpu_calls=0, files_written=0), ensure_ascii=False), flush=True)
            return 0
        if not args.inputs or not args.inputs_sha256 or not args.source_sha256:
            raise Hold("두 full 종결과 총괄 입력 명세가 아직 없다")
        require(10 <= args.max_wall_sec <= 600, "전체 CPU 통계 시간창은10..600초다")
        deadline = datetime.fromisoformat(args.deadline.replace("Z", "+00:00"))
        require(deadline.tzinfo is not None and deadline <= official.END, "현재 CPU 연구 마감은26일17시 안이다")
        budget = supervisor.Budget(args.max_wall_sec, deadline.timestamp(), started=STARTED, reserve=1)
        with supervisor.total_budget(budget), supervisor.termination_guard():
            prepared = prepare(dict(path=args.inputs, sha256=args.inputs_sha256), args.source_sha256, budget)
            if args.check_only:
                result = dict(schema=SCHEMA, status="CLOSED_FULL_METADATA_ONLY", statistics="NOT_RUN", raw_recount="NOT_RUN",
                    new_models=NEW_MODELS, planned_pairs=PAIRS, tests_in_one_holm_family=FAMILY,
                    model_weight_bodies_read=False, models_loaded=0, gpu_calls=0, files_written=0)
            else:
                require(args.output is not None, "새 통계 출력 경로가 필요하다")
                target = output_path(args.output); target.mkdir(); owned = True
                summary = collect(prepared, budget)
                report = dict(schema=SCHEMA, status="PAIR_STATS_COMPUTE_CLOSED_PENDING_TERMINAL", returncode=9,
                    candidate_returncode=0, candidate_status="PAIR_STATS_CPU_COMPLETE", source_identity=prepared["source"],
                    input_manifest=prepared["config_ref"], **summary, whole_parent_seconds=time.monotonic() - budget.started,
                    actual_parent_exit="ROOT_MUST_COLLECT", external_root_timeout_required=True,
                    acceptance_requires="ACTUAL_PROCESS_EXIT0_AND_SINGLE_TERMINAL0_AND_UNCHANGED_INPUTS")
                supervisor.write_once(target / "report.json", report, budget)
                result = dict(schema=SCHEMA, status="PAIR_STATS_SUCCESS_CANDIDATE", report_path=str(target / "report.json"),
                    report_sha256=official.digest(target / "report.json", budget), tests=FAMILY, pairs=len(PAIRS),
                    model_weight_bodies_read=False, models_loaded=0, gpu_calls=0, raw_arrays_copied=False)
            final_check(prepared, budget)
            budget.check("통계 작은 출력 전")
            print(json.dumps(result, ensure_ascii=False), flush=True)
            budget.check("통계 작은 출력 뒤")
        budget.check("통계 타이머·신호 복구 뒤")
        if owned:
            supervisor.append_terminal(target, dict(event="OBSERVATION", returncode=0))
            budget.check("통계 최종 종결 뒤")
        return 0
    except BaseException as error:
        record = supervisor.error_record(error, "새 형식 통계 준비·종결")
        if owned and target is not None and target.is_dir():
            try:
                supervisor.append_terminal(target, dict(event="TERMINAL_VETO", returncode=9, error=record))
            except BaseException:
                pass
        code = 8 if isinstance(error, Hold) and not owned else 9
        try:
            print(json.dumps(dict(schema=SCHEMA, returncode=code, error=record), ensure_ascii=False), flush=True)
        except BaseException:
            code = 9
        return code


if __name__ == "__main__":
    raise SystemExit(main())
