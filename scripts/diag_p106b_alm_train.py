#!/usr/bin/env python3
"""Opt-in fixed-reference ALM core study; not full-vocabulary distillation.

The original updater, encoder, weight route, optimizer factory and generator
remain their owners. This controller adds only cache binding, a loss facade,
TRAIN gradient calibration and immutable study receipts. Import is stdlib-only.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TAG = "p106b_alm_train_v1_s1337"
SCHEMA = "P106B_ALM_REFERENCE_TRAIN_V1"
# Identity versioning must not change the historical DEV64 sample.
EVAL_SELECTION_SCHEMA = "P106B_ALM_REFERENCE_TRAIN_V1"
BASE = ROOT / "HF/sft_ready" / TAG
EVIDENCE = ROOT / "test_result/evidence" / TAG
DEADLINE = datetime(2026, 10, 23, 7, 30, tzinfo=timezone.utc)
LIMIT, TEMPERATURE, RHO = 19_999_999, 100., .25
ARMS = ("ce", "alm")
MAX_NEW = 64
SOURCE_NAMES = (
    "scripts/diag_p106b_alm_train.py", "scripts/test_p106b_alm_train.py",
    "scripts/diag_p106b_alm_cache.py", "scripts/p106b_alm_bytes.py",
    "scripts/p106b_alm_template_alignment.py",
    "scripts/diag_p101a_padding_gpu.py", "scripts/diag_p101a_sft_mtp.py",
    "scripts/interactive_research_infer.py", "scripts/p106b_weight_route.py",
    "scripts/p106b_gate_runtime.py", "scripts/p106b_shards.py",
    "scripts/p101a_sft_mtp_data.py", "tinylm/train/alm.py",
    "scripts/diag_p106b_native_weight_route.py",
    "tinylm/train/mtp_sft.py", "tinylm/train/muon.py",
    "tinylm/train/optimizer_audit.py", "tinylm/model/transformer.py",
    "tinylm/model/modules.py", "tinylm/model/ternary.py", "tinylm/config.py",
    "tinylm/infer/generate.py", "tinylm/chat/serialize.py", "tinylm/data/sft.py",
    "scripts/diag_p101a_mtp_parity.py",
    "scripts/test_p106b_weight_route.py",
    # Import-time package owners and the strict loader/native-probe helpers.
    # Pin them too; this list does not import or execute any of these modules.
    "scripts/p106b_stage_receipt.py", "tinylm/__init__.py", "tinylm/paths.py",
    "tinylm/model/__init__.py", "tinylm/model/ternary_kernel.py",
    "tinylm/infer/__init__.py", "tinylm/infer/mtp.py",
    "tinylm/data/__init__.py", "tinylm/data/prepare.py", "tinylm/data/loader.py",
    "tinylm/chat/__init__.py", "tinylm/chat/canonical.py", "tinylm/chat/tokens.py",
    "tinylm/train/__init__.py", "tinylm/train/trainer.py", "tinylm/train/lr_finder.py",
    "tinylm/train/init_utils.py", "tinylm/train/init_mapping.py",
    "tinylm/train/anneal_schedule.py", "tinylm/training_defaults.py", "tinylm/audit_io.py",
    "tinylm/eval/__init__.py", "tinylm/eval/evaluate.py", "tinylm/eval/compare.py",
    # Existing helper imports and closed V7 contract owners, not teacher edits.
    "scripts/build_p106b_job_deck.py", "scripts/build_p106b_multisource_deck.py",
    "scripts/diag_p090b_oasst2_translation_candidates.py", "scripts/diag_p106_bonsai_assets.py",
    "scripts/diag_p106_oasst2_teacher_ko_gate.py", "scripts/diag_p106b_online_pseudo_sft.py",
    "scripts/diag_p106b_teacher_answer_repair.py", "scripts/p106b_teacher_format.py",
    "scripts/p106b_teacher_wrapper.py", "scripts/probe_p076_micro_accum.py",
    "scripts/train_sft_p090.py", "scripts/test_p106b_alm_cache.py",
    "scripts/diag_p106b_teacher_tf.py", "scripts/p106b_qwen_teacher.py",
    "scripts/diag_p106b_qwen_coload.py", "scripts/diag_p106b_mtp_teacher.py",
    "scripts/p106b_mtp_teacher.py", "scripts/diag_p106_coload.py",
    "scripts/diag_p106_full_coload_accum.py", "scripts/diag_p106b_online_rate5.py",
    "scripts/diag_p106_vram_sample.py", "scripts/p106b_http_errors.py",
    "scripts/test_p106b_alm_template_alignment.py", "scripts/p106b_alm_utf8_probability.py",
    "scripts/test_p106b_alm_utf8_probability.py",
)
USER_QUESTIONS = (
    "1+1은?", "2+2는?", "A는 사과고 B는 당근이다. B는?",
    "문맥: 민수는 사과 3개, 영희는 사과 5개를 가지고 있습니다. 질문: 영희의 사과는 몇 개입니까? 답만 쓰세요.",
    "사과에 대해 알려줘", "농구란?", "What is 1+1?", "Explain what an apple is.",
)


@dataclass(frozen=True)
class StudyProfile:
    name: str
    tag: str
    schema: str
    parent_name: str
    weight_route: str

    def metadata(self):
        return dict(name=self.name, tag=self.tag, schema=self.schema,
            parent_name=self.parent_name, weight_route=self.weight_route,
            quantization_scope="TLINEAR_WEIGHTS_ONLY", master_dtype="fp32",
            embedding_head_policy="FP32_TIED_EMBEDDING_AND_HEAD", anneal=1.,
            evaluation_selection_schema=EVAL_SELECTION_SCHEMA,
            comparison_scope="WITHIN_PARENT_CE_VS_ALM; F_VS_Q_IS_NOT_QUANTIZATION_ONLY")


LEGACY_PROFILE = StudyProfile("float_v1", TAG, SCHEMA, "native595-f", "float")
FLOAT_PROFILE = StudyProfile("float_v2", "p106b_alm_train_float_v2_s1337",
    "P106B_ALM_REFERENCE_TRAIN_FLOAT_V2", "native595-f", "float")
TERNARY_PROFILE = StudyProfile("ternary_v1", "p106b_alm_train_ternary_v1_s1337",
    "P106B_ALM_REFERENCE_TRAIN_TERNARY_V1", "native595-q", "ternary")
STUDY_PROFILES = (LEGACY_PROFILE, FLOAT_PROFILE, TERNARY_PROFILE)


@dataclass(frozen=True)
class StudyContext:
    profile: StudyProfile
    root: Path
    base: Path
    evidence: Path


def study_context(name="float_v1", *, root=None):
    profile = next((p for p in STUDY_PROFILES if p.name == name), None)
    if profile is None:raise ValueError("registered explicit study profile required")
    selected_root = ROOT if root is None else Path(root)
    # Preserve the legacy API, including existing isolated synthetic callers.
    if profile == LEGACY_PROFILE and root is None:
        return StudyContext(profile, selected_root, BASE, EVIDENCE)
    return StudyContext(profile, selected_root, selected_root/"HF/sft_ready"/profile.tag,
                        selected_root/"test_result/evidence"/profile.tag)


def resolve_context(context=None):
    context = study_context() if context is None else context
    if not isinstance(context, StudyContext) or context.profile not in STUDY_PROFILES:
        raise ValueError("immutable registered study context required")
    if context.profile != LEGACY_PROFILE:
        expected = study_context(context.profile.name, root=context.root)
        if context != expected:raise ValueError("study namespace differs from its profile")
    return context


def profile_fields(context):
    context = resolve_context(context)
    if context.profile == LEGACY_PROFILE:return {}
    metadata = context.profile.metadata()
    return dict(study_profile=metadata, study_profile_sha256=sha(metadata))


def validate_prepared_profile(prepared, context=None):
    context = resolve_context(context);profile = context.profile
    if prepared["parent_name"] != profile.parent_name or prepared["study_policy"] != policy():
        raise ValueError("fixed parent/study policy differs")
    if profile != LEGACY_PROFILE:
        route = prepared["parent_entry"]["header"]["quantization_route"]
        if (any(prepared.get(k) != v for k,v in profile_fields(context).items())
                or prepared.get("evaluation_selection_schema") != EVAL_SELECTION_SCHEMA
                or not isinstance(route,dict) or route.get("mode") != profile.weight_route
                or route.get("scope") != "TLINEAR_WEIGHTS_ONLY"
                or route.get("master_dtype") != "fp32"
                or prepared.get("quantization_route") != route):
            raise ValueError("same study/profile/parent weight route required")
    return context


def fixed_evaluation_rows(val):
    selected=[]
    for language in ("ko","en"):
        rows=[r for r in val if r["meta"]["language"]==language]
        rows.sort(key=lambda r:sha([EVAL_SELECTION_SCHEMA,1337,"FIXED_DEV",r["meta"]["semantic_root_id"]]))
        selected.extend(rows[:32])
    if len(selected)!=64:raise ValueError("fixed bilingual64 first answers required")
    return selected


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest().upper()


def digest(path):
    path = Path(path)
    if not path.is_file() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("explicit nonlinked file required: " + str(path))
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest().upper()


def read(path):
    path = Path(path)
    if path.stat().st_size > LIMIT:
        raise ValueError("metadata20MB limit")
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path, value):
    raw = canonical(value) + b"\n"
    if len(raw) > LIMIT:
        raise ValueError("evidence20MB limit")
    with Path(path).open("xb") as stream:
        stream.write(raw)


def sources(context=None):
    context=resolve_context(context)
    return {name: digest(context.root / name) for name in SOURCE_NAMES}


def authority(cap):
    now = datetime.now(timezone.utc)
    if not 60 <= cap <= 1200 or now >= DEADLINE or (DEADLINE-now).total_seconds() < cap+30:
        raise ValueError("current23Oct authority/whole phase with cleanup does not fit")
    return dict(authorized_until=DEADLINE.isoformat(), admitted_at=now.isoformat(),
                max_wall_seconds=cap, user_authority="2026-10-23 17KST proactive CPU+GPU; model stop16:30")


def policy():
    """고정 손실/노출/optimizer 단위. 런 중 재교정하지 않는다."""
    return dict(temperature=TEMPERATURE, rho=RHO, seed=1337, epochs=4, updates=32,
        micro=8, accum=16, width=1024, checkpoint=True, precision="BF16_EAGER_TF32_OFF",
        head_chunk=64, compile=False, mtp=False, clip=1.,
        adam_lr=1e-5, adam_betas=[.9,.95], adam_eps=1e-8,
        muon_lr=4e-5, muon_scale="rms", muon_ns_steps=5, muon_momentum=.95,
        muon_nesterov=True, weight_decay=0., evaluation_max_new=MAX_NEW)


def input_path(relative,context=None):
    value=Path(relative)
    if (value.is_absolute() or not value.parts or ".." in value.parts
            or value.parts[0] not in ("HF","data_cache","runs","test_result")):
        raise ValueError("explicit study input path required")
    if value.parts[0]=="runs" and value.parts[:2]!=("runs","ckpt"):
        raise ValueError("only explicit parent checkpoints are run inputs")
    return resolve_context(context).root/value


def verify_pins(pins, guard=None,context=None):
    actual={}
    for name,expected in sorted(pins.items()):
        if guard is not None:guard.check("input SHA "+name)
        actual[name]=digest(input_path(name,context))
        if actual[name]!=expected:raise ValueError("study input changed: "+name)
    return actual


def manifest_pins(directory, manifest,context=None):
    result={}
    for item in manifest["shards"]:
        child=Path(item["path"])
        if child.is_absolute() or ".." in child.parts:
            raise ValueError("manifest input escape")
        result[str((directory/child).relative_to(resolve_context(context).root))]=item["sha256"]
    return result


def study_identity(prepared, preparation_sha, code,context=None):
    context=validate_prepared_profile(prepared,context)
    return dict(schema=context.profile.schema,tag=context.profile.tag,preparation_sha256=preparation_sha,
        parent_name=prepared["parent_name"],parent_checkpoint=prepared["parent_entry"]["checkpoint"],
        parent_core_sha256=prepared["parent_entry"]["core_sha256"],
        tokenizer_sha256=prepared["tokenizer"]["sha256"],source_code_sha256=code,
        row_sha256=prepared["row_sha256"],cache_reports_sha256=sha(prepared["cache_reports"]),
        evaluation_sha256=prepared["evaluation_sha256"],
        evaluation_admission_sha256=sha(prepared["evaluation_admission"]),policy=policy(),
        **(dict(quantization_route=prepared["quantization_route"]) if context.profile!=LEGACY_PROFILE else {}),
        **profile_fields(context))


def phase_identity(common,mode,arm,calibration_pin=None):
    if (mode not in ("calibrate","cost","train","evaluate")
            or (mode=="calibrate" and arm is not None)
            or (mode in ("cost","train") and arm not in ARMS)
            or (mode=="evaluate" and arm not in ARMS+("parent",))):
        raise ValueError("fixed phase/arm identity required")
    needs=mode in ("cost","train") or mode=="evaluate" and arm!="parent"
    if needs != (calibration_pin is not None):
        raise ValueError("exact calibration pin required only for student phases")
    if needs and "study_profile" in common and (
            any(calibration_pin.get(k)!=common[k] for k in ("study_profile","study_profile_sha256"))
            or calibration_pin.get("study_identity_sha256")!=sha(common)
            or calibration_pin.get("parent_core_sha256")!=common["parent_core_sha256"]
            or calibration_pin.get("quantization_route_sha256")!=sha(common["quantization_route"])):
        raise ValueError("own study/parent calibration pin required")
    return dict(study_identity_sha256=sha(common),preparation_sha256=common["preparation_sha256"],
                parent_core_sha256=common["parent_core_sha256"],mode=mode,arm=arm,
                calibration_pin=calibration_pin,
                **(dict(study_profile_sha256=common["study_profile_sha256"],
                        quantization_route_sha256=sha(common["quantization_route"]))
                   if "study_profile" in common else {}))


def validate_closed(report,common,mode,arm,status,calibration_pin=None,context=None):
    context=resolve_context(context)
    wanted=phase_identity(common,mode,arm,calibration_pin)
    if (common.get("schema")!=context.profile.schema or common.get("tag")!=context.profile.tag
            or any(common.get(k)!=v or report.get(k)!=v for k,v in profile_fields(context).items())
            or (context.profile!=LEGACY_PROFILE and report.get("quantization_route")!=common.get("quantization_route"))
            or report.get("schema")!=context.profile.schema or report.get("tag")!=context.profile.tag
            or report.get("mode")!=mode or report.get("arm")!=arm
            or report.get("status")!=status or report.get("returncode")!=0
            or report.get("study_identity")!=common
            or report.get("phase_identity")!=wanted
            or report.get("phase_identity_sha256")!=sha(wanted)
            or report.get("source_code_sha256")!=common["source_code_sha256"]
            or report.get("preparation_sha256")!=common["preparation_sha256"]
            or not all(report.get(key) is True for key in
                ("sources_unchanged","inputs_unchanged","parent_checkpoint_unchanged"))):
        raise ValueError("closed same-study/phase/arm/input identity required")


def calibration_pin(report,common,path,report_sha,context=None):
    context=resolve_context(context)
    validate_closed(report,common,"calibrate",None,"ALM_GRADIENT_CALIBRATED",context=context)
    stats=report.get("global_stats",{})
    ce,kd=stats.get("ce_norm"),stats.get("kd_norm")
    if (any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0
            for v in (ce,kd,report.get("weight")))
            or report.get("rho")!=RHO or report.get("temperature")!=TEMPERATURE
            or report["weight"]!=RHO*ce/kd or report.get("optimizer_updates")!=0
            or report.get("core_before")!=common["parent_core_sha256"]
            or report.get("core_after")!=common["parent_core_sha256"]
            or report.get("rng_unchanged") is not True):
        raise ValueError("same-parent finite TRAIN-only fixed calibration required")
    return dict(path=path,sha256=report_sha,weight=report["weight"],rho=RHO,
                temperature=TEMPERATURE,phase_identity_sha256=report["phase_identity_sha256"],
                **(dict(study_identity_sha256=sha(common),parent_core_sha256=common["parent_core_sha256"],
                        quantization_route_sha256=sha(common["quantization_route"]))
                   if context.profile!=LEGACY_PROFILE else {}),
                **profile_fields(context))


def closed_read(path):
    before=digest(path);value=read(path)
    if before!=digest(path):raise ValueError("closed report changed while reading")
    return value,before


def validate_cost(report,common,arm,pin,context=None):
    validate_closed(report,common,"cost",arm,"ALM_COST_COMPLETE",pin,context)
    if (report.get("updates")!=2 or report.get("optimizer_updates")!=2
            or report.get("checkpoint_writes")!=0
            or report.get("initial_core_sha256")!=common["parent_core_sha256"]
            or report.get("weight")!=(pin["weight"] if arm=="alm" else 0.)
            or report.get("initial_optimizer_state_empty") is not True
            or report.get("initial_gradients_all_none") is not True
            or not report.get("optimizer_groups")
            or report.get("optimizer_groups_after")!=report.get("optimizer_groups")
            or not report.get("initial_rng")):
        raise ValueError("same fresh parent/two-update cost/weight required")


def validate_training(report,common,arm,pin,context=None):
    context=resolve_context(context)
    validate_closed(report,common,"train",arm,"ALM_TRAIN_COMPLETE",pin,context)
    experiment=report.get("checkpoint_experiment",{})
    if (report.get("updates")!=32 or report.get("optimizer_updates")!=32
            or report.get("checkpoint_writes")!=1
            or report.get("initial_core_sha256")!=common["parent_core_sha256"]
            or report.get("weight")!=(pin["weight"] if arm=="alm" else 0.)
            or report.get("initial_optimizer_state_empty") is not True
            or report.get("initial_gradients_all_none") is not True
            or report.get("optimizer_groups_after")!=report.get("optimizer_groups")
            or report.get("checkpoint")!=str(checkpoint_path(arm,context).relative_to(context.root))
            or experiment.get("schema")!=context.profile.schema or experiment.get("tag")!=context.profile.tag
            or any(experiment.get(k)!=v for k,v in profile_fields(context).items())
            or (context.profile!=LEGACY_PROFILE and experiment.get("quantization_route_sha256")!=sha(common["quantization_route"]))
            or experiment.get("arm")!=arm or experiment.get("phase_identity")!=report["phase_identity"]
            or experiment.get("phase_identity_sha256")!=report["phase_identity_sha256"]
            or experiment.get("study_identity_sha256")!=sha(common)
            or experiment.get("preparation_sha256")!=common["preparation_sha256"]
            or experiment.get("parent")!=common["parent_checkpoint"]
            or experiment.get("source_code_sha256")!=common["source_code_sha256"]
            or experiment.get("weight")!=report["weight"]
            or experiment.get("temperature")!=TEMPERATURE or experiment.get("rho")!=RHO
            or experiment.get("optimizer_groups")!=report.get("optimizer_groups")):
        raise ValueError("exact same-study trained checkpoint experiment required")


def phase_input_pins(prepared,preparation_sha,extra=None,context=None):
    context=resolve_context(context)
    return {**prepared["input_pins"],**prepared["prepared_artifact_pins"],
            str((context.base/"report.json").relative_to(context.root)):preparation_sha,**(extra or {})}


def cuda_admission(model,guard,idle):
    guard.check("before CUDA idle admission")
    idle()
    guard.check("immediately before CUDA transfer")
    return model.cuda()


def child_header(payload,prepared,expected_experiment,context=None):
    context=validate_prepared_profile(prepared,context)
    entry=prepared["parent_entry"]
    if context.profile!=LEGACY_PROFILE and (
            not isinstance(expected_experiment,dict)
            or expected_experiment.get("schema")!=context.profile.schema
            or expected_experiment.get("tag")!=context.profile.tag
            or expected_experiment.get("parent")!=entry["checkpoint"]
            or expected_experiment.get("quantization_route_sha256")!=sha(prepared["quantization_route"])):
        raise ValueError("own study/parent child experiment required")
    if (not isinstance(payload,dict)
            or set(payload)!={"model","cfg","step","experiment","tokenizer_sha256","tokenizer_lineage","quantization_route"}
            or sha(payload["cfg"])!=sha(entry["header"]["cfg"]) or payload["step"]!=32
            or payload["experiment"]!=expected_experiment
            or payload["tokenizer_lineage"]!="chat32"
            or payload["tokenizer_sha256"]!=prepared["tokenizer"]["sha256"]
            or payload["quantization_route"]!=entry["header"]["quantization_route"]
            or any(expected_experiment.get(k)!=v for k,v in profile_fields(context).items())):
        raise ValueError("new study exact weight-only header/experiment differs")


def child_payload(torch,path,expected_sha,guard):
    guard.check("before CPU child checkpoint")
    path=Path(path)
    if any(p.is_symlink() for p in (path,*path.parents)):
        raise ValueError("nonlinked exact child checkpoint required")
    with path.open("rb") as stream:
        before=os.fstat(stream.fileno());h=hashlib.sha256()
        for part in iter(lambda:stream.read(1<<20),b""):
            guard.check("CPU child checkpoint hash");h.update(part)
        if h.hexdigest().upper()!=expected_sha:raise ValueError("child checkpoint SHA differs")
        stream.seek(0);guard.check("before CPU child tensor load")
        payload=torch.load(stream,map_location="cpu",weights_only=True)
        after=os.fstat(stream.fileno());current=path.stat()
        stamp=lambda value:(value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns)
        if stamp(before)!=stamp(after) or stamp(after)!=stamp(current):
            raise ValueError("child checkpoint changed while reading same handle")
    return payload


def grade(answer,expected):
    strict=answer in expected
    return dict(exact_original=strict,strict_whitespace_exact=strict,
        whitespace_normalized_exact=any(" ".join(answer.split())==" ".join(a.split()) for a in expected))


def chunk_observation(nll_sum,teacher_lp,denominator,chunks,weight,*,targets,byte_count,language,teacher_targets=0):
    if (denominator<1 or chunks<1 or not math.isfinite(nll_sum) or nll_sum<0
            or not math.isfinite(teacher_lp) or not -1e30<teacher_lp<=0):
        raise ValueError("finite raw chunk log probabilities and whole-update units required")
    s,t=-nll_sum/TEMPERATURE,teacher_lp/TEMPERATURE
    qs,qt=math.exp(s),math.exp(t)
    boundary=s==0 and t<0
    if not weight:
        coefficient=1./denominator
    elif boundary:
        coefficient=None
    else:
        if t==0:derivative=1./TEMPERATURE
        else:
            difference=qt*(-math.expm1(s-t)) if t>=s else qs*math.expm1(t-s)
            derivative=difference/(-math.expm1(s))/TEMPERATURE
        coefficient=1./denominator+weight*derivative/chunks
        if not math.isfinite(coefficient):
            coefficient=None
    sign=("boundary" if coefficient is None else "negative" if coefficient<0
          else "positive" if coefficient>0 else "zero")
    return dict(student_nll_sum=nll_sum,teacher_raw_logprob_sum=teacher_lp,
        student_logq=s,teacher_logq=t,student_q=qs,teacher_q=qt,
        student_exp_underflow=qs==0,teacher_exp_underflow=qt==0,
        student_q1_boundary=boundary,teacher_logq_zero=t==0,
        coefficient=coefficient,coefficient_sign=sign,
        ce_denominator=denominator,kd_denominator=chunks,weight=weight,temperature=TEMPERATURE,
        student_targets=targets,teacher_targets=teacher_targets,byte_count=byte_count,language=language)


def signal_summary(observations):
    result={}
    for language in ("ko","en"):
        values=[v for v in observations if v["language"]==language]
        finite=[v["coefficient"] for v in values if v["coefficient"] is not None]
        result[language]=dict(chunks=len(values),
            student_targets=sum(v["student_targets"] for v in values),
            teacher_targets=sum(v["teacher_targets"] for v in values),
            covered_bytes=sum(v["byte_count"] for v in values),
            student_q_min=min((v["student_q"] for v in values),default=None),
            student_q_max=max((v["student_q"] for v in values),default=None),
            teacher_q_min=min((v["teacher_q"] for v in values),default=None),
            teacher_q_max=max((v["teacher_q"] for v in values),default=None),
            student_exp_underflow_chunks=sum(v["student_exp_underflow"] for v in values),
            teacher_exp_underflow_chunks=sum(v["teacher_exp_underflow"] for v in values),
            coefficient_min=min(finite) if finite else None,coefficient_max=max(finite) if finite else None,
            coefficient_scope="DERIVATIVE_WRT_GOLD_NLL_IN_ALIGNED_CHUNK; NOT_PARAMETER_GRADIENT_OR_OPTIMIZER_UPDATE",
            by_sign={sign:dict(chunks=sum(v["coefficient_sign"]==sign for v in values),
                student_targets=sum(v["student_targets"] for v in values if v["coefficient_sign"]==sign),
                teacher_targets=sum(v["teacher_targets"] for v in values if v["coefficient_sign"]==sign),
                bytes=sum(v["byte_count"] for v in values if v["coefficient_sign"]==sign))
                for sign in ("positive","negative","zero","boundary")})
    return result


def coverage_summary(events):
    result={}
    for language in ("ko","en"):
        values=[event["coverage"][language] for event in events if language in event["coverage"]]
        totals={key:sum(value[key] for value in values) for key in
            ("ce_targets","answer_bytes","covered_bytes","student_kd_targets","teacher_kd_targets")}
        totals["ce_only_targets"]=totals["ce_targets"]-totals["student_kd_targets"]
        totals["uncovered_answer_bytes"]=totals["answer_bytes"]-totals["covered_bytes"]
        totals["answer_content_byte_acceptance"]=totals["covered_bytes"]/totals["answer_bytes"] if totals["answer_bytes"] else None
        totals["student_ce_target_acceptance"]=totals["student_kd_targets"]/totals["ce_targets"] if totals["ce_targets"] else None
        result[language]=totals
    return result


def evaluation_cases(prepared):
    from scripts.diag_p106b_alm_cache import message_text
    result=[]
    for index,row in enumerate(prepared["evaluation_rows"]):
        if [m.get("role") for m in row["messages"]] != ["user","assistant"]:
            raise ValueError("original two-message DEV QA required")
        result.append(dict(index=index,kind="OLD_DEV",language=row["meta"]["language"],
            question=message_text(row["messages"][0]),
            expected=[a["text"] for a in row["meta"]["answers"]],source_row=row))
    result.extend(dict(index=i,kind="USER_OBSERVATION_NOT_SCORED",question=q,expected=[])
                  for i,q in enumerate(USER_QUESTIONS))
    return result


def evaluation_admission(prepared,tok,max_seq=1024,render=None):
    if render is None:
        from tinylm.chat.serialize import serialize
        render=lambda question:serialize(dict(messages=[dict(role="user",content=question)]),
                                         "chatml",add_generation_prompt=True)
    cases=evaluation_cases(prepared);result=[]
    for case in cases:
        prompt=render(case["question"]);prefix=tok.encode(prompt).ids
        if len(prefix)+MAX_NEW>max_seq:
            raise ValueError("fixed evaluation prompt plus max-new exceeds context; no replacement/truncation")
        lengths=[]
        for answer in case["expected"]:
            joint=tok.encode(prompt+answer).ids
            stable=joint[:len(prefix)]==prefix
            lengths.append(dict(reference_sha256=hashlib.sha256(answer.encode("utf-8")).hexdigest().upper(),
                joint_prefix_stable=stable,body_tokens=len(joint)-len(prefix) if stable else None,
                exceeds_max_new=len(joint)-len(prefix)>MAX_NEW if stable else None))
        result.append(dict(index=case["index"],kind=case["kind"],
            prompt_sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest().upper(),
            prefix_ids_sha256=sha(prefix),prompt_tokens=len(prefix),max_new=MAX_NEW,max_seq=max_seq,
            reference_lengths=lengths,
            all_known_aliases_exceed_cap=bool(lengths) and all(v["exceeds_max_new"] is True for v in lengths),
            reference_limit_scope="NATIVE_JOINT_ENCODE_WITH_FIXED_PREFIX; UNSTABLE_PREFIX_IS_UNKNOWN; NOT_A_MODEL_ERROR"))
    return dict(cases=result,case_identity_sha256=sha(cases),max_new=MAX_NEW,max_seq=max_seq,
                long_reference_cases=sum(r["all_known_aliases_exceed_cap"] for r in result),
                unknown_reference_length_cases=sum(any(not v["joint_prefix_stable"] for v in r["reference_lengths"]) for r in result))


def generation_admission(generation,admitted):
    if (generation.get("prompt_tokens")!=admitted["prompt_tokens"]
            or generation.get("prompt_sha256")!=admitted["prompt_sha256"]):
        raise ValueError("actual generation prompt differs from fixed length admission")


def frozen_record(row):
    """Bind one immutable native cache to original full shifted labels/turns."""
    student = row["student"]
    ids, labels, turns = student["ids"], student["labels"], student["turn_ids"]
    if (not len(ids) == len(labels) == len(turns) or not 2 <= len(ids) <= 1025
            or student["ids_sha256"] != sha(ids) or row["eot_ce"] is not True
            or row["eot_kd"] is not False):
        raise ValueError("original native sequence/CE EOT identity differs")
    record = dict(x=ids[:-1], y=labels[1:], segments=turns[1:])
    seen, chunks,byte_spans = set(), [],[]
    for value in row["alignment"]["chunks"]:
        positions = value["student_shifted_indices"]
        if (not positions or positions != [i-1 for i in value["student_raw_indices"]]
                or positions != list(range(positions[0], positions[0]+len(positions)))
                or any(type(p) is not int or not 0 <= p < len(record["y"]) for p in positions)
                or seen.intersection(positions)):
            raise ValueError("original ordered nonoverlapping once-shifted positions required")
        if any(record["y"][p] in (-100, 2, 4) or record["segments"][p] != value["turn_id"]
               or record["y"][p] != ids[p+1] for p in positions):
            raise ValueError("KD target crosses role/turn/EOT or mismatches native ID")
        lp = value["teacher_raw_logprob_sum"]
        if isinstance(lp, bool) or not isinstance(lp, (int, float)) or not math.isfinite(lp) or not -1e30 < lp <= 0:
            raise ValueError("finite original native teacher logp required")
        seen.update(positions)
        left,right=value["byte_start"],value["byte_end"]
        teacher_indices=value["teacher_raw_indices"]
        if (type(left) is not int or type(right) is not int or not 0<=left<right
                or any(max(left,a)<min(right,b) for a,b in byte_spans)
                or not teacher_indices or any(type(i) is not int or i<1 for i in teacher_indices)
                or teacher_indices!=list(range(teacher_indices[0],teacher_indices[0]+len(teacher_indices)))):
            raise ValueError("positive original aligned chunk byte interval required")
        byte_spans.append((left,right))
        chunks.append(dict(positions=list(positions), teacher_logprob=float(lp),byte_count=right-left,
                           teacher_target_count=len(teacher_indices)))
    if not chunks or len(chunks) != row["kd_chunks"] or sum(y != -100 for y in record["y"]) != row["ce_targets"]:
        raise ValueError("closed row KD/CE count differs")
    answer_bytes=row["answer_projection"]["answer_byte_count"]
    if (type(answer_bytes) is not int or not 0<row["covered_bytes"]<=answer_bytes
            or any(right>answer_bytes for _,right in byte_spans)
            or sum(c["byte_count"] for c in chunks)!=row["covered_bytes"]):
        raise ValueError("original answer-only byte coverage differs")
    return dict(row_id=row["row_id"], language=row["language"], semantic_root_id=row["semantic_root_id"],
        prepared_row_sha256=row["prepared_row_sha256"], cache_row_sha256=row["cache_row_sha256"],
        source_row_sha256=row["source_row_sha256"], source_row=row["source_row"],
        record=record, record_sha256=sha(record), chunks=chunks, ce_targets=row["ce_targets"],
        kd_chunks=len(chunks), covered_bytes=row["covered_bytes"],answer_bytes=answer_bytes,
        coverage={key:row.get(key) for key in
            ("student_supervised_targets","teacher_supervised_targets","student_kd_targets",
             "teacher_targets","student_byte_acceptance","teacher_byte_acceptance","reference_byte_acceptance")})


def prepare(max_wall_sec=600,context=None):
    context=resolve_context(context)
    started=time.perf_counter()
    admission=authority(max_wall_sec)
    from scripts import diag_p101a_padding_gpu as updater
    from scripts.p106b_gate_runtime import wall_limit
    guard=updater.Guard(DEADLINE,max_wall_sec);guard.started=started
    with wall_limit(max_wall_sec):
        return _prepare(guard,started,admission,context)


def _prepare(guard,started,admission,context=None):
    context=resolve_context(context);profile=context.profile
    base=context.base;root=context.root
    from scripts import diag_p106b_alm_cache as cache
    from scripts import interactive_research_infer as ui
    from scripts.p101a_sft_mtp_data import stream_rows
    from scripts.p106b_shards import ShardWriter
    if base.exists() or base.is_symlink():
        raise FileExistsError("preserve existing training preparation")
    study_code=sources(context);guard.check("prepare source pins")
    source,source_pins=cache.source_inputs()
    code = cache.sources()
    original, selection = cache.load_prepared(code)
    prepared_cache_sha=cache.digest(cache.PREPARED/"report.json")
    tf_sha = cache.digest(cache.TF_REPORT)
    cache_inputs={str((cache.PREPARED/"report.json").relative_to(root)):prepared_cache_sha,
                  str(cache.TF_REPORT.relative_to(root)):tf_sha}
    cache_inputs.update(manifest_pins(cache.PREPARED,original["selection_manifest"],context))
    bound, reports = [], {}
    for index in range(64):
        guard.check("prepare closed cache batch")
        directory = cache.BASE / "teacher_cache" / f"batch_{index:06d}"
        batch_report_sha=digest(directory/"report.json")
        rows = selection[index*16:(index+1)*16]
        identity = cache.batch_identity(code, cache.digest(cache.PREPARED/"report.json"), rows,
                                        tf_sha, cache_prompt=False, batch_index=index)
        receipt = cache.closed_batch(directory, identity)
        if digest(directory/"report.json")!=batch_report_sha:
            raise ValueError("closed cache report changed during preparation")
        reports[str((directory/"report.json").relative_to(root))] = batch_report_sha
        for key in ("raw_manifest","cache_manifest"):
            cache_inputs.update(manifest_pins(directory,receipt[key],context))
        for row in stream_rows(directory, receipt["cache_manifest"]):
            cache.rebuild_student(row)
            bound.append(frozen_record(row))
    if (len(bound) != 1024 or [r["prepared_row_sha256"] for r in bound] != original["prepared_row_sha256"]
            or Counter(r["language"] for r in bound) != {"ko":512,"en":512}
            or len({r["semantic_root_id"] for r in bound}) != 1024):
        raise ValueError("same complete1024 bilingual cache required")
    # The old manifest is provenance only. New study authority is independent;
    # selected_runtime (inference-only/immutable-on-exit) is NEVER entered.
    manual = ui.verify_manifest()
    spec = ui.resolve_model(profile.parent_name)
    if spec.arm!=profile.weight_route:raise ValueError("parent spec/profile route differs")
    entry = manual["entries"][spec.name]
    ui.verify_descriptor(entry["checkpoint"], spec.checkpoint)
    from scripts import diag_p106b_native_weight_route as native
    if digest(native.VAL) != native.VAL_SHA:
        raise ValueError("same fixed native32 validation file required")
    source_pins[str(native.VAL.relative_to(root))] = native.VAL_SHA
    val = list(stream_rows(cache.SOURCE, source["manifests"]["val"]))
    if len(val) != 512:
        raise ValueError("original full DEV512 required")
    eval_rows = fixed_evaluation_rows(val)
    guard.check("prepare fixed evaluation lengths")
    ui.validate_import_environment()
    tok=ui.local_tokenizer(dict(tokenizer=manual["tokenizer"]))
    budget=evaluation_admission(dict(evaluation_rows=eval_rows),tok)
    del tok
    input_pins={**source_pins,**cache_inputs,**reports,
        entry["checkpoint"]["path"]:entry["checkpoint"]["sha256"],
        manual["tokenizer"]["path"]:manual["tokenizer"]["sha256"]}
    verified=verify_pins(input_pins,guard,context)
    if sources(context)!=study_code:raise ValueError("study sources changed during CPU preparation")
    base.mkdir(parents=True, exist_ok=False)
    writer = ShardWriter(base,"aligned",limit=LIMIT)
    for row in bound: writer.append(row)
    manifest = writer.close(lineage=dict(schema=profile.schema,source="CLOSED_NATIVE_QWEN_CACHE1024",
                                       training_admission="FROZEN_RESEARCH_STUDY_NOT_TRUTH_VERIFIED"))
    prepared = dict(schema=profile.schema,tag=profile.tag,status="ALM_TRAIN_PREPARED",source_code_sha256=study_code,
        cache_prepared_report_sha256=prepared_cache_sha, cache_reports=reports,
        parent_name=spec.name, parent_entry=entry, tokenizer=manual["tokenizer"],
        study_policy=policy(),input_pins=input_pins,
        prepared_artifact_pins={**manifest_pins(base,manifest,context),
            str((base/"aligned_shards_manifest.json").relative_to(root)):digest(base/"aligned_shards_manifest.json")},
        inputs_before=verified,inputs_after=verify_pins(input_pins,guard,context),inputs_unchanged=True,
        preparation_admission=admission,
        preparation_full_wall_before_report_write_seconds=time.perf_counter()-started,
        preparation_wall_scope="FROM_PREPARATION_ENTRY_INCLUDING_IMPORTS_SELECTION_TOKENIZATION_HASHES_WRITES; BEFORE_FINAL_REPORT_WRITE",
        evaluation_admission=budget,
        source_inputs=source_pins, training_authority="OWN_STAGE7C_AUTHORITY_NOT_MANUAL_INFERENCE_RUNTIME",
        rows=1024, language_rows={"ko":512,"en":512}, manifest=manifest,
        row_sha256=[sha(row) for row in bound], record_sha256=[r["record_sha256"] for r in bound],
        val_rows=val, val_sha256=sha(val), evaluation_rows=eval_rows, evaluation_sha256=sha(eval_rows),
        whole_exposure=dict(epochs=4,updates=32,micro=8,accum=16,width=1024,
            actual_x_tokens=4*sum(len(r["record"]["x"]) for r in bound),
            ce_targets=4*sum(r["ce_targets"] for r in bound),
            kd_chunks=4*sum(r["kd_chunks"] for r in bound),padded_slots=32*8*16*1024),
        semantics="ORIGINAL_REFERENCE_ANNOTATIONS_NOT_NEW_TEACHER_ANSWERS_NOT_TRUTH_VERIFIED",
        heldout="OLD_DEV512_NOT_FRESH_FINAL_TEST; OFFICIAL_BENCHMARKS_NEVER_IN_TRAIN",
        evaluation_selection_schema=EVAL_SELECTION_SCHEMA,
        quantization_route=entry["header"]["quantization_route"],**profile_fields(context))
    validate_prepared_profile(prepared,context)
    write_new(base/"report.json",prepared)
    return prepared


def load_prepared(context=None):
    context=resolve_context(context);profile=context.profile;base=context.base
    from scripts.p101a_sft_mtp_data import stream_rows
    p,preparation_sha=closed_read(base/"report.json")
    if (p.get("schema")!=profile.schema or p.get("tag")!=profile.tag or p.get("status") != "ALM_TRAIN_PREPARED" or p.get("source_code_sha256") != sources(context)
            or p.get("study_policy")!=policy() or p.get("inputs_unchanged") is not True):
        raise ValueError("same-code complete preparation required")
    validate_prepared_profile(p,context)
    if any(digest(context.root/name) != value for name,value in {**p["source_inputs"],**p["cache_reports"]}.items()):
        raise ValueError("source/cache report changed")
    rows = list(stream_rows(base,p["manifest"]))
    if (len(rows) != 1024 or [sha(r) for r in rows] != p["row_sha256"]
            or sha(p["val_rows"]) != p["val_sha256"] or sha(p["evaluation_rows"]) != p["evaluation_sha256"]):
        raise ValueError("prepared exact rows changed")
    if digest(base/"report.json")!=preparation_sha:
        raise ValueError("preparation report changed while loading")
    return p, rows,preparation_sha


@contextmanager
def runtime(prepared, guard, checkpoint=None, expected_core=None, expected_experiment=None,checkpoint_sha=None,*,context=None):
    context=validate_prepared_profile(prepared,context);mode=context.profile.weight_route
    from scripts import interactive_research_infer as ui
    from scripts import p106b_weight_route as method
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    import torch
    ui.validate_import_environment()
    spec = ui.resolve_model(prepared["parent_name"])
    if spec.arm!=mode:raise ValueError("runtime parent/profile route differs")
    entry = prepared["parent_entry"]
    # Common unchanged native initializer; own TRAIN authority precedes this call.
    payload = ui.read_selected_payload(torch,spec,entry)
    method.validate_route_metadata(payload["quantization_route"],mode)
    cfg = TMTConfig(**payload["cfg"])
    ui.validate_cfg(cfg,entry["header"])
    if not cfg.grad_checkpoint:
        raise ValueError("original checkpoint-on initializer required")
    tok = ui.local_tokenizer(dict(tokenizer=prepared["tokenizer"]))
    guard.check("CPU evaluation length admission")
    if evaluation_admission(prepared,tok,cfg.max_seq_len)!=prepared["evaluation_admission"]:
        raise ValueError("fixed evaluation prompt/reference token lengths changed")
    torch.manual_seed(1337)
    model = TiedMLPTransformer(cfg)
    with method.weight_route(model,mode):
        method.load_routed_state(model,payload,mode)
        if ui.state_fingerprint(model) != entry["core_sha256"]:
            raise ValueError("parent CPU core differs")
    del payload
    if checkpoint is not None:
        payload = child_payload(torch,checkpoint,checkpoint_sha,guard)
        child_header(payload,prepared,expected_experiment,context)
        with method.weight_route(model,mode):
            method.load_routed_state(model,payload,mode)
            if ui.state_fingerprint(model) != expected_core:
                raise ValueError("new study CPU core differs")
        del payload
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    pad_id=tok.token_to_id("<|pad|>")
    if pad_id is None:pad_id=tok.token_to_id("<pad>")
    if pad_id is None:raise ValueError("original PAD identity absent")
    model=cuda_admission(model,guard,ui.require_idle_gpu)
    model.train();model.clear_quant();model.set_anneal(1.)
    model._padding_pad_id=pad_id
    try:
        with method.weight_route(model,mode) as route:
            route.assert_active()
            if route.metadata!=entry["header"]["quantization_route"]:
                raise ValueError("actual GPU route differs from strict parent header")
            if ui.state_fingerprint(model)!=(expected_core or entry["core_sha256"]):
                raise ValueError("actual GPU entry core differs")
            guard.check("GPU core admitted")
            yield torch,model,tok,route
    finally:
        model.clear_quant();del model
        gc.collect();torch.cuda.empty_cache()


def records_for(rows):
    from tinylm.train.mtp_sft import Record
    records=[];bindings={}
    for row in rows:
        r=row["record"]
        if sha(r) != row["record_sha256"]:
            raise ValueError("unaltered original record required")
        record=Record(list(r["x"]),list(r["y"]),list(r["segments"]))
        records.append(record);bindings[id(record)]=row
    return records,bindings


class ALMCore:
    """Existing updater's components/normalization seam; no new optimizer loop."""
    def __init__(self, bindings, weight, observer=None):
        if not math.isfinite(weight) or weight < 0:
            raise ValueError("finite nonnegative frozen weight required")
        self.bindings,self.weight,self.observer=bindings,weight,observer
        self.events=[]
        self.observations=[]

    def configure(self,groups):
        self.queue=[list(micro) for micro in groups]
        self.denominator=sum(r.targets for micro in groups for r in micro)
        self.chunks=sum(self.bindings[id(r)]["kd_chunks"] for micro in groups for r in micro)
        self.events=[]
        self.observations=[]
        if not self.chunks or not self.denominator:
            raise ValueError("whole update needs CE and aligned KD")

    def pad_records(self,micro,*args,**kwargs):
        from tinylm.train.mtp_sft import pad_records
        if not self.queue or [id(r) for r in micro] != [id(r) for r in self.queue.pop(0)]:
            raise ValueError("actual ordered micro differs")
        self.current=[]
        self.current_coverage={}
        for index,record in enumerate(micro):
            binding=self.bindings[id(record)]
            if sha(dict(x=record.x,y=record.y,segments=record.segments)) != binding["record_sha256"]:
                raise ValueError("record mutated after source binding")
            language=binding["language"]
            coverage=self.current_coverage.setdefault(language,dict(ce_targets=0,answer_bytes=0,covered_bytes=0,
                student_kd_targets=0,teacher_kd_targets=0))
            coverage["ce_targets"]+=binding["ce_targets"]
            coverage["answer_bytes"]+=binding["answer_bytes"]
            coverage["covered_bytes"]+=binding["covered_bytes"]
            coverage["student_kd_targets"]+=sum(len(c["positions"]) for c in binding["chunks"])
            coverage["teacher_kd_targets"]+=sum(c["teacher_target_count"] for c in binding["chunks"])
            self.current.extend(dict(c,row=index,language=language,row_id=binding["row_id"]) for c in binding["chunks"])
        return pad_records(micro,*args,**kwargs)

    def components(self,model,hidden,y,segments,*,horizons):
        from tinylm.train import alm
        if horizons or not hasattr(self,"current"):
            raise ValueError("main-head only ordered micro required")
        nll,mask=alm.target_nll(model,hidden,y,chunk=64)
        detached=nll.detach().double().cpu().tolist()
        observations=[dict(chunk_observation(
            math.fsum(detached[c["row"]][p] for p in c["positions"]),c["teacher_logprob"],
            self.denominator,self.chunks,self.weight,targets=len(c["positions"]),
            byte_count=c["byte_count"],language=c["language"],
            teacher_targets=c["teacher_target_count"]),row_id=c["row_id"],
            student_shifted_indices=list(c["positions"])) for c in self.current]
        self.observations.extend(observations)
        event=dict(event="objective_observations",observations=observations,
                   coverage=self.current_coverage,statistics="DETACHED_CPU_FP64_SCALARS_NOT_MODEL_PRECISION")
        if self.observer is not None:self.observer(event)
        # CE-only must remain defined even when the unused binary KL has a pole.
        if self.weight:
            kl,k=alm.chunk_kl(nll,mask,self.current,temperature=TEMPERATURE)
        else:
            kl,k=None,len(self.current)
        self.events.append(dict(ce_sum=float(nll.detach().sum()),
            kl_sum=float(kl.detach()) if kl is not None else None,
            kl_status="COMPUTED" if self.weight else "NOT_COMPUTED_CE_ONLY",
            ce_targets=int(mask.sum()),kd_chunks=k,coverage=self.current_coverage,
            signal_summary=signal_summary(observations)))
        return {1:nll.sum(),"kl":kl},{1:int(mask.sum()),"kl":k}

    def normalized_loss(self,sums,denominators,weights):
        from tinylm.train import alm
        if denominators != {1:self.denominator} or weights:
            raise ValueError("original whole-update CE denominator changed")
        if self.weight==0:
            return sums[1]/self.denominator
        return alm.normalized_loss(sums[1],self.denominator,sums["kl"],self.chunks,weight=self.weight)


