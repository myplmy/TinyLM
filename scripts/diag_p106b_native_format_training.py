#!/usr/bin/env python3
"""원형/형식 native 전체 학습의 별도 CPU 준비·총괄 실행 진단.

원문 Muon·형식 Muon·형식 TinyLM-adapted NorMuon의 명시 profile을 지원한다.
기존 runtime·NS·CE·schedule을 사용하며 기본 trainer와 전역은 바꾸지 않는다.
cost8은 기술 관측이다. 전체2289 후의 native32도 공식 벤치나 full VAL가 아니다.
CP는 큰 로컬 파일 예외이고 JSON·updates·stdout shard는 각각20MB 미만이다.
"""
from __future__ import annotations
import time
STARTED = time.monotonic()
import argparse
import base64
from collections import Counter
import ctypes
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import secrets
import signal
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import p106b_native_format_pair as pair
from scripts import diag_p106b_native_weight_route as native
from scripts import diag_p106b_supported_supervisor as supervisor
from scripts import codex_smoke as smoke
from scripts.p106b_shards import ShardWriter, verify

SCHEMA = "P106B_NATIVE_FORMAT_TRAINING_V1"
PROFILE = "P106B_NATIVE_FORMAT_TRAINING_PROFILE_V1"
PREFIX = "p106b_native_format_training_v1_20261026_"
OWNER = "TINYLM_NATIVE_FORMAT_TRAIN_OWNER"
TRAIN_END = datetime(2026, 10, 26, 7, tzinfo=timezone.utc)
END = datetime(2026, 10, 26, 8, tzinfo=timezone.utc)
CORE = "028C46B232D6D4C5205CAF15A7C259E3B1687347FC4838D00B3F3CB938C0D1C5"
UPDATES, TARGETS, TOTAL = 2289, 131072, 300023808
RECIPE = dict(layers=14, dim=768, vocab=32768, seq=1024, seed=1337, micro=8, accum=16,
    updates=UPDATES, total_targets=TOTAL, checkpoint=True, amp="bf16", compile="default",
    tf32=False, objective="NTP_ONLY", adam_peak_lr=.001, matrix_peak_lr=.004,
    warmup=100, schedule="wsd", decay_frac=.2, quant_anneal="linear", quant_end=.8,
    quantization_scope="TLINEAR_WEIGHTS_ONLY", scratch_core_sha256=CORE)
CODE = tuple(sorted(set((*native.CODE, *pair.CODE,
    "scripts/diag_p106b_native_format_training.py", "scripts/test_p106b_native_format_training.py",
    "tinylm/train/normuon.py", "scripts/codex_smoke.py", "scripts/smoke_module.py",
    "scripts/smoke_execution_contract.py", "scripts/diag_p106b_supported_supervisor.py",
    "scripts/p106b_native_iq2_worker_window.py", "scripts/diag_p106_vram_sample.py",
    "scripts/diag_p106_full_coload_accum.py"))))


class Hold(FileNotFoundError):
    """원형 캐시·F4·paired cost 입장이 없는 실행 보류."""


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest().upper()


def path(name):
    return pair.safe(name, ROOT)


def read(name, wanted=None):
    target = path(name)
    if not target.is_file():
        raise Hold("정확한 선결 파일이 없다: " + str(name))
    actual = pair.file_sha(target)
    require(wanted is None or actual == wanted.upper(), "선결 SHA가 다르다: " + str(name))
    value = pair.read_json(target)
    require(pair.file_sha(target) == actual, "작은 명세를 읽는 중 SHA가 달라졌다")
    return value, actual


def source_identity():
    files = {name: pair.file_sha(path(name)) for name in CODE}
    return dict(sha256=sha(files), files=files)


def metadata(args):
    profile, profile_sha = read(args.profile, args.profile_sha256)
    if args.mode == "train" and resource.getrlimit(resource.RLIMIT_FSIZE)[0] != resource.RLIM_INFINITY:
        raise Hold("큰 CP를 허용하는 부모의 FSIZE 무제한 환경이 필요하다")
    require(profile.get("schema") == PROFILE and profile.get("recipe") == RECIPE,
            "정확한 전체 native recipe가 필요하다")
    arms = profile.get("arms", [])
    require(len(arms) in (2, 3) and len({a["id"] for a in arms}) == len(arms)
            and all(re.fullmatch("[A-Za-z0-9_]+", a["id"]) for a in arms), "명시한 두 필수 팔과 선택 팔만 허용한다")
    pairs = [(a["corpus"],a["optimizer"]) for a in arms]
    required = {pair for pair,a in zip(pairs,arms) if a["required"] is True}
    require(all(type(a["required"]) is bool for a in arms) and len(set(pairs)) == len(pairs)
            and set(pairs).issubset({("original","muon"),("format","muon"),("format","normuon")})
            and required in ({("original","muon"),("format","muon")},
                             {("format","muon"),("format","normuon")}),
            "명시한 원형 세 팔 중 총괄이 선택한 필수 두 팔이 필요하다")
    if any(a["optimizer"] == "normuon" for a in arms):
        require(profile.get("normuon") == dict(beta2=.95, eps=1e-10, implementation="TINYLM_ADAPTED_POST_NS_ROW_EMA"),
                "선택 NorMuon의 명시한 행별 EMA 계약이 필요하다")
    require(profile.get("train_deadline") == TRAIN_END.isoformat()
            and profile.get("final_deadline") == END.isoformat()
            and type(profile.get("cleanup_reserve_sec")) is int and profile["cleanup_reserve_sec"] >= 120
            and profile.get("evaluation_reserve_sec", 0) >= 3600
            and profile.get("minimum_pair_training_sec", 0) >= 15000
            and type(profile.get("entry_free_mib")) is int and profile["entry_free_mib"] > 0,
            "16시 학습 마감·17시 전체 마감과 명시 예약·입장 예산이 필요하다")
    require(profile.get("validation") == {"path": str(native.VAL.relative_to(ROOT)), "sha256": native.VAL_SHA},
            "같은 고정 native32 VAL만 허용한다")
    require(profile.get("geometry_parent") == dict(path=str(native.PARENT.relative_to(ROOT)),
            sha256=native.PARENT_SHA, use="CONFIG_AND_TOKEN_METADATA_ONLY"),
            "학습 가중치를 복사하지 않는 정확한 부모 형상·토큰 계보가 필요하다")
    if not path(profile["geometry_parent"]["path"]).is_file():
        raise Hold("원 helper가 형상과 토큰 계보를 검산할 부모 파일이 없다")
    identity = source_identity()
    f4, f4_sha = read(args.f4, args.f4_sha256)
    require(f4.get("schema") == "P106B_NATIVE_FORMAT_F4_V1" and f4.get("root_approved") is True
            and f4.get("source_sha256") == identity["sha256"] and f4.get("profile_sha256") == profile_sha
            and args.mode in f4.get("allowed_modes", []), "현재 source와 profile의 총괄 F4가 필요하다")
    complete, complete_sha = read(profile["pair_complete"]["path"], profile["pair_complete"]["sha256"])
    policy, policy_sha = read(profile["pair_policy"]["path"], profile["pair_policy"]["sha256"])
    cache = path(profile["pair_complete"]["path"]).parent
    require(not (cache / "failed.json").exists() and complete.get("schema") == pair.SCHEMA
            and complete.get("synthetic") is False
            and complete.get("training_admission") == "CPU_CACHE_PREPARED_NOT_TRAIN_OR_QUALITY_PASS"
            and policy.get("schema") == pair.POLICY and policy.get("approved_train_reuse") is True
            and policy.get("scope") == "TRAIN_FORMAT_COMPARISON_ONLY"
            and policy.get("full_semantic_review") is False
            and policy.get("review_queue_policy") == "PRESERVE_NOT_AUTOMATIC_HOLD"
            and policy.get("reserved_action") == "EXCLUDE_BOTH"
            and complete.get("policy_sha256") == policy_sha and policy.get("minimum_ids_per_arm") == pair.MIN_IDS
            and complete.get("source_identity", {}).get("sha256") == pair.source_identity()["sha256"]
            and profile.get("tokenizer") == policy.get("tokenizer")
            and profile.get("tokenizer", {}).get("sha256") == native.TOKENIZER_SHA
            and policy.get("validation") == profile["validation"], "원형 pair 캐시와 policy·토큰 계보가 필요하다")
    require(complete["ledger"]["lineage"] == dict(source_sha256=pair.SOURCE_SHA,
            policy_sha256=policy_sha, source_code_sha256=pair.source_identity()["sha256"],
            same_roster_and_order=True) and complete.get("unit") == "EOS_CACHE_SEGMENTS_NOT_ORIGINAL_URL_DOCUMENTS",
            "같은 EOS roster와 HOLD·VAL 공통 제외의 원형 ledger 계보가 필요하다")
    holds,_ = read(policy["holds"]["path"],policy["holds"]["sha256"])
    require(holds.get("schema") == "P106B_NATIVE_FORMAT_HOLDS_V1"
            and holds.get("source_sha256") == pair.SOURCE_SHA, "같은 원형의 HOLD 명세가 필요하다")
    pair.Holds(holds,pair.SOURCE_SHA)
    require(set(complete["holds"]) == {row["id"] for row in holds["holds"]}
            and all(type(v) is int and v > 0 for v in complete["holds"].values()), "미해결 HOLD를 허용하지 않는다")
    if any(not (cache/(arm+".bin")).is_file() for arm in ("original","format")):
        raise Hold("양팔의 완결된 실제 token bin이 없다")
    require(complete["output_readback"]["kept_documents"] == complete["kept_documents"]
            and all(type(complete["arms"][a]["tokens"]) is int
                    and complete["arms"][a]["tokens"] >= pair.MIN_IDS
                    and (cache / (a+".bin")).stat().st_size == complete["arms"][a]["tokens"]*2
                    and complete["output_readback"]["tokens"][a] == complete["arms"][a]["tokens"]
                    for a in ("original", "format")), "같은 roster의 두 실제 풀과 엄격한 두 배 크기가 필요하다")
    for ref in (profile["tokenizer"], profile["validation"]):
        if not path(ref["path"]).is_file():
            raise Hold("명시한 tokenizer 또는 VAL 원형이 없다")
    if profile.get("generation") is not None:
        require(profile["generation"].get("max_new") == 64
                and profile["generation"].get("sampler") == "ORIGINAL_EMIT64",
                "완주 뒤 선택 생성은 원 greedy64 helper만 쓴다")
        read(profile["generation"]["cases"]["path"], profile["generation"]["cases"]["sha256"])
    return dict(profile=profile, profile_sha256=profile_sha, f4_sha256=f4_sha,
                source_identity=identity, complete=complete, complete_sha256=complete_sha,
                policy=policy, policy_sha256=policy_sha, cache=str(cache.relative_to(ROOT)))


