"""A05: 계측과 학습이 공유하는 assistant-only token/label 계약."""
from __future__ import annotations
from dataclasses import dataclass

from .canonical import normalize, validate
from .serialize import serialize, loss_spans

IGNORE_INDEX = -100
CONTRACT = "canonical-offsets-assistant-v1-no-packing"


@dataclass
class EncodedSample:
    ident: str
    text: str
    input_ids: list
    labels: list
    total_tokens_before: int
    assistant_tokens_before: int
    boundary_tokens_masked: int
    truncated_tokens: int

    @property
    def loss_tokens(self):
        # input_ids[:-1]가 labels[1:]를 예측한다.
        return sum(value != IGNORE_INDEX for value in self.labels[1:])


def encode_sample(record, tok, *, kind="chatml", max_length=1025,
                  train_thinking=True, overflow="error", objective="assistant"):
    if max_length < 2 or overflow not in ("error", "truncate"):
        raise ValueError("max_length/overflow 오류")
    conv = validate(normalize(record))
    if not conv["messages"] or conv["messages"][-1]["role"] != "assistant":
        raise ValueError("학습 샘플은 assistant 답으로 끝나야 함")
    if not any(m["role"] == "user" for m in conv["messages"]):
        raise ValueError("학습 샘플에 user 입력이 없음")
    for message in conv["messages"]:
        if message["role"] == "assistant" and not any(
                b.get("type") == "tool_call" or b.get("text", "").strip()
                for b in message["content"]):
            raise ValueError("비어 있는 assistant 본문; 종료 marker만 학습하지 않음")
    text = serialize(conv, kind)
    spans = loss_spans(conv, kind, train_thinking=train_thinking)
    encoded = tok.encode(text, add_special_tokens=False)
    if not hasattr(encoded, "offsets") or len(encoded.offsets) != len(encoded.ids):
        raise ValueError("문자 offset을 제공하는 tokenizer 필요")
    if any(not (0 <= start < end <= len(text)) for start, end in encoded.offsets):
        raise ValueError("빈/범위 밖 offset: 자동 special-token 주입 및 offset 단위 확인")
    labels, boundary = [], 0
    for token, (start, end) in zip(encoded.ids, encoded.offsets):
        inside = any(start >= left and end <= right for left, right in spans)
        crosses = not inside and any(start < right and end > left for left, right in spans)
        boundary += int(crosses)
        labels.append(token if objective == "all" or inside else IGNORE_INDEX)
    if objective not in ("assistant", "all"):
        raise ValueError("objective는 assistant/all")
    before = len(encoded.ids)
    assistant_before = sum(any(start >= left and end <= right for left, right in spans)
                           for start, end in encoded.offsets)
    if before > max_length and overflow == "error":
        raise ValueError(f"샘플 {record.get('meta', {}).get('id')}: {before} > {max_length}; 자동 절단하지 않음")
    ident = str(record.get("id") or record.get("meta", {}).get("id") or "")
    sample = EncodedSample(ident, text, list(encoded.ids[:max_length]), labels[:max_length],
                           before, assistant_before, boundary, max(0, before - max_length))
    if sample.loss_tokens < 1:
        raise ValueError(f"{ident}: shift 후 유효 손실 token 0개")
    return sample


def encode_text_sample(record, tok, *, max_length, overflow="error"):
    """C0의 별도 clean 원문 학습. 메타/정답을 text 뒤에 조용히 덧붙이지 않는다."""
    text = record.get("text")
    if not isinstance(text, str) or not text:
        raise ValueError("text 형식에는 비어 있지 않은 text 필요")
    ids = tok.encode(text, add_special_tokens=False).ids
    eos = tok.token_to_id("<eos>")
    if eos is not None:
        ids = ids + [eos]
    if len(ids) > max_length and overflow == "error":
        raise ValueError("C0 text가 max_length 초과; 명시적으로 분할된 자료 필요")
    sample = EncodedSample(str(record.get("id", "")), text, ids[:max_length], ids[:max_length],
                           len(ids), 0, 0, max(0, len(ids) - max_length))
    if sample.loss_tokens == 0:
        raise ValueError("C0 shift 후 token 0개")
    return sample


def collate_samples(samples, *, pad_id=0, device="cpu"):
    import torch
    if not samples:
        raise ValueError("빈 batch")
    width = max(len(s.input_ids) for s in samples)
    ids = torch.full((len(samples), width), pad_id, dtype=torch.long, device=device)
    labels = torch.full_like(ids, IGNORE_INDEX)
    for i, sample in enumerate(samples):
        ids[i, :len(sample.input_ids)] = torch.tensor(sample.input_ids, device=device)
        labels[i, :len(sample.labels)] = torch.tensor(sample.labels, device=device)
    # 오른쪽 padding은 causal mask상 실제 target의 과거 입력에 들어가지 않는다.
    return ids[:, :-1].contiguous(), labels[:, 1:].contiguous()


def masked_ce_sum(logits, targets, *, chunk=256):
    import torch.nn.functional as F
    if logits.shape[:2] != targets.shape:
        raise ValueError("logits와 shifted labels shape 불일치")
    flat, truth = logits.reshape(-1, logits.size(-1)), targets.reshape(-1)
    count = int((truth != IGNORE_INDEX).sum())
    if count == 0:
        raise ValueError("손실 token 0개")
    total = None
    for start in range(0, truth.numel(), max(1, chunk)):
        y = truth[start:start + max(1, chunk)]
        if not bool((y != IGNORE_INDEX).any()):
            continue
        term = F.cross_entropy(flat[start:start + len(y)].float(), y,
                               ignore_index=IGNORE_INDEX, reduction="sum")
        total = term if total is None else total + term
    return total, count


def sample_totals(samples):
    return {"records": len(samples),
            "serialized_tokens_before_truncation": sum(s.total_tokens_before for s in samples),
            "assistant_tokens_before_truncation": sum(s.assistant_tokens_before for s in samples),
            "serialized_tokens_used": sum(len(s.input_ids) for s in samples),
            "shifted_loss_tokens": sum(s.loss_tokens for s in samples),
            "boundary_tokens_masked": sum(s.boundary_tokens_masked for s in samples),
            "truncated_tokens": sum(s.truncated_tokens for s in samples),
            "truncated_records": sum(s.truncated_tokens > 0 for s in samples),
            "packing": False, "contract": CONTRACT}
