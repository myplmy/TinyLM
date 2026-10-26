#!/usr/bin/env python3
"""완주한 새 native 형식 대조 CP의 별도 공식 Core6 접점.

기존 공식 과제·adapter·우도·집계와 소유 감독을 그대로 호출한다.
CPU 준비는 모델을 열지 않는다. 총괄이 회수한 완주 부모0·새 CP·새
카나리와 비용 영수증이 있어야 전량을 연다. 기존 모델명·마감·전역은
바꾸지 않는다. 부모 강제 사망 뒤 전체 자손 회수는 외부 감독 소유다.
"""
from __future__ import annotations
import time
STARTED = time.monotonic()
import argparse
import base64
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import sysconfig
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_native_format_training as training
from scripts import diag_p106b_official_core6 as official
from scripts import diag_p106b_official_adapter as original_canary
from scripts import p106b_official_lm_adapter as adapter
from scripts import prepare_p106b_official_eval as assets
from scripts.p106b_shards import ShardWriter, verify

supervisor = training.supervisor
Hold = training.Hold
SCHEMA = "P106B_NATIVE_FORMAT_OFFICIAL_V1"
PROFILE = "P106B_NATIVE_FORMAT_OFFICIAL_PROFILE_V1"
ADMISSION = "P106B_NATIVE_FORMAT_OFFICIAL_ADMISSION_V1"
PREFIX = "p106b_native_format_official_v1_20261026_"
END = datetime(2026, 10, 26, 8, tzinfo=timezone.utc)
MODES = ("canary", "cost", "full")
ITEMS, REQUESTS = 19965, 67106
ATOL, RTOL = official.ATOL, official.RTOL
CASES = original_canary.CASES * 2
CONTRACT = dict(master="FP32", compute="FP32", attention="SDPA_MATH", tf32=False,
    mtp=False, anneal=1., freeze_quant=True, batch_size=8, atol=ATOL, rtol=RTOL,
    quantization_scope="TLINEAR_WEIGHTS_ONLY", tolerance_source="scripts/test_p070b_cla_routes.py")
ROUTE = dict(schema="P106B_WEIGHT_ROUTE_V1", mode="ternary", scope="TLINEAR_WEIGHTS_ONLY",
    master_dtype="fp32", compute_policy="CALLER_MATCHED_BF16_AMP_TRAIN_FP32_MATH_EVAL",
    forward="ORIGINAL_ANNEALED_TERNARY", backward="ORIGINAL_STE_WINDOW", dedicated_loader_required=True)
CODE = tuple(sorted(set((*training.CODE, *official.SOURCES,
    "scripts/diag_p106b_official_adapter.py", "scripts/p106b_official_lm_adapter.py",
    "scripts/diag_p106b_native_format_official.py", "scripts/test_p106b_native_format_official.py"))))


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return adapter.canonical(value)


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest().upper()


def safe(name):
    return supervisor.safe(name, root=ROOT)


def digest(path, budget=None):
    path = Path(path)
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)), "비링크 정규 파일이 필요하다")
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            if budget is not None:
                budget.check("파일 SHA 검산")
            result.update(block)
    return result.hexdigest().upper()


def source_identity(budget=None):
    files = {name: digest(safe(name), budget) for name in CODE}
    return dict(files=files, sha256=sha(files))


def read_ref(ref, budget=None):
    require(isinstance(ref, dict) and re.fullmatch("[0-9A-F]{64}", str(ref.get("sha256", ""))), "명시한 파일과 SHA가 필요하다")
    path = safe(ref["path"])
    if not path.is_file():
        raise Hold("선결 원형 파일이 아직 없다: " + ref["path"])
    require(path.stat().st_size < 20_000_000, "작은 원형 JSON은20MB 미만이어야 한다")
    require(digest(path, budget) == ref["sha256"], "원형 SHA가 다르다: " + ref["path"])
    value = json.loads(path.read_bytes(), object_pairs_hook=adapter._unique_object)
    canonical(value)
    require(digest(path, budget) == ref["sha256"], "읽는 중 원형이 달라졌다")
    return value


def policy():
    return official.policy()


def metadata(args, budget):
    own = source_identity(budget)
    require(args.source_sha256 == own["sha256"], "총괄이 지정한 새 평가 source가 다르다")
    ref = dict(path=args.profile, sha256=args.profile_sha256)
    profile = read_ref(ref, budget)
    require(profile.get("schema") == PROFILE and profile.get("root_approved") is True
        and profile.get("source_sha256") == own["sha256"]
        and canonical(profile.get("official_policy")) == canonical(policy())
        and canonical(profile.get("numerical_contract")) == canonical(CONTRACT)
        and profile.get("deadline") == END.isoformat()
        and type(profile.get("cleanup_reserve_sec")) is int and profile["cleanup_reserve_sec"] >= 120
        and type(profile.get("entry_free_mib")) is int and profile["entry_free_mib"] > 0,
        "새 평가의 정확한 총괄 profile·원 수치 문턱·17시 마감이 필요하다")
    train_args = SimpleNamespace(mode="train", profile=profile["training_profile"]["path"],
        profile_sha256=profile["training_profile"]["sha256"], f4=profile["training_f4"]["path"],
        f4_sha256=profile["training_f4"]["sha256"])
    train_state = training.metadata(train_args)
    require(profile.get("training_source_sha256") == train_state["source_identity"]["sha256"], "동결 학습 source pin이 다르다")
    closed = training.read_closed(profile["closed_train"], train_state, profile["arm"], "train")
    child = closed["worker"]
    require(child.get("updates") == 2289 and child.get("totals") == dict(targets=300023808, x_tokens=300023808)
        and child.get("status") == "TRAIN2289_COMPLETE" and child.get("synthetic") is False
        and type(child.get("updates")) is int and child.get("scratch_core_sha256") == training.CORE
        and child.get("original_weights_copied") is False and isinstance(child.get("cfg"), dict)
        and re.fullmatch("[0-9A-F]{64}", str(child.get("final_core_sha256", "")))
        and canonical(child.get("quantization_route")) == canonical(ROUTE), "실제 전체300M 완주와 본체 지문이 필요하다")
    checkpoint = safe(child["checkpoint"])
    require(Path(child["checkpoint"]).parts[:2] == ("runs", "ckpt") and len(Path(child["checkpoint"]).parts) == 3,
        "새 완주 CP의 명시한 로컬 경로가 필요하다")
    if not checkpoint.is_file():
        raise Hold("완주한 실제 새 CP가 아직 없다")
    require(digest(checkpoint, budget) == child["checkpoint_sha256"], "실제 새 CP SHA가 다르다")
    require(digest(safe(str((assets.ASSETS / "manifest.json").relative_to(ROOT))), budget) == assets.MANIFEST_SHA,
        "기존 공식 과제 manifest가 다르다")
    specs = assets.task_specs(supervisor.read_json(assets.ASSETS / "manifest.json"))
    assets.verify_assets(specs)
    framework = adapter.verify_harness_source()
    budget.check("평가 metadata와 공식 원형 검산 후")
    return dict(profile=profile, profile_sha256=args.profile_sha256, profile_ref=ref,
        source_identity=own, training_state=train_state, training_args=train_args,
        train=child, train_spec=profile["closed_train"], task_specs=specs, framework=framework)