def arm_for(state, name):
    choices = [item for item in state["profile"]["arms"] if item["id"] == name]
    require(len(choices) == 1, "등록된 정확한 팔이 필요하다")
    return choices[0]


def full_cache(state, budget):
    budget.check("양팔 실제 캐시 검산 전")
    pair.verify_outputs(path(state["cache"]), state["complete"], budget)
    for item in (state["profile"]["tokenizer"], state["profile"]["validation"]):
        require(pair.file_sha(path(item["path"])) == item["sha256"], "실제 tokenizer 또는 VAL SHA가 다르다")
    budget.check("양팔 실제 캐시 검산 후")


def immutable_metadata(args, state, budget):
    budget.check("명세 불변 재검산 전")
    for name, wanted in ((args.profile,state["profile_sha256"]), (args.f4,state["f4_sha256"]),
            (state["profile"]["pair_complete"]["path"],state["complete_sha256"]),
            (state["profile"]["pair_policy"]["path"],state["policy_sha256"])):
        require(pair.file_sha(path(name)) == wanted, "실행 중 원형 명세가 달라졌다")
    require(source_identity() == state["source_identity"], "실행 중 source identity가 달라졌다")
    budget.check("명세 불변 재검산 후")


def optimizer_pair(model, arm, profile, *, make=None, constructor=None):
    make = native.make_optimizers if make is None else make
    optimizers, receipt = make(model, "native")
    adam, muon = optimizers
    require(not adam.state and not muon.state, "fresh optimizer 상태가 필요하다")
    if arm["optimizer"] == "muon":
        return optimizers, receipt, dict(kind="ORIGINAL_MUON")
    if constructor is None:
        from tinylm.train.normuon import NorMuon
        constructor = NorMuon
    require(getattr(muon, "scale_mode", None) == "rms", "원 RMS4 Muon group이 필요하다")
    original = [dict(g, params=list(g["params"])) for g in muon.param_groups]
    keys = ("lr", "momentum", "nesterov", "ns_steps", "weight_decay", "scale_mode")
    options = {key: muon.defaults[key] for key in keys}
    require(options["scale_mode"] == "rms" and all(g["weight_decay"] == 0 for g in original),
            "원 형상 스케일과 matrix WD0이 필요하다")
    spec = profile["normuon"]
    adapted = constructor([dict(g, params=list(g["params"])) for g in original],
                          **options, beta2=spec["beta2"], eps=spec["eps"])
    require(not adapted.state and getattr(adapted, "scale_mode", None) == "rms"
            and len(adapted.param_groups) == len(original), "fresh NorMuon 상태와 group 수가 다르다")
    for old, new in zip(original, adapted.param_groups):
        require([id(p) for p in old["params"]] == [id(p) for p in new["params"]]
                and all(new[k] == value for k, value in old.items() if k != "params")
                and set(new) - set(old) == {"beta2", "eps"}, "행별 EMA 외 원 Muon group이 바뀌었다")
    current = native.optimizer_receipt(model, (adam, adapted)) if constructor.__module__ == "tinylm.train.normuon" else [
        dict(row, optimizer="NorMuon" if row["optimizer"] != "AdamW" else "AdamW") for row in receipt]
    current = [dict(row, runtime_lr=old["runtime_lr"], runtime_weight_decay=old["runtime_weight_decay"],
                    lr_multiplier=old["lr_multiplier"]) for row, old in zip(current, receipt)]
    native.validate_optimizer_groups(current, "native")
    return (adam, adapted), current, dict(kind="TINYLM_ADAPTED_NORMUON",
        beta2=spec["beta2"], eps=spec["eps"], adam_unchanged=True, original_groups_preserved=True,
        none_gradient_policy="FROZEN_OPTIMIZER_SKIP", gradient_input_mutation=False)