def gradient_stats(torch,left,right):
    # A physical parameter is a coordinate once; None is an explicit zero.
    if set(left) != set(right):raise ValueError("same gradient coordinates required")
    a=sum(float(v.double().square().sum()) for v in left.values())
    b=sum(float(v.double().square().sum()) for v in right.values())
    dot=sum(float((left[k].double()*right[k].double()).sum()) for k in left)
    if not all(math.isfinite(v) for v in (a,b,dot)):
        raise FloatingPointError("nonfinite task gradient")
    return dict(ce_norm=math.sqrt(a),kd_norm=math.sqrt(b),dot=dot,
                cosine=dot/math.sqrt(a*b) if a>0 and b>0 else None)


def last_block_parameters(model):
    """Layer.mlp and shared attention are references, not registered children."""
    schedule=list(model.visit_schedule())
    if not schedule:raise ValueError("actual visit schedule absent")
    index=schedule[-1]
    layer=model.layers[index]
    owners=(layer,layer.mlp[0],layer.attn_mod)
    params=[];seen=set()
    for owner in owners:
        for parameter in owner.parameters():
            if parameter.requires_grad and id(parameter) not in seen:
                seen.add(id(parameter));params.append(parameter)
    names={id(p):name for name,p in model.named_parameters()}
    if not params or any(id(p) not in names for p in params):
        raise ValueError("registered canonical last block references required")
    return index,params


