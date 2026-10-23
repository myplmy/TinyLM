#!/usr/bin/env python3
"""Opt-in TinyLM likelihood bridge for the pinned official Core6 harness.

Import is stdlib-only: no lm_eval/torch/tokenizer/model import, asset read,
download, registration or CUDA call. The owner explicitly opens an existing
strict runtime and calls create_adapter only after installation approval.
This module never installs, patches or registers official source/backends.

Core6 profile: native IDs, chat template OFF, FP32 MATH, common context1024,
sum continuation loglikelihood, no PMI/length normalization/skip fallback.
Continuation >1024 is an error; rolling and free generation are NOT supported.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import importlib
import importlib.metadata
import importlib.util
import inspect
import json
import math
from pathlib import Path, PurePosixPath
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "P106B_OFFICIAL_TINYLM_LIKELIHOOD_V1"
COMMIT = "d6de81643928d653435c431bae19945d41d32520"
VERSION = "0.4.14.dev0"
ARCHIVE_SHA256 = "C60D18C7DCEDB03FDD95D43CD2F0BC4A575862A64EB8C9B390E96F5129E442A4"
ARCHIVE_BYTES = 3_640_478
SOURCE_TREE_SHA256 = "798FA248B3C3A2342CA733FB89CCB507E938D955FD6D7B26F8405A89AF43FC54"
SOURCE = ROOT / "data_cache/p106b_official_eval_tools" / ("lm_eval_" + COMMIT) / "source"
MANIFEST = SOURCE.parent / "manifest.json"
MAX_CONTEXT, IGNORE = 1024, -100
CRITICAL_FILES = ("lm_eval/__init__.py", "lm_eval/api/model.py", "lm_eval/api/instance.py", "lm_eval/utils.py", "pyproject.toml")
RUNTIME_FILES = CRITICAL_FILES[:-1]
FILE_LIMIT = 2_000_000


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_file(path):
    path = regular_path(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def regular_path(path):
    path = Path(path).absolute()
    if ".." in path.parts or any(parent.is_symlink() for parent in (path, *path.parents)) or not path.is_file():
        raise ValueError("명시된 비링크 정규 파일이 필요합니다: " + str(path))
    return path


def _unique_object(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("중복 JSON 키입니다: " + key)
        result[key] = value
    return result


def verify_harness_source(manifest_path=MANIFEST, source_root=SOURCE):
    """Read a receipt/archive and five critical source files, never import them.

    Archive identity is pinned. This does NOT claim a fresh full-tree audit;
    record that distinction instead of promoting the historical tree checksum.
    """
    manifest_path = regular_path(manifest_path)
    source_root = Path(source_root).absolute()
    with manifest_path.open("rb") as stream:
        raw = stream.read(FILE_LIMIT + 1)
    if len(raw) > FILE_LIMIT:
        raise ValueError("공식 소스 영수증 크기 한도를 넘었습니다.")
    receipt = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    if (receipt.get("schema") != "TINYLM_OFFICIAL_EVAL_SOURCE_RECEIPT_V1"
            or receipt.get("repo_id") != "EleutherAI/lm-evaluation-harness"
            or receipt.get("revision") != COMMIT
            or str(receipt.get("archive_sha256", "")).upper() != ARCHIVE_SHA256
            or str(receipt.get("source_tree_sha256", "")).upper() != SOURCE_TREE_SHA256
            or Path(receipt.get("source_root", "")).absolute() != source_root
            or receipt.get("archive_bytes") != ARCHIVE_BYTES):
        raise ValueError("공식 source commit/archive/경로 영수증이 고정값과 다릅니다.")
    archive = regular_path(receipt["archive_path"])
    if archive.parent != source_root.parent or archive.name != "official_source.tar.gz":
        raise ValueError("공식 archive 경로가 영수증 namespace와 다릅니다.")
    if archive.stat().st_size != ARCHIVE_BYTES or sha256_file(archive) != ARCHIVE_SHA256:
        raise ValueError("공식 고정 archive 바이트가 다릅니다.")
    critical = {}
    top = "lm-evaluation-harness-" + COMMIT
    with tarfile.open(archive, "r:gz") as source:
        for member in source:
            parts = PurePosixPath(member.name).parts
            if not parts or parts[0] != top or ".." in parts:
                raise ValueError("공식 archive 내부 경로가 예상과 다릅니다.")
            relative = "/".join(parts[1:])
            if relative not in CRITICAL_FILES:
                continue
            if not member.isfile() or member.size > FILE_LIMIT or relative in critical:
                raise ValueError("공식 핵심 source가 정규 파일/크기 계약을 위반했습니다.")
            stream = source.extractfile(member)
            if stream is None:
                raise ValueError("공식 archive 핵심 source를 읽을 수 없습니다.")
            with stream:
                body = stream.read(FILE_LIMIT + 1)
            expected = hashlib.sha256(body).hexdigest().upper()
            if len(body) != member.size or sha256_file(source_root / relative) != expected:
                raise ValueError("보존한 공식 source가 archive와 다릅니다: " + relative)
            critical[relative] = expected
    if set(critical) != set(CRITICAL_FILES):
        raise ValueError("공식 archive 핵심 source가 누락됐습니다.")
    return dict(framework_source_commit=COMMIT, framework_version_expected=VERSION,
        framework_archive_sha256=ARCHIVE_SHA256, source_root=str(source_root),
        manifest_path=str(manifest_path), manifest_sha256=hashlib.sha256(raw).hexdigest().upper(),
        critical_files=critical, historical_source_tree_sha256=SOURCE_TREE_SHA256,
        verification_scope="PINNED_ARCHIVE_AND_FIVE_CRITICAL_FILES_NOT_FRESH_FULL_TREE_AUDIT")


def verify_imported_framework(module, receipt, distribution, *, runtime_root=None):
    """Reject a same-version but wrong-path/wrong-source TemplateLM at runtime."""
    if distribution.version != VERSION:
        raise ValueError("설치한 lm_eval 배포 metadata 버전이 다릅니다.")
    approved = Path(runtime_root or receipt["source_root"]).absolute()
    actual = regular_path(module.__file__)
    if actual != approved / "lm_eval/api/model.py":
        raise ValueError("실제 lm_eval import 경로가 명시된 runtime source와 다릅니다.")
    for relative in RUNTIME_FILES:
        if sha256_file(approved / relative) != receipt["critical_files"][relative]:
            raise ValueError("실제 harness runtime source가 고정 archive와 다릅니다: " + relative)
    template = module.TemplateLM
    for name in ("_encode_pair", "loglikelihood"):
        method = getattr(template, name)
        if Path(inspect.getsourcefile(method) or "").absolute() != actual:
            raise ValueError("실제 TemplateLM 메서드 원천이 바뀌었습니다: " + name)
    direct_url = distribution.read_text("direct_url.json")
    direct = json.loads(direct_url) if direct_url else None
    if direct and direct.get("vcs_info", {}).get("commit_id", COMMIT) != COMMIT:
        raise ValueError("설치한 harness VCS metadata commit이 다릅니다.")
    return dict(runtime_api_model_path=str(actual), approved_runtime_root=str(approved),
        distribution_version=distribution.version, distribution_root=str(distribution.locate_file("")),
        distribution_direct_url=direct,
        runtime_verification_scope="EXPLICIT_IMPORT_PATH_AND_FOUR_CRITICAL_FILES; DISTRIBUTION_VERSION_IS_NOT_A_COMMIT_PROOF")


def token_ids(values, vocab_size, *, empty=False):
    if (type(vocab_size) is not int or vocab_size < 2
            or not isinstance(values, (list, tuple)) or (not values and not empty)
            or any(type(value) is not int or not 0 <= value < vocab_size for value in values)):
        raise ValueError("모델 어휘 범위 안의 실제 정수 ID열이 필요합니다.")
    return tuple(values)


@dataclass(frozen=True)
class TokenPlan:
    input_ids: tuple
    labels: tuple
    continuation_ids: tuple
    target_start: int
    original_context_tokens: int
    kept_context_tokens: int
    truncated_context_tokens: int


def plan_tokens(context, continuation, vocab_size, max_length=MAX_CONTEXT):
    """Exactly HFLM's last(max+1) then input[:-1], retaining every target."""
    if type(vocab_size) is not int or vocab_size < 2 or type(max_length) is not int or not 1 <= max_length <= MAX_CONTEXT:
        raise ValueError("실제 어휘와 최대1024의 명시 문맥 길이가 필요합니다.")
    context, continuation = token_ids(context, vocab_size), token_ids(continuation, vocab_size)
    if len(continuation) > max_length:
        raise ValueError(f"continuation {len(continuation)}토큰 > 문맥 {max_length}: 후보 절단/skip은 금지하며 rolling은 미지원입니다.")
    removed = max(0, len(context) + len(continuation) - max_length - 1)
    kept = (context + continuation)[removed:]
    inputs = kept[:-1]
    start = len(inputs) - len(continuation)
    if start < 0 or removed >= len(context):
        raise ValueError("전체 continuation을 예측할 최소 prefix가 없습니다.")
    return TokenPlan(inputs, (IGNORE,) * start + continuation, continuation, start,
                     len(context), len(context) - removed, removed)