def update_loop(adapter, offsets, writer, budget, *, cost):
    count = 8 if cost else UPDATES
    totals, times = Counter(), []
    for step in range(count):
        budget.check("전체 update 전")
        if not cost and time.time() >= TRAIN_END.timestamp():
            raise TimeoutError("16시 이후에는 본학습 update를 시작하지 않는다")
        adapter.route.assert_active()
        tick = time.perf_counter()
        policy = native.schedule(step, updates=UPDATES)
        adapter.begin(policy)
        chosen = [int(v) for v in offsets[step*128:(step+1)*128]]
        require(len(chosen) == 128, "실제 update의 crop128개가 필요하다")
        numerator = observed = used = 0
        for start in range(0, 128, 8):
            budget.check("물리 micro 전")
            if not cost and time.time() >= TRAIN_END.timestamp():
                raise TimeoutError("16시 이후에는 본학습 micro를 시작하지 않는다")
            value, targets, inputs = adapter.backward(chosen[start:start+8], TARGETS)
            numerator += value; observed += targets; used += inputs
        require(observed == TARGETS and used == TARGETS and math.isfinite(numerator),
                "전체131072 target/input과 유한한 numerator가 필요하다")
        gradient = adapter.finish()
        require(type(gradient) in (int, float) and math.isfinite(gradient) and gradient >= 0,
                "비유한 gradient는 정상 update가 아니다")
        seconds = time.perf_counter()-tick
        if not cost and time.time() >= TRAIN_END.timestamp():
            raise TimeoutError("본학습 update가16시 마감을 넘었다")
        require(math.isfinite(seconds) and seconds > 0, "양의 전체 update 시간이 필요하다")
        event = dict(update=step+1, targets=observed, x_tokens=used, ce=numerator/observed,
            offsets=chosen, offsets_sha256=sha(chosen), schedule=policy,
            actual_lrs=adapter.lrs(), gradient_norm=gradient, clipped=gradient > 1.,
            step_seconds=seconds, synthetic=adapter.synthetic)
        writer.append(event)
        times.append(seconds); totals.update(targets=observed, x_tokens=used)
        if cost or (step+1) % 100 == 0 or step+1 == count:
            print("[NATIVE_FORMAT_UPDATE] "+json.dumps({k:v for k,v in event.items() if k!="offsets"}), flush=True)
    require(totals["targets"] == count*TARGETS, "전체 예정 target을 완주하지 않았다")
    return dict(updates=count, totals=dict(totals), step_seconds=times, synthetic=adapter.synthetic)


class NativeAdapter:
    synthetic = False
    def __init__(self, torch, model, forward, tokens, optimizers, route):
        self.torch, self.model, self.forward = torch, model, forward
        self.tokens, self.optimizers, self.route = tokens, optimizers, route
        self.bases = [[g["lr"] for g in opt.param_groups] for opt in optimizers]

    def begin(self, policy):
        for optimizer, rates in zip(self.optimizers, self.bases):
            optimizer.zero_grad(set_to_none=True)
            for group, base in zip(optimizer.param_groups, rates):
                group["lr"] = base*policy["lr_factor"]
        self.model.set_anneal(policy["anneal"])

    def backward(self, chosen, denominator):
        return native.backward_micro(self.model, self.forward, native.native_records(self.tokens, chosen),
                                     denominator, self.torch)

    def finish(self):
        grad = self.torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.)
        require(bool(self.torch.isfinite(grad)), "비유한 gradient여서 optimizer를 실행하지 않는다")
        for optimizer in self.optimizers:
            optimizer.step()
        self.torch.cuda.synchronize()
        return float(grad)

    def lrs(self):
        return [[float(g["lr"]) for g in opt.param_groups] for opt in self.optimizers]


class MemorySamples:
    """동기 조회를 별도 thread에서 수행한다. 누락을 보간하지 않는다."""
    def __init__(self):
        self.stop = threading.Event()
        self.samples, self.errors = [], []
        self.thread = None
    def __enter__(self):
        from scripts.diag_p106_vram_sample import read_memory
        def sample():
            while not self.stop.is_set():
                began = time.monotonic()
                try:
                    used, free = read_memory()
                    require(type(used) is int and type(free) is int and min(used, free) >= 0, "계측 수치가 유효하지 않다")
                    self.samples.append(dict(monotonic=time.monotonic(), query_sec=time.monotonic()-began,
                                             global_used_mib=used, free_mib=free))
                except BaseException as error:
                    self.errors.append(dict(monotonic=time.monotonic(), error_type=type(error).__name__))
                self.stop.wait(2.)
        self.thread = threading.Thread(target=sample, daemon=True)
        self.thread.start()
        return self
    def __exit__(self, kind, primary, traceback):
        self.stop.set()
        self.thread.join(timeout=7)
        if self.thread.is_alive():
            error = OSError("계측 thread의 실제 종료를 확인하지 못했다")
            if primary is None:
                raise error
            primary.supported_cleanup_errors = [*getattr(primary,"supported_cleanup_errors",[]),
                supervisor.error_record(error,"계측 thread 종료")]
    def summary(self):
        require(self.samples, "실제 GPU 메모리 표본이 없다")
        gaps = [b["monotonic"]-a["monotonic"] for a,b in zip(self.samples,self.samples[1:])]
        return dict(samples=len(self.samples), missing_queries=len(self.errors), errors=self.errors,
                    raw_samples=self.samples, observed_interval_max_sec=max(gaps) if gaps else None,
                    sampled_global_peak_mib=max(row["global_used_mib"] for row in self.samples),
                    sampled_min_free_mib=min(row["free_mib"] for row in self.samples),
                    continuous_peak_verified=False, model_size_or_packed_bytes="NOT_INFERRED")


def finite_number(value, *, positive=False):
    return type(value) in (int,float) and math.isfinite(value) and (value > 0 if positive else value >= 0)


def forecasts(cost, parent_seconds):
    require(cost.get("status") == "COST8_COMPLETE" and cost.get("updates") == 8
            and cost.get("synthetic") is False and cost.get("checkpoint") is None
            and cost.get("native32") is None, "실제 cost8 기술 영수증이 필요하다")
    times = cost["step_seconds"]
    require(len(times) == 8 and all(type(t) in (int,float) and math.isfinite(t) and t > 0 for t in times),
            "cold1와 warm7의 실제 시간이 필요하다")
    preparation = cost["pre_training_seconds"]
    require(all(finite_number(v,positive=True) for v in
            (preparation,parent_seconds,cost["whole_worker_seconds"],cost["late"]["seconds"],cost["cache_audit"]["seconds"]))
            and parent_seconds >= cost["whole_worker_seconds"] >= preparation+sum(times),
            "모델 준비·첫 컴파일·후행 검산을 포함한 실제 전체 시간이 필요하다")
    require(cost["late"].get("optimizer_updates") == 0 and cost["late"].get("micro_batches") == 1
            and cost["late"].get("targets") == 8192 and cost["late"].get("finite") is True
            and cost["late"].get("core_before") == cost["late"].get("core_after"),
            "원 late micro의 무갱신·유한성·가중치 불변 영수증이 필요하다")
    steady = max(max(times[1:]),16*cost["late"]["seconds"])
    post = parent_seconds-preparation-sum(times)
    return preparation+times[0]+steady*(UPDATES-1)*1.35+post


def rows(directory, manifest):
    verify(directory,manifest)
    for spec in manifest["shards"]:
        with (directory/spec["path"]).open(encoding="utf-8") as stream:
            for line in stream:
                value = json.loads(line); canonical(value)
                yield value


