"""TinyLM 채팅 canonical 스키마와 직렬화기.

> 설계 근거: `docs/20260829_TinyLM-채팅템플릿-설계검토와-제안.md`
> **사용자 승인 2026-08-30** — *"권고안인 선택 D 의 변형 승인"* · 예약 슬롯 **32개**(보수적).

## 이 패키지가 무엇인가

**하나의 canonical 표현**(OpenAI/Claude 공통분모의 블록 모델)에서
**여러 직렬화 문자열**을 뽑는다. 그래서 *"어느 문자열 규약이 나은가"* 를
**같은 데이터 위에서** 비교할 수 있다(사용자 지시 6, 2026-08-29).

```
canonical(dict)  ──serialize("chatml")──>  "<|im_start|>user\\n…<|im_end|>\\n"
                 ──serialize("gemma")───>  "<start_of_turn>user\\n…<end_of_turn>\\n"
                 ──serialize("minimal")─>  "<|user|>…<|end|>"
```

## 🚫경계 — 이 패키지가 하지 않는 것

- **토크나이저를 건드리지 않는다.** 예약 토큰을 어휘에 **심는 것은 P075 단계1**(어휘 재학습)이다.
  여기서는 **어떤 문자열을 쓸지**만 정한다.
- **학습 루프에 안 들어간다.** `loss_mask()` 는 **구간을 돌려줄 뿐**이고
  그것을 쓰는 쪽은 아직 없다(채팅 학습은 미착수).
- 🚫**기본 off·비트 동일**: 이 패키지를 import 하지 않으면 기존 경로는 **한 바이트도 안 바뀐다**(R28).
"""

from .canonical import (
    CANONICAL_VERSION,
    ChatValidationError,
    normalize,
    validate,
)
from .tokens import (
    RESERVED_SLOTS,
    SLOT_NAMES,
    slot_report,
)
from .serialize import (
    SERIALIZERS,
    serialize,
    loss_spans,
)

__all__ = [
    "CANONICAL_VERSION", "ChatValidationError", "normalize", "validate",
    "RESERVED_SLOTS", "SLOT_NAMES", "slot_report",
    "SERIALIZERS", "serialize", "loss_spans",
]