def padded_batch(plans, pad_id, vocab_size):
    token_ids([pad_id], vocab_size)
    if not plans:
        raise ValueError("빈 likelihood batch는 실행하지 않습니다.")
    width = max(len(plan.input_ids) for plan in plans)
    return dict(input_ids=[list(plan.input_ids) + [pad_id] * (width - len(plan.input_ids)) for plan in plans],
        labels=[list(plan.labels) + [IGNORE] * (width - len(plan.labels)) for plan in plans],
        attention_mask=[[1] * len(plan.input_ids) + [0] * (width - len(plan.input_ids)) for plan in plans],
        lengths=[len(plan.input_ids) for plan in plans], target_starts=[plan.target_start for plan in plans],
        continuation_ids=[list(plan.continuation_ids) for plan in plans],
        padding_side="right", model_attention="EXISTING_CAUSAL_ONLY; no assistant-loss mask is passed as attention")


def logits_oracle(plan, logits, vocab_size):
    """Small stdlib dense-logit oracle; not a fast model evaluator or gate."""
    if len(logits) < len(plan.input_ids):
        raise ValueError("직접 logits oracle에 실제 입력 위치가 누락됐습니다.")
    logps, greedy = [], True
    for index, target in enumerate(plan.continuation_ids, plan.target_start):
        row = [float(value) for value in logits[index]]
        if len(row) != vocab_size or not all(math.isfinite(value) for value in row):
            raise ValueError("직접 logits oracle의 어휘/유한값 계약이 다릅니다.")
        maximum = max(row)
        lse = maximum + math.log(math.fsum(math.exp(value - maximum) for value in row))
        logps.append(row[target] - lse)
        greedy = greedy and max(range(vocab_size), key=row.__getitem__) == target
    return math.fsum(logps), bool(greedy)