def calibrate(torch,model,rows,bindings,records,guard,observer=None):
    from scripts import interactive_research_infer as ui
    from scripts import diag_p101a_padding_gpu as updater
    selected=[]
    for language in ("ko","en"):
        selected.extend([record for record in records if bindings[id(record)]["language"]==language][:64])
    groups=[selected[i:i+8] for i in range(0,128,8)]
    facade=ALMCore(bindings,1.,observer);facade.configure(groups)
    names={id(p):name for name,p in model.named_parameters()}
    last_index,params=last_block_parameters(model)
    if not params:raise ValueError("last physical transformer block absent")
    before=ui.state_fingerprint(model);rng=updater.rng_identity(torch)
    if any(p.grad is not None for p in model.parameters()):
        raise ValueError("calibration must enter with all gradients None")
    training_flags=[(name,module.training) for name,module in model.named_modules()]
    requires_grad=[(name,p.requires_grad) for name,p in model.named_parameters()]
    buffers={language:[{names[id(p)]:torch.zeros_like(p) for p in params} for _ in range(2)] for language in ("ko","en")}
    seen={language:[0,0] for language in ("ko","en")}
    none_counts={language:[Counter(),Counter()] for language in ("ko","en")}
    for micro in groups:
        guard.check("calibration micro")
        language=bindings[id(micro[0])]["language"]
        x,y,seg=facade.pad_records(micro,model._padding_pad_id,"cuda",fixed_width=1024,batch_size=8)
        with torch.autocast("cuda",dtype=torch.bfloat16):
            hidden=model(x,return_hidden=True)
            sums,counts=facade.components(model,hidden,y,seg,horizons=())
            ce=sums[1]/facade.denominator;kd=sums["kl"]/facade.chunks
        for number,loss in enumerate((ce,kd)):
            gradients=torch.autograd.grad(loss,params,retain_graph=number==0,allow_unused=True)
            for p,value in zip(params,gradients):
                if value is None:
                    none_counts[language][number][names[id(p)]]+=1
                if value is not None:
                    if not bool(torch.isfinite(value).all()):raise FloatingPointError("nonfinite split gradient")
                    buffers[language][number][names[id(p)]].add_(value.detach())
            del gradients
        seen[language][0]+=counts[1];seen[language][1]+=counts["kl"]
        del x,y,seg,hidden,sums,ce,kd,loss
    global_grad=[{name:buffers["ko"][i][name]+buffers["en"][i][name] for name in buffers["ko"][i]} for i in range(2)]
    stats=gradient_stats(torch,*global_grad)
    conditional={}
    for language in ("ko","en"):
        ce={k:v*facade.denominator/seen[language][0] for k,v in buffers[language][0].items()}
        kd={k:v*facade.chunks/seen[language][1] for k,v in buffers[language][1].items()}
        conditional[language]=dict(gradient_stats(torch,ce,kd),ce_targets=seen[language][0],kd_chunks=seen[language][1],
            normalization="LANGUAGE_OWN_CE_AND_KD_MEANS; NOT_GLOBAL_CONTRIBUTION")
    if stats["ce_norm"]<=0 or stats["kd_norm"]<=0:
        raise ValueError("zero TRAIN calibration signal; HOLD rather than inflate weight")
    weight=RHO*stats["ce_norm"]/stats["kd_norm"]
    if not math.isfinite(weight) or weight<=0:raise ValueError("unusable frozen lambda")
    model.clear_quant()
    if (before!=ui.state_fingerprint(model) or rng!=updater.rng_identity(torch)
            or any(p.grad is not None for p in model.parameters())
            or training_flags!=[(name,module.training) for name,module in model.named_modules()]
            or requires_grad!=[(name,p.requires_grad) for name,p in model.named_parameters()]):
        raise ValueError("gradient-only calibration changed core or RNG")
    calibrated=[dict(chunk_observation(v["student_nll_sum"],v["teacher_raw_logprob_sum"],
        facade.denominator,facade.chunks,weight,targets=v["student_targets"],
        byte_count=v["byte_count"],language=v["language"],teacher_targets=v["teacher_targets"]),row_id=v["row_id"],
        student_shifted_indices=v["student_shifted_indices"]) for v in facade.observations]
    if observer is not None:
        observer(dict(event="calibrated_fixed_weight_observations",observations=calibrated))
    return dict(status="ALM_GRADIENT_CALIBRATED",weight=weight,rho=RHO,temperature=TEMPERATURE,
        gradient_scope="UNIQUE_TRAINABLE_PARAMETERS_OF_LAST_ACTUAL_TRANSFORMER_BLOCK",
        parameter_names=[names[id(p)] for p in params],parameter_names_sha256=sha([names[id(p)] for p in params]),
        global_stats=stats,by_language=conditional,ce_targets=facade.denominator,kd_chunks=facade.chunks,
        global_normalization="ONE_128_ROW_WHOLE_UPDATE_CE_N_AND_KD_K",
        calibrated_signal_summary=signal_summary(calibrated),
        coverage=coverage_summary(facade.events),
        gradient_statistics_dtype="FP64_ON_GRADIENT_DEVICE; FP32_GRADIENT_INPUTS",
        last_actual_layer_index=last_index,
        none_counts={lang:[dict(values) for values in lanes] for lang,lanes in none_counts.items()},
        none_statistics_policy="None is zero only for norm coordinates; counts retained, no .grad assignment",
        row_ids=[bindings[id(r)]["row_id"] for r in selected],micro_events=facade.events,
        core_before=before,core_after=before,rng_unchanged=True,optimizer_updates=0,
        algorithm="TRAIN_ONLY_ONE_OFF_NORM_CALIBRATION_NOT_PAPER_GRADMAG")