def validate_worker(child, state, name, mode, directory):
    arm = arm_for(state,name)
    count = 8 if mode == "cost" else UPDATES
    require(child.get("schema") == SCHEMA and child.get("mode") == mode
            and child.get("arm") == name and child.get("corpus") == arm["corpus"]
            and child.get("optimizer") == arm["optimizer"] and child.get("synthetic") is False
            and child.get("source_sha256") == state["source_identity"]["sha256"]
            and child.get("profile_sha256") == state["profile_sha256"]
            and child.get("pair_complete_sha256") == state["complete_sha256"]
            and child.get("scratch_core_sha256") == CORE and child.get("original_weights_copied") is False
            and child.get("updates") == count
            and child.get("totals") == dict(targets=count*TARGETS,x_tokens=count*TARGETS),
            "정확한 팔·초기화·전체 update·target 종결이 필요하다")
    groups = child["actual_optimizer_groups"]
    native.validate_optimizer_groups(groups,"native")
    require({g["optimizer"] for g in groups} == {"AdamW","Muon" if arm["optimizer"] == "muon" else "NorMuon"},
            "선택한 원형 optimizer 쌍이 다르다")
    proof = child["offsets"]
    pool = state["complete"]["arms"][arm["corpus"]]["tokens"]
    require(proof["pool_tokens"] == pool and proof["crops"] == UPDATES*128
            and proof["draw_tokens"] == TOTAL and proof["twice_draw"] == 2*TOTAL
            and proof["seed"] == 1337 and proof["window_tokens"] == 1025
            and re.fullmatch("[0-9A-F]{64}",proof["offsets_bytes_sha256"]), "전체 native sampler 계보가 다르다")
    count_read = 0
    for index,event in enumerate(rows(directory/"updates",child["event_manifest"])):
        require(index < count and event["update"] == index+1 and event["targets"] == TARGETS
                and event["x_tokens"] == TARGETS and event["synthetic"] is False
                and event["schedule"] == native.schedule(index,updates=UPDATES)
                and event["actual_lrs"] == native.actual_lrs(groups,event["schedule"]["lr_factor"])
                and finite_number(event["gradient_norm"]) and finite_number(event["ce"])
                and finite_number(event["step_seconds"],positive=True)
                and event["step_seconds"] == child["step_seconds"][index]
                and event["clipped"] == (event["gradient_norm"] > 1.)
                and len(event["offsets"]) == 128
                and all(type(v) is int and 0 <= v < pool-1024 for v in event["offsets"])
                and event["offsets_sha256"] == sha(event["offsets"]), "실제 update ledger의 수치·일정·offset이 다르다")
        count_read += 1
    require(count_read == count and len(child["step_seconds"]) == count, "실제 update ledger가 미완이다")
    cache = child["cache_audit"]
    require(cache.get("quality_forwards") == 0 and cache.get("optimizer_updates") == 0
            and cache.get("finite") is True and cache.get("core_before") == cache.get("core_after")
            and child["route"] == cache["route"] and child["route"]["mode"] == "ternary"
            and child["route"]["metadata"] == child["quantization_route"]
            and child["quantization_route"]["scope"] == "TLINEAR_WEIGHTS_ONLY"
            and child["route"]["tlinear_instances"] > 0
            and child["route"]["owned_tlinear_instances"] == child["route"]["refreshed_tlinear_instances"]
                == child["route"]["tlinear_instances"], "원 cache/route 검산의 전체 소유 증거가 필요하다")
    require(child["memory"]["samples"] > 0 and finite_number(child["memory"]["sampled_global_peak_mib"]),
            "실제 GPU 표본과 누락 명세가 필요하다")
    if mode == "cost":
        forecasts(child,child["whole_worker_seconds"])
    else:
        require(child.get("status") == "TRAIN2289_COMPLETE"
                and child.get("training_completed_epoch",math.inf) < TRAIN_END.timestamp(), "16시 이전 완주가 필요하다")
        native.validate_native32(child["native32"])
        checkpoint = path(child["checkpoint"])
        require(checkpoint.is_file() and pair.file_sha(checkpoint) == child["checkpoint_sha256"], "완료 CP의 실제 SHA가 다르다")
    return child


def read_closed(spec, state, name, mode):
    require(type(spec.get("actual_supervisor_exit")) is int and spec["actual_supervisor_exit"] == 0,
            "총괄이 회수한 실제 부모 종료0이 필요하다")
    report, _ = read(spec["path"],spec["sha256"])
    directory = path(spec["path"]).parent
    require(path(spec["path"]).name == "report.json" and report.get("schema") == SCHEMA
            and type(report.get("returncode")) is int and report["returncode"] == 0
            and report.get("mode") == mode and report.get("arm") == name
            and report.get("source_sha256") == state["source_identity"]["sha256"]
            and report.get("profile_sha256") == state["profile_sha256"]
            and report.get("f4_sha256") == state["f4_sha256"]
            and report.get("pair_complete_sha256") == state["complete_sha256"]
            and supervision_ok(report.get("supervision",{})), "실제 부모 종결과 소스 계보가 다르다")
    terminal = directory/"terminal.jsonl"
    require(terminal.is_file() and not terminal.is_symlink() and terminal.stat().st_size < 20_000_000
            and pair.file_sha(terminal) == spec["terminal_sha256"], "append-only 종결 SHA가 다르다")
    events = [json.loads(line) for line in terminal.read_text(encoding="utf-8").splitlines()]
    require(events == [dict(event="OBSERVATION",returncode=0)], "후행 종결 거부가 있거나 정상 종결 원장이 미완이다")
    child, digest = read(str((directory/"worker.json").relative_to(ROOT)),report["worker_sha256"])
    require(report["worker"] == child and digest == report["worker_sha256"], "자식 보고서의 실제 원형이 다르다")
    validate_worker(child,state,name,mode,directory)
    require(finite_number(spec.get("actual_parent_wall_sec"),positive=True)
            and spec["actual_parent_wall_sec"] >= report["whole_parent_seconds"],
            "총괄이 회수한 출력·정리·실제 종료까지의 전체 시간이 필요하다")
    return dict(report,root_actual_parent_wall_seconds=spec["actual_parent_wall_sec"])


