"""P081 단계0 — **어텐션 싱크 실사.** 🚫**아직 못 돈다. 선결이 하나 있다.**

## 왜 이 파일이 "막힘" 상태로 존재하는가

StreamingLLM(arXiv:2309.17453)의 전제는 *"처음 몇 토큰이 어텐션 질량을 크게 먹는다"* 다.
그것이 우리 모델에서도 사실이면 **최근 창 W + 싱크 S 만 남기고** KV 를 버릴 수 있고,
KV 가 **컨텍스트와 무관한 상수**가 된다(P081 §0).

★**그런데 그 질량을 재려면 어텐션 확률 행렬이 필요하다.**
🚫**우리 `Attention.forward` 는 `scaled_dot_product_attention`(SDPA)을 쓴다 —
SDPA 는 출력만 돌려주고 확률을 안 준다.** Flash 백엔드에서는 확률 행렬이
**애초에 물질화되지 않는다.**

⚠️★**이 파일을 "도는 것처럼" 만들지 않은 이유**: 훅으로 입력을 가로채 확률을 다시
계산하는 코드를 쓸 수는 있지만, 그것은 **RoPE·QK-norm·CLA 공유를 forward 밖에서 재현**하는
일이고 **두 곳에서 같은 규약을 정의하는 것**(함정 18)이다. 그렇게 만든 수치가 실제
어텐션과 다르면 **조용히 틀린다.**

## ★선결 — 한 가지 (⚙0.3h)

`tinylm/model/modules.py` 의 `Attention.forward` 에 **진단 전용 경로**를 연다:

    def forward(self, ..., return_probs=False):
        if return_probs:                      # ★기본 False = 비트 동일
            att = (q @ k.transpose(-2, -1)) * scale + mask
            p = att.softmax(-1)
            return p @ v, p
        return F.scaled_dot_product_attention(...)

★**요건 셋**
  1. **기본 off 에서 비트 동일**이어야 한다(기존 런 수치를 안 바꾼다)
  2. 그 경로를 **켠 스모크 팔**을 함께 넣는다(함정 37)
  3. `check_smoke_fields` 가 볼 필드가 없으므로 **동적 스모크로만** 검증된다

## 그 다음 이 파일이 할 일

| 지표 | 판정 |
|---|---|
| 위치 0~3 이 받는 어텐션 질량 비중(층·헤드 평균) | ^> 10% -> ✅싱크 있음 / 3~10% 경계 / ^< 3% -> 🚫없음 |
| 층별 분포 | 논문은 깊은 층일수록 크다고 한다 |
| ★재귀 2회차 통과에서도 같은가 | P081 S3 |

⚠️★**균등 기준선을 반드시 함께 인쇄한다** — seq T 에서 앞 4토큰의 균등 몫은 `4/T` 다.
T=1024 면 **0.39%** 이므로 *"10%"* 는 균등의 26배다. 🚫**그 기준선 없이 크다고 말할 수 없다.**
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ★성공 기준값 — 구현 뒤에 쓴다. `check_diag_data` 가 이 상수의 존재를 본다(함정 32).
SINK_YES = 0.10
SINK_NO = 0.03


def main() -> int:
    print("=" * 96)
    print("  P081 단계0 — 어텐션 싱크 실사   🚫**아직 못 돈다**")
    print("=" * 96)
    print("  선결: `Attention.forward` 에 `return_probs` 진단 경로 (⚙0.3h)")
    print("        SDPA 는 확률 행렬을 돌려주지 않는다. Flash 백엔드에서는 물질화조차 안 된다.")
    print()
    print("  🚫훅으로 밖에서 재계산하는 우회는 쓰지 않는다 —")
    print("     RoPE·QK-norm·CLA 공유 규약을 두 곳에서 정의하게 되고(함정 18),")
    print("     그렇게 만든 수치가 실제 어텐션과 다르면 **조용히 틀린다**.")
    print()
    print(f"  구현 뒤 판정 기준: 앞 4토큰 질량 ^> {SINK_YES:.0%} 싱크 있음 / "
          f"^< {SINK_NO:.0%} 없음")
    print(f"  ⚠️균등 기준선 4/seq 와 비교해서 읽는다(seq 1024 면 0.39%).")
    print("=" * 96)
    return 2                       # ★0 도 1 도 아니다 — '안 돌았다' 는 뜻


if __name__ == "__main__":
    sys.exit(main())