def immutable(state, budget):
    require(source_identity(budget) == state["source_identity"], "실행 중 평가·학습 source가 달라졌다")
    require(read_ref(state["profile_ref"], budget) == state["profile"], "실행 중 총괄 profile이 달라졌다")
    current = training.metadata(state["training_args"])
    require(current == state["training_state"], "학습 계보 metadata가 달라졌다")
    closed = training.read_closed(state["train_spec"], current, state["profile"]["arm"], "train")
    require(closed["worker"] == state["train"], "완주 원형이 달라졌다")
    require(digest(assets.ASSETS / "manifest.json", budget) == assets.MANIFEST_SHA, "공식 과제 manifest가 달라졌다")
    require(assets.task_specs(supervisor.read_json(assets.ASSETS / "manifest.json")) == state["task_specs"], "공식 과제 명세가 달라졌다")
    assets.verify_assets(state["task_specs"])
    require(adapter.verify_harness_source() == state["framework"], "공식 harness 원형이 달라졌다")
    budget.check("전체 원형 불변 검산 후")


def validate_payload(payload, cfg, state):
    child = state["train"]
    require(isinstance(payload, dict) and set(payload) == {"model", "cfg", "step", "tokenizer_sha256",
        "tokenizer_lineage", "quantization_route", "experiment"}, "새 CP 최상위 정확한7키가 필요하다")
    require(type(payload["step"]) is int and payload["step"] == 2289
        and canonical(payload["cfg"]) == canonical(child["cfg"]) == canonical(asdict(cfg))
        and payload["tokenizer_sha256"] == training.native.TOKENIZER_SHA and payload["tokenizer_lineage"] == "chat32"
        and payload["quantization_route"] == child["quantization_route"]
        and canonical(payload["experiment"]) == canonical(training.checkpoint_experiment(child)), "새 CP의 cfg·실제 완주·원천·삼진 계보가 다르다")
    require(cfg.n_layers == 14 and cfg.dim == 768 and cfg.vocab_size == 32768
        and cfg.max_seq_len == 1024 and cfg.grad_checkpoint is True and cfg.mtp_aux is False
        and cfg.tie_mlp is False, "정확한 native14·FP32 master·MTPoff 형상이 필요하다")


def aliases(model):
    groups = {}
    for name, parameter in model.named_parameters(remove_duplicate=False):
        groups.setdefault(id(parameter), []).append(name)
    return sorted(sorted(names) for names in groups.values() if len(names) > 1)


def live_contract(runtime):
    torch, model, route = runtime["torch"], runtime["model"], runtime["route"]
    route.assert_active()
    require(route.mode == "ternary" and route.metadata == runtime["quantization_route"]
        and route.metadata["scope"] == "TLINEAR_WEIGHTS_ONLY" and not model.training
        and model.cfg.mtp_aux is False and model._quant_frozen is True and float(model._anneal) == 1.
        and all(p.dtype == torch.float32 for p in model.parameters())
        and not torch.backends.cuda.matmul.allow_tf32 and not torch.backends.cudnn.allow_tf32,
        "실제 FP32·삼진·동결·MTPoff·TF32off 경로가 필요하다")
    for module in route.linears:
        require(module._wq is not None and module._wq.dtype == torch.float32
            and route._versions.get(id(module)) == module.weight._version
            and bool(torch.isfinite(module._wq).all()), "동결 삼진 cache의 실제 갱신·유한값·FP32가 다르다")
    return training.native.route_receipt(model, route)


