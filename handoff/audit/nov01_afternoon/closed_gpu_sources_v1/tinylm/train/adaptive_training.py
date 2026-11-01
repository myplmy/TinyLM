"""명시 문서 입력의 causal/MNTP 학습 연결. 기존 trainer 기본값은 변경하지 않는다.

호출자는 source.next_update()/state_dict()/load_state_dict()와 명시적 예측-ID
수집기를 제공한다. optimizer 실패는 부분 변경 가능성이 있어 전체 복원 전 재사용을 금지한다.
"""
from __future__ import annotations

from contextlib import nullcontext
from dataclasses import asdict
import copy
import random
import time

import numpy as np
import torch

from .adaptive_masking import HardMaskPolicy
from .hybrid_mntp import causal_batch, mntp_batch, objective_mean, uniform_mntp_selection

SCHEMA = "P107_ADAPTIVE_TRAINING_BOUNDARY_V1"


class SyntheticDocumentStream:
    """파일을 읽지 않는 기술 시험용 원천. 정제 코퍼스나 실제 언어 자료가 아니다."""
    def __init__(self, *, batch=2, length=24, micros=4, vocab=64, seed=19):
        if min(batch, length, micros) < 1 or vocab <= 35:
            raise ValueError("양수 fixture 형상과 예약 ID 밖의 어휘가 필요합니다")
        self.batch, self.length, self.micros, self.vocab, self.seed = batch, length, micros, vocab, seed
        self.cursor = 0

    def state_dict(self):
        return dict(cursor=self.cursor, signature=("EXPLICIT_SYNTHETIC_DOCS_V1", self.batch,
                    self.length, self.micros, self.vocab, self.seed))

    def load_state_dict(self, state):
        if state["signature"] != self.state_dict()["signature"] or type(state["cursor"]) is not int or state["cursor"] < 0:
            raise ValueError("다른 source 상태")
        self.cursor = state["cursor"]

    def next_update(self):
        out = []
        for index in range(self.micros):
            generator = torch.Generator().manual_seed(self.seed + self.cursor * self.micros + index)
            tokens = torch.randint(35, self.vocab, (self.batch, self.length + 1), generator=generator)
            docs = (torch.arange(self.length + 1) // max(1, self.length // 4)).repeat(self.batch, 1).long()
            docs[:, -2:] = -1
            tokens[:, -2:] = 0
            out.append((tokens, docs))
        self.cursor += 1
        return out


def cpu_copy(value):
    if isinstance(value, torch.Tensor):
        return value.detach().to("cpu").clone()
    if isinstance(value, dict):
        return {k: cpu_copy(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return type(value)(cpu_copy(v) for v in value)
    return copy.deepcopy(value)


class AdaptiveMNTPTrainer:
    """한 완료 갱신 안에서 별도 목적별 target 합으로 정규화한다.

    uniform: 원형 uniform RNG만 사용. observe: 같은 mask에 실제 통계만 추가.
    adaptive: 완료 TRAIN 관측으로 다음 선정 확률을 갱신. 검증 split 관측은 불허한다.
    """
    def __init__(self, model, optimizers, source, *, policy_config, mode,
                 masked_micros, signature, collect_ids=None, autocast_dtype=None, clip=1.0):
        if (mode not in ("uniform", "observe", "adaptive") or not isinstance(signature, str)
                or len(signature) != 64 or any(c not in "0123456789ABCDEF" for c in signature)):
            raise ValueError("명시한 mode와 64자리 실행 서명이 필요합니다")
        if not optimizers or type(masked_micros) is not int or masked_micros < 1 or clip <= 0:
            raise ValueError("optimizer·masked micro 수·양수 clip이 필요합니다")
        if mode != "uniform" and not callable(collect_ids):
            raise ValueError("실제 예측 ID 수집기를 명시해야 합니다")
        self.model, self.optimizers, self.source = model, list(optimizers), source
        self.config, self.mode, self.masked_micros = policy_config, mode, masked_micros
        self.signature, self.collect_ids, self.autocast_dtype, self.clip = signature, collect_ids, autocast_dtype, clip
        self.policy = None if mode == "uniform" else HardMaskPolicy(policy_config)
        self.uniform_rng = torch.Generator(device="cpu").manual_seed(policy_config.seed)
        self.cursor, self.active, self.dirty = 0, False, False
        params = [p for p in model.parameters() if p.requires_grad]
        assigned = [p for opt in self.optimizers for group in opt.param_groups for p in group["params"]]
        if len({id(p) for p in assigned}) != len(assigned) or set(map(id, assigned)) != set(map(id, params)):
            raise ValueError("각 trainable parameter는 정확히 한 optimizer에 속해야 합니다")
        devices = {p.device for p in params}
        if len(devices) != 1:
            raise ValueError("단일 장치의 모델만 지원합니다")
        self.device = next(iter(devices))

    def _sync(self):
        if self.device.type == "cuda":
            torch.cuda.synchronize(self.device)

    def _rng(self):
        ns = np.random.get_state()
        return dict(torch=torch.get_rng_state().clone(), python=random.getstate(),
                    numpy=(ns[0], ns[1].tolist(), ns[2], ns[3], ns[4]),
                    cuda=torch.cuda.get_rng_state(self.device).cpu() if self.device.type == "cuda" else None)

    def _restore_rng(self, state):
        torch.set_rng_state(state["torch"])
        random.setstate(state["python"])
        ns = state["numpy"]
        np.random.set_state((ns[0], np.array(ns[1], dtype=np.uint32), *ns[2:]))
        if self.device.type == "cuda":
            if state["cuda"] is None:
                raise ValueError("CUDA RNG 누락")
            torch.cuda.set_rng_state(state["cuda"], self.device)
        elif state["cuda"] is not None:
            raise ValueError("다른 장치의 RNG 경계")

    def update(self):
        if self.active or self.dirty:
            raise ValueError("완료 경계 또는 전체 상태 복원이 필요합니다")
        self._sync()
        started = time.perf_counter()
        source_before, rng_before = cpu_copy(self.source.state_dict()), self._rng()
        policy_before = self.policy.state_dict() if self.policy else None
        uniform_before = self.uniform_rng.get_state().clone()
        self.active = True
        optimizer_attempted = False
        policy_started = False
        forward_attempted = False
        metrics = dict(update=self.cursor, executed_input_tokens=0, masked_targets=0, causal_targets=0,
                       model_forwards=0, observed_micro_batches=0, id_seconds=0.0, observe_seconds=0.0)
        self.model.zero_grad(set_to_none=True)
        try:
            pairs = self.source.next_update()
            if not isinstance(pairs, (list, tuple)) or not self.masked_micros < len(pairs):
                raise ValueError("causal과 MNTP를 모두 포함한 명시 micro 입력이 필요합니다")
            if self.policy:
                self.policy.begin_update(self.cursor, split="train", expected_observations=self.masked_micros)
                policy_started = True
            batches = []
            for index, (tokens, docs) in enumerate(pairs):
                if tokens.device.type != "cpu" or docs.device.type != "cpu":
                    raise ValueError("문서 경계와 원 입력은 명시 CPU 텐서여야 합니다")
                if index < len(pairs) - self.masked_micros:
                    batch = causal_batch(tokens, docs, vocab_size=self.config.vocab_size)
                    kind = "causal"
                else:
                    if self.policy:
                        selected, _ = self.policy.select(tokens, docs, adaptive=self.mode == "adaptive")
                    else:
                        selected = uniform_mntp_selection(tokens, docs, vocab_size=self.config.vocab_size,
                            probability=self.config.mask_rate, generator=self.uniform_rng,
                            special_max=self.config.special_max, mask_id=self.config.mask_id)
                    batch = mntp_batch(tokens, docs, selected, vocab_size=self.config.vocab_size,
                                       special_max=self.config.special_max, mask_id=self.config.mask_id)
                    kind = "masked"
                if batch.target_count == 0:
                    raise ValueError("zero-target micro는 재추첨하거나 강제로 채우지 않습니다")
                batches.append((batch, kind))
                metrics[kind + "_targets"] += batch.target_count
            self._sync()
            metrics["prepare_seconds"] = time.perf_counter() - started
            compute_started = time.perf_counter()
            weighted_loss, ticket = 0.0, 0
            for batch, kind in batches:
                context = (torch.autocast(self.device.type, dtype=self.autocast_dtype)
                           if self.autocast_dtype is not None else nullcontext())
                with context:
                    forward_attempted = True
                    logits = self.model(batch.inputs.to(self.device), attention_mask=batch.attention_mask.to(self.device))
                    loss, count = objective_mean(logits, batch.targets.to(self.device))
                    scaled = loss * (0.5 * count / metrics[kind + "_targets"])
                if kind == "masked" and self.policy:
                    at = time.perf_counter()
                    prediction_ids = self.collect_ids(logits.detach(), batch.targets)
                    metrics["id_seconds"] += time.perf_counter() - at
                    at = time.perf_counter()
                    self.policy.observe(batch, prediction_ids, observation_index=ticket)
                    metrics["observe_seconds"] += time.perf_counter() - at
                    ticket += 1
                scaled.backward()
                weighted_loss += float(scaled.detach())
                metrics["executed_input_tokens"] += batch.executed_input_tokens
                metrics["model_forwards"] += 1
                del logits, loss, scaled
            self._sync()
            metrics["forward_backward_observe_seconds"] = time.perf_counter() - compute_started
            at = time.perf_counter()
            if any(p.grad is None for p in self.model.parameters() if p.requires_grad):
                raise ValueError("일부 trainable parameter의 gradient가 없습니다")
            norm = torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.clip, error_if_nonfinite=True)
            metrics["pre_clip_gradient_norm"] = float(norm)
            # 정책 검증을 먼저 닫는다. optimizer 실패는 전체 복원 전 재사용을 거부한다.
            if self.policy:
                metrics["policy_commit"] = self.policy.finish_update(accepted=True)
                policy_started = False
            metrics["observed_micro_batches"] = ticket
            self._sync()
            metrics["clip_and_commit_seconds"] = time.perf_counter() - at
            at = time.perf_counter()
            optimizer_attempted = True
            for opt in self.optimizers:
                opt.step()
            self._sync()
            metrics["optimizer_seconds"] = time.perf_counter() - at
            self.cursor += 1
            self.model.zero_grad(set_to_none=True)
            metrics.update(status="COMPLETE", loss=weighted_loss, seconds=time.perf_counter() - started)
            return metrics
        except BaseException:
            self.model.zero_grad(set_to_none=True)
            if self.policy:
                if policy_started:
                    self.policy.finish_update(accepted=False)
                self.policy.load_state_dict(policy_before)
            self.uniform_rng.set_state(uniform_before)
            self.source.load_state_dict(source_before)
            self._restore_rng(rng_before)
            self.dirty = optimizer_attempted or forward_attempted
            raise
        finally:
            self.active = False

    def state_dict(self):
        if self.active or self.dirty or any(p.grad is not None for p in self.model.parameters()):
            raise ValueError("gradient가 없는 정상 완료 경계에서만 저장할 수 있습니다")
        return dict(schema=SCHEMA, signature=self.signature, mode=self.mode, cursor=self.cursor,
                    config=asdict(self.config), autocast_dtype=str(self.autocast_dtype), clip=self.clip,
                    masked_micros=self.masked_micros, model=cpu_copy(self.model.state_dict()),
                    optimizers=[cpu_copy(o.state_dict()) for o in self.optimizers],
                    policy=self.policy.state_dict() if self.policy else None,
                    uniform_rng=self.uniform_rng.get_state().clone(), source=cpu_copy(self.source.state_dict()),
                    rng=self._rng(), training=self.model.training)

    def load_state_dict(self, state):
        if self.active:
            raise ValueError("진행 중 update에는 복원할 수 없습니다")
        if (state.get("schema") != SCHEMA or state.get("signature") != self.signature
                or state.get("mode") != self.mode or state.get("masked_micros") != self.masked_micros
                or state.get("config") != asdict(self.config) or state.get("clip") != self.clip
                or state.get("autocast_dtype") != str(self.autocast_dtype)
                or len(state.get("optimizers", [])) != len(self.optimizers)
                or type(state.get("cursor")) is not int or state["cursor"] < 0):
            raise ValueError("실행 서명·구조·optimizer·경계가 다릅니다")
        current = self.model.state_dict()
        if set(current) != set(state["model"]) or any(current[n].shape != state["model"][n].shape
                or current[n].dtype != state["model"][n].dtype for n in current):
            raise ValueError("전체 모델 key/shape/dtype이 다릅니다")
        if self.policy:
            probe = HardMaskPolicy(self.config)
            probe.load_state_dict(state["policy"])
            if probe.next_update != state["cursor"]:
                raise ValueError("policy와 모델 경계 불일치")
        elif state["policy"] is not None:
            raise ValueError("uniform 경로에 정책 state가 있습니다")
        self.dirty = True
        try:
            self.model.load_state_dict(state["model"], strict=True)
            if callable(getattr(self.model, "clear_quant", None)):
                self.model.clear_quant()
            for opt, value in zip(self.optimizers, state["optimizers"]):
                opt.load_state_dict(cpu_copy(value))
            if self.policy:
                self.policy.load_state_dict(state["policy"])
            self.uniform_rng.set_state(state["uniform_rng"])
            self.source.load_state_dict(copy.deepcopy(state["source"]))
            self.model.train(state["training"])
            self._restore_rng(state["rng"])
            self.model.zero_grad(set_to_none=True)
            self.cursor, self.dirty = state["cursor"], False
        except BaseException:
            # 실패한 부분 복원을 정상 trainer로 노출하지 않는다.
            raise