def budget_admission(args, state):
    if not args.budget or not args.budget_sha256:
        raise Hold("본학습에는 총괄의 paired cost budget JSON이 필요하다")
    approval, digest = read(args.budget, args.budget_sha256)
    require(approval.get("schema") == "P106B_NATIVE_FORMAT_COST_ADMISSION_V1"
            and approval.get("root_approved") is True
            and approval.get("source_sha256") == state["source_identity"]["sha256"]
            and approval.get("profile_sha256") == state["profile_sha256"]
            and approval.get("f4_sha256") == state["f4_sha256"]
            and approval.get("pair_complete_sha256") == state["complete_sha256"],
            "같은 source/profile/F4/pair의 총괄 비용 입장이 필요하다")
    arms = approval.get("admitted_arms", [])
    required = [row["id"] for row in state["profile"]["arms"] if row["required"]]
    require(set(required).issubset(arms) and len(arms) == len(set(arms))
            and set(arms).issubset({row["id"] for row in state["profile"]["arms"]}), "필수 두 팔을 우선해야 한다")
    if args.arm not in arms:
        raise Hold("선택 팔은 현재 실제 시간 예산에 들어가지 않았다")
    costs, estimates, completed = {}, {}, []
    post_reserve = approval.get("unmeasured_post_training_reserve_sec_per_arm")
    require(finite_number(post_reserve,positive=True) and post_reserve >= 300,
            "각 팔의 미측정 native32·생성·큰 CP·정리에는 최소300초 별도 예약이 필요하다")
    for name in arms:
        spec = approval["cost_reports"][name]
        closed = read_closed(spec,state,name,"cost")
        cost = closed["worker"]
        require(cost["arm"] == name and cost["scratch_core_sha256"] == CORE
                and cost["corpus"] == arm_for(state,name)["corpus"]
                and cost["optimizer"] == arm_for(state,name)["optimizer"], "해당 팔의 비용 원형이 다르다")
        costs[name] = cost
        planned = approval.get("completed_train_reports",{}).get(name)
        if planned is not None:
            read_closed(planned,state,name,"train")
            completed.append(name); estimates[name] = 0.
        else:
            floor = forecasts(cost,closed["root_actual_parent_wall_seconds"])
            estimate = approval["conservative_seconds_by_arm"][name]
            require(finite_number(estimate,positive=True) and estimate >= floor+post_reserve,
                    "총괄의 보수 예측이 실제 cold/warm/late 전체 비용 하한보다 작다")
            estimates[name] = estimate
    same_format = [cost for cost in costs.values() if cost["corpus"] == "format"]
    if len(same_format) == 2:
        first,second=same_format
        def normalized(cost):
            receipt=[dict(group,optimizer="Muon" if group["optimizer"] == "NorMuon" else group["optimizer"])
                for group in cost["actual_optimizer_groups"]]
            contract=[[{key:value for key,value in group.items() if index == 0 or key not in ("beta2","eps")}
                for group in groups] for index,groups in enumerate(cost["optimizer_contract"])]
            return receipt,contract
        require(first["offsets"] == second["offsets"] and first["scratch_core_sha256"] == second["scratch_core_sha256"] == CORE
                and normalized(first) == normalized(second),
                "같은 형식 두 팔의 offsets·fresh init·AdamW·원 matrix group/LR가 다르다")
    pending = sum(estimates.values())
    if args.arm in completed:
        raise Hold("이미 완주한 해당 팔은 다시 실행하지 않는다")
    if not arm_for(state,args.arm)["required"] and not set(required).issubset(completed):
        raise Hold("선택 팔은 현재 profile의 필수 두 팔 전체 완주 뒤에만 실행한다")
    minimum = state["profile"]["minimum_pair_training_sec"]+post_reserve*len(arms) if not completed else 0
    remaining = TRAIN_END.timestamp()-time.time()
    if max(pending, minimum) > remaining:
        raise Hold("보수적인 전체 팔의 본학습이16시 안에 들어오지 않는다")
    if state["profile"]["evaluation_reserve_sec"] > END.timestamp()-TRAIN_END.timestamp():
        raise Hold("평가·기록 예약이 전체 권한창보다 크다")
    return dict(root_budget_sha256=digest, estimates_seconds=estimates, completed_arms=completed,
                pending_forecast_seconds=pending, admitted_arms=arms, current_cost=costs[args.arm],
                unmeasured_post_training_reserve_sec_per_arm=post_reserve,post_reserve_measured=False,
                estimate="preparation+cold1+max(warm7,late_micro*16)*2288*1.35+post; future safety not guaranteed")


def fresh_admission(profile, budget):
    from scripts.diag_p106_vram_sample import read_memory
    from scripts.diag_p106_full_coload_accum import _compute_apps
    budget.check("GPU 입장 전")
    apps = _compute_apps(); used, free = read_memory()
    require(type(used) is int and type(free) is int and min(used,free) >= 0,
            "실제 입장 메모리 수치가 유효하지 않다")
    if apps or free < profile["entry_free_mib"]:
        raise Hold("총괄이 지정한 GPU 유휴·여유 입장이 충족되지 않았다")
    budget.check("GPU 입장 후")
    return dict(global_used_mib=used, free_mib=free, compute_apps=apps, monotonic=time.monotonic())


def checkpoint_experiment(child):
    require(child["updates"] == UPDATES and child["totals"]["targets"] == TOTAL
            and child["scratch_core_sha256"] == CORE, "완주와 fresh 초기화가 없는 CP 명세는 허용하지 않는다")
    return dict(schema=SCHEMA,arm=child["arm"],corpus=child["corpus"],optimizer=child["optimizer"],
        source_sha256=child["source_sha256"],profile_sha256=child["profile_sha256"],
        pair_complete_sha256=child["pair_complete_sha256"],scratch_core_sha256=CORE,
        core_sha256=child["final_core_sha256"],updates=UPDATES,targets=TOTAL,seed=1337,
        original_training_weights_copied=False)


def close_preserving(primary, actions):
    errors=[]
    for stage,action in actions:
        try:
            action()
        except BaseException as error:
            errors.append(supervisor.error_record(error,stage))
    if errors:
        owner=primary if primary is not None else OSError("부분 파일 정리가 불완전하다")
        owner.supported_cleanup_errors=[*getattr(owner,"supported_cleanup_errors",[]),*errors]
        if primary is None:
            raise owner