@contextmanager
def strict_runtime(state, budget):
    """새 CP 전용 로더. 옛 endpoint·모델 enum·완주 판정은 호출하지 않는다."""
    from scripts import diag_p101a_sft_mtp as original_runtime
    from scripts import p106b_weight_route as method
    from scripts.interactive_research_infer import require_idle_gpu, state_fingerprint
    torch = model = payload = active = cpu_route = route = None
    primary = None
    gpu_attempted = False
    checkpoint = safe(state["train"]["checkpoint"])
    try:
        budget.check("새 strict CPU 로더 전")
        torch, model, cfg, tok, scratch = original_runtime.load_runtime("scratch_ntp")
        require(scratch == training.CORE, "같은 fresh initializer 지문이 필요하다")
        payload = torch.load(checkpoint, map_location="cpu", weights_only=True)
        require(digest(checkpoint, budget) == state["train"]["checkpoint_sha256"], "CPU load 중 CP SHA가 달라졌다")
        validate_payload(payload, cfg, state)
        training.native.validate_cpu_state(model, payload, torch)
        require(all(not value.is_floating_point() or bool(torch.isfinite(value).all()) for value in payload["model"].values()),
            "CP의 모든 부동소수 상태가 유한해야 한다")
        state_header = {name: dict(shape=list(value.shape), dtype=str(value.dtype), layout=str(value.layout))
            for name, value in model.state_dict().items()}
        method.validate_route_metadata(payload["quantization_route"], "ternary")
        expected_aliases = aliases(model)
        with method.weight_route(model, "ternary") as cpu_route:
            cpu_route.assert_active()
            method.load_routed_state(model, payload, "ternary")
            require(state_fingerprint(model) == state["train"]["final_core_sha256"], "실제 CPU load 본체 지문이 다르다")
        payload = None
        admission = training.fresh_admission(state["profile"], budget)
        point = require_idle_gpu()
        require(torch.cuda.is_available(), "CUDA 전용 공식 평가이며 CPU 대체는 없다")
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        gpu_attempted = True
        model = model.cuda()
        require(aliases(model) == expected_aliases, "CUDA 이동 뒤 공유 Parameter 관계가 달라졌다")
        with method.weight_route(model, "ternary") as route:
            route_error = None
            try:
                model.clear_quant(); model.eval(); model.set_anneal(1.)
                with torch.no_grad():
                    model.freeze_quant()
                before = state_fingerprint(model)
                require(before == state["train"]["final_core_sha256"], "실제 GPU load 본체 지문이 다르다")
                active = dict(root=str(ROOT), torch=torch, model=model, cfg=cfg, tokenizer=tok, route=route,
                    precision="FP32_MATH", checkpoint=state["train"]["checkpoint"],
                    checkpoint_sha256=state["train"]["checkpoint_sha256"], tokenizer_sha256=training.native.TOKENIZER_SHA,
                    quantization_route=route.metadata)
                proof = dict(checkpoint=active["checkpoint"], checkpoint_sha256=active["checkpoint_sha256"],
                    cpu_and_gpu_core_sha256=before, aliases=expected_aliases,
                    scratch_core_sha256=scratch, state_header_sha256=sha(state_header), state_keys=len(state_header),
                    cpu_key_shape_dtype_layout_alias_verified=True, all_checkpoint_floats_finite=True,
                    cfg=json.loads(canonical(asdict(cfg))), contract=CONTRACT, gpu_point_query=point, admission=admission,
                    route=live_contract(active), original_training_weights_copied=False, updates=2289, targets=300023808,
                    parameter_requires_grad="기존 route 검사 보존; eval·no_grad·양자화 cache 동결; optimizer 없음")
                yield active, proof
                proof["final_route"] = live_contract(active)
                proof["final_core_sha256"] = state_fingerprint(model)
                require(proof["final_core_sha256"] == before, "평가 중 FP32 master가 바뀌었다")
                require(aliases(model) == expected_aliases, "평가 중 공유 Parameter 관계가 달라졌다")
                require(digest(checkpoint, budget) == active["checkpoint_sha256"], "평가 중 CP 원형이 바뀌었다")
            except BaseException as error:
                route_error = error
                raise
            finally:
                training.close_preserving(route_error, [("평가 양자화 cache 해제", model.clear_quant)])
    except BaseException as error:
        primary = error
        raise
    finally:
        if active is not None:
            active.clear()
        active = payload = model = cpu_route = route = None
        actions = [("평가 CPU 참조 회수", gc.collect)]
        if gpu_attempted:
            actions.append(("평가 CUDA cache 회수", torch.cuda.empty_cache))
        training.close_preserving(primary, actions)


def close_pair(left, right):
    require(isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)) and len(left) == len(right) == 2
        and type(left[1]) is type(right[1]) is bool and all(type(x[0]) in (float, int)
            and math.isfinite(x[0]) and x[0] <= 0 for x in (left, right)), "유한한 전체 우도·greedy bool이 필요하다")
    return math.isclose(left[0], right[0], abs_tol=ATOL, rel_tol=RTOL) and left[1] == right[1]


def canary(lm, torch):
    from lm_eval.api.instance import Instance
    require(lm.core.batch_size == 8 and len(CASES) == 8, "실제 배치8 카나리만 허용한다")
    scorer, blocks, batch_size = lm.core.score_batch, [], lm.core.batch_size
    def compare(batch):
        left = list(scorer(batch))
        right = adapter.direct_label_oracle(torch, scorer.forward, batch, scorer.runtime["cfg"].vocab_size)
        require(len(left) == len(right) == len(batch["lengths"]), "full-label oracle 분모가 다르다")
        rows = [dict(gather=list(a), full_label=list(b), close=close_pair(a, b)) for a, b in zip(left, right)]
        blocks.append(dict(lengths=batch["lengths"], labels=batch["labels"], rows=rows))
        require(all(row["close"] for row in rows), "기존 문턱의 전체 라벨 CE 카나리에 미달했다")
        return left
    try:
        lm.core.score_batch = compare
        requests = [Instance(request_type="loglikelihood", doc={}, arguments=case, idx=i,
            metadata=("synthetic_backend_canary", i, 1)) for i, case in enumerate(CASES)]
        batched = lm.loglikelihood(requests, disable_tqdm=True)
        lm.core.batch_size = 1
        separate = lm.loglikelihood(requests, disable_tqdm=True)
        require(len(batched) == len(separate) == 8, "배치·단일 요청 분모가 다르다")
        pairs = [dict(batched=list(a), separate=list(b), close=close_pair(a, b)) for a, b in zip(batched, separate)]
        result = dict(status="CANARY_COMPLETE", batch_size=8, requests=[list(c) for c in CASES],
            atol=ATOL, rtol=RTOL, oracle_blocks=blocks, batch_vs_separate=pairs, quality_claim=False)
        validate_canary(result)
        return result
    finally:
        lm.core.score_batch = scorer
        lm.core.batch_size = batch_size