def optimizers(model):
    from scripts.diag_p101a_sft_mtp import optimizers as existing
    adam,muon=existing(model)
    for optimizer in (adam,muon):
        for group in optimizer.param_groups:
            group["lr"]*=.1
            group["weight_decay"]=0.
    ids=[id(p) for opt in (adam,muon) for g in opt.param_groups for p in g["params"]]
    if len(ids)!=len(set(ids)) or set(ids)!={id(p) for p in model.parameters() if p.requires_grad}:
        raise ValueError("unique whole trainable optimizer ownership required")
    if getattr(muon,"scale_mode",None)!="rms":raise ValueError("original RMS4 Muon required")
    return (adam,muon)


def optimizer_receipt(model,opts):
    names={id(p):name for name,p in model.named_parameters()}
    return [dict(kind=type(opt).__name__,group=index,names=[names[id(p)] for p in g["params"]],
        names_sha256=sha([names[id(p)] for p in g["params"]]),
        parameters=len(g["params"]),elements=sum(p.numel() for p in g["params"]),
        hyperparameters=json.loads(canonical({key:g.get(key,getattr(opt,key,None)) for key in
            sorted((set(g)-{"params"}) | {"lr","weight_decay","betas","eps","momentum",
                                         "nesterov","ns_steps","scale_mode"})})))
        for opt in opts for index,g in enumerate(opt.param_groups)]