def direct_label_oracle(torch, forward, batch, vocab_size):
    """Owner-run actual full-label CE oracle, independent of target-row gather.

    Explicit call performs a forward; import does not. Return raw values, not a
    tolerance/gate. The root owns tiny-model/device parity before any task run.
    """
    device = next(forward.parameters()).device
    inputs = torch.tensor(batch["input_ids"], dtype=torch.long, device=device)
    labels = torch.tensor(batch["labels"], dtype=torch.long, device=device)
    with torch.no_grad(), torch.autocast(device.type, enabled=False):
        logits = forward(inputs, use_cache=False)
        if (not torch.is_tensor(logits) or logits.dtype != torch.float32
                or tuple(logits.shape) != (*inputs.shape, vocab_size)):
            raise ValueError("직접 label oracle의 FP32 full logits shape가 다릅니다.")
        losses = torch.nn.functional.cross_entropy(logits.reshape(-1, vocab_size), labels.reshape(-1),
            ignore_index=IGNORE, reduction="none").reshape_as(labels)
        if not bool(torch.isfinite(losses).all()):
            raise ValueError("직접 label oracle의 CE가 유한하지 않습니다.")
        greedy = logits.argmax(-1)
        return [(float(-losses[index].sum()), bool(greedy[index][labels[index] != IGNORE].eq(labels[index][labels[index] != IGNORE]).all()))
                for index in range(inputs.shape[0])]