def validate_canary(value):
    require(value.get("status") == "CANARY_COMPLETE" and value.get("batch_size") == 8
        and value.get("requests") == [list(c) for c in CASES] and value.get("atol") == ATOL
        and value.get("rtol") == RTOL and value.get("quality_claim") is False,
        "현재 CP의 원 문턱·배치8 카나리 계약이 필요하다")
    blocks, pairs = value["oracle_blocks"], value["batch_vs_separate"]
    require(len(blocks) == 9 and [len(b["lengths"]) for b in blocks] == [8] + [1] * 8
        and len(pairs) == 8, "배치8 한 번과 단일8회의 전체 라벨 oracle이 필요하다")
    for block in blocks:
        require(len(block["rows"]) == len(block["lengths"]) == len(block["labels"]), "oracle 행 수가 다르다")
        require(all(type(v) is int and v > 0 for v in block["lengths"]), "실제 카나리 길이가 필요하다")
        for length, labels in zip(block["lengths"], block["labels"]):
            require(len(labels) >= length and all(type(v) is int and (v == -100 or 0 <= v < 32768) for v in labels)
                and any(v >= 0 for v in labels[:length]) and all(v == -100 for v in labels[length:]),
                "실제 continuation label과 우측 pad 제외가 필요하다")
        for row in block["rows"]:
            require(row.get("close") is True and close_pair(row["gather"], row["full_label"]), "full-label 수치를 재검산하면 다르다")
    require(all(row.get("close") is True and close_pair(row["batched"], row["separate"]) for row in pairs),
        "배치 대 단일 수치를 재검산하면 다르다")
    require(all(pair["batched"] == blocks[0]["rows"][i]["gather"]
        and pair["separate"] == blocks[i+1]["rows"][0]["gather"] for i, pair in enumerate(pairs)),
        "배치 비교와 full-label 블록의 실제 관측값이 다르다")


def audit_rows(rows, expected, spec):
    """원 과제에서 보존한 선택지·원 label로 기존 집계 함수를 재사용한다."""
    docs = []
    for row in rows:
        require(type(row["doc_id"]) is int, "원 문항 번호는 실제 정수여야 한다")
        info = row["native_format_recount"]
        require(info["task"] == spec["task"] and info["data_sha256"] == spec["data_sha256"]
            and info["official_yaml_sha256"] == spec["official_yaml_sha256"]
            and info["dataset_revision"] == spec["dataset_revision"] and info["doc_sha256"] == sha(row["doc"]),
            "원 문항·label·과제 SHA 계보가 다르다")
        require(all(isinstance(value, (list, tuple)) and len(value) == 2 and type(value[1]) is bool
            for value in row["filtered_resps"]), "선택지 전체 우도와 greedy 원형이 필요하다")
        docs.append(info)
    task = SimpleNamespace(eval_docs=docs, multiple_input=False,
        doc_to_choice=lambda doc: doc["choices"], doc_to_target=lambda doc: doc["gold"])
    return official.audit_samples(task, rows, expected)


def manifests_rows(directory, manifest, budget):
    verify(directory, manifest)
    for spec in manifest["shards"]:
        require(spec["bytes"] < 20_000_000, "raw shard는20MB 미만이어야 한다")
        with (directory / spec["path"]).open(encoding="utf-8") as stream:
            for line in stream:
                budget.check("raw 문항 재계수")
                value = json.loads(line, object_pairs_hook=adapter._unique_object)
                canonical(value)
                yield value


def validate_route_receipt(value):
    """표준 라이브러리 영수증 검사. 실제 route 설치는 strict_runtime 소유다."""
    require(value.get("mode") == "ternary" and canonical(value.get("metadata")) == canonical(ROUTE)
        and type(value.get("tlinear_instances")) is int and value["tlinear_instances"] > 0
        and type(value.get("owned_tlinear_instances")) is int
        and type(value.get("refreshed_tlinear_instances")) is int
        and value["owned_tlinear_instances"] == value["refreshed_tlinear_instances"] == value["tlinear_instances"]
        and value.get("forward_methods") == ["_guarded_forward"]
        and value.get("refresh_methods") == ["_ternary_refresh"], "실제 전체 TLinear 소유·갱신 영수증이 다르다")


