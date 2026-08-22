"""★★P067 — **외부 HF 모델의 config·토크나이저를 읽는다. torch 를 쓰지 않는다.**

⚠️★**왜 `train/hf_teacher.py` 에서 분리했나**: `tinylm.train.__init__` 이 `trainer` 를
  import 하고 그것이 `torch` 를 끌어온다. 그러면 **config 만 읽는 진단조차 torch 를
  요구**하게 되고, `--spec-only` 같은 값싼 게이트가 값싸지 않게 된다.
  **읽기만 하는 것은 읽기만 하는 곳에 둔다.**
"""
from __future__ import annotations

import json
from pathlib import Path


def _snapshot(root: Path) -> Path:
    """HF 캐시 폴더든 평평한 폴더든 **`config.json` 이 있는 디렉터리**를 찾는다.

    ⚠️`HF/models--org--name/snapshots/<sha>/` 형태와 `HF/models--name/` 평평한 형태가
    **둘 다 이 저장소에 실재한다**(2026-08-22 실사). 하나만 가정하면 조용히 실패한다.
    """
    root = Path(root)
    if (root / "config.json").exists():
        return root
    snaps = sorted((root / "snapshots").glob("*")) if (root / "snapshots").is_dir() else []
    for s in snaps:
        if (s / "config.json").exists():
            return s
    raise FileNotFoundError(f"config.json 을 못 찾았다: {root} (snapshots 도 확인함)")


def teacher_spec(path) -> dict:
    """**모델을 로드하지 않고** config 만 읽는다. GPU 0 · 메모리 0.

    ★배치·계획서가 *"이 교사를 쓰면 vocab 이 얼마가 되는가"* 를 **학습 전에** 알아야 한다.
    """
    d = _snapshot(path)
    c = json.loads((d / "config.json").read_text(encoding="utf-8"))
    t = c.get("text_config", c)
    return {
        "dir": str(d),
        "model_type": c.get("model_type"),
        "arch": (c.get("architectures") or [None])[0],
        "text_only": "text_config" not in c and "vision_config" not in c,
        "n_layers": t.get("num_hidden_layers"),
        "hidden": t.get("hidden_size"),
        "vocab_size": t.get("vocab_size"),
        "dtype": t.get("torch_dtype") or t.get("dtype") or c.get("dtype"),
        "tie": t.get("tie_word_embeddings", True),
        "has_tokenizer": (d / "tokenizer.json").exists(),
    }




def load_hf_tokenizer(path):
    """`tokenizers.Tokenizer` 를 돌려준다 — ★**우리 데이터 경로는 `tokenizers` 만 쓴다.**

    `transformers` 의 `AutoTokenizer` 를 쓰면 의존이 데이터 준비까지 번진다.
    HF 모델 폴더의 `tokenizer.json` 은 **`tokenizers` 포맷 그대로**이므로 직접 읽는다.
    """
    from tokenizers import Tokenizer
    d = _snapshot(path)
    f = d / "tokenizer.json"
    if not f.exists():
        raise FileNotFoundError(
            f"{f} 가 없다. ★`tokenizer.model`(SentencePiece)만 있는 모델은 "
            f"`tokenizer.json` 으로 변환이 필요하다 — 이 경로는 아직 구현하지 않았다.")
    return Tokenizer.from_file(str(f)), str(d)
