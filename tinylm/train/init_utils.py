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

    # ★2026-08-07(P046) — `--emb-rank` 로 E 를 바꾸면 임베딩 shape 이 교사와 다르다.
    #   종전에는 `load_state_dict` 가 **strict 라 즉사**했다. 지금은 **건너뛰고 크게 알린다** —
    #   조용히 넘기면 "부모초기화했다" 고 믿는 채로 임베딩만 난수인 런이 생긴다.
    #   어텐션·MLP shape 은 E 에 의존하지 않으므로 그쪽 이식은 그대로 유효하다.
    if student.emb.weight.shape == teacher.emb.weight.shape:
        student.emb.load_state_dict(teacher.emb.state_dict())
        if student.emb_up is not None:
            student.emb_up.load_state_dict(teacher.emb_up.state_dict())
    else:
        print(f"[init] ★★경고: 임베딩 shape 불일치 — 학생 {tuple(student.emb.weight.shape)} vs "
              f"교사 {tuple(teacher.emb.weight.shape)}")
        print(f"[init] ★임베딩·emb_up 은 **부모초기화하지 않고 난수로 시작**한다"
              f"(어텐션·MLP 는 정상 이식). `--emb-rank` 를 바꾼 런이면 의도된 동작이다.")
        print(f"[init] ⚠️ 이 런을 E 가 같은 런과 비교할 때 **초기화 조건이 다르다**는 것을 명시할 것.")
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