def validate_worker(child, state, mode, directory, budget):
    require(child.get("schema") == SCHEMA and child.get("mode") == mode and child.get("synthetic") is False
        and child.get("source_sha256") == state["source_identity"]["sha256"]
        and child.get("profile_sha256") == state["profile_sha256"]
        and child.get("arm") == state["profile"]["arm"]
        and child.get("training_report_sha256") == state["train_spec"]["sha256"]
        and child.get("checkpoint_sha256") == state["train"]["checkpoint_sha256"]
        and child.get("framework_commit") == assets.COMMIT and child.get("data_manifest_sha256") == assets.MANIFEST_SHA
        and child.get("policy") == policy() and child.get("contract") == CONTRACT
        and type(child.get("optimizer_updates")) is int and child["optimizer_updates"] == 0
        and type(child.get("checkpoint_writes")) is int and child["checkpoint_writes"] == 0
        and type(child.get("models_loaded")) is int and child["models_loaded"] == 1,
        "실제 새 CP의 무학습 공식 평가 계보가 다르다")
    validate_canary(child["canary"])
    proof = child["model_proof"]
    require(proof.get("checkpoint_sha256") == child["checkpoint_sha256"] and proof.get("cfg") == state["train"]["cfg"]
        and proof.get("cpu_and_gpu_core_sha256") == proof.get("final_core_sha256") == state["train"]["final_core_sha256"]
        and proof.get("contract") == CONTRACT and proof.get("updates") == 2289 and proof.get("targets") == 300023808
        and proof.get("scratch_core_sha256") == training.CORE
        and re.fullmatch("[0-9A-F]{64}", str(proof.get("state_header_sha256", "")))
        and type(proof.get("state_keys")) is int and proof["state_keys"] > 0
        and proof.get("cpu_key_shape_dtype_layout_alias_verified") is True and proof.get("all_checkpoint_floats_finite") is True
        and proof.get("original_training_weights_copied") is False, "CPU/GPU load와 세션 종료의 본체 지문이 다르다")
    for key in ("route", "final_route"):
        validate_route_receipt(proof[key])
        require(proof[key]["metadata"] == state["train"]["quantization_route"], "실제 살아있는 삼진 route가 다르다")
    require(child.get("status") == {"canary": "CANARY_COMPLETE", "cost": "LIMITED_COST_DIAGNOSTIC",
        "full": "OFFICIAL_CORE6_FULL_COMPLETE"}[mode], "완결 상태가 정확한 실행 범위와 다르다")
    if mode == "canary":
        require(child.get("actual_counts") == {} and child.get("quality_claim") is False, "카나리는 공식 점수가 아니다")
        return child
    counts = official.expected_counts(mode)
    require(child.get("actual_counts") == counts and child.get("task_specs") == state["task_specs"]
        and set(child["sample_manifests"]) == set(counts) and set(child["task_evaluation_seconds"]) == set(counts)
        and all(type(t) in (int, float) and math.isfinite(t) and t > 0 for t in child["task_evaluation_seconds"].values()),
        "정확한 공식 과제·분모·실제 시간이 필요하다")
    requests = 0
    for spec in state["task_specs"]:
        name = spec["task"]
        rows = list(manifests_rows(directory, child["sample_manifests"][name], budget))
        audit = audit_rows(rows, counts[name], spec)
        require(canonical(audit) == canonical(child["independent_audits"][name]), "raw 독립 재계수가 보고 집계와 다르다")
        official_metrics = child["official_results"][name]["results"][name]
        require("acc,none" in official_metrics and (name in ("boolq", "winogrande") or "acc_norm,none" in official_metrics),
            "원 과제의 공식 정확도 집계가 누락됐다")
        for metric, key in (("acc", "correct"), ("acc_norm", "correct_norm")):
            value = official_metrics.get(metric + ",none")
            if value is not None:
                require(type(value) in (float, int) and math.isfinite(value)
                    and math.isclose(value, audit[key] / counts[name], abs_tol=1e-12), "공식 전체 집계와 raw가 다르다")
        requests += sum(len(row["filtered_resps"]) for row in rows)
    lengths = list(manifests_rows(directory, child["lengths_manifest"], budget))
    require([r["index"] for r in lengths] == list(range(requests))
        and child["token_lengths_summary"]["requests"] == len(lengths) == requests, "선택지 전체 요청 분모가 다르다")
    for row in lengths:
        require(all(type(row[key]) is int for key in ("index", "context_tokens", "continuation_tokens", "truncated_context_tokens"))
            and row["context_tokens"] > 0 and 0 < row["continuation_tokens"] <= 1024
            and row["truncated_context_tokens"] == max(0, row["context_tokens"] + row["continuation_tokens"] - 1025)
            and re.fullmatch("[0-9A-F]{64}", row["key_sha256"]), "전체 continuation과 문맥 절단 기록이 다르다")
    summary = dict(requests=requests, context_truncated_requests=sum(r["truncated_context_tokens"] > 0 for r in lengths),
        context_tokens_removed=sum(r["truncated_context_tokens"] for r in lengths),
        continuation_tokens=sum(r["continuation_tokens"] for r in lengths))
    require(summary == child["token_lengths_summary"], "요청 길이 raw 재계수가 다르다")
    if mode == "full":
        require(sum(counts.values()) == ITEMS and requests == REQUESTS, "전량19965문항·67106요청이 필요하다")
    return child


