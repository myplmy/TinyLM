#!/usr/bin/env python3
"""공식 lambada_openai/default의 독립 제어기. 기존 모델/평가 소스는 수정하지 않는다.

체크 전용 호출은 표준 라이브러리와 소스 metadata만 읽는다. 자료 준비와 실제 모델은
root의 명시 --execute에 한정한다. 다운로드·설치·학습·생성은 구현하지 않는다.
"""
from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import sysconfig
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_babylm_window as control

TAG = "p106b_lambada_default_v2_s1337"
SCHEMA = "P106B_LAMBADA_DEFAULT_V2"
TASK = "lambada_openai"
ROWS = 5153
REVISION = "900124bf3b8235c6daf21033af9948b3f07346c4"
DATA_SHA = "99D8A9E54CDA761C6340DDD4FA6FEDA7F846FFB0E716AFA52968DEA75495EEA7"
DATA_BYTES = 1_157_764
DATA_REL = f"HF/datasets--EleutherAI--lambada_openai/snapshots/{REVISION}/en/test/en.parquet"
HARNESS_COMMIT = "d6de81643928d653435c431bae19945d41d32520"
SOURCE_REL = f"data_cache/p106b_official_eval_tools/lm_eval_{HARNESS_COMMIT}/source"
YAML_REL = SOURCE_REL + "/lm_eval/tasks/lambada/lambada_openai.yaml"
YAML_SHA = "96DEE2FE378666B6B5411958A25AD5C83F5B43EB6B3C830F4B0FD485F9ADB6A5"
REMOTE_API = f"https://huggingface.co/api/datasets/EleutherAI/lambada_openai/tree/{REVISION}/default/test?recursive=false"
OUTPUT = ROOT / "test_result/evidence" / TAG
CACHE = OUTPUT / "runtime_cache"
HF_MODELS = ("qwen06", "gemma270", "gemma1b")
MODELS = ("native595-f", "native595-q", "new595-broad-f", "falcon90m", *HF_MODELS)
DEFINITION_FILES = ("lm_eval/api/task.py", "lm_eval/api/metrics.py", "lm_eval/tasks/_yaml_loader.py")
OWN_FILES = ("scripts/diag_p106b_lambada_default.py", "scripts/test_p106b_lambada_default.py", YAML_REL,
             *(SOURCE_REL + "/" + name for name in DEFINITION_FILES))
PROMPT = "{{text.split(' ')[:-1]|join(' ')}}"
TARGET = "{{' '+text.split(' ')[-1]}}"


def identity():
    files = dict(control.identity()["files"])
    files.update({name: control.original.digest(ROOT / name) for name in OWN_FILES})
    return dict(files=files, sha256=control.original.object_sha(files))


def policy(model=None):
    if model is not None and model not in MODELS:
        raise ValueError("사전등록한 모델만 허용한다")
    return dict(task=TASK, official_config="default", output_type="loglikelihood", full_rows=ROWS,
        num_fewshot=0, chat_template=False, max_context=1024, batch_size=1 if model in HF_MODELS else 8,
        precision="FP32_MATH_OR_NATIVE_EAGER_TF32_OFF", cache=False, generation=False, training=False,
        target="PINNED_LAST_SPACE_DELIMITED_WORD_WITH_LEADING_SPACE_ALL_SUBWORDS",
        metrics=["acc", "perplexity"], normalization="WHOLE_CONTINUATION_SUM_LOGPROB",
        context_truncation="LEFT_ONLY_FULL_TARGET_RETAINED_RECORDED", retries=0,
        model_comparison="EXTERNAL_PRETRAINING_AND_TOKENIZERS_NOT_MATCHED")


