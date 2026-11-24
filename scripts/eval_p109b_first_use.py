"""Generate first-use answers from the finished P109B pair on sealed authored cases."""

import argparse
from datetime import datetime
import gc
import json
import os
from pathlib import Path
import signal
import time
import unicodedata

from scripts import eval_p109b_scratch_pair_20261120 as previous


pair = previous.pair
OUT = pair.ROOT / "test_result/evidence/p109b_first_use128_v1_20261120"
CUTOFF = datetime.fromisoformat("2026-11-21T12:57:00+09:00").timestamp()
CONTEXT, INPUT, ANSWER, MAX_WALL = 1024, 896, 128, 480
CASES = (
    ("lookup", "루마 상자에는 주황색 열쇠가 있다. 열쇠의 색은? 색 이름만 쓰세요.",
     "주황색", "The Luma box holds an orange key. What color is the key? Give only the color.", "orange"),
    ("changed_value", "처음 유나의 코드는 23이었다. 오후에 71로 바뀌었다. 현재 코드를 숫자로만 답하세요.",
     "71", "Yuna's code was 23. In the afternoon it changed to 71. Give only the current number.", "71"),
    ("same_value", "도준의 방은 64호, 세나의 방은 31호였다. 세나만 58호로 옮겼다. 도준의 방 번호는?",
     "64", "Dojun was in room 64 and Sena in room 31. Only Sena moved, to room 58. What is Dojun's room number?", "64"),
    ("arithmetic", "바구니에 돌이 47개 있었다. 18개를 꺼냈다. 남은 개수만 숫자로 쓰세요.",
     "29", "A basket held 47 stones. 18 were removed. Give only the number left.", "29"),
    ("role", "고래는 나래가 그리고, 사슴은 리온이 그렸다. 사슴을 그린 사람 이름만 답하세요.",
     "리온", "Nara painted the whale and Rion painted the deer. Give only the name of the deer painter.", "Rion"),
    ("order", "작업은 자르기, 붙이기, 말리기 순서다. 첫 작업 이름만 답하세요.",
     "자르기", "The steps are cutting, gluing, then drying. Give only the first step.", "cutting"),
    ("negative", "예약 가능한 요일은 화요일과 금요일이다. 화요일 예약은 취소되었다. 남은 요일만 쓰세요.",
     "금요일", "Tuesday and Friday were available. Tuesday was cancelled. Give only the remaining day.", "Friday"),
    ("input_limit", "미로의 출구 번호는 37번입니다.", "37",
     "The exit number in the maze is 37.", "37"),
)


def dialog(body):
    return "<|im_start|>user\n" + body + "<|im_end|>\n<|im_start|>assistant\n"


def examples(tokenizer):
    rows = []
    for name, ko, ko_answer, en, en_answer in CASES:
        for language, body, answer in (("ko", ko, ko_answer), ("en", en, en_answer)):
            if name == "input_limit":
                ending = "\n출구 번호를 숫자로만 답하세요." if language == "ko" else "\nGive only the exit number."
                length = len(tokenizer.encode(dialog(body + ending)).ids)
                body += " x" * (INPUT - length) + ending
            prompt = dialog(body)
            ids = tokenizer.encode(prompt).ids
            if not 0 < len(ids) <= INPUT or (name == "input_limit" and len(ids) != INPUT):
                raise ValueError(f"{name}/{language}: unexpected prompt length {len(ids)}")
            rows.append({"case": name, "language": language, "prompt": prompt, "input_ids": ids, "answer": answer})
    return rows


def inputs():
    from tokenizers import Tokenizer

    pins = previous.frozen.audit.Inputs()
    for path in (Path(__file__), Path(previous.__file__), pair.ROOT / "tinylm/infer/generate.py",
                 pair.ROOT / "tinylm/model/transformer.py", pair.ROOT / "tinylm/config.py",
                 pair.ROOT / "tinylm/model/modules.py", pair.ROOT / "tinylm/model/ternary.py",
                 pair.ROOT / "tinylm/model/visibility.py"):
        pins.add(path)
    pins.add(pair.TOKENIZER, previous.TOKENIZER_SHA)
    readback = pair.OUT / "readback.json"
    pins.add(readback)
    saved = previous.read(readback)
    if not saved["complete"] or set(saved["arms"]) != set(pair.ARMS):
        raise ValueError("the input pair has not completed")
    for policy, arm in saved["arms"].items():
        if (arm["tag"] != pair.ARMS[policy] or arm["updates"] != pair.STEPS
                or arm["draw_tokens"] != pair.STEPS * pair.MICRO * pair.ACCUM * pair.SEQ):
            raise ValueError("trained arms have different exposure")
        pins.add(pair.ROOT / arm["checkpoint"], arm["checkpoint_sha256"])
    tokenizer = Tokenizer.from_file(str(pair.TOKENIZER))
    special = [tokenizer.token_to_id(t) for t in ("<pad>", "<bos>", "<eos>", "<|im_start|>", "<|im_end|>")]
    if special != [0, 1, 2, 3, 4] or tokenizer.get_vocab_size() != 32768:
        raise ValueError(f"unexpected chat32 vocabulary or stop IDs: {special}")
    profile = dict(approval="WIP191", pins=pins.files, context=CONTEXT, max_input=INPUT, max_answer=ANSWER,
                   eos=special[2], eot=special[4], repeat=2, visits=28, precision="BF16 autocast, MATH SDPA",
                   greedy=True, examples=examples(tokenizer))
    return pins, tokenizer, profile