def read_closed(spec, state, mode, budget):
    require(type(spec.get("actual_supervisor_exit")) is int and spec["actual_supervisor_exit"] == 0,
        "총괄이 회수한 실제 평가 부모 종료0이 필요하다")
    report = read_ref(spec, budget)
    directory = safe(spec["path"]).parent
    require(Path(spec["path"]).name == "report.json" and report.get("schema") == SCHEMA
        and type(report.get("returncode")) is int and report["returncode"] == 0
        and report.get("mode") == mode and report.get("source_sha256") == state["source_identity"]["sha256"]
        and report.get("profile_sha256") == state["profile_sha256"]
        and training.supervision_ok(report.get("supervision", {})), "같은 CP·원형의 실제 소유 종결이 필요하다")
    terminal = directory / "terminal.jsonl"
    require(terminal.is_file() and terminal.stat().st_size < 20_000_000
        and digest(terminal, budget) == spec["terminal_sha256"], "종결 원장 SHA가 다르다")
    require([json.loads(line, object_pairs_hook=adapter._unique_object) for line in terminal.read_text(encoding="utf-8").splitlines()]
        == [dict(event="OBSERVATION", returncode=0)], "후행 종결 거부가 있거나 종결이 미완이다")
    child = read_ref(dict(path=str((directory / "worker.json").relative_to(ROOT)), sha256=report["worker_sha256"]), budget)
    require(report["worker"] == child, "부모가 보존한 자식 원형이 다르다")
    validate_worker(child, state, mode, directory, budget)
    require(type(spec.get("actual_parent_wall_sec")) in (float, int) and math.isfinite(spec["actual_parent_wall_sec"])
        and spec["actual_parent_wall_sec"] > 0 and spec["actual_parent_wall_sec"] >= report["whole_parent_seconds"],
        "실제 출력·회수·종료까지의 총괄 전체 시간이 필요하다")
    output_hash, output_bytes = hashlib.sha256(), 0
    for row in manifests_rows(directory / "stdout", report["supervision"]["stdout_manifest"], budget):
        require(row.get("encoding") == "BASE64_RAW_STDOUT" and isinstance(row.get("bytes"), str), "원 stdout의 직렬화가 다르다")
        raw = base64.b64decode(row["bytes"], validate=True)
        output_hash.update(raw); output_bytes += len(raw)
    require(output_hash.hexdigest().upper() == report["supervision"]["stdout_sha256"]
        and output_bytes == report["supervision"]["stdout_bytes"], "원 stdout의 전체 SHA·바이트가 다르다")
    return report


def admission(args, state, budget):
    if args.mode == "canary":
        require(not args.admission and not args.admission_sha256, "첫 카나리는 과거 영수증을 대체 참조하지 않는다")
        return dict(status="NEW_CP_CANARY_REQUIRED")
    if not args.admission or not args.admission_sha256:
        raise Hold("같은 새 CP의 닫힌 카나리·비용 원형이 아직 없다")
    value = read_ref(dict(path=args.admission, sha256=args.admission_sha256), budget)
    require(value.get("schema") == ADMISSION and value.get("source_sha256") == state["source_identity"]["sha256"]
        and value.get("profile_sha256") == state["profile_sha256"], "총괄의 현재 평가 입장 명세가 다르다")
    closed_canary = read_closed(value["canary"], state, "canary", budget)
    result = dict(canary_report_sha256=value["canary"]["sha256"], actual_canary_parent_exit=0)
    if args.mode == "full":
        cost = read_closed(value["cost"], state, "cost", budget)
        timing = cost["worker"]["task_evaluation_seconds"]
        scale = sum(official.TASK_COUNTS[name] * seconds / 32 for name, seconds in timing.items())
        overhead = max(0., value["cost"]["actual_parent_wall_sec"] - sum(timing.values()))
        forecast = 1.5 * (scale + overhead) + 60
        if forecast > 7200 or forecast > budget.remaining() - budget.reserve:
            raise Hold("실제 비용의 전량 예측이 정리 예약을 남긴 현재 전체 창에 들어가지 않는다")
        result.update(cost_report_sha256=value["cost"]["sha256"], work_forecast_seconds=forecast,
            forecast_factor=1.5, measured_parent_overhead_seconds=overhead, cleanup_reserve_seconds=budget.reserve)
    return result


