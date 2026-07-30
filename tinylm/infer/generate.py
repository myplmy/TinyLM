"""추론 테스트기: 체크포인트를 불러와 프롬프트에서 샘플링한다.

KV 캐시 없이 매 스텝 전체 시퀀스를 재계산한다(짧은 정성 확인용). 배포용 최적화 아님.
"""
from __future__ import annotations

from pathlib import Path

import torch
import torch.nn.functional as F

from .. import paths
from ..config import TMTConfig
from ..model import TiedMLPTransformer
from ..data import tokenizer_path

CKPT = paths.RUNS / "ckpt"


def _strip(sd):
    # torch.compile 로 저장하면 '_orig_mod.' 접두사가 붙는다.
    return {k.replace("_orig_mod.", ""): v for k, v in sd.items()}


def load_model(arch="tied", ckpt_path=None, device=None):
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    path = Path(ckpt_path) if ckpt_path else CKPT / f"{arch}.pt"
    st = torch.load(path, map_location=device)
    cfg = TMTConfig(**st["cfg"])
    model = TiedMLPTransformer(cfg).to(device)
    model.load_state_dict(_strip(st["model"]))
    model.set_anneal(1.0)                       # 배포 상태(완전 삼진)에서 추론
    model.eval()
    return model, cfg, device


@torch.no_grad()
def sample(model, cfg, tok, prompt, max_new=100, temperature=0.8, top_k=40, device=None):
    """★샘플링 루프의 **단일 소스**. 이미 로드된 모델을 받아 텍스트를 이어쓴다.

    `generate()`(체크포인트 경로로 매번 로드)와 여러 프롬프트를 한 모델로 돌리는 도구
    (`scripts/probe_prompts.py`)가 **같은 코드**를 쓰도록 분리했다.
    P029 최초판이 이 루프를 따로 구현했다가 `cfg.seq_len`(존재하지 않음, 실제는 `max_seq_len`)
    로 크래시했다 — 중복 구현이 원인이었으므로 여기로 합쳤다.
    """
    device = device or next(model.parameters()).device
    ids = tok.encode(prompt).ids
    x = torch.tensor([ids], dtype=torch.long, device=device)
    dev_type = device if isinstance(device, str) else device.type
    for _ in range(max_new):
        xin = x[:, -cfg.max_seq_len:]
        with torch.autocast(dev_type, dtype=torch.bfloat16, enabled=(dev_type == "cuda")):
            logits = model(xin)[:, -1, :].float()
        if temperature <= 0:
            nxt = logits.argmax(-1, keepdim=True)
        else:
            logits = logits / temperature
            if top_k:
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < v[:, [-1]]] = -float("inf")
            p = F.softmax(logits, dim=-1)
            nxt = torch.multinomial(p, 1)
        x = torch.cat([x, nxt], dim=1)
    return tok.decode(x[0].tolist())


def generate(prompt, arch="tied", data="ko-en", max_new=100, temperature=0.8,
             top_k=40, ckpt_path=None, device=None):
    from tokenizers import Tokenizer
    model, cfg, device = load_model(arch, ckpt_path, device)
    tok = Tokenizer.from_file(str(tokenizer_path(data)))
    text = sample(model, cfg, tok, prompt, max_new=max_new, temperature=temperature,
                  top_k=top_k, device=device)
    print(text)
    return text
