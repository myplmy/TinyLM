#!/usr/bin/env python3
"""공식 Belebele KO/EN의 독립 제어기. 실제 취득/모델은 root의 명시 실행만 허용한다.

import/check-only는 HF·모델을 열지 않는다. prepare는 정확 두 원자료와 token-only CPU
동결만 소유한다. 기존 평가기·모델·harness 함수와 globals는 변경하지 않는다.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import copy
from datetime import datetime, timezone
import gc
import hashlib
import json
import math
from pathlib import Path
import signal
import sys
import sysconfig
import time
from types import SimpleNamespace
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_lambada_default as base

TAG, SCHEMA = "p106b_belebele_v2_s1337", "P106B_BELEBELE_V2"
CLOSURE_SCHEMA = "P106B_BELEBELE_PHASE_CLOSURE_V2"
CLOSURE_CONTRACT = ("REPORT0_ALONE_IS_NOT_SUCCESS; ROOT_REQUIRES_CLOSURE_AND_REAL_PROCESS_EXIT0_AND_NO_VETO_AND_EXTERNAL_HARDCAP; "
                    "NO_ATOMIC_FILESYSTEM_PROCESS_EXIT_OR_POST_LAST_READ_TAMPER_PROOF")
BASE_SOURCE_SHA = "A400D971EDA6609E2ECA726F0CB49D0F9373028363EE4ABC19D6A5A1B519584D"
REVISION = "7899cdfa4e1e0d733fd77c848e2c273cb1d32be2"
LANGUAGES = ("kor_Hang", "eng_Latn")
MODELS, HF_MODELS = base.MODELS, base.HF_MODELS
ROWS, LINKS = 900, 488
OUTPUT = ROOT / "test_result/evidence" / TAG
DATA = ROOT / "data_cache/p106b_official_eval_assets/belebele_7899cdf_20261024"
LICENSE = "CC-BY-SA-4.0"
SOURCE_REL = base.SOURCE_REL
YAML_DIR = SOURCE_REL + "/lm_eval/tasks/belebele/"
YAML_PINS = {
    "belebele_kor_Hang.yaml": "E5FF26886FD1C0488A50DD0CDB031FF386D203551C4540CEAAEEDC8EEFCBA9BB",
    "belebele_eng_Latn.yaml": "CE981F1F8F08489B2809DB5EA88C2231E033ED9F7F76CE302C85F08AC4543FD6",
    "_default_template_yaml": "AF87BAF2916FE45B4CCBDD394B8ED1BDA04E0DF52B4A412BC8C3A1BE562B658D",
}
SPECS = {
    "kor_Hang": dict(bytes=1534047, git_blob_oid="7772046854ba9d68c33d86d8aff064f7507fbd2a"),
    "eng_Latn": dict(bytes=836071, git_blob_oid="a678517e601a401ba28a8c51287b7e186b161ef6"),
}
for _language, _spec in SPECS.items():
    _spec.update(language=_language, filename=_language + ".jsonl",
        url=f"https://huggingface.co/datasets/facebook/belebele/resolve/{REVISION}/data/{_language}.jsonl")
ALLOWED_URLS = frozenset(item["url"] for item in SPECS.values())
FIELDS = frozenset(("link", "question_number", "flores_passage", "question", "mc_answer1", "mc_answer2",
                    "mc_answer3", "mc_answer4", "correct_answer_num", "dialect", "ds"))
PROMPT = ("P: {{flores_passage}}\nQ: {{question.strip()}}\nA: {{mc_answer1}}\nB: {{mc_answer2}}\n"
          "C: {{mc_answer3}}\nD: {{mc_answer4}}\nAnswer:")
TARGET = "{{['1', '2', '3', '4'].index(correct_answer_num)}}"
DEFINITIONS = (*base.DEFINITION_FILES, "lm_eval/config/task.py", "lm_eval/models/huggingface.py", "lm_eval/models/utils.py")
OWN_FILES = ("scripts/diag_p106b_belebele.py", "scripts/test_p106b_belebele.py",
    "scripts/summarize_p106b_core6_pairs.py", "tinylm/__init__.py", "tinylm/paths.py",
    *(YAML_DIR + name for name in YAML_PINS), *(SOURCE_REL + "/" + name for name in DEFINITIONS))
digest, object_sha = base.control.original.digest, base.control.original.object_sha


def identity():
    previous = base.identity()
    if previous["sha256"] != BASE_SOURCE_SHA:
        raise ValueError("동결된 LAMBADA/HF/Falcon helper source가 변경됐다")
    files = dict(previous["files"])
    files.update({name: digest(ROOT / name) for name in OWN_FILES})
    return dict(files=files, sha256=object_sha(files))


def policy(model=None):
    if model is not None and model not in MODELS:
        raise ValueError("고정 7모델만 허용한다")
    return dict(languages=list(LANGUAGES), rows_per_language=ROWS, full_rows=2 * ROWS,
        full_choice_likelihoods=8 * ROWS, num_fewshot=0, chat_template=False, max_context=1024,
        batch_size=1 if model in HF_MODELS else 8, seed=1337, precision="FP32_MATH_OR_NATIVE_EAGER_TF32_OFF",
        cache=False, generation=False, training=False, target="OFFICIAL_A_B_C_D_LABEL_COMPLETE_SUM_LL",
        metrics=["acc", "acc_norm"], character_denominators=[1, 1, 1, 1],
        context_truncation="LEFT_ONLY_RECORDED_FULL_TARGET_NEVER_TRUNCATED",
        auxiliary="PRE_OUTPUT_FIXED7MODELS_X2LANGUAGES_X4CHOICES_COMMON_UNTRUNCATED_KEYS",
        confidence_intervals="NOT_IMPLEMENTED_NOT_CLAIMED", retries=0,
        model_comparison="EXTERNAL_PRETRAINING_TOKENIZERS_AND_MODEL_SIZES_NOT_MATCHED")


def unique_object(items):
    value = {}
    for key, item in items:
        if key in value:
            raise ValueError("중복 JSON key는 허용하지 않는다")
        value[key] = item
    return value


def decode(raw):
    def bad(value):
        raise ValueError("비유한 JSON 상수는 허용하지 않는다: " + value)
    return json.loads(raw, object_pairs_hook=unique_object, parse_constant=bad)


def verify_blob(raw, spec):
    if len(raw) != spec["bytes"]:
        raise ValueError("지명 원 JSONL의 정확 bytes가 다르다")
    oid = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if oid != spec["git_blob_oid"]:
        raise ValueError("공급자 Git blob OID가 다르다; LFS SHA로 대신하지 않는다")
    return dict(bytes=len(raw), git_blob_oid=oid, sha256=hashlib.sha256(raw).hexdigest().upper())


def check_directory(path):
    path = Path(path)
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise ValueError("cache/output의 symlink를 허용하지 않는다")
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir():
        raise ValueError("정규 cache 폴더가 필요하다")
    return path


def verify_official_url(url):
    parsed = urlsplit(url)
    hostname = parsed.hostname or ""
    if (parsed.scheme != "https" or parsed.username or parsed.password
            or not (hostname == "huggingface.co" or hostname.endswith(".huggingface.co")
                    or hostname == "cas-bridge.xethub.hf.co")):
        raise ValueError("공식 HF의 HTTPS redirect만 허용한다")


class OfficialRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        verify_official_url(newurl)  # redirect 목적지의 네트워크 요청보다 먼저 검사한다.
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def official_open(request, *, timeout):
    return build_opener(OfficialRedirect()).open(request, timeout=timeout)


def acquire_file(directory, spec, *, allow_download=False, opener=official_open):
    """두 고정 URL만 요청하며 기존 파일은 재검산하고 절대로 덮지 않는다."""
    if spec["url"] not in ALLOWED_URLS or spec["filename"] not in {item["filename"] for item in SPECS.values()}:
        raise ValueError("사전 승인된 두 원자료 URL/파일명만 허용한다")
    if type(spec["bytes"]) is not int or not 0 < spec["bytes"] < base.control.LIMIT:
        raise ValueError("원자료 크기 상한이 다르다")
    directory = check_directory(directory)
    path = directory / spec["filename"]
    if path.is_symlink():
        raise ValueError("연결된 원자료를 허용하지 않는다")
    downloaded = False
    if not path.exists():
        if not allow_download:
            raise FileNotFoundError("root prepare의 지명 원자료 취득이 먼저 필요하다")
        request = Request(spec["url"], headers={"User-Agent": "TinyLM-pinned-Belebele-prepare"})
        with opener(request, timeout=30) as response:
            verify_official_url(response.geturl())
            if response.status != 200:
                raise ValueError("원자료 HTTP 완료 상태가 아니다")
            advertised = response.headers.get("Content-Length")
            if advertised is not None and int(advertised) != spec["bytes"]:
                raise ValueError("원자료 HTTP 길이가 정확 bytes와 다르다")
            received = 0
            with path.open("xb") as stream:
                while True:
                    block = response.read(min(65536, spec["bytes"] - received + 1))
                    if not block:
                        break
                    received += len(block)
                    if received > spec["bytes"]:
                        raise ValueError("원자료가 고정 byte 상한을 넘었다; 부분 파일은 보존한다")
                    stream.write(block)
        downloaded = True
    if not path.is_file() or path.stat().st_size != spec["bytes"]:
        raise ValueError("기존/부분 원자료의 정확 크기가 다르다; 덮어쓰지 않는다")
    raw = path.read_bytes()
    return raw, dict(spec, **verify_blob(raw, spec), path=str(path), downloaded_in_this_phase=downloaded,
        license=LICENSE, repo_id="facebook/belebele", revision=REVISION,
        upstream_integrity="GIT_BLOB_SHA1_WITH_HEADER; LOCAL_ACTUAL_SHA256_SEPARATELY_RECORDED",
        source_card=f"https://huggingface.co/datasets/facebook/belebele/blob/{REVISION}/README.md")


def key_for(doc):
    return doc["link"], doc["question_number"]


def validate_rows(rows, language, *, expected_rows=ROWS, expected_links=LINKS):
    if language not in LANGUAGES or len(rows) != expected_rows:
        raise ValueError("정확 언어별 900행이 필요하다")
    for doc in rows:
        if (not isinstance(doc, dict) or set(doc) != FIELDS
                or any(not isinstance(doc[name], str) or not doc[name].strip() for name in FIELDS - {"question_number"})
                or type(doc["question_number"]) is not int or doc["question_number"] not in (1, 2)
                or doc["dialect"] != language or doc["correct_answer_num"] not in ("1", "2", "3", "4")):
            raise ValueError("원자료 schema/언어/문자열 정답/문항번호가 다르다; skip하지 않는다")
    keys = [key_for(doc) for doc in rows]
    links = Counter(doc["link"] for doc in rows)
    if len(set(keys)) != expected_rows or len(links) != expected_links or any(count not in (1, 2) for count in links.values()):
        raise ValueError("정확한 유일 대응키/488 link 묶음이 필요하다")
    return dict(rows=len(rows), unique_keys=len(set(keys)), links=len(links),
                questions_per_link={str(k): v for k, v in sorted(Counter(links.values()).items())},
                ordered_keys_sha256=object_sha(keys), ordered_document_sha256=object_sha(rows),
                key_fields=["link", "question_number"], ds_is_not_a_join_key=True, row_order_is_not_a_join_key=True)


def align_languages(documents, *, expected_rows=ROWS, expected_links=LINKS):
    if set(documents) != set(LANGUAGES):
        raise ValueError("두 고정 언어가 모두 필요하다")
    audits = {language: validate_rows(documents[language], language, expected_rows=expected_rows,
                                     expected_links=expected_links) for language in LANGUAGES}
    maps = {language: {key_for(doc): doc for doc in documents[language]} for language in LANGUAGES}
    left, right = (maps[language] for language in LANGUAGES)
    if set(left) != set(right) or any(left[key]["correct_answer_num"] != right[key]["correct_answer_num"] for key in left):
        raise ValueError("900 exact key join 또는 대응 정답 라벨이 다르다")
    return dict(languages=audits, paired_keys=expected_rows, paired_links=expected_links, gold_index_disagreements=0,
                paired_sorted_keys_sha256=object_sha(sorted(left)), confidence_intervals="NOT_RUN")


def read_assets(*, allow_download=False, directory=DATA, opener=official_open):
    documents, receipts = {}, {}
    for language, spec in SPECS.items():
        raw, receipt = acquire_file(directory, spec, allow_download=allow_download, opener=opener)
        documents[language] = [decode(line) for line in raw.decode("utf-8").splitlines()]
        receipts[language] = receipt
    audit = align_languages(documents)
    stable = {language: {key: value for key, value in receipt.items() if key != "downloaded_in_this_phase"}
              for language, receipt in receipts.items()}
    return documents, stable, audit


def validate_yaml(task_yaml, language):
    expected = dict(task="belebele_" + language, dataset_path="facebook/belebele", dataset_name=language,
        output_type="multiple_choice", test_split="test", fewshot_split="test", doc_to_text=PROMPT,
        doc_to_choice=["A", "B", "C", "D"], doc_to_target=TARGET)
    if any(task_yaml.get(key) != value for key, value in expected.items()):
        raise ValueError("고정 공식 Belebele task/prompt/라벨 계약이 다르다")
    metrics = [dict(metric=name, aggregation="mean", higher_is_better=True) for name in ("acc", "acc_norm")]
    if task_yaml.get("metric_list") != metrics:
        raise ValueError("공식 acc/문자길이 acc_norm을 바꾸지 않는다")
    if task_yaml.get("fewshot_config") != dict(sampler="first_n"):
        raise ValueError("공식 first_n fewshot 정의를 바꾸지 않는다")
    return {key: copy.deepcopy(value) for key, value in task_yaml.items()
            if key not in ("dataset_path", "dataset_name", "dataset_kwargs")}


def verify_task_fields(task, before):
    for key, value in before.items():
        # 공식 TaskConfig는 원 YAML의 dict를 FewshotConfig 객체로 정규화한다.
        if key not in ("num_fewshot", "fewshot_config") and getattr(task.config, key) != value:
            raise ValueError("공식 task 과학적 정의가 바뀌었다: " + key)
    if task.config.num_fewshot != 0 or task.config.target_delimiter != " " or task.fewshot_cfg.sampler != "first_n":
        raise ValueError("공식 선행공백/0-shot/first_n task 정규화가 다르다")


def configure_runtime():
    import tinylm  # noqa: F401 -- 기존 project 경로 정책을 HF import보다 먼저 적용한다.
    from scripts.prepare_p106b_official_eval import configure_hf_cache
    from scripts.diag_p106b_official_core6 import OFFLINE
    import os
    receipt = configure_hf_cache()
    for key, value in OFFLINE.items():
        os.environ[key] = value
    return receipt


def load_tasks(documents):
    configure_runtime()
    from scripts.p106b_official_lm_adapter import prepare_harness, ARCHIVE_SHA256
    _, framework = prepare_harness(runtime_root=Path(sysconfig.get_paths()["purelib"]))
    definitions = base.verify_definition_sources(ROOT / SOURCE_REL, Path(sysconfig.get_paths()["purelib"]),
        (ROOT / SOURCE_REL).parent / "official_source.tar.gz", ARCHIVE_SHA256, base.HARNESS_COMMIT, DEFINITIONS)
    for name, sha in YAML_PINS.items():
        if digest(ROOT / YAML_DIR / name) != sha:
            raise ValueError("공식 Belebele 원 YAML/include가 변경됐다")
    from lm_eval.tasks._yaml_loader import load_yaml
    from lm_eval.api.task import ConfigurableTask
    from lm_eval.models.huggingface import HFLM  # noqa: F401 -- 실제 import 원형 경로도 검증한다.
    from datasets import Dataset
    from scripts.summarize_p106b_core6_pairs import memory_task
    for name, item in definitions.items():
        module = sys.modules[name[:-3].replace("/", ".")]
        actual = Path(module.__file__).absolute()
        if actual != Path(item["runtime_path"]).absolute() or digest(actual) != item["sha256"]:
            raise ValueError("실제 import한 공식 정의 경로/SHA가 다르다: " + name)
    tasks, contracts = {}, {}
    for language in LANGUAGES:
        task_yaml = load_yaml(str(ROOT / YAML_DIR / ("belebele_" + language + ".yaml")), resolve_func=True, recursive=True)
        before = validate_yaml(task_yaml, language)
        task_yaml.update(dataset_path="json", dataset_name=None, dataset_kwargs=dict(data_files={"test": str(DATA / (language + ".jsonl"))}),
                         num_fewshot=0)
        task = memory_task(ConfigurableTask, task_yaml, {"test": Dataset.from_list(documents[language])})
        if set(task.dataset) != {"test"} or len(task.eval_docs) != ROWS or task.dataset["test"].cache_files:
            raise ValueError("공식 900행의 in-memory storage-only binding이 다르다")
        verify_task_fields(task, before)
        if [dict(doc) for doc in task.eval_docs] != documents[language]:
            raise ValueError("공식 task의 원문/순서가 원 JSONL과 다르다")
        tasks[language] = task
        contracts[language] = dict(task="belebele_" + language, official_fields=before,
            rows=ROWS, storage_override_only=True, dataset_loader_calls=0, ordered_document_sha256=object_sha(documents[language]))
    return tasks, dict(tasks=contracts, framework_provenance=framework, official_definition_sources=definitions,
                       storage="PINNED_JSONL_TO_IN_MEMORY_DATASET; ORIGINAL_OFFICIAL_METHODS")


def requests_for(task, doc, index):
    from scripts.p106b_official_tasks import task_requests
    context, choices, requests = task_requests(task, doc, index)
    if (choices != ["A", "B", "C", "D"] or len(requests) != 4
            or type(task.doc_to_target(doc)) is not int or task.doc_to_target(doc) != int(doc["correct_answer_num"]) - 1
            or [list(request.args) for request in requests] != [[context, " " + choice] for choice in choices]):
        raise ValueError("공식 단일 글자 라벨/선행공백/0-based 정답 요청이 다르다")
    return requests


def token_plan(lm, request):
    """원 planner의 길이와 원 _encode_pair의 전체 토큰열 지문을 함께 동결한다."""
    from scripts.p106b_official_lm_adapter import plan_tokens
    context, continuation = request.args
    if not context:
        raise ValueError("공식 Belebele prompt는 빈 context가 될 수 없다")
    ctx, cont = lm._encode_pair(context, continuation)
    vocab = lm.core.vocab_size if hasattr(lm, "core") else lm.model.config.vocab_size
    plan = plan_tokens(ctx, cont, vocab, 1024)
    return dict(original_context_tokens=plan.original_context_tokens, kept_context_tokens=plan.kept_context_tokens,
        truncated_context_tokens=plan.truncated_context_tokens, continuation_tokens=len(plan.continuation_ids),
        input_tokens=len(plan.input_ids), target_start=plan.target_start,
        encoded_context_sha256=object_sha(ctx), encoded_continuation_sha256=object_sha(cont))


def token_only_hf_type(hflm, template):
    """새 비점수 wrapper. 원 HFLM encoder와 TemplateLM 경계 처리를 그대로 상속한다."""
    class TokenOnlyHF(hflm):
        def __init__(self, tokenizer, vocab):
            template.__init__(self)
            self.tokenizer, self.add_bos_token, self.custom_prefix_token_id = tokenizer, False, None
            self.backend, self._max_length, self._device = "causal", 1024, "cpu"
            self.core = SimpleNamespace(vocab_size=vocab)

        def loglikelihood(self, *args, **kwargs):
            raise RuntimeError("prepare token-only wrapper에서 점수/forward를 실행하지 않는다")

        def _model_call(self, *args, **kwargs):
            raise RuntimeError("prepare token-only wrapper에서 모델을 호출하지 않는다")
    return TokenOnlyHF


@contextmanager
def token_only_runtime(model, pins):
    from scripts.p106b_official_lm_adapter import prepare_harness, _adapter_type, LikelihoodCore
    from scripts import diag_p106b_external_core6 as external
    from scripts import diag_p106b_official_core6 as official
    template, _ = prepare_harness(runtime_root=Path(sysconfig.get_paths()["purelib"]))
    tokenizer = lm = None
    try:
        if model.startswith(("native595-", "new595-broad-")):
            from scripts.interactive_research_infer import TOKENIZER, TOKENIZER_SHA
            from tokenizers import Tokenizer
            if digest(ROOT / TOKENIZER) != TOKENIZER_SHA:
                raise ValueError("기존 native tokenizer SHA가 다르다")
            pins[TOKENIZER] = TOKENIZER_SHA
            tokenizer = Tokenizer.from_file(str(ROOT / TOKENIZER))
            bos, eos, pad = (tokenizer.token_to_id(name) for name in ("<bos>", "<eos>", "<pad>"))
            def no_forward(batch):
                raise RuntimeError("prepare native token-only callback에서 forward를 실행하지 않는다")
            core = LikelihoodCore(vocab_size=32768, pad_id=pad, score_batch=no_forward, batch_size=8)
            lm = _adapter_type(template)(core=core, tokenizer=tokenizer, prefix_id=bos if bos is not None else eos,
                eos_id=eos, provenance=dict(device="cpu", tokenizer_sha256=TOKENIZER_SHA))
            proof = dict(model=model, tokenizer_sha256=TOKENIZER_SHA, vocabulary=32768, model_instances=0, forward_calls=0)
        else:
            from transformers import AutoTokenizer
            from lm_eval.models.huggingface import HFLM
            from lm_eval.models.utils import configure_pad_token
            declared = official.FALCON if model == "falcon90m" else ROOT / external.REGISTRY[model]["path"]
            folder = declared.resolve()
            if not folder.is_relative_to((ROOT / "HF").resolve()):
                raise ValueError("고정 HF namespace 밖의 tokenizer는 허용하지 않는다")
            metadata_files = {}
            for name in external.SMALL_ASSETS:
                path = folder / name
                if path.exists():
                    resolved = path.resolve(strict=True)
                    if not resolved.is_file() or not resolved.is_relative_to((ROOT / "HF").resolve()):
                        raise ValueError("tokenizer metadata가 고정 HF 범위를 벗어났다")
                    sha = digest(resolved)
                    pins[str(resolved.relative_to(ROOT))] = sha
                    metadata_files[name] = sha
            if not external.REQUIRED_SMALL.issubset(metadata_files):
                raise ValueError("정확 tokenizer/config metadata가 부족하다")
            model_metadata = decode((folder / "config.json").read_text(encoding="utf-8"))
            vocab = model_metadata["vocab_size"]
            tokenizer = AutoTokenizer.from_pretrained(str(folder), local_files_only=True, trust_remote_code=False)
            # 원 HFLM의 preinstantiated-tokenizer 초기화에서 적용하는 공식 CPU 정책이다.
            tokenizer = configure_pad_token(tokenizer, model_config=SimpleNamespace(**model_metadata))
            lm = token_only_hf_type(HFLM, template)(tokenizer, vocab)
            implementation = Path(sys.modules[type(tokenizer).__module__].__file__).absolute()
            pins[str(implementation)] = digest(implementation)
            proof = dict(model=model, metadata_sha256=metadata_files, vocabulary=vocab,
                         hflm_source=external.hflm_source_identity(HFLM), model_instances=0, forward_calls=0)
        yield lm, proof
    finally:
        lm = tokenizer = None
        gc.collect()


def close_writer(writer, lineage, report, label):
    """manifest 저장 실패여도 이미 기록한 원형의 위치/크기/해시를 잃지 않는다."""
    try:
        return writer.close(lineage=lineage)
    except BaseException as exc:
        report.setdefault("artifact_close_errors", {})[label] = dict(type=type(exc).__name__, message=str(exc)[:1000],
            manifest_path=str(writer.manifest_path), rows=writer._total_rows, bytes=writer._total_bytes,
            shards=copy.deepcopy(writer.shards))
        raise


def freeze_tokens(tasks, directory, pins, check, *, models=MODELS, factory=token_only_runtime,
                  request_builder=requests_for, partial_report=None):
    from scripts.p106b_shards import ShardWriter
    common = set(key_for(doc) for doc in tasks[LANGUAGES[0]].eval_docs)
    writer = ShardWriter(directory, "token_lengths", limit=base.control.LIMIT)
    audits = {}
    try:
        for model in models:
            check()
            with factory(model, pins) as (lm, proof):
                model_audit = dict(tokenizer_proof=proof, languages={})
                for language in LANGUAGES:
                    counts = Counter()
                    for index, doc in enumerate(tasks[language].eval_docs):
                        check()
                        plans = [token_plan(lm, request) for request in request_builder(tasks[language], doc, index)]
                        if len(plans) != 4:
                            raise ValueError("토큰 동결은 모든 네 보기를 요구한다")
                        untruncated = all(plan["truncated_context_tokens"] == 0 for plan in plans)
                        if not untruncated:
                            common.discard(key_for(doc))
                        counts.update(rows=1, requests=4, untruncated=int(untruncated))
                        writer.append(dict(model=model, language=language, doc_id=index, key=list(key_for(doc)),
                                           plans=plans, untruncated=untruncated))
                    model_audit["languages"][language] = dict(counts)
                audits[model] = model_audit
        closing, writer = writer, None
        manifest = close_writer(closing, dict(models=list(models), languages=list(LANGUAGES), forward_calls=0,
            quality_claim=False), {} if partial_report is None else partial_report, "token_lengths")
        return dict(models=list(models), model_audits=audits, token_manifest=manifest,
                    common_keys=[list(key) for key in sorted(common)], common_rows_per_language=len(common),
                    frozen_before_model_output=True, model_instances=0, forward_calls=0, gpu_calls=0, quality_claim=False)
    finally:
        if writer is not None:
            partial = {}
            base.control.close_partial(writer, partial)
            if partial_report is not None:
                partial_report["partial_token_artifacts"] = partial


def read_frozen(prepare_directory, frozen, documents, model, *, models=MODELS, expected_rows=ROWS):
    from scripts.p106b_shards import verify
    if (frozen.get("models") != list(models) or model not in models or frozen.get("frozen_before_model_output") is not True
            or frozen.get("model_instances") != 0 or frozen.get("forward_calls") != 0 or frozen.get("gpu_calls") != 0):
        raise ValueError("고정 7모델의 사전 token-only 동결이 필요하다")
    manifest = frozen["token_manifest"]
    if manifest.get("rows") != len(models) * len(LANGUAGES) * expected_rows:
        raise ValueError("토큰 동결의 정확 12600 문항 분모가 필요하다")
    verify(Path(prepare_directory), manifest)
    selected, seen = {language: {} for language in LANGUAGES}, set()
    common = set(key_for(doc) for doc in documents[LANGUAGES[0]])
    for shard in manifest["shards"]:
        with (Path(prepare_directory) / shard["path"]).open(encoding="utf-8") as stream:
            for line in stream:
                row = decode(line)
                name, language, index = row["model"], row["language"], row["doc_id"]
                uid = name, language, index
                if (name not in models or language not in LANGUAGES or type(index) is not int or not 0 <= index < expected_rows
                        or uid in seen or row["key"] != list(key_for(documents[language][index])) or len(row["plans"]) != 4):
                    raise ValueError("토큰 동결의 모델/언어/문항/대응키가 다르다")
                seen.add(uid)
                untruncated = all(plan["truncated_context_tokens"] == 0 for plan in row["plans"])
                if row["untruncated"] is not untruncated:
                    raise ValueError("토큰 동결의 무절단 표지가 다르다")
                if not untruncated:
                    common.discard(tuple(row["key"]))
                if name == model:
                    selected[language][index] = row["plans"]
    if (len(seen) != len(models) * 2 * expected_rows or frozen.get("common_keys") != [list(key) for key in sorted(common)]
            or frozen.get("common_rows_per_language") != len(common)):
        raise ValueError("모든 모델·언어의 사전 공통 무절단 교집합이 다르다")
    return selected, common


def item_metrics(task, doc, responses):
    from scripts.diag_p106b_official_core6 import independent_row
    if len(responses) != 4:
        raise ValueError("네 라벨의 전체 우도를 모두 요구한다")
    checked = [base.valid_response(value) for value in responses]
    audit = independent_row(task.doc_to_choice(doc), task.doc_to_target(doc), [value[0] for value in checked])
    metrics = task.process_results(doc, checked)
    if (set(metrics) != {"acc", "acc_norm"} or metrics["acc"] != audit["acc"]
            or metrics["acc_norm"] != audit["acc_norm"] or metrics["acc"] != metrics["acc_norm"]):
        raise ValueError("공식 acc/라벨 문자길이 정규화와 독립 재계수가 다르다")
    return checked, metrics


def aggregate(task, records):
    if not records:
        return dict(rows=0, metrics=None, denominator_policy="EMPTY_AUXILIARY_IS_NOT_ZERO_ACCURACY")
    methods = task.aggregation()
    if set(methods) != {"acc", "acc_norm"}:
        raise ValueError("공식 acc/acc_norm 집계만 허용한다")
    metrics = {name: float(methods[name]([row["metrics"][name] for row in records])) for name in methods}
    expected = math.fsum(row["metrics"]["acc"] for row in records) / len(records)
    if any(not math.isfinite(value) or not math.isclose(value, expected, abs_tol=1e-12, rel_tol=1e-10) for value in metrics.values()):
        raise ValueError("공식 집계와 독립 라벨 정답 재계수가 다르다")
    return dict(rows=len(records), metrics=metrics)


def recount_raw(task, documents, language, directory, manifest, expected, frozen_plans, common, *, request_builder=requests_for):
    from scripts.p106b_shards import verify
    verify(Path(directory), manifest)
    records = []
    for shard in manifest["shards"]:
        with (Path(directory) / shard["path"]).open(encoding="utf-8") as stream:
            for line in stream:
                row = decode(line); index = len(records)
                if (index >= expected or row.get("doc_id") != index or row.get("language") != language
                        or row.get("doc") != documents[index] or row.get("key") != list(key_for(documents[index]))):
                    raise ValueError("원형의 정확 문항·순서·언어·원문이 다르다")
                requests = request_builder(task, task.eval_docs[index], index)
                if row.get("arguments") != [list(request.args) for request in requests] or row.get("plans") != frozen_plans[index]:
                    raise ValueError("원 공식 요청/사전 토큰 동결과 저장 원형이 다르다")
                _, metrics = item_metrics(task, task.eval_docs[index], row.get("responses", []))
                if row.get("metrics") != metrics or row.get("common_untruncated") is not (key_for(documents[index]) in common):
                    raise ValueError("원형의 공식 문항 metric/사전 공통부분 표지가 다르다")
                records.append(row)
    if len(records) != expected:
        raise ValueError("정확 cost32/full900 분모가 필요하다; 부분은 전량이 아니다")
    return dict(aggregate(task, records), auxiliary_common_untruncated=aggregate(task, [row for row in records if row["common_untruncated"]]),
        choice_likelihoods=4 * expected, raw_sha_verified=True,
        context_truncated_rows=sum(any(plan["truncated_context_tokens"] for plan in row["plans"]) for row in records))


def evaluate(tasks, documents, lm, model, mode, directory, report, check, frozen_plans, common, *, request_builder=requests_for):
    from scripts.p106b_shards import ShardWriter
    count = 32 if mode == "cost" else ROWS
    report.update(actual_counts={}, sample_manifests={}, independent_audits={}, evaluation_seconds={})
    for language in LANGUAGES:
        writer = ShardWriter(directory, language + "_samples", limit=base.control.LIMIT)
        tick = time.perf_counter()
        try:
            for index in range(count):
                check()
                doc = tasks[language].eval_docs[index]
                requests = request_builder(tasks[language], doc, index)
                plans = [token_plan(lm, request) for request in requests]
                if plans != frozen_plans[language][index]:
                    raise ValueError("실제 strict tokenizer의 길이가 사전 동결과 다르다")
                responses, metrics = item_metrics(tasks[language], doc, lm.loglikelihood(requests, disable_tqdm=True))
                writer.append(dict(doc_id=index, language=language, key=list(key_for(documents[language][index])),
                    doc=documents[language][index], arguments=[list(request.args) for request in requests],
                    responses=[list(value) for value in responses], metrics=metrics, plans=plans,
                    common_untruncated=key_for(documents[language][index]) in common))
            closing, writer = writer, None
            manifest = close_writer(closing, dict(task="belebele_" + language, model=model, mode=mode, revision=REVISION),
                                    report, language)
            report["sample_manifests"][language] = manifest
            report["evaluation_seconds"][language] = time.perf_counter() - tick
            audit = recount_raw(tasks[language], documents[language], language, directory, manifest, count,
                                frozen_plans[language], common, request_builder=request_builder)
            report["actual_counts"][language] = count
            report["independent_audits"][language] = audit
        finally:
            if writer is not None:
                partial = {}
                base.control.close_partial(writer, partial)
                report.setdefault("partial_artifacts", {})[language] = partial
    report.update(raw_independent_recount=True, actual_rows=2 * count, actual_choice_likelihoods=8 * count,
                  quality_claim=mode == "full", confidence_intervals="NOT_RUN")


class OperationalHold(ValueError):
    def __init__(self, reason, message):
        super().__init__(message)
        self.reason = reason


def remaining_budget(admission, started, *, elapsed=None, now=None):
    elapsed = time.perf_counter() - started if elapsed is None else elapsed
    now = time.time() if now is None else now
    if not base.control.finite(elapsed) or not base.control.finite(now):
        raise ValueError("실측 경과시간/절대시각이 유한하지 않다")
    remaining = min(admission["hard_cap_seconds"] - elapsed,
                    admission["deadline_epoch"] - admission["cleanup_reserve_seconds"] - now)
    if not base.control.finite(remaining, positive=True):
        raise TimeoutError("종료 저장·재읽기를 포함한 cap/deadline 잔여시간이 없다")
    return remaining


def full_admission(cost, signature, model, admission, canary_sha, prepared_sha, *, now=None, elapsed=0.):
    expected = dict(schema=SCHEMA, tag=TAG, model=model, mode="cost", status="BELEBELE_COST_COMPLETE", returncode=0,
        source_identity=signature, policy=policy(model), canary_report_sha256=canary_sha,
        prepare_report_sha256=prepared_sha, sources_unchanged=True, inputs_unchanged=True,
        raw_independent_recount=True, actual_counts={language: 32 for language in LANGUAGES},
        actual_rows=64, actual_choice_likelihoods=256)
    if any(cost.get(key) != value for key, value in expected.items()):
        raise ValueError("동일 source/모델/prepare/canary의 두 언어 cost32가 필요하다")
    timing = cost.get("evaluation_seconds", {})
    if set(timing) != set(LANGUAGES) or any(not base.control.finite(value, positive=True) for value in timing.values()):
        raise ValueError("언어별 실제 양수 평가 시간이 필요하다")
    wall = cost.get("wall_seconds")
    if not base.control.finite(wall, positive=True) or wall < sum(timing.values()):
        raise ValueError("실제 cost의 전체 시간이 평가 시간보다 작다")
    overhead = wall - sum(timing.values())
    forecast = sum(ROWS * value / 32 for value in timing.values()) * 1.5 + overhead + 120
    now = time.time() if now is None else now
    try:
        available = remaining_budget(admission, 0, elapsed=elapsed, now=now)
    except TimeoutError as exc:
        raise OperationalHold("FORECAST_BUDGET", str(exc)) from exc
    if forecast > available:
        raise OperationalHold("FORECAST_BUDGET", "실측 전량 외삽이 이미 소비한 시간을 뺀 cap/deadline 잔여창을 넘는다")
    return dict(admission, forecast_seconds=forecast, forecast_multiplier=1.5,
                spent_at_admission_seconds=elapsed, remaining_at_admission_seconds=available,
                observed_non_eval_overhead_seconds=overhead, fixed_overhead_reserve_seconds=120)


def record_failure(report, error, primary_error=None):
    primary = error if primary_error is None else primary_error
    if error is not primary:
        report.setdefault("secondary_runtime_errors", []).append(dict(type=type(error).__name__, message=str(error)[:1000]))
    hold = isinstance(primary, OperationalHold) and error is primary
    report.update(status="BELEBELE_HOLD" if hold else "BELEBELE_PARTIAL",
        returncode=130 if isinstance(primary, KeyboardInterrupt) else 8 if hold else 9,
        failure_domain="OPERATIONAL_HOLD" if hold else "RUNTIME_DATA_SOURCE_OR_CLEANUP",
        hold_reason=primary.reason if hold else None,
        quality_claim=False, error_type=type(primary).__name__, error=str(primary)[:2000], timed_out=isinstance(primary, TimeoutError))
    return primary


def require_gpu_idle(query):
    try:
        return query()
    except RuntimeError as exc:
        prefix = "다른 GPU compute PID가 있습니다: "
        pids = str(exc)[len(prefix):].split(", ") if str(exc).startswith(prefix) else []
        if pids and all(pid.isascii() and pid.isdecimal() and int(pid) > 0 for pid in pids):
            raise OperationalHold("GPU_BUSY", str(exc)) from exc
        raise  # NVML 조회/파싱 실패는 busy로 추측하지 않는다.


def terminal_write(path, value):
    from scripts.diag_p106b_external_core6 import write_json
    write_json(path, value)  # 기존 bounded/exclusive writer, 기존 파일 덮기 금지.


def closure_paths(directory):
    directory = Path(directory)
    return directory / "phase_closure.json", directory / "phase_veto.json"


@contextmanager
def closure_wall_limit(seconds):
    """공유 helper가 첫 TimeoutError를 잡더라도 종료 신호를 단발로 소모하지 않는다."""
    if not base.control.finite(seconds, positive=True):
        raise TimeoutError("종료 timer에 양수 잔여시간이 필요하다")
    if any(signal.getitimer(signal.ITIMER_REAL)):
        raise RuntimeError("활성 alarm을 덮어쓰는 중첩 종료 timer는 허용하지 않는다")
    previous = signal.getsignal(signal.SIGALRM)
    def expired(*args):
        raise TimeoutError("Belebele 종료 저장·재읽기 잔여시간 상한")
    signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, seconds, .05)
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def finish_phase(report, directory, started, signature, pins, admission, *, torch=None, idle_fn=None,
                 primary_error=None, finish_fn=base.finish_execution, identity_fn=identity,
                 verify_fn=base.control.original.verify_pins, timer_fn=None, write_fn=terminal_write,
                 read_fn=base.control.read_report, digest_fn=digest, clock_fn=time.perf_counter, wall_fn=time.time):
    """원 종료 helper와 모든 저장/재읽기를 잔여 timer 안에서 처리한다.

    마지막 재읽기 이후 변조나 원자적 FS/프로세스 exit까지 증명하지 않는다. root가 실제
    프로세스 0·외부 hardcap·closure·veto 부재를 함께 확인해야 최종 채택할 수 있다.
    """
    from scripts.diag_p106b_external_core6 import json_ready
    timer_fn = closure_wall_limit if timer_fn is None else timer_fn
    directory = Path(directory)
    report_path = directory / "report.json"
    closure_path, veto_path = closure_paths(directory)
    budget = lambda: remaining_budget(admission, started, elapsed=clock_fn() - started, now=wall_fn())
    saved = None
    try:
        with timer_fn(budget()):
            finish_fn(report, directory, started, signature, pins, torch=torch, idle_fn=idle_fn,
                      primary_error=primary_error, identity_fn=identity_fn, verify_fn=verify_fn)
            budget()
            saved = read_fn(report_path)
            if saved != json_ready(report):
                raise ValueError("종료 보고서가 저장 후 원 상태와 다르다; fallback은 성공 보고서가 아니다")
            if not report.get("sources_unchanged") or not report.get("inputs_unchanged"):
                raise ValueError("종료 source/입력 검증 미완결은 HOLD가 아니라 실패다")
            if report.get("model_load_attempted") and report.get("owned_cleanup_complete") is not True:
                raise ValueError("소유 모델 정리가 완결되지 않았다")
            report_sha = digest_fn(report_path)
            observed_elapsed, observed_wall = clock_fn() - started, wall_fn()
            remaining_budget(admission, started, elapsed=observed_elapsed, now=observed_wall)
            closure = dict(schema=CLOSURE_SCHEMA, tag=TAG, model=report["model"], mode=report["mode"],
                status="CLOSED_WITHIN_OBSERVED_BOUNDS", returncode=report["returncode"],
                source_sha256=signature["sha256"], report_sha256=report_sha,
                admission=copy.deepcopy(report["admission"]), observed_elapsed_seconds=observed_elapsed,
                observed_wall_epoch=observed_wall, report_closed_re_read=True,
                contract=CLOSURE_CONTRACT, root_actual_exit0_required=True, atomicity_claim=False)
            write_fn(closure_path, closure)
            if read_fn(closure_path) != closure or digest_fn(report_path) != report_sha:
                raise ValueError("최종 영수증 재읽기 또는 보고서 전후 SHA가 다르다")
            closure_sha = digest_fn(closure_path)
            if veto_path.exists() or veto_path.is_symlink():
                raise ValueError("최종 veto가 있는 단계는 성공할 수 없다")
            budget()
        completed_elapsed, completed_wall = clock_fn() - started, wall_fn()
        remaining_budget(admission, started, elapsed=completed_elapsed, now=completed_wall)
        report.update(phase_closure_verified=True, phase_closure_sha256=closure_sha,
                      phase_completion_wall_seconds=completed_elapsed, closure_contract=CLOSURE_CONTRACT)
    except BaseException as exc:
        original = primary_error if primary_error is not None else exc
        try:
            failed_elapsed, failed_wall = clock_fn() - started, wall_fn()
        except BaseException:
            failed_elapsed = failed_wall = None
        report.update(phase_closure_verified=False, status="BELEBELE_CLOSURE_VETO", returncode=130 if isinstance(original, KeyboardInterrupt) else 9,
            quality_claim=False, closure_error=dict(type=type(exc).__name__, message=str(exc)[:1000]),
            error_type=type(original).__name__, error=str(original)[:2000], closure_contract=CLOSURE_CONTRACT,
            phase_completion_wall_seconds=failed_elapsed)
        veto = dict(schema=CLOSURE_SCHEMA, tag=TAG, model=report["model"], mode=report["mode"],
            status="VETO", returncode=report["returncode"], source_sha256=signature["sha256"],
            preserved_report_returncode=None if saved is None else saved.get("returncode"),
            original_error=dict(type=type(original).__name__, message=str(original)[:2000]),
            closure_error=report["closure_error"], contract=CLOSURE_CONTRACT,
            observed_elapsed_seconds=failed_elapsed, observed_wall_epoch=failed_wall, admission=admission)
        try:
            write_fn(veto_path, veto)
        except BaseException as veto_error:
            report["veto_write_error"] = dict(type=type(veto_error).__name__, message=str(veto_error)[:1000])
            print("[BELEBELE_VETO_WRITE_ERROR] " + json.dumps(veto, ensure_ascii=False), file=sys.stderr, flush=True)
        # 만료 뒤 veto 저장도 보장할 수 없다. CLI 비정상/closure 누락도 독립 채택 금지 사유다.
    return report


def closed_prerequisite(report_path, signature, model, mode, pins):
    """파일 선결 검사. root의 실제 이전 프로세스 exit0 확인을 대신하지 않는다."""
    report_path = Path(report_path)
    closure_path, veto_path = closure_paths(report_path.parent)
    if veto_path.exists() or veto_path.is_symlink():
        raise ValueError("veto가 있는 단계는 선결로 채택하지 않는다")
    report = base.control.read_report(report_path)
    closure = base.control.read_report(closure_path)  # 없으면 fail-closed.
    report_sha = digest(report_path)
    expected = dict(schema=CLOSURE_SCHEMA, tag=TAG, model=model, mode=mode,
        status="CLOSED_WITHIN_OBSERVED_BOUNDS", returncode=0, source_sha256=signature["sha256"],
        report_sha256=report_sha, admission=report.get("admission"), report_closed_re_read=True,
        contract=CLOSURE_CONTRACT, root_actual_exit0_required=True, atomicity_claim=False)
    if any(closure.get(key) != value for key, value in expected.items()):
        raise ValueError("동일 source/단계/모델/보고서의 최종 종결 영수증이 필요하다")
    if (report.get("schema") != SCHEMA or report.get("tag") != TAG or report.get("source_identity") != signature
            or report.get("mode") != mode or report.get("model") != model or report.get("returncode") != 0
            or report.get("sources_unchanged") is not True or report.get("inputs_unchanged") is not True):
        raise ValueError("최종 종결된 원 보고서의 성공/불변 검증이 다르다")
    admission = report["admission"]
    upper = 7200 if mode == "full" else 600
    if (type(admission.get("hard_cap_seconds")) is not int or not 60 <= admission["hard_cap_seconds"] <= upper
            or admission.get("cleanup_reserve_seconds") != 30
            or not base.control.finite(admission.get("deadline_epoch"))
            or admission["deadline_epoch"] > base.control.LATEST_DEADLINE
            or not base.control.finite(closure.get("observed_elapsed_seconds"))
            or not base.control.finite(closure.get("observed_wall_epoch"))):
        raise ValueError("종결의 단계 cap/마감/소유 정리예비/실측시간 계약이 다르다")
    remaining_budget(admission, 0, elapsed=closure.get("observed_elapsed_seconds"), now=closure.get("observed_wall_epoch"))
    if (not base.control.finite(report.get("wall_seconds"))
            or report["wall_seconds"] > closure["observed_elapsed_seconds"]):
        raise ValueError("종결 관측시간이 원 보고서 경과시간보다 작다")
    for path, sha in ((report_path, report_sha), (closure_path, digest(closure_path))):
        pins[str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)] = sha
    if veto_path.exists() or veto_path.is_symlink():
        raise ValueError("종결 재읽기 중 veto가 생긴 단계는 채택하지 않는다")
    return report


def execute(mode, model, expected_source, deadline, max_wall_sec):
    from scripts import diag_p106b_external_core6 as external
    from scripts import diag_p106b_official_core6 as official
    started = time.perf_counter()
    if mode not in ("prepare", "canary", "cost", "full") or (mode != "prepare" and model not in MODELS):
        raise ValueError("명시된 단계와 고정 모델이 필요하다")
    admission = base.control.window(deadline, max_wall_sec, mode)
    signature = identity()
    if signature["sha256"] != expected_source:
        raise ValueError("현재 source 동결 SHA가 다르다")
    directory = base.control.reserve(OUTPUT / ("prepare" if mode == "prepare" else model + "/" + mode))
    pins = {}
    torch = require_idle_gpu = primary_error = None
    report = dict(schema=SCHEMA, tag=TAG, model=model, mode=mode, policy=policy(model), source_identity=signature,
        admission=admission, input_pins=pins, sources_unchanged=False, inputs_unchanged=False,
        status="STARTED", returncode=9, quality_claim=False, training=False, optimizer_updates=0, checkpoint_writes=0,
        started_at=datetime.now(timezone.utc).isoformat(), confidence_intervals="NOT_RUN",
        data_directory=str(DATA), allowed_data_urls=sorted(ALLOWED_URLS),
        model_load_attempted=False, closure_contract=CLOSURE_CONTRACT,
        contamination="PRETRAINING_OVERLAP_NOT_AUDITED; SHOULD_DECONTAMINATE_FLAG_IS_NOT_AN_AUDIT")
    check = lambda: base.control.check_time(admission, started)
    try:
        with external.phase_wall_limit(remaining_budget(admission, started)):
            check()
            configure_runtime()
            documents, assets, audit = read_assets(allow_download=mode == "prepare")
            report.update(data_assets=assets, data_audit=audit)
            for item in assets.values():
                pins[str(Path(item["path"]).relative_to(ROOT))] = item["sha256"]
            tasks, task_contract = load_tasks(documents)
            report["task_contract"] = task_contract
            for item in task_contract["official_definition_sources"].values():
                pins[item["runtime_path"]] = item["sha256"]
            if mode == "prepare":
                import torch as cpu_torch
                if cpu_torch.cuda.is_initialized():
                    raise ValueError("token-only prepare 전에 CUDA가 초기화됐다")
                report["frozen_tokens"] = freeze_tokens(tasks, directory, pins, check, partial_report=report)
                if cpu_torch.cuda.is_initialized():
                    raise ValueError("token-only prepare가 CUDA를 초기화했다")
                frozen = report["frozen_tokens"]
                for item in frozen["token_manifest"]["shards"]:
                    pins[str((directory / item["path"]).relative_to(ROOT))] = item["sha256"]
                manifest_path = directory / "token_lengths_shards_manifest.json"
                pins[str(manifest_path.relative_to(ROOT))] = digest(manifest_path)
                report.update(status="BELEBELE_PREPARED", returncode=0, model_loads=0, gpu_calls=0)
                torch = None  # CPU tokenizer import만 했으므로 CUDA cleanup/query를 호출하지 않는다.
            else:
                prepared_path = OUTPUT / "prepare/report.json"
                prepared = closed_prerequisite(prepared_path, signature, None, "prepare", pins)
                expected = dict(schema=SCHEMA, tag=TAG, mode="prepare", status="BELEBELE_PREPARED", returncode=0,
                    source_identity=signature, sources_unchanged=True, inputs_unchanged=True, data_assets=assets,
                    data_audit=audit, task_contract=task_contract)
                if any(prepared.get(key) != value for key, value in expected.items()):
                    raise ValueError("동일 source/원자료/공식 과제의 완결 prepare가 필요하다")
                report["prepare_report_sha256"] = digest(prepared_path)
                pins.update(prepared["input_pins"])
                base.control.original.verify_pins(pins)
                pins[str(prepared_path.relative_to(ROOT))] = report["prepare_report_sha256"]
                frozen_plans, common = read_frozen(OUTPUT / "prepare", prepared["frozen_tokens"], documents, model)
                report["auxiliary_common_rows_per_language"] = len(common)
                canary = None
                if mode != "canary":
                    canary_path = OUTPUT / model / "canary/report.json"
                    canary = closed_prerequisite(canary_path, signature, model, "canary", pins)
                    expected = dict(schema=SCHEMA, tag=TAG, model=model, mode="canary", status="BELEBELE_CANARY_COMPLETE",
                        returncode=0, numerical_canary_passed=True, source_identity=signature, policy=policy(model),
                        prepare_report_sha256=report["prepare_report_sha256"], sources_unchanged=True, inputs_unchanged=True)
                    if any(canary.get(key) != value for key, value in expected.items()):
                        raise ValueError("동일 prepare/source/모델의 새 numerical canary가 필요하다")
                    report["canary_report_sha256"] = digest(canary_path)
                    pins[str(canary_path.relative_to(ROOT))] = report["canary_report_sha256"]
                    if mode == "full":
                        cost_path = OUTPUT / model / "cost/report.json"
                        cost = closed_prerequisite(cost_path, signature, model, "cost", pins)
                        if cost.get("model_identity") != canary.get("model_identity"):
                            raise ValueError("canary/cost 모델 또는 tokenizer 자산 계보가 다르다")
                        report["admission"] = full_admission(cost, signature, model, admission,
                            report["canary_report_sha256"], report["prepare_report_sha256"],
                            elapsed=time.perf_counter() - started)
                        pins[str(cost_path.relative_to(ROOT))] = digest(cost_path)
                runtime_assets = external.asset_identity(model) if model in HF_MODELS else None
                if runtime_assets:
                    report["assets"] = runtime_assets
                    for item in runtime_assets["files"].values():
                        pins[str(Path(item["resolved_path"]).relative_to(ROOT))] = item["sha256"]
                report["strict_runtime_prerequisite"] = official.prerequisites()
                import torch
                from torch.nn.attention import sdpa_kernel, SDPBackend
                from scripts.interactive_research_infer import require_idle_gpu, state_fingerprint
                torch.set_num_threads(4); torch.manual_seed(1337)
                torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
                check()
                with sdpa_kernel(SDPBackend.MATH), torch.no_grad():
                    report["gpu_point_query"] = require_gpu_idle(require_idle_gpu)
                    report["model_load_attempted"] = True
                    with base.model_runtime(model, torch, runtime_assets) as (lm, proof):
                        report["model_proof"] = proof
                        base.bind_model_pins(model, proof, pins)
                        report["model_identity"] = base.model_identity(model, proof, runtime_assets)
                        if canary is not None and canary.get("model_identity") != report["model_identity"]:
                            raise ValueError("현재 strict 모델이 수치 canary 모델과 다르다")
                        body = lm.core.score_batch.runtime["model"] if hasattr(lm, "core") else lm.model
                        before = state_fingerprint(body)
                        implementation = Path(sys.modules[type(body).__module__].__file__).absolute()
                        pins[str(implementation)] = digest(implementation)
                        caught = None
                        try:
                            check()
                            if mode == "canary":
                                report["numerical_oracle"] = external.numerical_canary(lm, torch) if model in HF_MODELS else official.numerical_canary(lm, torch)
                                for language in LANGUAGES:
                                    actual = [token_plan(lm, request) for request in requests_for(tasks[language], tasks[language].eval_docs[0], 0)]
                                    if actual != frozen_plans[language][0]:
                                        raise ValueError("실제 strict tokenizer와 사전 동결이 다르다")
                                report["numerical_canary_passed"] = True
                            else:
                                evaluate(tasks, documents, lm, model, mode, directory, report, check, frozen_plans, common)
                        except BaseException as exc:
                            primary_error = exc  # 기존 runtime의 정리에서 2차 오류가 나도 원 평가 오류를 보존한다.
                            caught = exc
                            raise
                        finally:
                            try:
                                report["body_unchanged"] = before == state_fingerprint(body)
                                if not report["body_unchanged"]:
                                    raise ValueError("모델 body가 평가 중 변경됐다")
                            except BaseException as exc:
                                report["body_unchanged"] = False
                                report["body_exit_error"] = dict(type=type(exc).__name__, message=str(exc)[:1000])
                                if caught is None:
                                    raise
                            finally:
                                body = lm = caught = None
                check()
                report.update(status={"canary": "BELEBELE_CANARY_COMPLETE", "cost": "BELEBELE_COST_COMPLETE",
                                      "full": "BELEBELE_FULL_COMPLETE"}[mode], returncode=0)
            check()
    except BaseException as exc:
        primary_error = record_failure(report, exc, primary_error)
    finally:
        finish_phase(report, directory, started, signature, pins, admission,
            torch=torch if report["model_load_attempted"] else None, idle_fn=require_idle_gpu,
            primary_error=primary_error)
    return {key: report.get(key) for key in ("status", "returncode", "model", "mode", "actual_rows", "wall_seconds", "error_type", "error",
                                            "hold_reason", "phase_closure_verified", "phase_closure_sha256",
                                            "phase_completion_wall_seconds", "closure_contract")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check-only", action="store_true")
    action.add_argument("--prepare", action="store_true")
    action.add_argument("--execute", action="store_true")
    parser.add_argument("--mode", choices=("prepare", "canary", "cost", "full"), default="prepare")
    parser.add_argument("--model", choices=MODELS)
    parser.add_argument("--source-sha256")
    parser.add_argument("--deadline", default=base.control.DEADLINE_ISO)
    parser.add_argument("--max-wall-sec", type=int, default=600)
    args = parser.parse_args(argv)
    if args.check_only:
        result = dict(status="CHECK_ONLY", source_identity=identity(), policy=policy(args.model), models=list(MODELS),
                      tag=TAG, dataset_loading="NOT_RUN", model_loading="NOT_RUN", downloads="NOT_RUN", closure_contract=CLOSURE_CONTRACT)
    else:
        if args.prepare and args.mode != "prepare":
            parser.error("--prepare는 CPU 준비 단계에만 사용한다")
        if not args.source_sha256 or (args.mode != "prepare" and args.model is None):
            parser.error("실행에는 source SHA와 모델 단계의 --model이 필요하다")
        if args.mode == "prepare" and args.model is not None:
            parser.error("CPU prepare는 모델 선택 없이 고정 7모델 token-only를 동결한다")
        try:
            result = execute(args.mode, args.model, args.source_sha256, args.deadline, args.max_wall_sec)
        except (Exception, KeyboardInterrupt) as exc:
            result = {}
            record_failure(result, exc)
    print("[BELEBELE_FINAL] " + json.dumps(result, ensure_ascii=False), flush=True)
    return result.get("returncode", 0)


if __name__ == "__main__":
    raise SystemExit(main())