def execute_training(args, state, budget):
    arm = arm_for(state, args.arm)
    full_cache(state, budget)
    reservation = None if args.mode == "cost" else budget_admission(args, state)
    admission = fresh_admission(state["profile"], budget)
    import numpy as np
    tokens = np.memmap(path(state["cache"])/(arm["corpus"]+".bin"), dtype="<u2", mode="r")
    offsets, offset_proof = native.make_offsets(pool_tokens=len(tokens), updates=UPDATES)
    if reservation is not None:
        require(offset_proof == reservation["current_cost"]["offsets"], "cost와 본학습의 실제 offsets가 다르다")
    runtime = native.modules()[0]
    writer = ShardWriter(args.output/"updates", "updates", limit=19_999_999)
    child = dict(schema=SCHEMA, mode=args.mode, arm=args.arm, corpus=arm["corpus"], optimizer=arm["optimizer"],
        source_sha256=state["source_identity"]["sha256"], profile_sha256=state["profile_sha256"],
        pair_complete_sha256=state["complete_sha256"], admission=admission, offsets=offset_proof,
        same_token_seed_does_not_pair_original_windows=True, original_weights_copied=False,
        inherited_fsize_bytes=list(resource.getrlimit(resource.RLIMIT_FSIZE)),
        checkpoint=None, checkpoint_sha256=None, native32=None, synthetic=False, semantic_quality="NOT_EVALUATED")
    checkpoint = path("runs/ckpt/"+args.output.name+"_"+args.arm+".pt")
    require(args.mode == "cost" or not checkpoint.exists(), "완료 또는 부분 CP를 보존한다")
    forward,primary = None,None
    try:
        with MemorySamples() as memory:
            with native.routed_runtime("ternary", None) as (torch, model, cfg, tok, scratch, route):
                require(scratch == CORE and runtime.state_fingerprint(model) == CORE, "같은028C46 fresh core가 필요하다")
                child["scratch_core_sha256"] = scratch
                child["cfg"] = json.loads(canonical(asdict(cfg)))
                child["geometry_and_token_metadata"] = dict(state["profile"]["geometry_parent"],
                    runtime="load_runtime(scratch_ntp)",tokenizer_sha256=native.TOKENIZER_SHA,
                    tokenizer_lineage="chat32",strict_lineage_helper="validate_parent_lineage")
                model.train(); model.clear_quant(); model.set_anneal(0.)
                optimizers, groups, adaptation = optimizer_pair(model, arm, state["profile"])
                child["actual_optimizer_groups"], child["optimizer_adaptation"] = groups, adaptation
                child["optimizer_contract"] = json.loads(canonical([
                    [{k:v for k,v in group.items() if k != "params"} for group in opt.param_groups]
                    for opt in optimizers]))
                if reservation is not None:
                    require(groups == reservation["current_cost"]["actual_optimizer_groups"]
                        and child["optimizer_contract"] == reservation["current_cost"]["optimizer_contract"],
                        "cost와 실제 optimizer group·기타 설정이 다르다")
                forward = torch.compile(model, mode="default")
                adapter = NativeAdapter(torch, model, forward, tokens, optimizers, route)
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.synchronize()
                child["pre_training_seconds"] = time.monotonic()-budget.started
                value = update_loop(adapter, offsets, writer, budget, cost=args.mode=="cost")
                child.update(value)
                child["primary_peak"] = dict(allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                    reserved_mib=torch.cuda.max_memory_reserved()/2**20,scope="UPDATE_LOOP_ONLY_NOT_MODEL_STARTUP")
                if args.mode == "cost":
                    child["late"] = native.late_probe(torch,model,forward,optimizers,tokens,offsets)
                    child["cache_audit"] = native.cache_audit(torch,model,route)
                    child["status"] = "COST8_COMPLETE"
                else:
                    require(value["updates"] == UPDATES and value["totals"]["targets"] == TOTAL,
                            "완주 이전에는 평가나 CP를 허용하지 않는다")
                    child["training_completed_epoch"] = time.time()
                    require(child["training_completed_epoch"] < TRAIN_END.timestamp(), "16시 이전에 본학습을 마쳐야 한다")
                    supervisor.write_once(args.output/"training_complete.json",dict(updates=UPDATES,targets=TOTAL,
                        source_sha256=state["source_identity"]["sha256"],
                        training_completed_epoch=child["training_completed_epoch"]),budget)
                    model.clear_quant(); model.set_anneal(1.)
                    core_before = runtime.state_fingerprint(model)
                    child["native32"] = native.validate_native32(native.native_probe(torch,model))
                    child["cache_audit"] = native.cache_audit(torch,model,route)
                    generation = state["profile"].get("generation")
                    if generation is not None:
                        cases, _ = read(generation["cases"]["path"], generation["cases"]["sha256"])
                        answers = ShardWriter(args.output/"answers", "answers", limit=19_999_999)
                        answer_error=None
                        try:
                            for case in cases:
                                budget.check("완주 뒤 원답 생성")
                                answer, trace = native.modules()[1].emit64(model,cfg,tok,case["messages"])
                                answers.append(dict(id=case["id"], answer=answer, generation=trace))
                            manifest = answers.close(lineage=dict(source_sha256=state["source_identity"]["sha256"],
                                                                full_updates=UPDATES))
                            verify(args.output/"answers", manifest); child["generation"] = manifest
                        except BaseException as error:
                            answer_error=error
                            raise
                        finally:
                            close_preserving(answer_error,[("부분 원답 shard 닫기",answers._finish)])
                    require(runtime.state_fingerprint(model) == core_before, "완주 뒤 평가가 본체를 바꿨다")
                    child["final_core_sha256"] = core_before
                    checkpoint.parent.mkdir(parents=True, exist_ok=True)
                    budget.check("새 CP 저장 전")
                    with checkpoint.open("xb") as stream:
                        torch.save(dict(model=model.state_dict(),cfg=asdict(cfg),step=UPDATES,
                            tokenizer_sha256=native.TOKENIZER_SHA,tokenizer_lineage="chat32",
                            quantization_route=route.metadata,experiment=checkpoint_experiment(child)),stream)
                        stream.flush(); os.fsync(stream.fileno())
                    budget.check("큰 CP 저장과 동기화 후")
                    child.update(checkpoint=str(checkpoint.relative_to(ROOT)), checkpoint_sha256=pair.file_sha(checkpoint),
                                 final_core_sha256=core_before, status="TRAIN2289_COMPLETE",
                                 optimizer_state_saved=False, training_resume_supported=False)
                child["route"] = native.route_receipt(model,route)
                native.validate_route_receipt(child["route"],"ternary")
                child["quantization_route"] = route.metadata
                require(route.metadata["scope"] == "TLINEAR_WEIGHTS_ONLY", "본체 전체 삼진 경로로 승격하지 않는다")
                model.clear_quant()
                del adapter, forward, optimizers
                forward = None
        child["memory"] = memory.summary()
        manifest = writer.close(lineage=dict(source_sha256=state["source_identity"]["sha256"],
                        profile_sha256=state["profile_sha256"], arm=args.arm, mode=args.mode))
        verify(args.output/"updates", manifest)
        child["event_manifest"] = manifest
        immutable_metadata(args,state,budget)
        full_cache(state,budget)
        child["whole_worker_seconds"] = time.monotonic()-budget.started
        return child
    except BaseException as error:
        primary=error
        raise
    finally:
        close_preserving(primary,[("부분 update shard 닫기",writer._finish),("읽기 전용 token map 닫기",tokens._mmap.close)])
        if forward is not None:
            del forward


def child_limits(parent):
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    library = ctypes.CDLL(None, use_errno=True)
    if library.prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "직접 자식 부모 사망 종료 설정 실패")
    if os.getppid() != parent:
        os.kill(os.getpid(),signal.SIGTERM)


def owned_members(saved, known, command, token, *, proc_root=Path("/proc"), stat=None):
    """같은 세션·시작 시각·실행파일을 확인한 경우에만 소유 환경을 읽는다."""
    stat = supervisor.proc.proc_stat if stat is None else stat
    current = []
    expected = str(Path(command[0]).resolve(strict=True))
    for entry in proc_root.iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            row = stat(int(entry.name))
            if row["pgid"] != saved["pgid"] or row["session"] != saved["session"]:
                continue
            require(row["starttime"] >= saved["starttime"], "과거 그룹 구성원을 거부한다")
            previous = known.get(row["pid"])
            require(previous is None or previous["starttime"] == row["starttime"], "관측 PID가 재사용됐다")
            if row["state"] == "Z":
                if previous is not None:
                    current.append(row)
                continue
            executable = os.readlink(entry/"exe")
            parent_proved = row["pid"] == saved["pid"] or row["ppid"] in known or previous is not None
            if executable != expected and not parent_proved:
                continue
            if row["pid"] == saved["pid"]:
                require(executable == expected, "학습 leader의 정확한 실행파일이 다르다")
            environment = (entry/"environ").read_bytes()
            owned = (OWNER+"="+token).encode() in environment.split(b"\0")
            del environment
            if owned:
                row["executable"] = executable
                known[row["pid"]] = row
                current.append(row)
        except (FileNotFoundError,ProcessLookupError):
            continue
    return current


