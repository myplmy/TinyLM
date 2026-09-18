"""TinyLM 학습 recipe의 사용자 승인 기본값.

아키텍처 preset과 학습 recipe를 섞지 않기 위해 optimizer 관련 기본값만 이 모듈이
소유한다. ``matrix_weight_decay=None``은 "WD를 끈다"가 아니라 optimizer별 기존
라우팅을 유지한다는 뜻이다: Muon 행렬 0, AdamW 행렬 0.1. 임베딩·norm·bias·LRM은
각 모델 param-group 규약을 계속 따른다.
"""
from __future__ import annotations


DEFAULT_OPTIMIZER = "muon"
DEFAULT_MUON_LR_MULT = 4.0
DEFAULT_MUON_SCALE = "rms"
DEFAULT_MATRIX_WEIGHT_DECAY = None
DEFAULT_KD = False


def effective_matrix_weight_decay(optimizer: str, override=None) -> float:
    """일반 2-D 행렬에 실제 적용될 WD를 설명용으로 반환한다.

    명시값은 두 optimizer의 행렬에 공통 적용한다. 미지정이면 현재 라우팅 계약대로
    Muon 행렬은 0, AdamW 행렬은 모델 기본 0.1을 쓴다. 임베딩과 특수 그룹에는 이
    함수의 값이 적용되지 않는다.
    """
    if override is not None:
        return float(override)
    if optimizer == "muon":
        return 0.0
    if optimizer == "adamw":
        return 0.1
    raise ValueError(f"모르는 optimizer: {optimizer!r}")