def checkpoint_path(arm,context=None):
    if arm not in ARMS:raise ValueError("fixed study arm required")
    context=resolve_context(context)
    return context.root/"runs/ckpt"/("m100s10_ko-en_"+context.profile.tag+"_"+arm+".pt")


def do_train(torch,model,prepared,rows,arm,calibration,guard,journal,*,cost=False,
             phase=None,observer=None,expected_rng=None,expected_optimizer_groups=None,context=None):
    context=validate_prepared_profile(prepared,context);profile=context.profile
    from scripts import diag_p101a_padding_gpu as updater
    from scripts.diag_p101a_sft_mtp import batches
    from scripts import interactive_research_infer as ui
    if phase is None or phase["mode"]!=("cost" if cost else "train") or phase["arm"]!=arm:
        raise ValueError("exact phase identity required before training")
    if profile!=LEGACY_PROFILE and (
            any(calibration.get(k)!=v for k,v in profile_fields(context).items())
            or any((phase.get("calibration_pin") or {}).get(k)!=v for k,v in profile_fields(context).items())
            or phase.get("parent_core_sha256")!=prepared["parent_entry"]["core_sha256"]
            or phase.get("study_identity_sha256")!=sha(calibration.get("study_identity"))
            or phase["calibration_pin"].get("weight")!=calibration.get("weight")
            or phase["calibration_pin"].get("phase_identity_sha256")!=calibration.get("phase_identity_sha256")):
        raise ValueError("own profile/parent TRAIN calibration required before updates")
    records,bindings=records_for(rows)
    facade=ALMCore(bindings,calibration["weight"] if arm=="alm" else 0.,observer)
    opts=optimizers(model);initial=ui.state_fingerprint(model)
    initial_rng=updater.rng_identity(torch)
    if (initial!=prepared["parent_entry"]["core_sha256"]
            or any(p.grad is not None for p in model.parameters()) or any(opt.state for opt in opts)):
        raise ValueError("fresh same-parent core/None gradients/empty optimizer state required")
    if expected_rng is not None and initial_rng!=expected_rng:
        raise ValueError("cost and training initial RNG differ")
    optimizer_groups=optimizer_receipt(model,opts)
    if expected_optimizer_groups is not None and optimizer_groups!=expected_optimizer_groups:
        raise ValueError("cost and training optimizer ownership/hyperparameters differ")
    receipt=[];updates=0
    for epoch in range(1 if cost else 4):
        for groups in batches(records,epoch):
            if cost and updates==2:break
            plan=updater.update_plan(groups);facade.configure(groups)
            if observer is not None:
                facade.observer=lambda event,u=updates,e=epoch:observer(dict(update=u,epoch=e,**event))
            value,_=updater.one_update(torch,facade,model,opts,groups,plan,"fixed1024","bf16_eager",
                                      guard,journal,arm,updates,"cost" if cost else "train")
            if facade.queue or sum(r["kd_chunks"] for r in facade.events)!=facade.chunks:
                raise ValueError("all sixteen actual micros/KD chunks must close")
            kl=sum(r["kl_sum"] for r in facade.events)/facade.chunks if facade.weight else None
            value.update(epoch=epoch,weight=facade.weight,kd_chunks=facade.chunks,
                         kl=kl,kl_status="COMPUTED" if facade.weight else "NOT_COMPUTED_CE_ONLY",
                         objective=value["loss"]+facade.weight*kl if kl is not None else value["loss"],
                         signal_summary=signal_summary(facade.observations),
                         coverage=coverage_summary(facade.events),
                         micro_objective_events=facade.events,
                         row_ids=[bindings[id(r)]["row_id"] for micro in groups for r in micro])
            receipt.append(value);updates+=1
            print("[ALM_UPDATE] "+json.dumps({k:value[k] for k in ("update","epoch","loss","kl","weight","whole_update_seconds")}),flush=True)
    expected=2 if cost else 32
    if updates!=expected:raise ValueError("complete original update count required")
    result=dict(status="ALM_COST_COMPLETE" if cost else "ALM_TRAIN_COMPLETE",arm=arm,updates=updates,
        initial_core_sha256=initial,final_core_sha256=ui.state_fingerprint(model),weight=facade.weight,
        initial_rng=initial_rng,initial_optimizer_state_empty=True,initial_gradients_all_none=True,
        history=receipt,optimizer_updates=updates,checkpoint_writes=0,optimizer_saved=False,
        actual_x_tokens=sum(r["actual_x_tokens"] for r in receipt),
        ce_targets=sum(r["assistant_targets"] for r in receipt),kd_chunks=sum(r["kd_chunks"] for r in receipt),
        training_seconds=sum(r["whole_update_seconds"] for r in receipt),precision="BF16_EAGER_TF32_OFF",
        optimizer_groups=optimizer_groups,optimizer_groups_after=optimizer_receipt(model,opts),
        **(dict(quantization_route=prepared["quantization_route"]) if profile!=LEGACY_PROFILE else {}),
        **profile_fields(context))
    if result["optimizer_groups_after"]!=optimizer_groups:
        raise ValueError("optimizer group ownership/hyperparameters changed")
    if not cost:
        guard.check("before weight-only checkpoint")
        exposure=prepared["whole_exposure"]
        if result["actual_x_tokens"]!=exposure["actual_x_tokens"] or result["ce_targets"]!=exposure["ce_targets"] or result["kd_chunks"]!=exposure["kd_chunks"]:
            raise ValueError("complete same four-epoch exposure differs")
        from dataclasses import asdict
        path=checkpoint_path(arm,context)
        experiment=dict(schema=profile.schema,tag=profile.tag,arm=arm,parent=prepared["parent_entry"]["checkpoint"],
            phase_identity=phase,phase_identity_sha256=sha(phase),
            study_identity_sha256=phase["study_identity_sha256"],
            preparation_sha256=phase["preparation_sha256"],
            source_code_sha256=sources(context),weight=facade.weight,temperature=TEMPERATURE,rho=RHO,
            optimizer_groups=optimizer_groups,
            **(dict(quantization_route_sha256=sha(prepared["quantization_route"])) if profile!=LEGACY_PROFILE else {}),
            **profile_fields(context))
        payload=dict(model={k:v.detach().cpu() for k,v in model.state_dict().items()},cfg=asdict(model.cfg),step=32,
            tokenizer_sha256=prepared["tokenizer"]["sha256"],tokenizer_lineage="chat32",
            quantization_route=prepared["parent_entry"]["header"]["quantization_route"],
            experiment=experiment)
        with path.open("xb") as stream:torch.save(payload,stream)
        result.update(checkpoint=str(path.relative_to(context.root)),checkpoint_sha256=digest(path),checkpoint_writes=1,
                      checkpoint_experiment=experiment)
    return result