def supervise(command, output, budget, *, factory=subprocess.Popen, training_marker=None):
    """소유 그룹 helper를 사용한다. 강제 회수와 leader 선종료를 정상화하지 않는다.

    부모 SIGKILL 뒤 전체 자손 종료는 보장하지 않는다. 외부 OS timeout과
    실제 부모 종료·잔존 검산은 총괄이 별도로 회수해야 한다.
    """
    token = secrets.token_hex(32)
    process, saved, logger, logs, old_subreaper = None, None, None, None, None
    known, errors = {}, []
    result = dict(actual_child_exit=None,launch_state="NOT_STARTED",forced_cleanup=False,
        original_error=None,cleanup_errors=[],child_group_quiescent=False,stdout_complete=False,
        subreaper_restored=False,owner_sha256=hashlib.sha256(token.encode()).hexdigest().upper())
    def scan():
        return [] if saved is None else owned_members(saved,known,command,token)
    try:
        old_subreaper = supervisor.proc.set_subreaper(1)
        logs = ShardWriter(output/"stdout","stdout",limit=19_999_999)
        compile_dir = path("data_cache/"+output.name+"_compile")
        require(not compile_dir.exists() and not compile_dir.is_symlink(), "기존 compile 캐시를 재사용하지 않는다")
        budget.check("학습 자식 생성 전")
        result["launch_state"] = "PENDING"
        parent_pid = os.getpid()
        process = factory(command,cwd=ROOT,env=dict(os.environ,**{OWNER:token},PYTHONDONTWRITEBYTECODE="1",
            TORCHINDUCTOR_CACHE_DIR=str(compile_dir),TRITON_CACHE_DIR=str(compile_dir/"triton")),
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            start_new_session=True,bufsize=0,preexec_fn=lambda owner=parent_pid:child_limits(owner))
        result["launch_state"] = "STARTED"
        smoke._register_owned(process,start_new_session=True)
        saved = supervisor.proc.proc_stat(process.pid)
        require(saved["ppid"] == parent_pid and saved["pid"] == saved["pgid"] == saved["session"],
                "학습 자식의 직접 부모·새 세션이 다르다")
        known[saved["pid"]] = saved
        result["controller_identity"] = saved
        def drain():
            try:
                whole, count = hashlib.sha256(),0
                for chunk in iter(lambda:process.stdout.read(65536),b""):
                    count += len(chunk); whole.update(chunk)
                    logs.append(dict(encoding="BASE64_RAW_STDOUT",bytes=base64.b64encode(chunk).decode("ascii")))
                result.update(stdout_bytes=count,stdout_sha256=whole.hexdigest().upper(),stdout_complete=True)
            except BaseException as error:
                errors.append(supervisor.error_record(error,"stdout 분할 보존",token))
        logger = threading.Thread(target=drain,daemon=True); logger.start()
        while True:
            scan()
            code = process.poll()
            if code is not None:
                result["actual_child_exit"] = code
                break
            if errors:
                raise OSError("stdout 원형 보존에 실패했다")
            if training_marker is not None and time.time() >= TRAIN_END.timestamp():
                require(training_marker.is_file(), "16시 전에 본학습 완결 표지가 없다")
                marker = pair.read_json(training_marker)
                require(marker.get("updates") == UPDATES and marker.get("targets") == TOTAL
                    and marker.get("training_completed_epoch",math.inf) < TRAIN_END.timestamp(),
                    "본학습 완결 표지가16시 마감과 다르다")
            if budget.remaining() <= budget.reserve:
                raise TimeoutError("본체·평가 종료 뒤 정리 예약에 도달했다")
            time.sleep(.03)
    except BaseException as error:
        result["original_error"] = supervisor.error_record(error,"학습 부모",token)
    finally:
        previous_mask = None
        try:
            previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
        except BaseException as error:
            result["cleanup_errors"].append(supervisor.error_record(error,"정리 신호 차단",token))
        if process is not None:
            try:
                process.poll()
                members = scan()
                live = [row for row in members if row["state"] != "Z"]
                if process.returncode is not None and not live and members:
                    result["reaped"] = supervisor.reap_group(process.pid,min(budget.end,time.monotonic()+.5))
                if process.poll() is None or smoke.owned_group_alive(process):
                    result["forced_cleanup"] = True
                    require(live,"현재 생존 소유 구성원 확인 없이 과거 PGID를 종료하지 않는다")
                    os.killpg(process.pid,signal.SIGTERM)
                    result["signals"] = ["SIGTERM"]
                    try:
                        process.wait(timeout=min(.5,max(.01,budget.remaining())))
                    except subprocess.TimeoutExpired:
                        pass
                    if smoke.owned_group_alive(process):
                        fresh = [row for row in scan() if row["state"] != "Z"]
                        if fresh:
                            notes = smoke.stop_process_group(process,min(budget.end,time.monotonic()+5),time.monotonic)
                            result["cleanup_notes"] = notes
                            audit = supervisor.cleanup_note_state(notes)
                            if audit["errors"]:
                                result["cleanup_errors"].append(dict(type="CleanupAuditError",
                                    stage="공용 그룹 정리 반환 감사",notes=audit["errors"]))
                process.wait(timeout=max(.01,min(1.,budget.remaining())))
                result["actual_child_exit"] = process.returncode
                result["reaped"] = [*result.get("reaped",[]),
                    *supervisor.reap_group(process.pid,min(budget.end,time.monotonic()+2))]
                result["child_group_quiescent"] = not smoke.owned_group_alive(process)
                require(result["child_group_quiescent"],"소유 학습 그룹의 잔존이 있다")
            except BaseException as error:
                result["cleanup_errors"].append(supervisor.error_record(error,"학습 그룹 회수",token))
            finally:
                for stage,action in (
                        ("실제 자식 종료 재확인",lambda:process.poll()),
                        ("stdout thread 대기",lambda:logger.join(timeout=max(.01,min(2.,budget.remaining())))
                            if logger is not None else None),
                        ("stdout 닫기",lambda:process.stdout.close()
                            if process.stdout is not None and (logger is None or not logger.is_alive()) else None),
                        ("소유 그룹 등록 해제",lambda:smoke._forget_owned(process))):
                    try:
                        action()
                    except BaseException as error:
                        result["cleanup_errors"].append(supervisor.error_record(error,stage,token))
                if process.returncode is not None:
                    result["actual_child_exit"] = process.returncode
                if logger is not None and logger.is_alive():
                    result["cleanup_errors"].append(dict(type="TimeoutError",stage="stdout thread 종료"))
        if previous_mask is not None:
            try:
                signal.pthread_sigmask(signal.SIG_SETMASK,previous_mask)
            except BaseException as error:
                result["cleanup_errors"].append(supervisor.error_record(error,"정리 신호 복구",token))
        result["cleanup_errors"].extend(errors)
        if old_subreaper is not None:
            try:
                supervisor.proc.set_subreaper(old_subreaper)
                result["subreaper_restored"] = True
            except BaseException as error:
                result["cleanup_errors"].append(supervisor.error_record(error,"subreaper 복원",token))
        try:
            if logs is not None and (logger is None or not logger.is_alive()):
                if logs._total_rows:
                    manifest = logs.close(lineage=dict(schema=SCHEMA))
                    verify(output/"stdout",manifest); result["stdout_manifest"] = manifest
                else:
                    logs._finish()
        except BaseException as error:
            result["cleanup_errors"].append(supervisor.error_record(error,"stdout 저장·재읽기",token))
        result["observed_descendants"] = list(known.values())
    return result


