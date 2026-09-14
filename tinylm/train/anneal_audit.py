# -*- coding: utf-8 -*-
"""Opt-in 삼진 anneal 동역학 계측.

기본 학습 경로에서는 이 모듈을 import하지 않는다. 사용자가 ``--anneal-audit``를
명시한 fresh run에서만 유니크 ``TLinear`` 표본의 양자화 거리·코드 변화·점유율·
경계 여유와 gradient/update RMS를 JSONL로 남긴다. CPU 복사와 동기화가 있으므로
속도 판정 팔에는 사용하지 않는다.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import torch

from ..audit_io import write_json_new
from ..model.ternary import TLinear, _group_of, ternary


def _jsonable(value):
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    return str(value)


def _finite(value):
    value = float(value)
    return value if math.isfinite(value) else None


def _rms(tensor):
    if tensor is None or tensor.numel() == 0:
        return None
    return _finite(tensor.detach().float().square().mean().sqrt())


def _quantile(tensor, q, max_elements=65_536):
    if tensor.numel() == 0:
        return None
    flat = tensor.detach().float().reshape(-1)
    if flat.numel() > max_elements:
        stride = math.ceil(flat.numel() / max_elements)
        flat = flat[::stride][:max_elements]
    return _finite(torch.quantile(flat, q))


def _grid_margin(module, latent):
    """코드 경계까지의 상대 여유. sparse34와 TWN은 의미가 달라 kind를 함께 기록한다."""
    out_features, in_features = latent.shape
    group = _group_of(module.cfg, in_features)
    grouped = latent.detach().float().abs().reshape(out_features, in_features // group, group)
    if getattr(module.cfg, "sparse34", False):
        blocks = grouped.reshape(out_features, in_features // group, group // 4, 4)
        pair = torch.topk(blocks, k=2, dim=-1, largest=False).values
        margin = (pair[..., 1] - pair[..., 0]) / pair[..., 1].clamp_min(1e-12)
        kind = "sparse34_selection"
    else:
        threshold = float(module.cfg.twn_thr_ratio) * grouped.mean(dim=2, keepdim=True)
        margin = (grouped - threshold).abs() / threshold.abs().clamp_min(1e-12)
        kind = "twn_threshold"
    return {"kind": kind, "p10": _quantile(margin, 0.10), "median": _quantile(margin, 0.50)}


def _quant_stats(module, previous_code):
    with torch.no_grad():
        latent = module._w().detach()
        quantized = ternary(latent, module.cfg).detach()
        code = torch.sign(quantized).to(torch.int8)
        latent_norm = torch.linalg.vector_norm(latent.float())
        distance = torch.linalg.vector_norm((latent - quantized).float())
        norm_distance = distance / latent_norm.clamp_min(1e-12)
        total = max(code.numel(), 1)
        occupancy = {
            "negative": _finite((code < 0).sum() / total),
            "zero": _finite((code == 0).sum() / total),
            "positive": _finite((code > 0).sum() / total),
        }
        code_cpu = code.cpu()
        flip = None
        if previous_code is not None:
            if tuple(previous_code.shape) != tuple(code_cpu.shape):
                raise ValueError("anneal audit 코드 shape가 실행 중 바뀌었다")
            flip = _finite((previous_code != code_cpu).float().mean())
        return {
            "quant_distance_l2_over_weight_l2": _finite(norm_distance),
            "code_flip_rate_since_previous_sample": flip,
            "occupancy": occupancy,
            "grid_margin": _grid_margin(module, latent),
        }, code_cpu


class AnnealAudit:
    """낮은 빈도로 유니크 TLinear 표본의 anneal 동역학을 기록한다."""

    def __init__(self, path, model, *, every, max_modules=8, contract=None):
        self.path = Path(path)
        self.contract_path = self.path.with_suffix(".contract.json")
        if self.path.exists() or self.contract_path.exists():
            raise FileExistsError("anneal-audit 출력이 이미 있음")
        if every < 1 or max_modules < 1:
            raise ValueError("anneal audit every/max_modules는 양수")

        # named_modules()는 같은 공유 객체를 한 번만 내놓는다. id도 다시 확인해 계약을 고정한다.
        candidates, seen = [], set()
        for name, module in model.named_modules():
            if not isinstance(module, TLinear) or id(module) in seen:
                continue
            if module.weight.numel() == 0 or not module.weight.requires_grad:
                continue
            seen.add(id(module))
            candidates.append((name, module))
        candidates.sort(key=lambda item: item[0])
        if not candidates:
            raise ValueError("anneal audit 대상 TLinear가 0개다")
        count = min(max_modules, len(candidates))
        indices = (sorted({round(i * (len(candidates) - 1) / max(1, count - 1))
                           for i in range(count)}) if count else [])
        self.selected = [candidates[i] for i in indices]
        self.every = int(every)
        self.previous_codes = {}
        self.pending = None

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("x", encoding="utf-8", newline="\n"):
            pass
        try:
            write_json_new(self.contract_path, {
                "schema": "tinylm.anneal-audit.v1",
                "contract": _jsonable(contract),
                "selected_modules": [name for name, _ in self.selected],
                "sample_note": "이름 순서에서 고르게 고른 유니크 TLinear 표본; 전체 층 분포로 일반화 금지",
                "metric_note": ("quant_distance는 완전 ternary Wq 기준이며 현재 blend W_forward 거리가 아니다. "
                                "grid_margin kind가 다른 TWN/sparse34를 직접 합산하지 않는다. "
                                "grid_margin quantile은 이름·평탄화 순서의 결정적 최대 65536개 표본이다"),
                "timing_note": "detach·CPU 복사·동기화가 step timing에 포함되므로 속도 판정 팔에 사용 금지",
            })
        except Exception:
            # 생성 도중 계약 쓰기가 실패하면 빈 본문만 남겨 성공 산출물처럼 보이는 것을 막는다.
            self.path.unlink(missing_ok=True)
            raise

    def before(self, step, *, progress, anneal):
        self.pending = None
        if step % self.every:
            return False
        rows = []
        for name, module in self.selected:
            stats, code = _quant_stats(module, self.previous_codes.get(name))
            self.previous_codes[name] = code
            before = module.weight.detach().float().cpu().clone()
            rows.append({
                "name": name,
                "module": module,
                "before": before,
                "gradient_rms_after_clip": _rms(module.weight.grad),
                "quant": stats,
            })
        self.pending = {
            "step": int(step), "progress": float(progress), "quant_anneal": float(anneal),
            "matrices": rows,
        }
        return True

    def after(self, step, *, applied):
        if self.pending is None:
            return
        if self.pending["step"] != int(step):
            raise ValueError("anneal audit before/after step 불일치")
        matrices = []
        for item in self.pending["matrices"]:
            before = item["before"]
            after = item["module"].weight.detach().float().cpu()
            update = after - before
            update_rms = _rms(update) if applied else None
            weight_rms = _rms(before)
            matrices.append({
                "name": item["name"],
                "elements": int(before.numel()),
                "gradient_rms_after_clip": item["gradient_rms_after_clip"],
                "update_rms_including_wd": update_rms,
                "weight_rms_before": weight_rms,
                "update_weight_ratio": (update_rms / weight_rms
                                        if update_rms is not None and weight_rms else None),
                **item["quant"],
            })
        row = {
            "step": self.pending["step"],
            "progress": self.pending["progress"],
            "quant_anneal": self.pending["quant_anneal"],
            "applied": bool(applied),
            "matrices": matrices,
        }
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        self.pending = None