class LikelihoodCore:
    """Stdlib injected planner/executor; no tokenizer/model/import ownership."""
    def __init__(self, *, vocab_size, pad_id, score_batch, batch_size=1, max_length=MAX_CONTEXT):
        if (type(batch_size) is not int or batch_size < 1 or not callable(score_batch)
                or type(max_length) is not int or not 1 <= max_length <= MAX_CONTEXT):
            raise ValueError("양의 batch 크기와 명시 likelihood callback이 필요합니다.")
        token_ids([pad_id], vocab_size)
        self.vocab_size, self.pad_id, self.max_length = vocab_size, pad_id, max_length
        self.batch_size, self.score_batch = batch_size, score_batch
        self.records, self.forward_batches = [], 0

    def score_encoded(self, requests):
        if self.score_batch is None:
            raise RuntimeError("종료한 adapter는 다시 실행하지 않습니다.")
        # Plan the entire call before any forward: no selectively truncated,
        # partially scored candidate set after a later long-continuation error.
        plans = [plan_tokens(context, continuation, self.vocab_size, self.max_length)
                 for _, context, continuation in requests]
        results = []
        for offset in range(0, len(plans), self.batch_size):
            block = plans[offset:offset + self.batch_size]
            batch = padded_batch(block, self.pad_id, self.vocab_size)
            scored = list(self.score_batch(batch))
            if len(scored) != len(block):
                raise ValueError("likelihood callback 결과 수가 원 요청과 다릅니다.")
            for plan, score in zip(block, scored):
                if (not isinstance(score, (tuple, list)) or len(score) != 2 or type(score[1]) is not bool
                        or isinstance(score[0], bool) or not isinstance(score[0], (int, float))
                        or not math.isfinite(score[0]) or score[0] > 0):
                    raise ValueError("유한한 전체 loglikelihood와 실제 greedy bool이 필요합니다.")
                results.append((float(score[0]), score[1]))
                self.records.append(dict(context_tokens=plan.original_context_tokens,
                    kept_context_tokens=plan.kept_context_tokens, continuation_tokens=len(plan.continuation_ids),
                    truncated_context_tokens=plan.truncated_context_tokens, input_tokens=len(plan.input_ids)))
            self.forward_batches += 1
        return results

    def diagnostics(self):
        return dict(schema=SCHEMA, profile="CORE6_LIKELIHOOD_ONLY", max_length=self.max_length,
            requests_scored=len(self.records), forward_batches=self.forward_batches,
            context_truncated_requests=sum(record["truncated_context_tokens"] > 0 for record in self.records),
            context_tokens_removed=sum(record["truncated_context_tokens"] for record in self.records),
            continuation_tokens_scored=sum(record["continuation_tokens"] for record in self.records),
            token_lengths=list(self.records), long_continuation_policy="ERROR_NOT_PARTIAL_TRUNCATION_NOT_ROLLING",
            normalization="SUM_CONTINUATION_LOGPROB_ONLY; TASK_OWNS_ACC_NORM", rolling=False, generation=False)

    def close(self):
        callback, self.score_batch = self.score_batch, None
        if callable(getattr(callback, "close", None)):
            callback.close()


