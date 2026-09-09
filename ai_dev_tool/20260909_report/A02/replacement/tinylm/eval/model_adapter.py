"""TinyLM/HF 로컬 모델을 같은 명시적 평가 규약으로 호출한다."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from .audit_io import sha256_file, tokenizer_digest


class HFTokenizerAdapter:
    def __init__(self, inner):
        self.inner = inner

    def encode(self, text, add_special_tokens=False):
        data = self.inner(text, add_special_tokens=add_special_tokens, return_offsets_mapping=True)
        return SimpleNamespace(ids=data["input_ids"], offsets=data["offset_mapping"])

    def decode(self, ids):
        return self.inner.decode(ids, skip_special_tokens=False)

    def get_vocab_size(self):
        return len(self.inner)

    def token_to_id(self, token):
        return self.inner.get_vocab().get(token)


class HFLogitsAdapter:
    def __init__(self, inner):
        self.inner = inner

    def __call__(self, ids):
        return self.inner(input_ids=ids, use_cache=False).logits

    def eval(self):
        self.inner.eval()
        return self


def parse_map(values):
    out = {}
    for value in values or []:
        if "=" not in value:
            raise ValueError(f"TAG=경로 필요: {value}")
        key, path = value.split("=", 1)
        if not key or not path or key in out:
            raise ValueError(f"잘못되거나 중복인 TAG: {value}")
        out[key] = path
    return out


def load_local_model(tag, *, checkpoint=None, hf_path=None, data="ko-en",
                     tokenizer_path=None, tokenizer_hf=None, device="cpu",
                     deployment=None):
    import torch
    if hf_path:
        if checkpoint or tokenizer_path or tokenizer_hf or deployment:
            raise ValueError("HF 모델은 같은 폴더의 tokenizer 사용; TinyLM 변환 옵션 혼용 불가")
        from transformers import AutoModelForCausalLM, AutoTokenizer
        folder = Path(hf_path).resolve()
        if not folder.is_dir():
            raise FileNotFoundError(folder)
        inner_tok = AutoTokenizer.from_pretrained(
            str(folder), local_files_only=True, trust_remote_code=False, use_fast=True)
        if not inner_tok.is_fast:
            raise ValueError("offset contract를 제공하는 fast tokenizer 필요")
        model = AutoModelForCausalLM.from_pretrained(
            str(folder), local_files_only=True, trust_remote_code=False,
            torch_dtype=torch.bfloat16 if str(device).startswith("cuda") else torch.float32)
        model.to(device).eval()
        tok = HFTokenizerAdapter(inner_tok)
        cfg = model.config
        # shard 파일의 SHA로 실제 local checkpoint를 식별한다.
        weights = sorted(set(folder.glob("*.safetensors")) | set(folder.glob("pytorch_model*.bin")))
        if not weights:
            raise ValueError("HF 로컬 가중치 파일 없음")
        meta = {"tag": tag, "backend": "huggingface", "path": str(folder),
                "weights": {p.name: sha256_file(p) for p in weights},
                "config_sha256": sha256_file(folder / "config.json"),
                "tokenizer_sha256": tokenizer_digest(tok),
                "max_seq_len": int(getattr(cfg, "max_position_embeddings", 1024))}
        return HFLogitsAdapter(model), tok, meta

    from ..data import load_tokenizer
    from ..infer.generate import load_model
    from ..hf_spec import load_hf_tokenizer
    if not checkpoint:
        raise ValueError("TinyLM checkpoint 필요")
    if tokenizer_path and tokenizer_hf:
        raise ValueError("tokenizer_path/tokenizer_hf 중 하나만 지정")
    if tokenizer_path:
        from tokenizers import Tokenizer
        tok = Tokenizer.from_file(str(tokenizer_path))
    elif tokenizer_hf:
        folder = Path(tokenizer_hf)
        if not (folder / "config.json").is_file() or not (folder / "tokenizer.json").is_file():
            raise ValueError("tokenizer-hf는 특정 snapshot의 config/tokenizer.json 폴더를 명시")
        tok, _ = load_hf_tokenizer(folder)
    else:
        tok = load_tokenizer(data)
    model, cfg, _ = load_model(ckpt_path=str(checkpoint), device=device, **(deployment or {}))
    if int(tok.get_vocab_size()) != int(cfg.vocab_size):
        raise ValueError("tokenizer vocabulary와 checkpoint vocab_size 불일치")
    meta = {"tag": tag, "backend": "tinylm", "checkpoint": str(Path(checkpoint).resolve()),
            "checkpoint_sha256": sha256_file(checkpoint),
            "tokenizer_sha256": tokenizer_digest(tok),
            "max_seq_len": int(cfg.max_seq_len),
            "train_repeat": float(cfg.train_repeat),
            "visits": list(model.visit_schedule()), "deployment": deployment or {}}
    return model.eval(), tok, meta


def prefix_ids(tok, explicit_id=None):
    if explicit_id is not None:
        if not 0 <= explicit_id < tok.get_vocab_size():
            raise ValueError("prefix token id 범위 오류")
        return [explicit_id], "explicit_id"
    for token in ("<bos>", "<eos>", "<|endoftext|>"):
        value = tok.token_to_id(token)
        if value is not None:
            return [value], token
    newline = tok.encode("\n", add_special_tokens=False).ids
    if not newline:
        raise ValueError("빈 prefix; --prefix-id 필요")
    return newline, "newline_encoded"


def continuation_nll(model, tok, prompt, continuation, *, device="cpu", seq_max=1024,
                     ce_chunk=256):
    """로컬 규약: prompt/continuation을 별도로 token화. 공식 harness 점수로 명명하지 않는다."""
    import torch
    import torch.nn.functional as F
    prefix = tok.encode(prompt, add_special_tokens=False).ids if prompt else prefix_ids(tok)[0]
    target = tok.encode(continuation, add_special_tokens=False).ids
    if not prefix or not target:
        return None, "empty_prefix_or_target"
    if len(prefix) + len(target) - 1 > seq_max:
        return None, "context_overflow"
    ids = prefix + target
    x = torch.tensor([ids[:-1]], dtype=torch.long, device=device)
    y = torch.tensor(target, dtype=torch.long, device=device)
    dev_type = torch.device(device).type
    with torch.inference_mode(), torch.autocast(dev_type, dtype=torch.bfloat16,
                                               enabled=dev_type == "cuda"):
        logits = model(x)
    tail = logits[0, len(prefix) - 1:]
    total = 0.0
    with torch.inference_mode():
        for start in range(0, len(target), max(1, ce_chunk)):
            stop = start + max(1, ce_chunk)
            total += float(F.cross_entropy(tail[start:stop].float(), y[start:stop],
                                           reduction="sum"))
    import math
    if not math.isfinite(total):
        return None, "nonfinite_nll"
    return {"nll_sum": total, "nll_mean": total / len(target), "tokens": len(target),
            "bytes": len(continuation.encode("utf-8")),
            "chars": len(continuation)}, None


def greedy_completion(model, tok, prompt, *, device="cpu", seq_max=1024, max_new=96,
                      stop_strings=()):
    """앞 context를 조용히 버리지 않는다. 초과/잘림과 생성 token을 별도 기록한다."""
    import torch
    ids = tok.encode(prompt, add_special_tokens=False).ids
    if not ids:
        return {"status": "skipped", "reason": "empty_prompt", "text": "", "tokens": []}
    if len(ids) >= seq_max:
        return {"status": "skipped", "reason": "prompt_overflow", "text": "", "tokens": []}
    if max_new < 1:
        raise ValueError("max_new는 양수")
    generated, finish = [], "max_new"
    stop_ids = {i for s in ("<eos>", "<|im_end|>", "<end_of_turn>", "<|end|>")
                if (i := tok.token_to_id(s)) is not None}
    dev_type = torch.device(device).type
    for _ in range(max_new):
        if len(ids) > seq_max:
            finish = "context_limit"
            break
        with torch.inference_mode(), torch.autocast(dev_type, dtype=torch.bfloat16,
                                                   enabled=dev_type == "cuda"):
            logits = model(torch.tensor([ids], dtype=torch.long, device=device))
        nxt = int(logits[0, -1].argmax())
        ids.append(nxt)
        generated.append(nxt)
        if nxt in stop_ids:
            finish = "end_token"
            break
        text = tok.decode(generated)
        if any(s and s in text for s in stop_strings):
            finish = "stop_string"
            break
    visible = generated[:-1] if finish == "end_token" else generated
    text = tok.decode(visible)
    for stop in stop_strings:
        if stop and stop in text:
            text = text.split(stop, 1)[0]
    return {"status": "ok", "text": text, "tokens": generated, "finish": finish,
            "truncated": finish in ("max_new", "context_limit")}
