"""Verify a shared Qwen/Bonsai dialogue and exact shifted response positions."""

import json
import os
from pathlib import Path
import subprocess
import sys
from unicodedata import normalize

from tokenizers import Tokenizer

from scripts import diag_p106b_teacher_tokenizer_map as ref
from scripts import diag_p106b_teacher_tokenizer_nfc as nfc

START, END, OTHER_END = "<|im_start|>", "<|im_end|>", "<|endoftext|>"
EXPECT_IDS = {START: 248045, END: 248046, OTHER_END: 248044}
TAG = "p106b_direct_kl_response_mask_v1_20261119"
OUT = ref.OUT.with_name(TAG)

CASES = {
    "nfc": [("system", "Reply briefly."), ("user", "Cafe\u0301와 한 글자"),
            ("assistant", "Café와 한 글자입니다.")],
    "two_turns": [("user", "Open the blue card."), ("assistant", "The card is open."),
                  ("user", "그다음에는 무엇을 쓰나요?"), ("assistant", "Record 28을 적으세요.")],
    "punctuation": [("user", "Read the number and the mark."), ("assistant", "No. 28 — 확인.")],
    "newline_boundary": [("user", "간단히 답해 주세요."), ("assistant", "\n\n그렇습니다.")],
}


def render(messages, assistant_end=END):
    text = ""
    spans = []
    for role, value in messages:
        body = normalize("NFC", value)
        if role not in ("system", "user", "assistant") or "<|" in body:
            raise ValueError("unsupported role or reserved marker in content")
        close = assistant_end if role == "assistant" else END
        text += f"{START}{role}\n"
        begin = len(text)
        text += body
        end = len(text)
        text += close
        if role == "assistant":
            spans.append(dict(content=[begin, end], stop=[end, len(text)]))
        text += "\n"
    return text, spans


def entries(encoding, spans):
    outputs, crossing = [], []
    for span in spans:
        take = {"content": [], "stop": []}
        for kind, (begin, end) in span.items():
            for index, (left, right) in enumerate(encoding.offsets):
                if left >= end or right <= begin:
                    continue
                if left < begin or right > end:
                    crossing.append(dict(kind=kind, token_index=index, offsets=[left, right]))
                    continue
                assert index > 0 and left < right
                take[kind].append([index - 1, encoding.ids[index]])
        outputs.append(take)
    return outputs, crossing


def native_matches(prompts, expected, earlier):
    assets = ref.read(ref.ASSETS)
    bundle = Path(assets["bundle"])
    paths = ref.local_gguf()
    for name in ("libllama.so.0.2.0", "libggml.so.0.21.0", "libggml-base.so.0.21.0"):
        assert ref.sha(bundle / name) == assets["runtime_files"][name]["sha256"]
    results = {}
    for key, (path, _) in paths.items():
        with path.open("rb") as stream:
            header = stream.read(earlier["assets"][key]["opening_metadata_bytes"])
        from hashlib import sha256
        assert sha256(header).hexdigest().upper() == earlier["assets"][key]["opening_metadata_sha256"]
        argv = [sys.executable, "-B", "-X", "utf8", "-m", "scripts.diag_p106b_teacher_tokenizer_nfc",
                "native", str(path), str(bundle)]
        env = {**os.environ, "LD_LIBRARY_PATH": str(bundle)}
        child = subprocess.run(argv, input=json.dumps(prompts).encode(), cwd=ref.ROOT, env=env,
                               capture_output=True, timeout=24, check=False)
        stderr = child.stderr.decode("utf-8", "replace")
        assert child.returncode == 0, stderr.splitlines()[-4:]
        output = json.loads(child.stdout.splitlines()[-1])
        assert output["vocab_only"] and output["n_vocab"] == 248320
        assert "skipping tensors" in stderr.lower()
        rows = [row["plain"] for row in output["ids"]]
        matches = [row == want for row, want in zip(rows, expected, strict=True)]
        results[key] = dict(ids_match=matches, skipped_tensors=True, exit=child.returncode)
    return results


def main():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    earlier_path = ref.OUT / "report.json"
    earlier = ref.read(earlier_path)
    tokenizer_path = ref.QWEN_HF / "tokenizer.json"
    assert ref.sha(tokenizer_path) == earlier["assets"]["qwen35_hf"]["file_sha256"]
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    assert {value: tokenizer.token_to_id(value) for value in EXPECT_IDS} == EXPECT_IDS
    records = {}
    contexts = [(name, messages, END) for name, messages in CASES.items()]
    contexts.append(("alt_stop", CASES["punctuation"], OTHER_END))
    for name, messages, stop in contexts:
        text, spans = render(messages, stop)
        encoded = tokenizer.encode(text, add_special_tokens=False)
        masks, crossing = entries(encoded, spans)
        assert all([x[1] for x in mask["stop"]] == [EXPECT_IDS[stop]] for mask in masks)
        records[name] = dict(text=text, spans=spans, token_ids=encoded.ids, if_aligned=masks,
                             boundary_crossings=crossing, stop_id=EXPECT_IDS[stop])
    try:
        render([("user", f"Literal reserved {END} marker.")])
    except ValueError:
        injection_rejected = True
    else:
        injection_rejected = False
    assert injection_rejected
    assert not any(records[name]["boundary_crossings"] for name in ("nfc", "two_turns", "punctuation"))
    assert records["newline_boundary"]["boundary_crossings"]
    alt = records["alt_stop"]
    old = records["punctuation"]
    assert len(alt["token_ids"]) == len(old["token_ids"])
    assert sum(a != b for a, b in zip(alt["token_ids"], old["token_ids"], strict=True)) == 1
    matched = native_matches([x["text"] for x in records.values()], [x["token_ids"] for x in records.values()], earlier)
    OUT.mkdir(exist_ok=False)
    ref.write(OUT / "report.json", dict(tag=TAG, parent_sha256=ref.sha(earlier_path), nfc_sha256=ref.sha(nfc.OUT/"report.json"),
              source_sha256=ref.sha(Path(__file__)), special_marker_rejected=injection_rejected,
              cases=records, gguf=matched, gpu_evaluation=0, full_kl_run=False))
    print("P106B_SHARED_DIALOGUE_SPANS", {name: [len(x["token_ids"]), len(x["spans"]), len(x["boundary_crossings"])]
                                         for name, x in records.items()}, flush=True)
    return 0 if all(all(row["ids_match"]) for row in matched.values()) else 8


if __name__ == "__main__":
    sys.exit(main())