def evaluate(torch,model,tok,route,prepared,guard,directory,context=None):
    context=validate_prepared_profile(prepared,context)
    from tinylm.train import mtp_sft as core
    from scripts import interactive_research_infer as ui
    from scripts.diag_p101a_sft_mtp import evaluate as original_evaluate
    from scripts.p106b_shards import ShardWriter
    before=ui.state_fingerprint(model)
    budget=evaluation_admission(prepared,tok,model.cfg.max_seq_len)
    if budget!=prepared["evaluation_admission"]:
        raise ValueError("same fixed evaluation length admission required")
    guard.check("before full DEV TF")
    val=[core.encode_record(r,tok) for r in prepared["val_rows"]]
    dev=original_evaluate(model,val,model._padding_pad_id)
    model.clear_quant();model.eval()
    with torch.no_grad():model.freeze_quant()
    active=dict(torch=torch,model=model,cfg=model.cfg,tokenizer=tok,route=route,root=str(context.root))
    writer=ShardWriter(directory,"answers",limit=LIMIT);events=[];manifest=None
    try:
        for index,row in enumerate(prepared["evaluation_rows"]):
            guard.check("fixed DEV first answer")
            question=row["messages"][0]["content"]
            if not isinstance(question,str):
                from scripts.diag_p106b_alm_cache import message_text
                question=message_text(row["messages"][0])
            answer,meta=ui.emit(active,question,max_new=MAX_NEW)
            generation_admission(meta,budget["cases"][index])
            expected=[a["text"] for a in row["meta"]["answers"]]
            event=dict(index=index,kind="OLD_DEV",language=row["meta"]["language"],source_row=row,
                question=question,answer=answer,expected_original_annotations=expected,generation=meta,
                length_admission=budget["cases"][index],**grade(answer,expected))
            writer.append(event);events.append(event)
        for index,question in enumerate(USER_QUESTIONS):
            guard.check("fixed user first answer")
            answer,meta=ui.emit(active,question,max_new=MAX_NEW)
            generation_admission(meta,budget["cases"][64+index])
            event=dict(index=index,kind="USER_OBSERVATION_NOT_SCORED",question=question,answer=answer,generation=meta,
                       length_admission=budget["cases"][64+index])
            writer.append(event);events.append(event)
        manifest=writer.close(lineage=dict(schema=context.profile.schema,source="FIXED_OLD_DEV_AND_USER_FIRST_ANSWERS",
                                          complete=True,training_admission="EVALUATION_ONLY"))
    finally:
        if manifest is None:
            if writer._total_rows:
                writer.close(lineage=dict(schema=context.profile.schema,complete=False,training_admission="EVALUATION_ONLY"))
            else:
                writer._finish()
    model.clear_quant();model.train()
    from scripts.diag_p106b_native_weight_route import native_probe
    guard.check("before fixed native32")
    native=native_probe(torch,model)
    model.clear_quant()
    if before!=ui.state_fingerprint(model):raise ValueError("evaluation changed trained core")
    return dict(status="ALM_EVALUATION_COMPLETE",dev_tf=dev,
        first_answers=64,user_observations=8,answer_manifest=manifest,
        exact_original=sum(r.get("exact_original",False) for r in events),
        strict_whitespace_exact=sum(r.get("strict_whitespace_exact",False) for r in events),
        whitespace_normalized_exact=sum(r.get("whitespace_normalized_exact",False) for r in events),
        by_language={lang:dict(rows=32,exact_original=sum(e.get("exact_original",False) for e in events if e.get("language")==lang),
            strict_whitespace_exact=sum(e.get("strict_whitespace_exact",False) for e in events if e.get("language")==lang),
            whitespace_normalized_exact=sum(e.get("whitespace_normalized_exact",False) for e in events if e.get("language")==lang)) for lang in ("ko","en")},
        evaluation_admission=budget,long_reference_cases=budget["long_reference_cases"],
        unknown_reference_length_cases=budget["unknown_reference_length_cases"],
        native32=native,core_before=before,core_after=before,
        claims="OLD_DEV_STRING_DIAGNOSTIC_NOT_FRESH_TEST_NOT_GENERAL_DIALOGUE_SCORE")