def supervision_ok(value):
    return type(value.get("actual_child_exit")) is int and value["actual_child_exit"] == 0 \
        and value.get("child_group_quiescent") is True and value.get("stdout_complete") is True \
        and value.get("subreaper_restored") is True and value.get("launch_state") == "STARTED" \
        and not value.get("forced_cleanup") and not value.get("original_error") \
        and not value.get("cleanup_errors") and not value.get("post_errors")


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--mode",choices=("cost","train"),required=True)
    value.add_argument("--arm",required=True)
    value.add_argument("--profile",required=True)
    value.add_argument("--profile-sha256",required=True)
    value.add_argument("--f4",required=True)
    value.add_argument("--f4-sha256",required=True)
    value.add_argument("--budget")
    value.add_argument("--budget-sha256")
    value.add_argument("--output")
    value.add_argument("--max-wall-sec",type=int,required=True)
    value.add_argument("--deadline",default=END.isoformat())
    value.add_argument("--parent-started",type=float,help=argparse.SUPPRESS)
    group = value.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-only",action="store_true")
    group.add_argument("--execute",action="store_true")
    group.add_argument("--worker",action="store_true",help=argparse.SUPPRESS)
    return value


def main(argv=None):
    args = parser().parse_args(argv)
    output, owned, state = None,False,None
    try:
        require(300 <= args.max_wall_sec <= 28800,"현재 worker의 최대 시간은300..28800초다")
        deadline = datetime.fromisoformat(args.deadline.replace("Z","+00:00"))
        require(deadline.tzinfo is not None and deadline <= END,"전체 권한은26일17시 이내다")
        if args.mode == "train":
            deadline = min(deadline,TRAIN_END)
            if deadline.timestamp()-time.time() <= 120:
                raise Hold("본학습 팔 전체를16시 전에 닫을 정리 예약이 없다")
        start = args.parent_started if args.worker else STARTED
        require(start is not None,"현재 부모 시작 시각이 필요하다")
        budget = supervisor.Budget(args.max_wall_sec,deadline.timestamp(),started=start,reserve=120)
        with supervisor.total_budget(budget),supervisor.termination_guard():
            state = metadata(args)
            arm_for(state,args.arm)
            budget.reserve = state["profile"]["cleanup_reserve_sec"]
            require(budget.remaining() > budget.reserve,"명시한 정리 예약을 확보하지 못했다")
            reservation = budget_admission(args,state) if args.mode == "train" else None
            if reservation is not None and reservation["estimates_seconds"][args.arm] > budget.remaining()-budget.reserve:
                raise Hold("현재 팔의 전체 보수 비용이 이 부모의 실제 wall·정리 예약에 들어오지 않는다")
            if args.check_only:
                result = dict(schema=SCHEMA,source_sha256=state["source_identity"]["sha256"],
                    cache_full_verification="NOT_RUN",model_loaded=False,gpu_calls=0,files_written=0,
                    estimates_seconds=None if reservation is None else reservation["estimates_seconds"])
                code = 0
            else:
                require(args.output is not None and re.fullmatch(PREFIX+"[A-Za-z0-9_]+",Path(args.output).name),
                        "새 학습 증거 이름공간이 필요하다")
                output = path(args.output)
                require(Path(args.output).parts[:2] == ("test_result","evidence")
                    and len(Path(args.output).parts) == 3,"학습 증거는 지정된 위치에만 쓴다")
                args.output = output
                if args.worker:
                    invocation,_ = read(str((output/"invocation.json").relative_to(ROOT)))
                    require(os.getppid() == invocation["parent_pid"]
                        and supervisor.proc.proc_stat(os.getppid())["starttime"] == invocation["parent_starttime"]
                        and invocation["source_sha256"] == state["source_identity"]["sha256"]
                        and re.fullmatch("[0-9a-f]{64}",os.environ.get(OWNER,"")),
                        "소유 worker의 부모 신원이 다르다")
                    owned = True
                    child = execute_training(args,state,budget)
                    validate_worker(child,state,args.arm,args.mode,output)
                    supervisor.write_once(output/"worker.json",child,budget)
                    code = 0
                else:
                    require(not output.exists(),"기존 완료/부분 학습 결과를 보존한다")
                    output.mkdir(); owned=True
                    supervisor.write_once(output/"source.json",state["source_identity"],budget)
                    owner = supervisor.proc.proc_stat(os.getpid())
                    supervisor.write_once(output/"invocation.json",dict(parent_pid=os.getpid(),
                        parent_starttime=owner["starttime"],source_sha256=state["source_identity"]["sha256"]),budget)
                    command = [str(Path(sys.executable).resolve()),"-I","-B","-X","utf8",
                               str(ROOT/"scripts/diag_p106b_native_format_training.py")]
                    command += [item for item in (sys.argv[1:] if argv is None else argv) if item != "--execute"]
                    command += ["--worker","--parent-started",str(budget.started)]
                    observed = supervise(command,output,budget,
                        training_marker=output/"training_complete.json" if args.mode == "train" else None)
                    code = 0 if supervision_ok(observed) else 9
                    child,child_sha = None,None
                    try:
                        if (output/"worker.json").is_file():
                            child,child_sha = read(str((output/"worker.json").relative_to(ROOT)))
                        require(code != 0 or child is not None,"실제 자식 완결 증거가 없다")
                        if code == 0:
                            validate_worker(child,state,args.arm,args.mode,output)
                        immutable_metadata(args,state,budget)
                    except BaseException as error:
                        code = 9
                        observed.setdefault("post_errors",[]).append(supervisor.error_record(error,"부모 종결 검산"))
                    report = dict(schema=SCHEMA,mode=args.mode,arm=args.arm,returncode=code,
                        source_sha256=state["source_identity"]["sha256"],profile_sha256=state["profile_sha256"],
                        f4_sha256=state["f4_sha256"],pair_complete_sha256=state["complete_sha256"],
                        supervision=observed,worker=child,worker_sha256=child_sha,
                        whole_parent_seconds=time.monotonic()-budget.started,authority_end=END.isoformat(),
                        effective_process_deadline=deadline.isoformat(),
                        external_os_timeout_required=True,actual_supervisor_exit="ROOT_MUST_COLLECT")
                    supervisor.write_once(output/"report.json",report,budget)
                    supervisor.append_terminal(output,dict(event="OBSERVATION",returncode=code))
                result = dict(schema=SCHEMA,returncode=code,mode=args.mode,arm=args.arm)
            budget.check("작은 출력 전")
            print(json.dumps(result,ensure_ascii=False),flush=True)
            budget.check("작은 출력 뒤")
        budget.check("타이머와 신호 복구 뒤")
        return code
    except BaseException as error:
        record = supervisor.error_record(error,"전체 준비·실행·종결",os.environ.get(OWNER,""))
        if error.__context__ is not None and error.__context__ is not error:
            record["preceding_error"] = supervisor.error_record(error.__context__,"선행 원 예외",os.environ.get(OWNER,""))
        if owned and output is not None and output.is_dir():
            try:
                supervisor.append_terminal(output,dict(event="TERMINAL_VETO",returncode=9,error=record))
            except BaseException:
                pass
        code = 8 if isinstance(error,Hold) and not owned else 9
        print(json.dumps(dict(schema=SCHEMA,returncode=code,error_type=type(error).__name__)),flush=True)
        return code


if __name__ == "__main__":
    raise SystemExit(main())

