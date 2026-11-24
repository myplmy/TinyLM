"""Check natural EOS selections in the existing native 248K G4 request path."""

from datetime import datetime, timedelta
from hashlib import sha256
import os
from pathlib import Path
from unittest.mock import patch

import torch

from scripts import diag_p109_qwen_248k_text as run


TAG = "p109_qwen_248k_eos_readback_v1_20261119"
OUT = run.OUT.with_name(TAG)
SHORT_ENDINGS = (
    "The end.", "End of transcript.\n", "Thank you for reading.\n\n",
    "The conversation is over.", "Question: Are we finished?\nAnswer: Yes.",
    "The final answer is 42.\n",
    "끝.", "이야기가 끝났다.\n", "읽어 주셔서 감사합니다.\n\n",
    "대화가 끝났다.", "질문: 다 끝났나요?\n답변: 네.",
    "최종 답은 42입니다.\n",
)


@torch.inference_mode()
def main():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    cutoff = run.learned.parent.CUTOFF
    assert datetime.now(cutoff.tzinfo) + timedelta(seconds=180) < cutoff
    compiler = run.io.load(run.OUT / "compiler.json")
    paths = {k:Path(v["path"]) for k,v in compiler["binaries"].items()}
    for key, file in paths.items():
        assert run.io.digest(file) == compiler["binaries"][key]["sha256"]
    reference = run.io.load(run.OUT / "report.json")
    profile = run.io.load(run.OUT / "profile.json")
    assert run.io.digest(run.learned.EXPORT) == profile["train_packed_sha256"]
    assert run.io.digest(run.TOKENIZER) == run.io.load(run.io.OUT / "profile.json")["compact_sha256"]
    docs = run.io.load(run.io.AUTHORED)["data"]["documents"]
    inputs = [(d["language"],d["text"]) for d in docs if d["split"]=="held"]
    inputs.extend(("en" if i<6 else "ko", text) for i,text in enumerate(SHORT_ENDINGS))
    assert len(inputs) == 60
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    OUT.mkdir(exist_ok=False)
    model_fd = run.engine.prefill.base.memfile("qwen248_eos_g4")
    tok_fd = run.engine.prefill.base.memfile("qwen248_eos_tok")
    rows, comparisons = [], []
    try:
        run.engine.text.store(tok_fd, run.TOKENIZER.read_bytes())
        run.engine.seal(tok_fd)
        payload = torch.load(run.learned.EXPORT, map_location="cpu", weights_only=True)
        packed = run.learned.load_payload(payload, device="cpu", tile_rows=4096)
        model = run.serialize(packed, model_fd)
        del packed, payload
        assert model == reference["artifact"]
        with run.CompactQwenTokenizer(run.TOKENIZER) as codec:
            for serial,(language, text) in enumerate(inputs):
                raw = text.encode("utf-8")
                ids = codec.encode(text).ids
                original, _ = run.engine.native(paths["fp32"],model_fd,ids,run.text.GEN)
                eos = original["ids"][-1] == run.text.EOS
                rows.append(dict(language=language, sha256=sha256(raw).hexdigest().upper(), input_tokens=len(ids),
                                 generated=original["ids"], eos=eos, early=eos and len(original["ids"])<run.text.GEN))
                if eos and len(comparisons)<4:
                    with patch.object(run.engine,"OUT",OUT),patch.object(run.engine,"text",run.text):
                        result = run.engine.full_request(paths["text"],(model_fd,tok_fd),raw,language,serial)
                    assert result.pop("source_ids") == ids
                    result["match"] = result["ids"]==original["ids"] and result["finish"]=="eos" and (
                        result["text"]==codec.decode(original["ids"],skip_special_tokens=True))
                    comparisons.append(result)
                    print("P109_EOS_COMPARISON", language, len(result["ids"]), result["match"], flush=True)
    finally:
        os.close(model_fd)
        os.close(tok_fd)
    assert not torch.cuda.is_initialized()
    assert run.io.digest(run.learned.EXPORT) == profile["train_packed_sha256"]
    first_eos = sum(r["eos"] for r in rows)
    early = sum(r["early"] for r in rows)
    run.io.write(OUT/"report.json",dict(probes=rows, comparisons=comparisons, eos=first_eos, early=early,
        weights=model, profile_sha256=run.io.digest(run.OUT/"profile.json"),
        compiler_sha256=run.io.digest(run.OUT/"compiler.json"),
        source_sha256=run.io.digest(Path(__file__)), checkpoint_writes=0))
    print("P109_EOS_RESULT", len(rows), first_eos, early, len(comparisons), flush=True)
    return 0 if all(r["match"] for r in comparisons) else 8


if __name__ == "__main__":
    raise SystemExit(main())
