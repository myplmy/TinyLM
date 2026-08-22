"""★★P067 — **외부 HF 모델을 KD 교사로 쓴다.** (2026-08-22 사용자 지시)

## 실험 목적 (사용자, 2026-08-22)

> *"P067 실험의 목적은 **더 뛰어난 기존 소형 프런티어 모델을 통해 더 학습 효율을 올릴 수
>  있느냐** 및 **KD 가 기존에 유해했던 것은 우리 dense 가 무능했던 것이 원인이 아닌지**도
>  확인하기 위함임."*

★★**두 번째가 진짜 질문이다.** 결과 038 이 **KD 제거가 최대 VRAM 레버**(−59%)이고 품질도
**−0.0208(더 좋다)** 라고 했다. 그런데 **부모초기화 몫 +0.1386 vs KD 몫 −0.0032 = 43배** 였다.
🚫**"KD 가 무용하다" 는 결론은 "우리 교사가 무능하다" 와 구분되지 않는다** — 교사가
**우리와 같은 코퍼스·같은 크기로 학습한 dense** 였기 때문이다. **더 나은 교사면 답이 바뀔 수 있다.**

## ⚠️★왜 토크나이저를 통째로 갈아야 하는가

온라인 KD 는 **교사와 학생의 로짓을 같은 어휘 위에서** 비교한다. 어휘가 다르면 KL 이 정의되지
않는다. 정렬(vocab mapping)은 **정보 손실 + 큰 구현**이므로, **사용자 지시대로 우리가 교사의
토크나이저로 옮겨간다.**

> **사용자**: *"Vocab_size 및 dtype 를 변경(**다른 구조 변경은 최소화**)하여 교사 토크나이저에
>  일치시켜 실험이 실제로 수행될 수 있는 플래그 및 구현 준비할 것."*
> *"토크나이저+임베딩레이어 증가로 모델크기가 커지는 것은 **감수**할 것."*

🚫★**교사의 아키텍처(KV 공유·sliding·linear attention)는 도입하지 않는다** — 결과 053 의
구조 분석은 **참고**이고, **지금 도입하면 기준선을 다시 세워야 하는 교락**이다(사용자 지시).

## ★★비교 유효성 — **이 경로의 런은 기존 런과 직접 비교할 수 없다**

| 바뀌는 것 | 결과 |
|---|---|
| 토크나이저 | ★**val 셋의 토큰 경계가 다르다** → **CE·bpb 를 직접 비교 못 한다**(함정 2) |
| `vocab_size` | 임베딩·헤드 크기가 다르다 → **상주·packed 를 직접 비교 못 한다** |
| 데이터 캐시 | 토큰 id 가 다르다 → **별도 디렉터리**(자동) |

→ ★★**교차비교의 유일한 유효 경로는 `scripts/common_bpb.py`**(공통 원문 bpb, 토크나이저 무관).
**이 파일을 쓰는 모든 실험 결과는 common bpb 로 보고한다.**
"""
from __future__ import annotations

import torch
import torch.nn as nn

from ..hf_spec import _snapshot, teacher_spec, load_hf_tokenizer  # noqa: F401  (재수출)

__all__ = ["HFTeacher", "teacher_spec", "load_hf_tokenizer"]


class HFTeacher(nn.Module):
    """★HF `AutoModelForCausalLM` 을 **우리 교사 인터페이스**(`teacher(x) -> logits`)로 감싼다.

    ⚠️★**dtype 규약**: 교사는 **bf16 으로 돈다**(원본이 bf16 이고 fp32 로 올리면 VRAM 2배).
    🚫**그러나 로짓은 fp32 로 올려서 돌려준다** — KD 의 KL 은 fp32 산술이 정본이고
    (`docs/20260821_학습-dtype-지도`), bf16 로짓으로 log_softmax 를 하면 **꼬리가 뭉개진다**.
    **이 캐스팅이 이 클래스의 존재 이유의 절반이다.**

    ⚠️★**vocab 검증을 생성자에서 한다.** 학생 `cfg.vocab_size` 와 교사 `vocab_size` 가
    다르면 **KL 이 조용히 틀린 축으로 계산**된다(브로드캐스트가 아니라 shape 에러가 나면
    다행이고, 안 나면 재앙이다). **즉시 죽인다.**
    """

    def __init__(self, path, student_vocab: int, device, dtype: str = "bf16",
                 attn_impl: str | None = None):
        super().__init__()
        from transformers import AutoModelForCausalLM
        d = _snapshot(path)
        td = {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": torch.float32}[dtype]
        kw = {"dtype": td}
        if attn_impl:
            kw["attn_implementation"] = attn_impl
        self.m = AutoModelForCausalLM.from_pretrained(str(d), **kw)
        self.m.eval().to(device)
        for p in self.m.parameters():
            p.requires_grad_(False)
        v = int(getattr(self.m.config, "vocab_size", 0) or
                getattr(getattr(self.m.config, "text_config", None), "vocab_size", 0))
        if v != student_vocab:
            raise ValueError(
                f"★교사 vocab {v} != 학생 vocab {student_vocab}. **KD 는 같은 어휘 위에서만 "
                f"정의된다.** `--tokenizer-hf` 로 학생 토크나이저를 교사와 맞추거나, "
                f"`--vocab-size {v}` 를 주세요. (P067 §비교 유효성)")
        self.vocab_size = v
        n = sum(p.numel() for p in self.m.parameters())
        print(f"[kd-hf] 교사 로드 {d.name}  파라미터 {n/1e6:.1f}M  dtype={dtype}  vocab={v}")
        print(f"[kd-hf] ⚠️★로짓은 **fp32 로 올려서** 돌려준다 — bf16 log_softmax 는 꼬리를 뭉갠다")

    @torch.no_grad()
    def forward(self, x):
        out = self.m(input_ids=x)
        lg = out.logits if hasattr(out, "logits") else out[0]
        return lg.float()                       # ★fp32 로 올린다. 위 주석 참조

    # ── 우리 교사 인터페이스가 부르는 것들. HF 모델에는 없으므로 무해하게 받는다.
    def set_anneal(self, v):                     # noqa: D102
        pass

    def freeze_quant(self):                      # noqa: D102
        pass

    def drop_latent(self):                       # noqa: D102
        pass