def validate_loaded_runtime(runtime, vocabulary_validator):
    """Static/object contracts supplement, never replace, an existing loader."""
    required = ("model", "cfg", "tokenizer", "torch", "precision", "checkpoint_sha256", "tokenizer_sha256")
    if not isinstance(runtime, dict) or any(name not in runtime for name in required):
        raise ValueError("기존 strict loader가 연 명시 runtime이 필요합니다.")
    model, cfg, tokenizer = runtime["model"], runtime["cfg"], runtime["tokenizer"]
    if (runtime["precision"] != "FP32_MATH" or getattr(model, "training", True)
            or getattr(model, "cfg", None) is not cfg or cfg.max_seq_len < MAX_CONTEXT
            or getattr(cfg, "attn_kind", "softmax_cla") != "softmax_cla" or getattr(cfg, "mtp_aux", False)):
        raise ValueError("eval·FP32 MATH·causal·문맥1024·MTPoff인 기존 runtime이 필요합니다.")
    vocabulary_validator(tokenizer, dict(vocab_size=cfg.vocab_size), allow_extra_special=False)
    if tokenizer.get_vocab_size() != cfg.vocab_size or tuple(model.emb.weight.shape)[0] != cfg.vocab_size:
        raise ValueError("실제 tokenizer/cfg/embedding 어휘가 다릅니다.")
    for name in ("checkpoint_sha256", "tokenizer_sha256"):
        value = runtime[name]
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdefABCDEF" for c in value):
            raise ValueError("기존 strict runtime의 실제 SHA가 필요합니다: " + name)
    return cfg.vocab_size


class TorchLikelihood:
    """Explicit-runtime bridge. No torch import and no model construction here."""
    def __init__(self, runtime, forward):
        self.runtime, self.forward = runtime, forward

    def __call__(self, batch):
        if self.runtime is None:
            raise RuntimeError("종료한 numerical bridge입니다.")
        runtime, forward = self.runtime, self.forward
        torch = runtime["torch"]
        route = runtime.get("route")
        if route is not None:
            route.assert_active()
        device = next(runtime["model"].parameters()).device
        if device.type == "cuda" and (torch.backends.cuda.matmul.allow_tf32 or torch.backends.cudnn.allow_tf32):
            raise ValueError("FP32 MATH 대조는 기존 runtime에서 TF32가 이미 꺼져 있어야 합니다.")
        inputs = torch.tensor(batch["input_ids"], dtype=torch.long, device=device)
        with torch.no_grad(), torch.autocast(device.type, enabled=False):
            logits = forward(inputs, use_cache=False)
            if (not torch.is_tensor(logits) or logits.dtype != torch.float32
                    or tuple(logits.shape) != (*inputs.shape, runtime["cfg"].vocab_size)):
                raise ValueError("실제 FP32 full logits의 batch/위치/어휘 shape가 다릅니다.")
            results = []
            for index, (start, length, continuation) in enumerate(zip(batch["target_starts"], batch["lengths"], batch["continuation_ids"])):
                target = torch.tensor(continuation, dtype=torch.long, device=device)
                selected = logits[index, start:length, :]
                if selected.shape[0] != len(continuation) or not bool(torch.isfinite(selected).all()):
                    raise ValueError("모든 continuation 위치의 유한한 full logits가 필요합니다.")
                logps = torch.nn.functional.log_softmax(selected.float(), dim=-1)
                values = logps.gather(-1, target.unsqueeze(-1)).squeeze(-1)
                if not bool(torch.isfinite(values).all()):
                    raise ValueError("continuation logprob가 유한하지 않습니다.")
                results.append((float(values.sum()), bool(selected.argmax(-1).eq(target).all())))
        if route is not None:
            route.assert_active()
        return results

    def close(self):
        self.runtime = self.forward = None