def alias_contract(metadata):
    if (metadata.get("bytes") != DATA_BYTES or metadata.get("sha256", "").upper() != DATA_SHA
            or metadata.get("rows") != ROWS or metadata.get("columns") != ["text"]):
        raise ValueError("정확한 LAMBADA 영어 byte/SHA/5153행/text schema가 필요하다")
    return dict(repo_id="EleutherAI/lambada_openai", revision=REVISION, official_config="default",
        remote_api_url=REMOTE_API, remote_path="default/test/default.parquet", remote_bytes=DATA_BYTES,
        remote_lfs_sha256=DATA_SHA, local_relative_path=DATA_REL, local_bytes=metadata["bytes"],
        local_sha256=metadata["sha256"].upper(), rows=metadata["rows"], columns=metadata["columns"],
        byte_identical_alias=True, same_row_count_is_not_identity_proof=True,
        remote_metadata_provenance="ROOT_OBSERVED_OFFICIAL_IMMUTABLE_HF_API_RESPONSE_IN_STAGE8N_PREREGISTRATION",
        remote_request_in_this_driver=False, original_file_modified=False)


def asset_proof(root=ROOT):
    import pyarrow.parquet as pq
    path = Path(root) / DATA_REL
    sha = control.original.digest(path)
    metadata = pq.ParquetFile(path)
    proof = alias_contract(dict(bytes=path.stat().st_size, sha256=sha,
        rows=metadata.metadata.num_rows, columns=metadata.schema.names))
    if control.original.digest(Path(root) / YAML_REL) != YAML_SHA:
        raise ValueError("고정 공식 default YAML이 변경됐다")
    return proof


def validate_config(task_yaml):
    expected = dict(task=TASK, dataset_path="EleutherAI/lambada_openai", dataset_name="default",
                    output_type="loglikelihood", test_split="test", doc_to_text=PROMPT, doc_to_target=TARGET)
    if any(task_yaml.get(k) != v for k, v in expected.items()):
        raise ValueError("공식 default task/분할/prompt/target 계약이 다르다")
    metrics = task_yaml.get("metric_list", ())
    if metrics != [dict(metric="perplexity", aggregation="perplexity", higher_is_better=False),
                   dict(metric="acc", aggregation="mean", higher_is_better=True)]:
        raise ValueError("공식 LAMBADA metric/집계를 변경하지 않는다")
    return {k: copy.deepcopy(task_yaml[k]) for k in ("task", "output_type", "doc_to_text", "doc_to_target", "metric_list")}


def verify_definition_sources(source_root, runtime_root, archive_path, archive_sha, commit, names):
    """공식 archive 원형, 보존 source, 설치본의 정의 파일만 좁게 대조한다."""
    if control.original.digest(archive_path) != archive_sha:
        raise ValueError("공식 harness archive SHA가 다르다")
    result = {}
    with tarfile.open(archive_path, "r:gz") as archive:
        for name in names:
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError("공식 정의 상대경로가 필요하다")
            member = archive.getmember(f"lm-evaluation-harness-{commit}/" + name)
            if not member.isfile() or member.size > 2_000_000:
                raise ValueError("공식 정의는 2MB 이하 정규 파일이어야 한다")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("공식 archive 정의 파일이 없다")
            with stream:
                body = stream.read(2_000_001)
            sha = hashlib.sha256(body).hexdigest().upper()
            if (len(body) != member.size or control.original.digest(Path(source_root) / name) != sha
                    or control.original.digest(Path(runtime_root) / name) != sha):
                raise ValueError("공식 archive/source/설치본 정의가 다르다: " + name)
            result[name] = dict(sha256=sha, source_path=str(Path(source_root) / name),
                               runtime_path=str(Path(runtime_root) / name))
    return result