def execute_worker(args, state, budget, admitted):
    for key, value in official.OFFLINE.items():
        os.environ[key] = value
    assets.configure_hf_cache()
    from scripts.p106b_official_tasks import load_tasks
    tasks, specs, framework = load_tasks()
    require(specs == state["task_specs"] and set(tasks) == set(official.TASK_COUNTS), "실제 공식 과제 원형이 다르다")
    from lm_eval.evaluator import simple_evaluate
    from lm_eval.tasks import TaskManager
    manager = TaskManager()
    import torch
    from torch.nn.attention import sdpa_kernel, SDPBackend
    torch.set_num_threads(4); torch.manual_seed(1337)
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    child = dict(schema=SCHEMA, mode=args.mode, arm=state["profile"]["arm"], synthetic=False,
        source_sha256=state["source_identity"]["sha256"], profile_sha256=state["profile_sha256"],
        training_report_sha256=state["train_spec"]["sha256"], checkpoint_sha256=state["train"]["checkpoint_sha256"],
        framework_commit=assets.COMMIT, data_manifest_sha256=assets.MANIFEST_SHA,
        framework_revision_source="PINNED_ARCHIVE_AND_IMPORT_PROVENANCE; RESULT_GIT_HASH_IS_NOT_A_HARNESS_REVISION",
        policy=policy(), contract=CONTRACT, optimizer_updates=0, checkpoint_writes=0, models_loaded=1,
        actual_counts={}, quality_claim=False, admission=admitted, contamination="GLOBAL_PRETRAINING_NOT_AUDITED",
        sample_manifests={}, independent_audits={}, official_results={}, task_evaluation_seconds={})
    writer = ShardWriter(args.output, "token_lengths", limit=19_999_999) if args.mode != "canary" else None
    lm, primary = None, None
    try:
        budget.check("실제 CP 로딩 전")
        with sdpa_kernel(SDPBackend.MATH), torch.no_grad():
            with strict_runtime(state, budget) as (runtime, proof):
                adapter_error = None
                try:
                    lm = adapter.create_adapter(runtime, runtime_root=Path(sysconfig.get_paths()["purelib"]), batch_size=8)
                    child["model_proof"] = proof
                    child["canary"] = canary(lm, torch)
                    child["model_preparation_seconds"] = time.monotonic() - budget.started
                    if args.mode != "canary":
                        counts = official.expected_counts(args.mode)
                        with official.length_observer(lm, writer) as observed:
                            for spec in specs:
                                name, task = spec["task"], tasks[spec["task"]]
                                budget.check("공식 과제 실행 전")
                                tick = time.monotonic()
                                result = simple_evaluate(model=lm, tasks=[task], num_fewshot=0, task_manager=manager,
                                    batch_size=8, device="cuda", use_cache=None, cache_requests=False,
                                    limit=32 if args.mode == "cost" else None, bootstrap_iters=100000, log_samples=True,
                                    apply_chat_template=False, fewshot_as_multiturn=False, random_seed=1337,
                                    numpy_random_seed=1337, torch_random_seed=1337, fewshot_random_seed=1337)
                                torch.cuda.synchronize()
                                child["task_evaluation_seconds"][name] = time.monotonic() - tick
                                require(set(result["samples"]) == {name}, "공식 실제 과제집합이 다르다")
                                rows = result.pop("samples")[name]
                                audit = official.audit_samples(task, rows, counts[name])
                                raw = ShardWriter(args.output, name + "_samples", limit=19_999_999)
                                row_error = None
                                try:
                                    for row in rows:
                                        doc = task.eval_docs[row["doc_id"]]
                                        info = dict(task=name, choices=task.doc_to_choice(doc),
                                            gold=task.doc_to_text(doc) if task.multiple_input else task.doc_to_target(doc),
                                            doc_sha256=sha(official.plain(row["doc"])), data_sha256=spec["data_sha256"],
                                            official_yaml_sha256=spec["official_yaml_sha256"], dataset_revision=spec["dataset_revision"])
                                        raw.append(dict(official.plain(row), native_format_recount=official.plain(info)))
                                    child["sample_manifests"][name] = raw.close(lineage=dict(schema=SCHEMA,
                                        checkpoint_sha256=child["checkpoint_sha256"], task=name, mode=args.mode))
                                except BaseException as error:
                                    row_error = error
                                    raise
                                finally:
                                    training.close_preserving(row_error, [("공식 raw 부분 shard 닫기", raw._finish)])
                                child["independent_audits"][name] = audit_payload(audit)
                                child["official_results"][name] = official.plain(result)
                                child["actual_counts"][name] = counts[name]
                                budget.check("공식 과제 저장 후")
                        child["token_lengths_summary"] = observed
                        child["lengths_manifest"] = writer.close(lineage=dict(schema=SCHEMA, mode=args.mode,
                            checkpoint_sha256=child["checkpoint_sha256"]))
                        child["framework_provenance"], child["task_specs"] = framework, specs
                except BaseException as error:
                    adapter_error = error
                    raise
                finally:
                    if lm is not None:
                        training.close_preserving(adapter_error, [("공식 adapter 해제", lm.close)])
                        lm = None
        child["status"] = {"canary": "CANARY_COMPLETE", "cost": "LIMITED_COST_DIAGNOSTIC",
            "full": "OFFICIAL_CORE6_FULL_COMPLETE"}[args.mode]
        child["scope"] = "TECHNICAL_ONLY" if args.mode != "full" else "OFFICIAL_CORE6_FIXED_ENGLISH_TASKS"
        child["whole_worker_seconds"] = time.monotonic() - budget.started
        validate_worker(child, state, args.mode, args.output, budget)
        immutable(state, budget)
        return child
    except BaseException as error:
        primary = error
        raise
    finally:
        if writer is not None:
            training.close_preserving(primary, [("길이 부분 shard 닫기", writer._finish)])


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--mode", choices=MODES, default="canary")
    value.add_argument("--profile"); value.add_argument("--profile-sha256")
    value.add_argument("--source-sha256")
    value.add_argument("--admission"); value.add_argument("--admission-sha256")
    value.add_argument("--output"); value.add_argument("--max-wall-sec", type=int, default=600)
    value.add_argument("--deadline", default=END.isoformat())
    value.add_argument("--parent-started", type=float, help=argparse.SUPPRESS)
    value.add_argument("--work-end", type=float, help=argparse.SUPPRESS)
    group = value.add_mutually_exclusive_group(required=True)
    group.add_argument("--source-only", action="store_true")
    group.add_argument("--check-only", action="store_true")
    group.add_argument("--execute", action="store_true")
    group.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    return value


def audit_payload(value):
    """정수 label key를 JSON 표현으로 고정하며 수치와 검산 조건은 유지한다."""
    return json.loads(canonical(value), object_pairs_hook=adapter._unique_object)


def worker_python():
    """가상환경의 논리 실행 경로를 유지하고 실제 바이너리 검산은 감독에 맡긴다."""
    executable = sys.executable
    require(isinstance(executable, str) and os.path.isabs(executable)
        and Path(executable).is_file() and os.access(executable, os.X_OK),
        "worker Python의 유효한 기존 절대 실행 경로가 필요하다")
    return executable


