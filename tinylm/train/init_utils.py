"""부모(dense) 체크포인트 활용 — KD 교사 로드 & 부모초기화(RRT식 average-init)."""
from __future__ import annotations

from pathlib import Path

import torch

from ..config import TMTConfig
from ..model import TiedMLPTransformer


def _strip(sd):
    return {k.replace("_orig_mod.", ""): v for k, v in sd.items()}


def _cfg_of(model):
    """모델의 cfg. `load_dense` 가 돌려주는 것과 학생 둘 다 `.cfg` 를 갖는다."""
    return model.cfg


@torch.no_grad()
def _svd_emb_init(student, teacher) -> bool:
    """★P046 단계2(2026-08-07) — **E 가 줄어든 임베딩을 난수가 아니라 SVD 절단으로 시작한다.**

    ## 왜 필요한가 — 결과 030 의 판정이 이것 때문에 무효였다

    `--emb-rank 128` 런(`mC_e128`)은 임베딩만 **난수**로 시작했다. 그 결과:
      · step 0 의 `ce = 10.4051` ≈ `ln(32768) = 10.397` = **완전 무작위 출력**
        (같은 밤의 `mC_g16` 은 7.7742 로 부모초기화 이득이 살아 있었다)
      · **`grad_max = 19.32`** vs 기준선 0.847 — `CLAUDE.md` 판정 기준의
        *"> +0.15 는 grad_max 먼저 확인, **10 이상이면 학습 문제**"* 에 정확히 걸린다
    → **paired Δ +0.1768 은 "E=128 이 나쁘다" 가 아니라 "초기화가 깨졌다" 였다.**

    ## 무엇을 하는가 — 절단이 아니라 **최적 저랭크 근사**

    factorized embedding 의 실효 가중치는 두 행렬의 곱이다:
        `W = emb(V × E) @ emb_up(E × dim)`        shape (V, dim), 랭크 ≤ E
    학생의 E' < E 가 표현할 수 있는 최선은 **`W` 의 랭크 E' 최적 근사**이고,
    그건 Eckart–Young 정리로 **`W` 의 상위 E' 특이값**이다:
        `W ≈ U_k S_k V_k^T` → `emb' = U_k √S_k`, `emb_up' = √S_k V_k^T`
    `√S` 로 나눠 갖는 것은 두 인자의 스케일을 맞춰 초기 gradient 를 고르게 하려는 것이다.

    ⚠️ **이것이 "E=128 을 공짜로 만든다" 는 뜻은 아니다.** 로짓 랭크가 E' 로 제한되는
    구조적 한계는 그대로다. 이 함수는 **그 한계만 남기고 초기화 핸디캡을 걷어낸다** —
    즉 P046 을 "판정 불가" 에서 "판정 가능" 으로 옮기는 것이 전부다.

    ⚠️ **헤드가 임베딩과 tie** 돼 있으므로(결과 025) 이 근사는 입력과 출력에 **동시에**
    영향을 준다. 그래서 `W` 를 근사하는 것이 옳다 — `emb` 만 절단하면 출력 쪽이 깨진다.

    반환: 이식했으면 True, 조건이 안 맞으면 False(호출부가 난수 경로로 간다).
    """
    se, te = student.emb.weight, teacher.emb.weight
    if student.emb_up is None or teacher.emb_up is None:
        return False
    if se.shape[0] != te.shape[0]:              # 어휘가 다르면 이 방법이 성립하지 않는다
        return False
    k, k_t = se.shape[1], te.shape[1]
    if k >= k_t:                                # E 를 **키운** 경우는 절단이 아니다 → 난수
        return False

    W = (te.float() @ teacher.emb_up.weight.float().T)          # (V, dim), 랭크 ≤ k_t
    U, S, Vh = torch.linalg.svd(W, full_matrices=False)
    r = torch.sqrt(S[:k].clamp_min(0))
    student.emb.weight.data.copy_((U[:, :k] * r).to(se.dtype))
    student.emb_up.weight.data.copy_((r[:, None] * Vh[:k]).T.to(student.emb_up.weight.dtype))

    kept = float((S[:k] ** 2).sum() / (S ** 2).sum().clamp_min(1e-12))
    print(f"[init] ★임베딩 SVD 절단 이식 — E {k_t} -> {k}  (난수 아님, P046 단계2)")
    print(f"[init]   보존된 스펙트럼 에너지 {kept*100:.2f}%  "
          f"(σ_1 {float(S[0]):.3f} / σ_{k} {float(S[k-1]):.3f} / σ_{k_t} {float(S[-1]):.3f})")
    print(f"[init] ⚠️ 로짓 랭크가 {k} 로 제한되는 **구조적** 한계는 그대로다 — "
          f"이 이식은 **초기화 핸디캡만** 걷어낸다.")
    return True