def execute(args,context=None):
    context=resolve_context(context if context is not None else study_context(getattr(args,"study","float_v1")))
    if getattr(args,"study",context.profile.name)!=context.profile.name:
        raise ValueError("CLI study and explicit context differ")
    profile=context.profile
    began=time.perf_counter()
    admission=authority(args.max_wall_sec)
    from scripts import diag_p101a_padding_gpu as updater
    from scripts.p106b_gate_runtime import wall_limit
    from scripts.p106b_shards import ShardWriter
    guard=updater.Guard(DEADLINE,args.max_wall_sec);guard.started=began
    key=args.mode+("_"+args.arm if args.arm else "")
    directory=context.evidence/key
    if directory.exists() or directory.is_symlink():raise FileExistsError("preserve prior phase")
    if args.mode=="train" and checkpoint_path(args.arm,context).exists():raise FileExistsError("preserve prior checkpoint")
    result=dict(schema=profile.schema,tag=profile.tag,mode=args.mode,arm=args.arm,admission=admission,
        status="PARTIAL_NOT_COMPLETE",returncode=9,checkpoint_writes=0,
        inputs_unchanged=False,sources_unchanged=False,parent_checkpoint_unchanged=False,**profile_fields(context))
    journal=observations=None
    owned_directory=False
    current=prepared=pins=None
    torch=model=tok=route=None
    try:
        with wall_limit(args.max_wall_sec):
            guard.check("before phase source hashes")
            current=sources(context)
            if args.source_sha256!=sha(current):raise ValueError("explicit current source SHA required")
            directory.mkdir(parents=True,exist_ok=False)
            owned_directory=True
            journal=updater.Journal(directory/"events.jsonl")
            result["source_code_sha256"]=current
            prepared,rows,preparation_sha=load_prepared(context)
            common=study_identity(prepared,preparation_sha,current,context)
            if profile!=LEGACY_PROFILE:result["quantization_route"]=prepared["quantization_route"]
            extra={}
            def prerequisite(path):
                guard.check("phase prerequisite")
                report,identity=closed_read(path)
                extra[str(path.relative_to(context.root))]=identity
                if report.get("observation_manifest"):
                    extra.update(manifest_pins(path.parent,report["observation_manifest"],context))
                return report,identity
            calibration=pin=None
            if args.mode in ("cost","train") or args.mode=="evaluate" and args.arm!="parent":
                cal_path=context.evidence/"calibrate/report.json"
                calibration,cal_sha=prerequisite(cal_path)
                pin=calibration_pin(calibration,common,str(cal_path.relative_to(context.root)),cal_sha,context)
            phase=phase_identity(common,args.mode,args.arm,pin)
            result.update(preparation_sha256=preparation_sha,study_identity=common,
                          phase_identity=phase,phase_identity_sha256=sha(phase))
            expected_rng=expected_optimizer_groups=None
            if args.mode=="train":
                costs=[]
                for arm in ARMS:
                    cost,_=prerequisite(context.evidence/("cost_"+arm)/"report.json")
                    validate_cost(cost,common,arm,pin,context);costs.append(cost)
                if costs[0]["initial_rng"]!=costs[1]["initial_rng"]:
                    raise ValueError("both cost arms must start from the same RNG")
                if costs[0]["optimizer_groups"]!=costs[1]["optimizer_groups"]:
                    raise ValueError("both cost arms must use identical optimizer ownership/hyperparameters")
                expected_rng=costs[0]["initial_rng"]
                expected_optimizer_groups=costs[0]["optimizer_groups"]
                overhead=sum(max(0.,r["wall_seconds"]-r["training_seconds"]) for r in costs)
                estimate=sum(32*(r["training_seconds"]/2)*1.5 for r in costs)+overhead+3*300
                result["cost_admission_estimate"]=dict(seconds=estimate,
                    observed_non_update_overhead_seconds=overhead,evaluation_reserve_seconds=3*300,
                    scope="TWO_TRAIN_ARMS_PLUS_THREE_EVALUATIONS; RESERVE_IS_NOT_A_MEASUREMENT")
                if estimate>(DEADLINE-datetime.now(timezone.utc)).total_seconds():
                    raise ValueError("both arms and three evaluations do not fit conservative remaining budget")
            cp=expected=experiment=cp_sha=None
            if args.mode=="evaluate" and args.arm!="parent":
                receipt,_=prerequisite(context.evidence/("train_"+args.arm)/"report.json")
                validate_training(receipt,common,args.arm,pin,context)
                cp=checkpoint_path(args.arm,context);expected=receipt["final_core_sha256"]
                experiment=receipt["checkpoint_experiment"]
                cp_sha=receipt["checkpoint_sha256"]
                extra[str(cp.relative_to(context.root))]=cp_sha
            pins=phase_input_pins(prepared,preparation_sha,extra,context)
            tick=time.perf_counter();result["inputs_before"]=verify_pins(pins,guard,context)
            result["input_hash_before_seconds"]=time.perf_counter()-tick
            if args.mode!="evaluate":
                observations=ShardWriter(directory,"objective_observations",limit=LIMIT)
            def observer(event):
                if observations is not None:
                    observations.append(dict(mode=args.mode,arm=args.arm,
                        phase_identity_sha256=sha(phase),**event))
            with runtime(prepared,guard,cp,expected,experiment,cp_sha,context=context) as (torch,model,tok,route):
                guard.check("model loaded")
                if args.mode=="calibrate":
                    records,bindings=records_for(rows)
                    result.update(calibrate(torch,model,rows,bindings,records,guard,observer))
                elif args.mode in ("cost","train"):
                    result.update(do_train(torch,model,prepared,rows,args.arm,calibration,guard,journal,
                        cost=args.mode=="cost",phase=phase,observer=observer,expected_rng=expected_rng,
                        expected_optimizer_groups=expected_optimizer_groups,context=context))
                else:result.update(evaluate(torch,model,tok,route,prepared,guard,directory,context))
            # Drop caller-owned references too, before potentially long CPU end hashes.
            model=tok=route=None
            gc.collect()
            if torch is not None:torch.cuda.empty_cache()
            if observations is not None:
                closing=observations;observations=None
                result["observation_manifest"]=closing.close(lineage=dict(schema=profile.schema,
                    phase_identity_sha256=sha(phase),complete=True,scope="DETACHED_DIAGNOSTICS_ONLY"))
            guard.check("before final input hashes")
            tick=time.perf_counter();result["inputs_after"]=verify_pins(pins,guard,context)
            result["input_hash_after_seconds"]=time.perf_counter()-tick
            if result["inputs_after"]!=result["inputs_before"]:raise ValueError("study inputs changed")
            if sources(context)!=current:raise ValueError("study sources changed during execution")
            guard.check("phase close")
            result.update(returncode=0,sources_unchanged=True,inputs_unchanged=True,parent_checkpoint_unchanged=True)
    except BaseException as exc:
        result.update(status="PARTIAL_NOT_COMPLETE",returncode=9,error_type=type(exc).__name__,error=str(exc))
        if isinstance(exc,(KeyboardInterrupt,SystemExit)):result["interrupted"]=True
    finally:
        model=tok=route=None
        if observations is not None:
            try:
                if observations._total_rows:
                    result["partial_observation_manifest"]=observations.close(lineage=dict(schema=profile.schema,complete=False))
                else:observations._finish()
            except BaseException as exc:
                result.update(status="PARTIAL_NOT_COMPLETE",returncode=9,observation_close_error=repr(exc))
        if journal is not None:
            try:journal.close()
            except BaseException as exc:
                result.update(status="PARTIAL_NOT_COMPLETE",returncode=9,journal_close_error=repr(exc))
        result["wall_seconds"]=time.perf_counter()-began
        result["wall_scope"]="FROM_PHASE_ENTRY_INCLUDING_SOURCE_PREPARATION_LOAD_HASHES_AND_CLEANUP; BEFORE_FINAL_REPORT_WRITE"
        if owned_directory:write_new(directory/"report.json",result)
    print("[ALM_PHASE] "+json.dumps({k:result.get(k) for k in ("mode","arm","status","returncode","wall_seconds","error_type","error")},ensure_ascii=False),flush=True)
    return result["returncode"]


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study",choices=tuple(p.name for p in STUDY_PROFILES),default="float_v1")
    parser.add_argument("--prepare",action="store_true")
    parser.add_argument("--execute",action="store_true")
    parser.add_argument("--mode",choices=("calibrate","cost","train","evaluate"))
    parser.add_argument("--arm",choices=ARMS+("parent",))
    parser.add_argument("--source-sha256")
    parser.add_argument("--max-wall-sec",type=int,default=600)
    args=parser.parse_args(argv)
    context=study_context(args.study)
    if args.prepare and (args.execute or args.mode or args.arm):parser.error("prepare is CPU-only and separate")
    if args.execute and (not args.mode or not args.source_sha256):parser.error("explicit phase/source required")
    if args.execute and ((args.mode=="calibrate" and args.arm) or (args.mode in ("cost","train") and args.arm not in ARMS) or (args.mode=="evaluate" and not args.arm)):
        parser.error("registered phase/arm required")
    if not args.execute and not args.prepare and (args.mode or args.arm or args.source_sha256):parser.error("model flags require execute")
    try:
        if args.prepare:
            report=prepare(args.max_wall_sec,context);print(json.dumps({k:report[k] for k in ("status","rows","whole_exposure")},ensure_ascii=False));return 0
        if args.execute:return execute(args,context)
        current=sources(context);print(json.dumps(dict(schema=context.profile.schema,tag=context.profile.tag,
            source_code_sha256=current,source_sha256=sha(current),model_loads=0,gpu_calls=0,
            **profile_fields(context)),ensure_ascii=False));return 0
    except (ValueError,FileNotFoundError,FileExistsError) as exc:
        print("[ALM_PRECONDITION] "+str(exc),file=sys.stderr);return 9


if __name__=="__main__":raise SystemExit(main())