def _adapter_type(template_lm):
    """Injection seam for stdlib mocks; production passes the verified class."""
    class TinyLMOfficial(template_lm):
        backend = "causal"

        def __init__(self, *, core, tokenizer, prefix_id, eos_id, provenance):
            super().__init__()
            self.core, self.tokenizer = core, tokenizer
            self._prefix_id, self._eos_id = prefix_id, eos_id
            self.provenance = provenance
            self._device = provenance.get("device")

        @property
        def eot_token_id(self):
            return self._eos_id

        @property
        def prefix_token_id(self):
            return self._prefix_id

        @property
        def max_length(self):
            return self.core.max_length

        @property
        def batch_size(self):
            return self.core.batch_size

        @property
        def tokenizer_name(self):
            return "tinylm-native-" + self.provenance["tokenizer_sha256"]

        def tok_encode(self, string, add_special_tokens=None, **kwargs):
            if self.tokenizer is None:
                raise RuntimeError("종료한 adapter입니다.")
            if not isinstance(string, str) or kwargs or (add_special_tokens is not None and type(add_special_tokens) is not bool):
                raise ValueError("native 문자열 encode와 명시 special 정책만 지원합니다.")
            encoded = self.tokenizer.encode(string, add_special_tokens=False if add_special_tokens is None else add_special_tokens)
            return list(token_ids(encoded.ids, self.core.vocab_size, empty=True))

        def tok_decode(self, tokens, **kwargs):
            return self.tokenizer.decode(list(token_ids(tokens, self.core.vocab_size, empty=True)), **kwargs)

        def loglikelihood(self, requests, disable_tqdm=False):
            if self.core.score_batch is None:
                raise RuntimeError("종료한 adapter입니다.")
            requests = list(requests)
            for request in requests:
                args = request.args
                if (not isinstance(args, (tuple, list)) or len(args) != 2
                        or any(not isinstance(value, str) for value in args) or not args[1]):
                    raise ValueError("공식 (context, nonempty continuation) 요청이 필요합니다.")
                if args[0] == "" and not self.tok_encode(args[1], add_special_tokens=False):
                    raise ValueError("빈 context의 continuation이 빈 ID열로 변환됐습니다.")
            # Keep upstream _encode_pair AND empty-prefix logic unmodified.
            return super().loglikelihood(requests, disable_tqdm=disable_tqdm)

        def _loglikelihood_tokens(self, requests, **kwargs):
            if any(name != "disable_tqdm" for name in kwargs):
                raise ValueError("지원하지 않는 likelihood 실행 옵션입니다.")
            requests = list(requests)
            result = self.core.score_encoded(requests)
            for (key, _, _), value in zip(requests, result):
                if key is not None:
                    self.cache_hook.add_partial("loglikelihood", key, value)
            return result

        def loglikelihood_rolling(self, requests, disable_tqdm=False):
            raise NotImplementedError("Core6 전용 adapter는 rolling likelihood를 지원하지 않습니다.")

        def generate_until(self, requests, disable_tqdm=False):
            raise NotImplementedError("Core6 전용 adapter는 자유 생성을 지원하지 않습니다.")

        def apply_chat_template(self, *args, **kwargs):
            raise NotImplementedError("공식 Core6 대조는 chat template OFF입니다.")

        def chat_template(self, chat_template=False):
            if chat_template is not None and chat_template is not False:
                raise ValueError("공식 Core6 대조는 chat template OFF입니다.")
            return None

        def diagnostics(self):
            return dict(self.core.diagnostics(), provenance=self.provenance)

        def close(self):
            self.core.close()
            self.tokenizer = None

    TinyLMOfficial.__name__ = "TinyLMOfficialLikelihood"
    return TinyLMOfficial


def prepare_harness(*, source_root=SOURCE, manifest_path=MANIFEST, runtime_root=None):
    """Explicit package import only; run before opening any model runtime."""
    receipt = verify_harness_source(manifest_path, source_root)
    distribution = importlib.metadata.distribution("lm_eval")
    if distribution.version != VERSION:
        raise ValueError("설치한 공식 harness metadata 버전이 다릅니다.")
    approved = Path(runtime_root or receipt["source_root"]).absolute()
    for relative in RUNTIME_FILES:
        if sha256_file(approved / relative) != receipt["critical_files"][relative]:
            raise ValueError("import 전 harness runtime source가 고정값과 다릅니다: " + relative)
    # Top-level find_spec does not execute lm_eval.__init__. No nested module
    # lookup here: that would import the parent package before path admission.
    spec = importlib.util.find_spec("lm_eval")
    if spec is None or spec.origin is None or Path(spec.origin).absolute() != approved / "lm_eval/__init__.py":
        raise ValueError("import 전 lm_eval 검색 경로가 명시 runtime과 다릅니다.")
    module = importlib.import_module("lm_eval.api.model")
    binding = verify_imported_framework(module, receipt, distribution, runtime_root=runtime_root)
    return module.TemplateLM, dict(receipt, **binding)