def load_task():
    from scripts.prepare_p106b_official_eval import configure_hf_cache
    from scripts.p106b_official_lm_adapter import prepare_harness, ARCHIVE_SHA256
    configure_hf_cache()
    runtime_root = Path(sysconfig.get_paths()["purelib"])
    _, framework = prepare_harness(runtime_root=runtime_root)
    definitions = verify_definition_sources(ROOT / SOURCE_REL, runtime_root,
        (ROOT / SOURCE_REL).parent / "official_source.tar.gz", ARCHIVE_SHA256, HARNESS_COMMIT, DEFINITION_FILES)
    from lm_eval.tasks._yaml_loader import load_yaml
    from lm_eval.api.task import ConfigurableTask
    for name, item in definitions.items():
        module = sys.modules[name[:-3].replace("/", ".")]
        actual = Path(module.__file__).absolute()
        if actual != Path(item["runtime_path"]).absolute() or control.original.digest(actual) != item["sha256"]:
            raise ValueError("실제 import한 공식 정의 경로/SHA가 다르다: " + name)
    task_yaml = load_yaml(str(ROOT / YAML_REL), resolve_func=True, recursive=True)
    before = validate_config(task_yaml)
    task_yaml.update(dataset_path="parquet", dataset_name=None,
        dataset_kwargs=dict(data_files={"test": str(ROOT / DATA_REL)}, cache_dir=str(CACHE)),
        training_split=None, validation_split=None, test_split="test", fewshot_split=None,
        num_fewshot=0, fewshot_config=dict(samples=[]))
    task = ConfigurableTask(config=task_yaml)
    if set(task.dataset) != {"test"} or len(task.eval_docs) != ROWS or task.eval_docs.column_names != ["text"]:
        raise ValueError("공식 영어 test 전체5153행/schema가 필요하다")
    for key, value in before.items():
        if getattr(task.config, key) != value:
            raise ValueError("원 공식 prompt/target/metric이 task 생성 중 변경됐다: " + key)
    ordered = hashlib.sha256()
    for row in task.eval_docs:
        if set(row) != {"text"} or not isinstance(row["text"], str) or not row["text"]:
            raise ValueError("누락/빈 원문은 건너뛰지 않는다")
        ordered.update((json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode())
    return task, dict(task=TASK, rows=ROWS, columns=["text"], ordered_row_json_sha256=ordered.hexdigest().upper(),
        official_yaml_sha256=YAML_SHA, official_config="default", storage_override_only=True,
        task_fields_preserved=before, framework_provenance=framework, official_definition_sources=definitions)


def request_for(task, doc, index):
    context = task.fewshot_context(doc, num_fewshot=0, apply_chat_template=False,
                                 fewshot_as_multiturn=False, system_instruction=None)
    request = task.construct_requests(doc=doc, ctx=context,
        metadata=(TASK, index, task.config.repeats), apply_chat_template=False)
    requests = request if isinstance(request, list) else [request]
    if (len(requests) != 1 or requests[0].request_type != "loglikelihood"
            or tuple(requests[0].args) != (task.doc_to_text(doc), task.doc_to_target(doc))
            or any(not isinstance(s, str) for s in requests[0].args) or not requests[0].args[1]):
        raise ValueError("공식 context/전체 단어 target의 단일 likelihood 요청이 필요하다")
    return requests[0]


def token_plan(lm, request):
    from scripts.p106b_official_lm_adapter import plan_tokens
    context, continuation = request.args
    if context:
        ctx, cont = lm._encode_pair(context, continuation)
    else:
        cont = lm.tok_encode(continuation, add_special_tokens=False)
        if not cont:
            raise ValueError("빈 context의 target도 비어 있을 수 없다")
        ctx, cont = ([lm.prefix_token_id], cont) if cont[0] != lm.prefix_token_id else (cont[:1], cont[1:])
    vocab = lm.core.vocab_size if hasattr(lm, "core") else lm.model.config.vocab_size
    plan = plan_tokens(ctx, cont, vocab, 1024)
    return dict(original_context_tokens=plan.original_context_tokens, kept_context_tokens=plan.kept_context_tokens,
        truncated_context_tokens=plan.truncated_context_tokens, continuation_tokens=len(plan.continuation_ids),
        input_tokens=len(plan.input_ids), target_start=plan.target_start)


def valid_response(response):
    if (not isinstance(response, (list, tuple)) or len(response) != 2 or type(response[1]) is not bool
            or type(response[0]) not in (int, float) or not math.isfinite(response[0]) or response[0] > 0):
        raise ValueError("전체 target의 유한 logprob와 실제 greedy bool이 필요하다")
    return float(response[0]), response[1]


def independent_metrics(responses):
    values = [valid_response(r) for r in responses]
    if not values:
        raise ValueError("0행으로 metric을 만들지 않는다")
    return dict(acc=math.fsum(int(r[1]) for r in values) / len(values),
                perplexity=math.exp(-math.fsum(r[0] for r in values) / len(values)))


def aggregate(task, records):
    methods = task.aggregation()
    if set(methods) != {"acc", "perplexity"}:
        raise ValueError("공식 두 metric만 사용한다")
    official = {key: methods[key]([row["official_metrics"][key] for row in records]) for key in methods}
    expected = independent_metrics([row["response"] for row in records])
    if any(not math.isfinite(float(official[k])) or not math.isclose(official[k], expected[k], rel_tol=1e-10, abs_tol=1e-12) for k in expected):
        raise ValueError("공식 acc/perplexity와 독립 재계수가 다르다")
    return official


def record_for(task, doc, index, request, response, plan):
    ll, greedy = valid_response(response)
    metrics = task.process_results(doc, [(ll, greedy)])
    if metrics != dict(perplexity=ll, acc=int(greedy)):
        raise ValueError("공식 문항 metric과 전체 target 결과가 다르다")
    return dict(doc_id=index, doc=doc, arguments=list(request.args), response=[ll, greedy],
                official_metrics=metrics, token_plan=plan)


def recount_raw(task, directory, manifest, expected):
    from scripts.p106b_shards import verify
    verify(Path(directory), manifest)
    records = []
    for shard in manifest["shards"]:
        with (Path(directory) / shard["path"]).open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                index = len(records)
                if index >= expected or row.get("doc_id") != index or row.get("doc") != task.eval_docs[index]:
                    raise ValueError("저장 원문/5153행 순서가 다르다")
                request = request_for(task, task.eval_docs[index], index)
                if row.get("arguments") != list(request.args):
                    raise ValueError("원문으로 재구성한 공식 prompt/target과 원형이 다르다")
                response = valid_response(row.get("response"))
                if row.get("official_metrics") != task.process_results(row["doc"], [response]):
                    raise ValueError("원형의 문항 metric이 다르다")
                plan = row.get("token_plan", {})
                required = ("original_context_tokens", "kept_context_tokens", "truncated_context_tokens",
                            "continuation_tokens", "input_tokens", "target_start")
                if (set(plan) != set(required) or any(type(plan[k]) is not int or plan[k] < 0 for k in required)
                        or not 1 <= plan["continuation_tokens"] <= 1024 or not 1 <= plan["input_tokens"] <= 1024
                        or plan["kept_context_tokens"] < 1 or plan["target_start"] + 1 != plan["kept_context_tokens"]
                        or plan["kept_context_tokens"] + plan["truncated_context_tokens"] != plan["original_context_tokens"]
                        or plan["target_start"] + plan["continuation_tokens"] != plan["input_tokens"]):
                    raise ValueError("문맥 왼쪽 절단/전체 target의 길이 영수증이 다르다")
                records.append(row)
    if len(records) != expected:
        raise ValueError("정확한 cost32 또는 full5153 분모가 필요하다")
    metrics = aggregate(task, records)
    return dict(rows=len(records), metrics=metrics, raw_sha_verified=True,
                context_truncated_rows=sum(row["token_plan"]["truncated_context_tokens"] > 0 for row in records),
                context_tokens_removed=sum(row["token_plan"]["truncated_context_tokens"] for row in records),
                total_continuation_tokens=sum(row["token_plan"]["continuation_tokens"] for row in records))


def full_admission(cost, signature, model, admission, canary_sha, *, now=None):
    expected = dict(schema=SCHEMA, tag=TAG, task=TASK, mode="cost", model=model, returncode=0,
        status="LAMBADA_COST_COMPLETE", source_identity=signature, policy=policy(model),
        sources_unchanged=True, inputs_unchanged=True, raw_independent_recount=True,
        actual_rows=32, canary_report_sha256=canary_sha)
    if any(cost.get(k) != v for k, v in expected.items()):
        raise ValueError("같은 source/모델/정책/canary의 새 cost32 완료가 필요하다")
    seconds, wall = cost.get("evaluation_seconds"), cost.get("wall_seconds")
    if (not control.finite(seconds, positive=True) or not control.finite(wall, positive=True)
            or wall < seconds):
        raise ValueError("양수의 실제 평가/전체 시간이 필요하다")
    overhead = max(0., wall - seconds)
    forecast = seconds * ROWS / 32 * 1.5 + overhead + 120
    now = time.time() if now is None else now
    if not control.finite(forecast, positive=True) or forecast > admission["hard_cap_seconds"] or now + forecast + 30 > admission["deadline_epoch"]:
        raise ValueError("실측 LAMBADA 전량 외삽이7200초/마감/정리예비를 넘는다")
    return dict(admission, forecast_seconds=forecast, forecast_multiplier=1.5,
                observed_non_eval_overhead_seconds=overhead, fixed_overhead_reserve_seconds=120)


@contextmanager
def model_runtime(model, torch, assets):
    if model in HF_MODELS:
        from scripts.diag_p106b_external_core6 import model_runtime as hf_runtime
        with hf_runtime(model, torch, assets) as item:
            yield item
    else:
        from scripts.diag_p106b_official_core6 import model_runtime as existing_runtime
        with existing_runtime(model, torch) as item:
            yield item


def model_identity(model, proof, assets=None):
    if model in HF_MODELS:
        return dict(model=model, initial_core_sha256=proof["initial_core_sha256"], assets=assets,
                    model_source_sha256=proof["model_source_sha256"])
    if model == "falcon90m":
        return dict(model=model, initial_core_sha256=proof["initial_core_sha256"], assets=proof["asset_sha256"],
                    model_source_sha256=proof["model_source_sha256"])
    provenance = proof["provenance"]
    return dict(model=model, checkpoint_sha256=provenance["checkpoint_sha256"],
                tokenizer_sha256=provenance["tokenizer_sha256"])


def bind_model_pins(model, proof, pins):
    """기존 strict loader가 검증한 모델/토크나이저를 실패 시에도 사후 확인한다."""
    if model == "falcon90m":
        from scripts.diag_p106b_official_core6 import FALCON
        for name, sha in proof["asset_sha256"].items():
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError("Falcon 자산 경로가 고정 폴더를 벗어난다")
            pins[str((FALCON / name).relative_to(ROOT))] = sha
    elif model not in HF_MODELS:
        from scripts.interactive_research_infer import TOKENIZER
        provenance = proof["provenance"]
        checkpoint = provenance["checkpoint"]
        if not isinstance(checkpoint, str) or Path(checkpoint).is_absolute() or ".." in Path(checkpoint).parts:
            raise ValueError("기존 strict checkpoint 상대경로가 필요하다")
        pins[checkpoint] = provenance["checkpoint_sha256"]
        pins[TOKENIZER] = provenance["tokenizer_sha256"]


def finalize(report, directory, started, signature, pins, *, identity_fn=identity,
             verify_fn=control.original.verify_pins, primary_error=None):
    """사후 검증 뒤 기존 writer에 원 평가 예외를 직접 넘긴다."""
    if report.get("returncode") != 0 or not pins:
        report["quality_claim"] = False
    errors, exit_error = [], None
    for name, action in (("inputs_unchanged", lambda: verify_fn(pins)),
                         ("sources_unchanged", lambda: identity_fn() == signature)):
        try:
            if name == "inputs_unchanged" and not pins:
                raise ValueError("입력 pin 검증이 완결되지 않았다")
            if action() is False:
                raise ValueError("소유 입력/소스의 전후 값이 다르다")
            report[name] = True
        except BaseException as exc:
            report[name] = False
            report["quality_claim"] = False
            errors.append(dict(check=name, type=type(exc).__name__, message=str(exc)[:1000]))
            if exit_error is None:
                exit_error = exc
    if errors:
        report["exit_verification_errors"] = errors
        if report.get("returncode") == 0:
            report.update(status="EXIT_VERIFICATION_ERROR", returncode=9)
    report.update(ended_at=datetime.now(timezone.utc).isoformat(), wall_seconds=time.perf_counter() - started)
    from scripts.diag_p106b_external_core6 import close_report
    close_report(Path(directory) / "report.json", report,
                 primary_error=primary_error if primary_error is not None else exit_error)
    return report


def finish_execution(report, directory, started, signature, pins, *, torch=None, idle_fn=None,
                     primary_error=None, identity_fn=identity, verify_fn=control.original.verify_pins):
    """import가 일부만 끝나도 아직 없는 idle callback을 호출하지 않는다."""
    if torch is not None:
        control.cleanup_owned(torch, report, idle_fn)
    return finalize(report, directory, started, signature, pins, primary_error=primary_error,
                    identity_fn=identity_fn, verify_fn=verify_fn)


def boundary_canary(task, lm):
    documents = [dict(text="A short context extraordinarily_unfamiliar"), dict(text="One  two"), dict(text="Standalone")]
    requests = [request_for(task, doc, i) for i, doc in enumerate(documents)]
    plans = [token_plan(lm, request) for request in requests]
    responses = lm.loglikelihood(requests, disable_tqdm=True)
    if len(responses) != len(requests):
        raise ValueError("수치 경계 canary의 요청을 누락했다")
    for i, response in enumerate(responses):
        record_for(task, documents[i], i, requests[i], response, plans[i])
    return dict(quality_claim=False, request_arguments=[list(r.args) for r in requests],
                token_plans=plans, actual_responses=[list(valid_response(r)) for r in responses], passed=True)


def evaluate(task, lm, mode, directory, report, check):
    from scripts.p106b_shards import ShardWriter
    count = 32 if mode == "cost" else ROWS
    writer = ShardWriter(directory, "samples", limit=control.LIMIT)
    tick = time.perf_counter()
    try:
        for start in range(0, count, 8):
            check()
            indices = list(range(start, min(start + 8, count)))
            docs = [task.eval_docs[i] for i in indices]
            requests = [request_for(task, doc, i) for i, doc in zip(indices, docs)]
            plans = [token_plan(lm, request) for request in requests]
            responses = lm.loglikelihood(requests, disable_tqdm=True)
            if len(responses) != len(requests):
                raise ValueError("공식 요청의 일부를 누락했다")
            for i, doc, request, response, plan in zip(indices, docs, requests, responses, plans):
                writer.append(record_for(task, doc, i, request, response, plan))
        closing, writer = writer, None
        manifest = closing.close(lineage=dict(task=TASK, model=report["model"], mode=mode, data_sha256=DATA_SHA))
        report["sample_manifest"] = manifest
        report["evaluation_seconds"] = time.perf_counter() - tick
        recount = recount_raw(task, directory, manifest, count)
        report.update(actual_rows=count, raw_independent_recount=True, raw_recount=recount,
                      metrics=recount["metrics"], quality_claim=mode == "full")
    finally:
        control.close_partial(writer, report)


def execute(mode, model, expected_source, deadline, max_wall_sec):
    from scripts import diag_p106b_external_core6 as external
    from scripts import diag_p106b_official_core6 as official
    started = time.perf_counter()
    if mode not in ("prepare", "canary", "cost", "full") or (mode != "prepare" and model not in MODELS):
        raise ValueError("명시된 모델/단계가 필요하다")
    admission = control.window(deadline, max_wall_sec, mode)
    signature = identity()
    if signature["sha256"] != expected_source:
        raise ValueError("현재 동결 source SHA가 다르다")
    directory = control.reserve(OUTPUT / ("prepare" if mode == "prepare" else model + "/" + mode))
    report = dict(schema=SCHEMA, tag=TAG, task=TASK, model=model, mode=mode, status="STARTED", returncode=9,
        policy=policy(model), source_identity=signature, admission=admission, started_at=datetime.now(timezone.utc).isoformat(),
        input_pins={}, sources_unchanged=False, inputs_unchanged=False, training=False, optimizer_updates=0,
        checkpoint_writes=0, quality_claim=False, contamination="ALL_PRETRAINING_OVERLAP_NOT_AUDITED")
    pins = {}
    torch = require_idle_gpu = primary_error = None
    check = lambda: control.check_time(admission, started)
    try:
        with external.phase_wall_limit(admission["hard_cap_seconds"]):
            check()
            proof = asset_proof()
            pins.update({DATA_REL: DATA_SHA, YAML_REL: YAML_SHA})
            report.update(input_pins=pins, default_alias_proof=proof)
            import os
            from scripts.prepare_p106b_official_eval import configure_hf_cache
            configure_hf_cache()
            for key, value in official.OFFLINE.items():
                os.environ[key] = value
            task, data = load_task()
            report["task_contract"] = data
            for item in data["official_definition_sources"].values():
                pins[item["runtime_path"]] = item["sha256"]
            if mode == "prepare":
                report.update(status="LAMBADA_DEFAULT_PREPARED", returncode=0, model_loads=0, gpu_calls=0)
            else:
                prep_path = OUTPUT / "prepare/report.json"
                prepared = control.read_report(prep_path)
                if (prepared.get("status") != "LAMBADA_DEFAULT_PREPARED" or prepared.get("returncode") != 0
                        or prepared.get("source_identity") != signature or prepared.get("default_alias_proof") != proof
                        or prepared.get("task_contract") != data or not prepared.get("sources_unchanged")
                        or not prepared.get("inputs_unchanged")):
                    raise ValueError("같은 새 source의 default prepare 완료가 필요하다")
                pins[str(prep_path.relative_to(ROOT))] = control.original.digest(prep_path)
                canary = None
                if mode != "canary":
                    canary_path = OUTPUT / model / "canary/report.json"
                    canary = control.read_report(canary_path)
                    expected = dict(schema=SCHEMA, tag=TAG, model=model, mode="canary", status="LAMBADA_CANARY_COMPLETE",
                        source_identity=signature, policy=policy(model), returncode=0, numerical_canary_passed=True,
                        sources_unchanged=True, inputs_unchanged=True, default_alias_proof=proof, task_contract=data)
                    if any(canary.get(k) != v for k, v in expected.items()):
                        raise ValueError("같은 모델/source/default 수치 canary가 필요하다")
                    report["canary_report_sha256"] = control.original.digest(canary_path)
                    pins[str(canary_path.relative_to(ROOT))] = report["canary_report_sha256"]
                    if mode == "full":
                        cost_path = OUTPUT / model / "cost/report.json"
                        cost = control.read_report(cost_path)
                        if cost.get("model_identity") != canary.get("model_identity"):
                            raise ValueError("canary/cost 모델 가중치 계보가 다르다")
                        report["admission"] = full_admission(cost, signature, model, admission, report["canary_report_sha256"])
                        pins[str(cost_path.relative_to(ROOT))] = control.original.digest(cost_path)
                assets = external.asset_identity(model) if model in HF_MODELS else None
                if assets:
                    report["assets"] = assets
                    for item in assets["files"].values():
                        pins[str(Path(item["resolved_path"]).relative_to(ROOT))] = item["sha256"]
                report["strict_runtime_prerequisite"] = official.prerequisites()
                import torch
                from torch.nn.attention import sdpa_kernel, SDPBackend
                from scripts.interactive_research_infer import require_idle_gpu, state_fingerprint
                torch.set_num_threads(4); torch.manual_seed(1337)
                torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
                check()
                with sdpa_kernel(SDPBackend.MATH), torch.no_grad():
                    report["gpu_point_query"] = require_idle_gpu()
                    check()
                    with model_runtime(model, torch, assets) as (lm, runtime_proof):
                        report["model_proof"] = runtime_proof
                        bind_model_pins(model, runtime_proof, pins)
                        report["model_identity"] = model_identity(model, runtime_proof, assets)
                        if canary is not None and report["model_identity"] != canary.get("model_identity"):
                            raise ValueError("현재 strict 모델이 canary 모델과 다르다")
                        body = lm.core.score_batch.runtime["model"] if hasattr(lm, "core") else lm.model
                        before = state_fingerprint(body)
                        implementation = Path(sys.modules[type(body).__module__].__file__).absolute()
                        pins[str(implementation)] = control.original.digest(implementation)
                        caught = None
                        try:
                            check()
                            if mode == "canary":
                                report["numerical_oracle"] = external.numerical_canary(lm, torch) if model in HF_MODELS else official.numerical_canary(lm, torch)
                                report["boundary_canary"] = boundary_canary(task, lm)
                                report["numerical_canary_passed"] = True
                            else:
                                evaluate(task, lm, mode, directory, report, check)
                        except BaseException as exc:
                            caught = exc
                            raise
                        finally:
                            try:
                                report["body_unchanged"] = before == state_fingerprint(body)
                                if not report["body_unchanged"]:
                                    raise ValueError("모델 본체가 평가 중 변경됐다")
                            except BaseException as exc:
                                report["body_unchanged"] = False
                                report["body_exit_error"] = dict(type=type(exc).__name__, message=str(exc)[:1000])
                                if caught is None:
                                    raise
                            finally:
                                body = lm = caught = None
                check()
                report.update(status={"canary": "LAMBADA_CANARY_COMPLETE", "cost": "LAMBADA_COST_COMPLETE", "full": "LAMBADA_DEFAULT_COMPLETE"}[mode], returncode=0)
            check()
    except BaseException as exc:
        primary_error = exc
        report.update(status="LAMBADA_DEFAULT_PARTIAL", returncode=130 if isinstance(exc, KeyboardInterrupt) else 9,
            quality_claim=False, error_type=type(exc).__name__, error=str(exc)[:2000], timed_out=isinstance(exc, TimeoutError))
    finally:
        finish_execution(report, directory, started, signature, pins, torch=torch,
                         idle_fn=require_idle_gpu, primary_error=primary_error)
    return {k: report.get(k) for k in ("status", "returncode", "model", "mode", "actual_rows", "wall_seconds", "error_type", "error")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check-only", action="store_true")
    action.add_argument("--execute", action="store_true")
    parser.add_argument("--mode", choices=("prepare", "canary", "cost", "full"), default="prepare")
    parser.add_argument("--model", choices=MODELS)
    parser.add_argument("--source-sha256")
    parser.add_argument("--deadline", default=control.DEADLINE_ISO)
    parser.add_argument("--max-wall-sec", type=int, default=600)
    args = parser.parse_args(argv)
    if args.check_only:
        value = dict(status="CHECK_ONLY", source_identity=identity(), policy=policy(args.model), models=MODELS,
                     tag=TAG, model_loading="NOT_RUN", dataset_loading="NOT_RUN", output=str(OUTPUT.relative_to(ROOT)))
    else:
        if not args.source_sha256 or (args.mode != "prepare" and args.model is None):
            parser.error("명시 실행에는 정확 source SHA와 모델 단계의 --model이 필요하다")
        if args.mode == "prepare" and args.model is not None:
            parser.error("공통 CPU prepare에는 모델을 지정하지 않는다")
        value = execute(args.mode, args.model, args.source_sha256, args.deadline, args.max_wall_sec)
    print("[LAMBADA_DEFAULT_FINAL] " + json.dumps(value, ensure_ascii=False), flush=True)
    return value.get("returncode", 0)


if __name__ == "__main__":
    raise SystemExit(main())
