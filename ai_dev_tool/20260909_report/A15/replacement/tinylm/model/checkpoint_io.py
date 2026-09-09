"""로컬 TinyLM checkpoint를 정본 cfg로 읽는다. 파일 수정·변환 저장은 하지 않는다."""
from __future__ import annotations

from pathlib import Path


def normalize_state_dict(state):
    out = {}
    for key, value in state.items():
        while key.startswith("_orig_mod."):
            key = key[len("_orig_mod."):]
        if key in out:
            raise ValueError(f"checkpoint prefix 제거 후 key 충돌: {key}")
        out[key] = value
    return out


def read_checkpoint(path):
    import torch
    from ..config import TMTConfig
    # 자체 생성한 로컬 checkpoint만 사용한다. 임의의 외부 pickle을 받는 API가 아니다.
    obj = torch.load(Path(path), map_location="cpu", weights_only=True)
    if not isinstance(obj, dict) or not isinstance(obj.get("cfg"), dict):
        raise ValueError("cfg/model이 있는 TinyLM checkpoint 필요")
    if not isinstance(obj.get("model"), dict):
        raise ValueError("checkpoint model state_dict 없음")
    return normalize_state_dict(obj["model"]), TMTConfig(**obj["cfg"]), obj


def load_trainable(path, device="cpu"):
    from . import TiedMLPTransformer
    state, cfg, meta = read_checkpoint(path)
    model = TiedMLPTransformer(cfg)
    model.load_state_dict(state, strict=True)
    model.to(device)
    model.clear_quant()
    model.set_anneal(1.0)
    model.train()
    return model, cfg, meta