def _from_prepared(runtime, template, framework_provenance, *, batch_size=1, prefix_token_id=None,
                   bos_token="<bos>", eos_token="<eos>", pad_token="<pad>"):
    from tinylm.infer.dialogue import validate_vocabulary
    from scripts.interactive_research_infer import precision_types
    _, PrecisionForward = precision_types(root=Path(runtime.get("root", ROOT)))
    vocab = validate_loaded_runtime(runtime, validate_vocabulary)
    tokenizer = runtime["tokenizer"]
    eos, pad, bos = (tokenizer.token_to_id(token) for token in (eos_token, pad_token, bos_token))
    token_ids([eos, pad], vocab)
    prefix = prefix_token_id if prefix_token_id is not None else bos if bos is not None else eos
    token_ids([prefix], vocab)
    device = str(next(runtime["model"].parameters()).device)
    torch = runtime["torch"]
    if device.startswith("cuda") and (torch.backends.cuda.matmul.allow_tf32 or torch.backends.cudnn.allow_tf32):
        raise ValueError("기존 strict runtime의 TF32가 꺼져 있지 않습니다.")
    numerical = TorchLikelihood(runtime, PrecisionForward(runtime["model"], "fp32_math"))
    provenance = dict(framework_provenance, tokenizer_sha256=runtime["tokenizer_sha256"],
        checkpoint_sha256=runtime["checkpoint_sha256"], checkpoint=runtime.get("checkpoint"),
        strict_loader="CALLER_OWNS_EXISTING_STRICT_RUNTIME; OBJECT_CHECK_IS_NOT_A_WEIGHT_RELOAD",
        device=device, precision="MODEL_FP32_SDPA_MATH_TF32_OFF_REQUIRED", prefix_token_id=prefix,
        prefix_policy="EXPLICIT" if prefix_token_id is not None else "NATIVE_BOS_ELSE_EOS_AS_HFLM",
        eos_token_id=eos, pad_token_id=pad, add_special_tokens_default=False, chat_template=False,
        causal_pad_policy="RIGHT_PAD; NEVER_SCORE_PAD; VALID_PREFIX_CANNOT_ATTEND_FUTURE_PAD",
        framework_git_hash_policy="WRAPPER_MUST_NOT_LABEL_PROJECT_GIT_HASH_AS_HARNESS_COMMIT")
    try:
        core = LikelihoodCore(vocab_size=vocab, pad_id=pad, score_batch=numerical, batch_size=batch_size)
        return _adapter_type(template)(core=core, tokenizer=tokenizer, prefix_id=prefix, eos_id=eos, provenance=provenance)
    except BaseException:
        numerical.close()  # Failed factory tracebacks must not retain the model.
        raise


def create_adapter(runtime, *, source_root=SOURCE, manifest_path=MANIFEST, runtime_root=None, **adapter_options):
    """Explicit opt-in after installation approval; never loads a model.

    `runtime` must remain inside its existing strict loader's context. For the
    fixed research six use research_adapter below. A copied site-packages build
    needs its explicit runtime_root; no sys.path injection/fallback is done.
    """
    template, provenance = prepare_harness(source_root=source_root, manifest_path=manifest_path, runtime_root=runtime_root)
    return _from_prepared(runtime, template, provenance, **adapter_options)


@contextmanager
def research_adapter(model_name, *, source_root=SOURCE, manifest_path=MANIFEST, runtime_root=None, **adapter_options):
    """Reuse the unchanged strict route-aware research loader, no generic load."""
    template, provenance = prepare_harness(source_root=source_root, manifest_path=manifest_path, runtime_root=runtime_root)
    from scripts.interactive_research_infer import resolve_model, selected_runtime
    with selected_runtime(resolve_model(model_name)) as runtime:
        adapter = None
        try:
            adapter = _from_prepared(runtime, template, provenance, **adapter_options)
            yield adapter
        finally:
            if adapter is not None:
                adapter.close()  # Release bridge's model reference before loader exit.