def load_dense(path, device):
    """dense 체크포인트를 그 cfg로 복원한다(KD 교사 또는 초기화 소스)."""
    st = torch.load(path, map_location=device)
    cfg = TMTConfig(**st["cfg"])
    m = TiedMLPTransformer(cfg).to(device)
    m.load_state_dict(_strip(st["model"]))
    return m, cfg


@torch.no_grad()
def _depth_map(sc, tc):
    """★P049 선결 (2026-08-14) — **교사 층 → 학생 층 대응표**를 만든다.

    ## 왜 필요한가
    종전 `zip(student.layers, teacher.layers)` 는 **짧은 쪽에서 조용히 잘린다.**
    학생이 교사보다 깊으면(P049: 36층 vs 20층) **학생의 뒤 16층이 난수로 남고**,
    `mid_mlps` 는 `teacher.mid_mlps[j*g+k]` 가 범위를 넘어 **`IndexError` 로 죽는다.**
    결과 038 §9 가 **부모초기화의 몫이 +0.1386 이고 시드 노이즈까지 6.4배 줄인다**는 것을
    보인 뒤라, 이식이 깨진 채로 재면 **아키텍처를 두 번 과소평가**한다.

    ## 무엇을 하는가 — **역할 구간 안에서** 비례 대응
    전역 비례(`i * nt // ns`)를 쓰면 학생의 coda 가 교사의 중간층에서 값을 받는다.
    그래서 **prelude / middle / coda 를 각각 따로** 비례 배치한다:

        student prelude i  ->  teacher prelude  (i * nt_pre  // ns_pre)
        student middle  i  ->  teacher middle   (i * nt_mid  // ns_mid)
        student coda    i  ->  teacher coda     (i * nt_coda // ns_coda)

    ★**깊이가 같으면 항등 사상**이라 종전 동작과 **비트 동일**하다(2배로 늘릴 때만 갈라진다).
    ★깊이를 2배로 늘리면 `i//2` 가 되어 **교사 층을 연속 2회 복제**한다 —
      이는 depth up-scaling 문헌(층 복제)의 표준 형태다.

    ⚠️ **알려진 위험: 잔차 크기가 2배가 된다.** 같은 층을 두 번 통과하면 잔차 기여가
       중복된다. 그래서 `gate_scale` 모드를 함께 둔다(§`init_from_dense`). **어느 쪽이 맞는지는
       추측하지 않고 `run_P049_stage0_init_gate.bat` 이 잰다.**

    ⚠️★**이 함수를 학생이 더 얕을 때 기본으로 쓰면 기존 결과가 재현 불가가 된다.**
       `m100R1p`/`m100R1q`(1+16+1 = 18층)는 종전 `zip` 에서 `[0,1,...,17]` 을 받았는데
       역할 정렬은 `[0, 2,3,...,18]` 을 준다. **역할 정렬이 더 옳지만 결과 032 는 종전
       대응으로 측정됐다.** 그래서 `init_from_dense` 는 **학생이 더 깊을 때만** 이 표를 쓰고,
       얕을 때는 `--depth-init role` 로 **명시적으로** 골라야 한다(함정 2 = 비교 조건 불일치).
    """
    ns = (sc.n_prelude, sc.n_middle, sc.n_coda)
    nt = (tc.n_prelude, tc.n_middle, tc.n_coda)
    idx, base_t, rep = [], 0, []
    for s_n, t_n in zip(ns, nt):
        for i in range(s_n):
            j = min((i * t_n) // s_n, t_n - 1) if t_n else 0
            idx.append(base_t + j)
        base_t += t_n
    for a in idx:                     # 각 교사 층이 몇 번 쓰였나(잔차 중복 계수)
        rep.append(idx.count(a))
    return idx, rep


def init_from_dense(student: TiedMLPTransformer, dense_path, device, depth_init="prop"):
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
    elif _svd_emb_init(student, teacher):
        pass                                   # ★아래 함수가 알린다
    else:
        print(f"[init] ★★경고: 임베딩 shape 불일치 — 학생 {tuple(student.emb.weight.shape)} vs "
              f"교사 {tuple(teacher.emb.weight.shape)}")
        print(f"[init] ★임베딩·emb_up 은 **부모초기화하지 않고 난수로 시작**한다"
              f"(어텐션·MLP 는 정상 이식). `--emb-rank` 를 바꾼 런이면 의도된 동작이다.")
        print(f"[init] ⚠️ 이 런을 E 가 같은 런과 비교할 때 **초기화 조건이 다르다**는 것을 명시할 것.")
    student.norm_f_scale.data.copy_(teacher.norm_f_scale.data)

    # ★2026-08-07(P048) — **깊이·prelude/coda 개수가 다르면 `zip` 이 조용히 자른다.**
    #   `m100R1p`(1+16+1 = 18층)를 `m100` dense(2+16+2 = 20층)에서 초기화하면
    #   학생 층 0..17 이 교사 층 0..17 을 받는데, **학생의 층 17 은 coda 인데 교사의
    #   층 17 은 중간층**이다. 값은 들어가지만 **역할이 다른 층의 가중치**다.
    #   `pre_mlps`·`coda_mlps` 도 학생 개수만큼만 돌아 교사의 뒷것을 버린다.
    #   ⚠️ 이건 버그가 아니라 **의도된 부분 이식**이다. 다만 조용하면 안 된다 —
    #   "부모초기화했다" 고 믿는 채로 조건이 다른 런이 생기고, 그게 결과 015·026 계열
    #   사고의 형태다(계상되지 않은 차이). 그래서 **크게 알리고 무엇이 어긋났는지 적는다**.
    sc, tc = student.cfg, _cfg_of(teacher)
    ns, nt = len(student.layers), len(teacher.layers)
    deeper = ns > nt
    # ★대응표 선택 규칙 — **새 코드는 종전 코드가 죽던 자리에서만 켜진다.**
    #   학생이 더 깊으면 `zip` 은 뒤 층을 난수로 남기고 `mid_mlps` 는 IndexError 였다 →
    #   그때만 역할 정렬 비례표를 쓴다. 얕거나 같으면 **종전 zip 그대로 = 비트 동일**이라
    #   결과 032(`mC_p1c1`)·모든 기존 런이 그대로 재현된다. 역할 정렬을 쓰려면 명시한다.
    if deeper or depth_init == "role":
        lmap, lrep = _depth_map(sc, tc)
    else:
        n = min(ns, nt)
        lmap, lrep = list(range(n)), [1] * n
    assert len(lmap) <= ns, f"대응표 길이 {len(lmap)} ^> 학생 층 {ns}"
    if ns != nt or sc.n_prelude != tc.n_prelude or sc.n_coda != tc.n_coda:
        print(f"[init] ★★경고: 구조 불일치 — 학생 층 {ns}(prelude {sc.n_prelude}/mid {sc.n_middle}/"
              f"coda {sc.n_coda}) vs 교사 층 {nt}(prelude {tc.n_prelude}/mid {tc.n_middle}/coda {tc.n_coda})")
        if deeper or depth_init == "role":
            print(f"[init] ★**역할 구간별 비례 대응**으로 이식한다(P049 선결, 2026-08-14) — "
                  f"prelude↔prelude, middle↔middle, coda↔coda. 종전의 인덱스 zip 이 아니다.")
        else:
            print(f"[init] ★**종전 인덱스 zip** 으로 앞 {len(lmap)}층만 이식한다 — "
                  f"학생의 coda 가 교사의 중간층에서 값을 받는다(역할 불일치). "
                  f"기존 런(결과 032 등)과 **재현 가능하도록 일부러 유지**한다. "
                  f"역할 정렬을 쓰려면 `--depth-init role`.")
        print(f"[init] ★대응표 student->teacher: {lmap}")
        if deeper:
            mx = max(lrep)
            print(f"[init] ★★학생이 교사보다 깊다({ns} ^> {nt}). 교사 층이 최대 **{mx}회 복제**된다.")
            print(f"[init] ⚠️ **잔차 기여가 그만큼 중복된다.** depth_init={depth_init!r} — "
                  f"'prop'=gate 그대로 / 'gate_scale'=gate 를 복제횟수로 나눈다. "
                  f"어느 쪽이 맞는지는 추측하지 않는다. **단계0 게이트가 잰다.**")
        print(f"[init] ⚠️ 이 런을 층수가 같은 런과 비교할 때 **초기화 조건이 다르다**는 것을 명시할 것.")

    seen = {}                    # 교사 층 ti 가 몇 번째로 쓰였나 (identity 모드용)
    for si, ti in enumerate(lmap):
        ls, lt = student.layers[si], teacher.layers[ti]
        ls.attn_mod.q_proj.weight.data.copy_(lt.attn_mod.q_proj.weight.data)
        ls.attn_mod.o_proj.weight.data.copy_(lt.attn_mod.o_proj.weight.data)
        if ls.attn_mod.owns_kv:                     # 교사(dense, cla1)는 모든 층이 k/v 보유
            ls.attn_mod.k_proj.weight.data.copy_(lt.attn_mod.k_proj.weight.data)
            ls.attn_mod.v_proj.weight.data.copy_(lt.attn_mod.v_proj.weight.data)
        for a in ("a_scale", "a_shift", "m_scale", "m_shift", "gates"):
            getattr(ls, a).data.copy_(getattr(lt, a).data)
        # ★복제된 층의 잔차 중복 보정(선택). 'prop' 이면 아무것도 안 한다 = 종전 동작.
        if depth_init == "gate_scale" and lrep[si] > 1:
            ls.gates.data.div_(float(lrep[si]))
        # ★★'identity'(2026-08-13 신설) — **복제된 층의 gate 를 0 으로 만들어 항등으로 시작**한다.
        #   `Layer.forward` 가 `x = x + gates[k] * branch(...)` 이므로 gate 0 = **정확한 항등**이다.
        #   → 36층 학생이 step0 에 **교사 20층과 완전히 같은 함수**가 된다.
        #
        #   ★왜 필요한가 (결과 041): `prop`·`gate_scale` 이 **둘 다 난수보다 나빴다**
        #   (step0 CE 12.72 / 13.48 vs 난수 10.41). 원인은 잔차 크기가 아니라 **합성 불일치** —
        #   교사가 배운 f 에 **f 자신의 출력**을 넣으면 본 적 없는 분포다. 크기를 반으로 줄여도
        #   (gate_scale) 안 고쳐지고, 오히려 교사 층까지 약해져 더 나빠졌다.
        #
        #   문헌: 층 확장 시 **새 블록을 항등으로 초기화**하는 것이 표준이다
        #   (bert2BERT/LLaMA Pro 계열의 zero-init block expansion).
        #   여기서는 출력 projection 을 0 으로 만들 필요 없이 **gate 하나면 된다** —
        #   우리 구조에 이미 층별 residual gate 가 있기 때문이다.
        if depth_init == "identity" and seen.get(ti, 0) > 0:
            ls.gates.data.zero_()
        seen[ti] = seen.get(ti, 0) + 1

    # prelude/coda MLP 도 같은 대응표를 쓴다(구간 안 비례). 개수가 같으면 항등이다.
    for j, mlp_s in enumerate(student.pre_mlps):
        t_j = min((j * tc.n_prelude) // max(sc.n_prelude, 1), tc.n_prelude - 1)
        mlp_s.load_state_dict(teacher.pre_mlps[t_j].state_dict())
    for j, mlp_s in enumerate(student.coda_mlps):
        t_j = min((j * tc.n_coda) // max(sc.n_coda, 1), tc.n_coda - 1)
        mlp_s.load_state_dict(teacher.coda_mlps[t_j].state_dict())
    # 중간 MLP: **학생 그룹이 덮는 학생 중간층들을 대응표로 옮겨** 그 교사 MLP 들을 평균낸다.
    #   ★깊이가 같으면 members == [teacher.mid_mlps[j*g+k]] 로 **종전과 완전히 같다**.
    for j, mlp_s in enumerate(student.mid_mlps):
        if deeper or depth_init == "role":
            t_ids = [min((j * g + k) * tc.n_middle // sc.n_middle, tc.n_middle - 1)
                     for k in range(g)]
        else:
            t_ids = [j * g + k for k in range(g)]        # 종전 = 비트 동일
        members = [teacher.mid_mlps[t] for t in t_ids]
        ref = dict(mlp_s.named_parameters())
        for name, ps in ref.items():
            avg = sum(dict(mm.named_parameters())[name].data for mm in members) / len(members)
            ps.data.copy_(avg)
    del teacher
    if device == "cuda":
        torch.cuda.empty_cache()
    _extra = f", 깊이 확장 {nt}->{ns} 층 depth_init={depth_init}" if deeper else ""
    print(f"[init] dense 부모초기화 완료 (중간 MLP는 {g}층 평균{_extra})  <- {Path(dense_path).name}")
