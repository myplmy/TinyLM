"""작업폴더 기준 경로 + Hugging Face 캐시 리다이렉트.

이 모듈은 `datasets`/`transformers` 를 import 하기 전에 먼저 로드되어야 한다.
그래야 HF_HOME 등이 적용된 상태로 라이브러리가 캐시 위치를 잡는다.
tinylm.__init__ 이 이 모듈을 최상단에서 import 하므로, 패키지를 import 하는 한 보장된다.

경로는 환경변수로 덮어쓸 수 있다:
  TINYLM_DIR   프로젝트 루트 (기본: 이 패키지의 상위 폴더 = Z:\\TinyLM)
  HF_HOME 등   이미 설정돼 있으면 존중한다(setdefault).
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(os.environ.get("TINYLM_DIR", Path(__file__).resolve().parents[1]))

HF_DIR     = Path(os.environ.get("TINYLM_HF", ROOT / "HF"))  # 모델·데이터셋 로컬 캐시
DATA_CACHE = ROOT / "data_cache"   # 토큰화된 바이너리(크기별 재사용)
RUNS       = ROOT / "runs"         # 체크포인트·로그

# HF 캐시를 '강제로' 작업폴더 하위(HF/)로 돌린다.
# 사용자 환경의 외부 HF_HOME 이 다른 곳을 가리켜도 무시하고 여기로 받는다.
# (원래 위치를 쓰고 싶으면 실행 전 TINYLM_HF=<경로> 로 지정.)
os.environ["HF_HOME"] = str(HF_DIR)
os.environ["HF_HUB_CACHE"] = str(HF_DIR / "hub")
os.environ["HF_DATASETS_CACHE"] = str(HF_DIR / "datasets")
os.environ.pop("TRANSFORMERS_CACHE", None)   # 옛 변수가 외부를 가리키면 제거
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")  # 단편화 완화

for _d in (HF_DIR, HF_DIR / "hub", DATA_CACHE, RUNS, RUNS / "ckpt", RUNS / "logs"):
    _d.mkdir(parents=True, exist_ok=True)
