"""정적 게이트 14 — **설정이 파생하는 집합과 개수가 서로 어긋나지 않는가.**

★왜 생겼나 (2026-08-27, 로그 059 = P074 단계1)
    `run_P074_stage1_dense_depth_curve.bat` 의 학습 팔 **네 개가 전부** 죽었다.

        ZeroDivisionError: division by zero
          init_utils.py:308  avg = sum(...) / len(members)

    `config.n_mlp_groups`(속성)는 `tie_mlp` 를 보고 dense 면 `n_middle` 을 돌려주는데,
    `config.mlp_group_index`(함수)는 **같은 파일 안에서** `tie_mlp` 를 안 보고
    `j // mlp_group` 을 돌려주고 있었다. `mlp_group=2` 인 얕은 dense 프리셋에서
    모델은 MLP 를 `n_middle` 개 만들고, 이식 코드는 그중 절반에 **멤버가 0 개**라고
    답했다. 계측함정 18(적용 대상 집합을 두 곳에서 정의) 그대로다.

    ⚠️**스모크가 못 잡았다** — dense 학생을 `--init-from` 으로 돌린 배치가 그때까지
    하나도 없었기 때문이다. dense 는 늘 **부모**(scratch)였다.

★이 게이트가 보는 것
    프리셋 × {tied, dense} 전수에 대해 **"모델이 만들 개수" 와 "설정이 답하는 집합"이
    일치하는가**. torch 를 쓰지 않는다 — 이 불일치는 전부 `config.py` 안에서 결정된다.

    새 그룹 축을 뚫으면 `AXES` 에 한 줄 넣는다. 그러면 전 프리셋에 자동 적용된다.

    python scripts/check_group_map.py
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tinylm.config import (PRESETS, PRESET_PARENT, build_config,   # noqa: E402
                           mlp_group_index, mlp_group_members, n_unique_mid_mlp)

ARCHS = ("tied", "dense")
SEQS = (1024,)

fails: list[str] = []
checked = 0


def bad(msg: str) -> None:
    fails.append(msg)


def check_partition(name, where, index_fn, members_fn, n_items, n_groups):
    """`index_fn(j) for j in range(n_items)` 이 0..n_groups-1 의 **분할**인가."""
    idx = [index_fn(j) for j in range(n_items)]
    seen = sorted(set(idx))
    if seen and (seen[0] != 0 or seen[-1] != n_groups - 1 or len(seen) != n_groups):
        bad(f"{where} [{name}] 인덱스 상 {seen} 이 0..{n_groups - 1} 을 채우지 않는다 "
            f"(모델은 {n_groups} 개를 만든다)")
        return
    union = []
    for gi in range(n_groups):
        mem = list(members_fn(gi))
        if not mem:
            bad(f"{where} [{name}] 그룹 {gi} 의 멤버가 **0 개**다 — "
                f"평균/이식 코드가 0 으로 나눈다(P074 사망 형태)")
        union += mem
    if sorted(union) != list(range(n_items)):
        bad(f"{where} [{name}] 멤버 합집합 {sorted(union)} != range({n_items})")


for preset in sorted(PRESETS):
    for arch in ARCHS:
        for seq in SEQS:
            where = f"{preset}/{arch}"
            try:
                cfg = build_config(preset, arch, seq, True)
            except Exception as e:                       # noqa: BLE001
                bad(f"{where} build_config 실패: {type(e).__name__}: {e}")
                continue
            checked += 1

            # --- 축 1: 중간 MLP 그룹 -------------------------------------------------
            check_partition("mid_mlp", where,
                            lambda j, c=cfg: mlp_group_index(c, j),
                            lambda gi, c=cfg: mlp_group_members(c, gi),
                            cfg.n_middle, cfg.n_mlp_groups)
            if n_unique_mid_mlp(cfg) != cfg.n_mlp_groups:
                bad(f"{where} n_unique_mid_mlp {n_unique_mid_mlp(cfg)} != "
                    f"n_mlp_groups {cfg.n_mlp_groups} — 같은 수를 두 이름이 다르게 답한다")

            # --- 축 2: 공유 어텐션 그룹 (transformer.py 가 `j // ag` 로 색인한다) ------
            ag = int(getattr(cfg, "attn_group", 1) or 1)
            if ag > 1:
                if cfg.n_middle % ag:
                    bad(f"{where} n_middle {cfg.n_middle} % attn_group {ag} != 0 — "
                        f"모델 생성 시점에 assert 로 죽는다")
                else:
                    check_partition("mid_attn", where,
                                    lambda j, g=ag: j // g,
                                    lambda gi, g=ag: [j for j in range(cfg.n_middle)
                                                      if j // g == gi],
                                    cfg.n_middle, cfg.n_middle // ag)

            # --- 축 3: CLA (owner = i - i % cla_group) --------------------------------
            cg = int(getattr(cfg, "cla_group", 1) or 1)
            if cg < 1:
                bad(f"{where} cla_group {cg} < 1")
            elif cg > 1 and cfg.n_layers % cg:
                bad(f"{where} ⚠️n_layers {cfg.n_layers} % cla_group {cg} != 0 — "
                    f"마지막 그룹이 잘린다. 의도한 것이면 이 줄을 예외로 등록할 것")

            # --- 축 4: 임베딩 인수분해 ------------------------------------------------
            if cfg.emb_rank and cfg.emb_rank > cfg.dim:
                bad(f"{where} emb_rank {cfg.emb_rank} > dim {cfg.dim} — 인수분해가 아니다")

# --- 부모 프리셋 표 ------------------------------------------------------------
for child, parent in sorted(PRESET_PARENT.items()):
    if child not in PRESETS:
        bad(f"PRESET_PARENT 의 자식 {child!r} 이 PRESETS 에 없다")
    if parent not in PRESETS:
        bad(f"PRESET_PARENT[{child!r}] = {parent!r} 이 PRESETS 에 없다")

print("#" * 92)
print("  정적 게이트 14 — 설정 파생 집합 대 개수 일치 (torch 0)")
print("#" * 92)
print(f"  프리셋 {len(PRESETS)} 개 x arch {len(ARCHS)} = 조합 {checked} 개 검사")
if fails:
    print(f"\n  🚫 불일치 {len(fails)} 건\n")
    for f in fails:
        print(f"    - {f}")
    print("\n  ★고치는 곳은 대개 `tinylm/config.py` 의 **단일 소스 함수**다.")
    sys.exit(1)
print("\n  ✅ 전부 일치")
sys.exit(0)