def main(argv=None):
    args = parser().parse_args(argv)
    output, owned = None, False
    try:
        if args.source_only:
            print(json.dumps(dict(schema=SCHEMA, status="SOURCE_ONLY", source_identity=source_identity(),
                model_loaded=False, gpu_calls=0, files_written=0), ensure_ascii=False), flush=True)
            return 0
        if not args.profile or not args.profile_sha256 or not args.source_sha256:
            raise Hold("새 총괄 profile·source pin·완주 CP가 아직 준비되지 않았다")
        require(240 <= args.max_wall_sec <= (7200 if args.mode == "full" else 600), "각 모드의 전체 시간 상한이 다르다")
        deadline = datetime.fromisoformat(args.deadline.replace("Z", "+00:00"))
        require(deadline.tzinfo is not None and deadline <= END, "현재 권한은26일17시 이내다")
        start = args.parent_started if args.worker else STARTED
        budget = supervisor.Budget(args.max_wall_sec, deadline.timestamp(), started=start, reserve=120)
        if args.worker:
            require(type(args.work_end) is float and math.isfinite(args.work_end) and args.work_end < budget.end,
                "부모 종결 예약을 제외한 실제 worker 마감이 필요하다")
            budget.end = min(budget.end, args.work_end); budget.reserve = 0
        with supervisor.total_budget(budget), supervisor.termination_guard():
            state = metadata(args, budget)
            if not args.worker:
                budget.reserve = state["profile"]["cleanup_reserve_sec"]
            require(budget.remaining() > budget.reserve, "명시한 종결 예약을 확보하지 못했다")
            admitted = admission(args, state, budget)
            if args.check_only:
                result = dict(schema=SCHEMA, status="CPU_METADATA_ONLY", returncode=0, source_sha256=state["source_identity"]["sha256"],
                    checkpoint_sha256=state["train"]["checkpoint_sha256"], model_loaded=False, gpu_calls=0, files_written=0,
                    numerical_canary="NOT_RUN", full="NOT_RUN", admission=admitted)
                code = 0
            else:
                require(args.output and re.fullmatch(PREFIX + "[A-Za-z0-9_]+", Path(args.output).name)
                    and Path(args.output).parts[:2] == ("test_result", "evidence") and len(Path(args.output).parts) == 3,
                    "평가의 새 전용 이름공간이 필요하다")
                output = safe(args.output); args.output = output
                if args.worker:
                    invocation = supervisor.read_json(output / "invocation.json")
                    require(os.getppid() == invocation["parent_pid"]
                        and supervisor.proc.proc_stat(os.getppid())["starttime"] == invocation["parent_starttime"]
                        and invocation["source_sha256"] == state["source_identity"]["sha256"]
                        and invocation["profile_sha256"] == state["profile_sha256"] and invocation["mode"] == args.mode
                        and invocation["work_end"] == args.work_end
                        and re.fullmatch("[0-9a-f]{64}", os.environ.get(training.OWNER, "")), "직접 소유 worker의 부모 신원이 다르다")
                    owned = True
                    child = execute_worker(args, state, budget, admitted)
                    supervisor.write_once(output / "worker.json", child, budget)
                    code = 0
                else:
                    require(not output.exists(), "기존 완결·부분 증거를 보존한다")
                    output.mkdir(); owned = True
                    supervisor.write_once(output / "source.json", state["source_identity"], budget)
                    owner = supervisor.proc.proc_stat(os.getpid())
                    work_end = budget.end - budget.reserve
                    supervisor.write_once(output / "invocation.json", dict(parent_pid=os.getpid(), parent_starttime=owner["starttime"],
                        source_sha256=state["source_identity"]["sha256"], profile_sha256=state["profile_sha256"], mode=args.mode,
                        work_end=work_end), budget)
                    command = [worker_python(), "-I", "-B", "-X", "utf8", str(Path(__file__).resolve())]
                    command += [item for item in (sys.argv[1:] if argv is None else argv) if item != "--execute"]
                    command += ["--worker", "--parent-started", str(budget.started), "--work-end", str(work_end)]
                    observed = training.supervise(command, output, budget)
                    code = 0 if training.supervision_ok(observed) else 9
                    child, child_sha = None, None
                    try:
                        if (output / "worker.json").is_file():
                            child_sha = digest(output / "worker.json", budget)
                            child = read_ref(dict(path=str((output / "worker.json").relative_to(ROOT)), sha256=child_sha), budget)
                        require(code != 0 or child is not None, "실제 자식 완결 원형이 없다")
                        if code == 0:
                            validate_worker(child, state, args.mode, output, budget)
                        immutable(state, budget)
                    except BaseException as error:
                        code = 9
                        observed.setdefault("post_errors", []).append(supervisor.error_record(error, "평가 부모 종결 재검산"))
                    report = dict(schema=SCHEMA, mode=args.mode, arm=state["profile"]["arm"], returncode=code,
                        source_sha256=state["source_identity"]["sha256"], profile_sha256=state["profile_sha256"],
                        supervision=observed, worker=child, worker_sha256=child_sha,
                        whole_parent_seconds=time.monotonic() - budget.started, authority_end=END.isoformat(),
                        effective_deadline=deadline.isoformat(), cleanup_reserve_sec=budget.reserve,
                        external_os_timeout_required=True, actual_supervisor_exit="ROOT_MUST_COLLECT")
                    supervisor.write_once(output / "report.json", report, budget)
                    supervisor.append_terminal(output, dict(event="OBSERVATION", returncode=code))
                result = dict(schema=SCHEMA, returncode=code, mode=args.mode, arm=state["profile"]["arm"])
            budget.check("최종 작은 출력 전")
            print(json.dumps(result, ensure_ascii=False), flush=True)
            budget.check("최종 작은 출력 뒤")
        budget.check("타이머와 신호 복구 뒤")
        return code
    except BaseException as error:
        if owned and output is not None and output.is_dir():
            try:
                supervisor.append_terminal(output, dict(event="TERMINAL_VETO", returncode=9,
                    error=supervisor.error_record(error, "평가 전체 종결", os.environ.get(training.OWNER, ""))))
            except BaseException:
                pass
        code = 8 if isinstance(error, Hold) and not owned else 9
        record = supervisor.error_record(error, "평가 전체 종결", os.environ.get(training.OWNER, ""))
        try:
            print(json.dumps(dict(schema=SCHEMA, returncode=code, error_type=type(error).__name__, error=record), ensure_ascii=False), flush=True)
        except BaseException as post_error:
            if owned and output is not None and output.is_dir():
                try:
                    supervisor.append_terminal(output, dict(event="TERMINAL_VETO", returncode=9,
                        error=supervisor.error_record(post_error, "오류 출력 뒤 종결")))
                except BaseException:
                    pass
            code = 9
        return code


if __name__ == "__main__":
    raise SystemExit(main())
