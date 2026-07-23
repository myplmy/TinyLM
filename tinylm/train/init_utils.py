"""부모(dense) 체크포인트 활용 — KD 교사 로드 & 부모초기화(RRT식 average-init)."""
from __future__ import annotations

from pathlib import Path

import torch

from ..config import TMTConfig
from ..model import TiedMLPTransformer


def _strip(sd):
    return {k.replace("_orig_mod.", ""): v for k, v in sd.items()}


def load_dense(path, device):
    """dense 체크포인트를 그 cfg로 복원한다(KD 교사 또는 초기화 소스)."""
    st = torch.load(path, map_location=device)
    cfg = TMTConfig(**st["cfg"])
    m = TiedMLPTransformer(cfg).to(device)
    m.load_state_dict(_strip(st["model"]))
    return m, cfg


@torch.no_grad()
def init_from_dense(student: TiedMLPTransformer, dense_path, device):
    """dense 가중치를 tied 학생에 이식.
      - 임베딩·최종노름·어텐션(q/o, 소유층 k/v)·adaLN·gate: 인덱스 그대로 복사
      - prelude/coda MLP: 그대로 복사
      - 중간 MLP: dense의 mlp_group개 층을 평균 내어 공유 인스턴스에 넣음(RRT average-init)
    LoRA(있으면)는 U=0 초기화라 시작 시 항등 → 별도 처리 불필요."""
    teacher, _ = load_dense(dense_path, device)
    g = student.cfg.mlp_group

    student.emb.load_state_dict(teacher.emb.state_dict())
    if student.emb_up is not None:
        student.emb_up.load_state_dict(teacher.emb_up.state_dict())
    student.norm_f_scale.data.copy_(teacher.norm_f_scale.data)

    for ls, lt in zip(student.layers, teacher.layers):
        ls.attn.q_proj.weight.data.copy_(lt.attn.q_proj.weight.data)
        ls.attn.o_proj.weight.data.copy_(lt.attn.o_proj.weight.data)
        if ls.attn.owns_kv:                     # 교사(dense, cla1)는 모든 층이 k/v 보유
            ls.attn.k_proj.weight.data.copy_(lt.attn.k_proj.weight.data)
            ls.attn.v_proj.weight.data.copy_(lt.attn.v_proj.weight.data)
        for a in ("a_scale", "a_shift", "m_scale", "m_shift", "gates"):
            getattr(ls, a).data.copy_(getattr(lt, a).data)

    for j, mlp_s in enumerate(student.pre_mlps):
        mlp_s.load_state_dict(teacher.pre_mlps[j].state_dict())
    for j, mlp_s in enumerate(student.coda_mlps):
        mlp_s.load_state_dict(teacher.coda_mlps[j].state_dict())
    for j, mlp_s in enumerate(student.mid_mlps):     # 그룹 평균
        members = [teacher.mid_mlps[j * g + k] for k in range(g)]
        ref = dict(mlp_s.named_parameters())
        for name, ps in ref.items():
            avg = sum(dict(mm.named_parameters())[name].data for mm in members) / g
            ps.data.copy_(avg)
    del teacher
    if device == "cuda":
        torch.cuda.empty_cache()
    print(f"[init] dense 부모초기화 완료 (중간 MLP는 {g}층 평균)  <- {Path(dense_path).name}")