class DecodeSuffix:
    def __init__(self, tokenizer, input_ids):
        self.tokenizer = tokenizer
        self.input_ids = input_ids
        self.ids = []

    def encode(self, prompt):
        return self.tokenizer.encode(prompt)

    def decode(self, ids):
        if ids[:len(self.input_ids)] != self.input_ids:
            raise ValueError("generation changed the sealed prompt")
        self.ids = ids[len(self.input_ids):]
        return self.tokenizer.decode(self.ids, skip_special_tokens=True)


def strict(text):
    return unicodedata.normalize("NFC", text).strip().casefold()


def repeat_tail(ids):
    return any(ids[-period:] == ids[-2 * period:-period] == ids[-3 * period:-2 * period]
               for period in range(1, min(32, len(ids) // 3) + 1))


def evaluate():
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0" or time.time() + MAX_WALL >= CUTOFF:
        raise RuntimeError("no selected GPU or insufficient authorized time")
    signal.alarm(MAX_WALL)
    pair.idle_gpu()
    pins, tokenizer, profile = inputs()
    if previous.read(OUT / "profile.json") != profile:
        raise ValueError("a sealed input or source changed")
    import torch
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from tinylm.infer.generate import sample

    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    all_results = {}
    raw_path = OUT / "answers.jsonl"
    with raw_path.open("x", encoding="utf-8") as raw, sdpa_kernel(SDPBackend.MATH):
        for policy in pair.ARMS:
            torch.cuda.reset_peak_memory_stats()
            model, _ = previous.load_model(torch, pins, policy)
            if model.cfg.max_seq_len != CONTEXT:
                raise ValueError("context size differs from first use")
            rows = []
            for item in profile["examples"]:
                capture = DecodeSuffix(tokenizer, item["input_ids"])
                start = time.perf_counter()
                answer, meta = sample(model, model.cfg, capture, item["prompt"],
                                      max_new=ANSWER, temperature=0., top_k=0, device="cuda",
                                      eos_id=profile["eos"], stop_token_sequences=[[profile["eot"]]],
                                      logits_last_only=True, return_metadata=True)
                torch.cuda.synchronize()
                if len(capture.ids) != meta["generated_tokens"]:
                    raise ValueError("generation metadata and raw suffix disagree")
                row = dict(policy=policy, case=item["case"], language=item["language"],
                           input_len=len(item["input_ids"]), expected=item["answer"], answer=answer,
                           exact=strict(answer) == strict(item["answer"]), tokens=capture.ids, **meta,
                           repeat_tail=repeat_tail(capture.ids), seconds=time.perf_counter() - start)
                raw.write(json.dumps(row, ensure_ascii=False) + chr(10))
                raw.flush()
                rows.append(row)
            all_results[policy] = dict(
                rows=len(rows), exact=sum(row["exact"] for row in rows),
                stop=sum(row["finish_reason"] in ("EOS", "STOP_SEQUENCE") for row in rows),
                capped=sum(row["finish_reason"] == "MAX_NEW" for row in rows),
                repeat_tail=sum(row["repeat_tail"] for row in rows),
                peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                peak_reserved_bytes=torch.cuda.max_memory_reserved(),
                generation_seconds=sum(row["seconds"] for row in rows),
            )
            print("FIRST_USE_ARM", policy, all_results[policy], flush=True)
            del model
            gc.collect()
            torch.cuda.empty_cache()
    pins.unchanged()
    pair.publish(OUT / "report.json", dict(complete=True, arms=all_results, raw_sha256=pair.file_sha(raw_path),
                 profile_sha256=pair.file_sha(OUT / "profile.json"),
                 final_allocated_bytes=torch.cuda.memory_allocated(),
                 final_reserved_bytes=torch.cuda.memory_reserved()))
    signal.alarm(0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "gpu"))
    if parser.parse_args().phase == "prepare":
        pins, _, profile = inputs()
        pins.unchanged()
        OUT.mkdir(exist_ok=False)
        pair.publish(OUT / "profile.json", profile)
        print("FIRST_USE_SEALED", len(profile["examples"]),
              max(len(row["input_ids"]) for row in profile["examples"]), flush=True)
        return
    evaluate()


if __name__ == "__main__":
    main()
