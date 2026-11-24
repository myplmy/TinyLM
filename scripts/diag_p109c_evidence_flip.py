"""Compare two completed P109C models on newly authored, paired evidence changes."""

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import statistics
import time
from unittest.mock import patch

from scripts import eval_p109c_completed as completed
from scripts import eval_p109c_mixed_v2 as mixed
from scripts import p109_eval_resilient_supervisor as supervisor
from scripts import run_p109c_scratch330 as native
from tinylm.chat.serialize import serialize


TAG = "p109c_evidence_flip_dev_v1_20261124"
EVIDENCE = completed.ROOT / "test_result/evidence"
TRAINING = {
    "v1": EVIDENCE / "p109c_scratch330_v1_resume1030_protected_v2_20261121",
    "v2": EVIDENCE / "p109c_scratch_mixed_v2_v11_chat32_s1337_run1_20261123",
}
AUTHORIZATION_END = datetime.fromisoformat("2026-11-25T17:00:00+09:00")
BATCH, MAX_NEW = 16, 8
ANSWERS = {"en": ("Yes", "No"), "ko": ("예", "아니요")}
FORMATS = ("plain", "chat")
SCENARIOS = (
    # In each question, {a} and {b} retain their original values when the record is swapped.
    ("attribute", "In the exhibit log, the seal for Mira is {a} and the seal for Reno is {b}.",
     "Is Mira's seal {a}?", ("copper", "silver"),
     "전시 기록에 미라의 봉인은 {a}이고 레노의 봉인은 {b}이다.", "미라의 봉인은 {a}인가?", ("구리", "은")),
    ("attribute", "In the bindery, the atlas has a {a} cover and the register has a {b} cover.",
     "Does the register have a {b} cover?", ("linen", "leather"),
     "제본실에서 지도책의 표지는 {a}이고 장부의 표지는 {b}이다.", "장부의 표지는 {b}인가?", ("리넨", "가죽")),
    ("attribute", "For the drill, Dami received the {a} badge and Neri received the {b} badge.",
     "Did Dami receive the {a} badge?", ("triangle", "circle"),
     "훈련에서 다미는 {a} 배지를 받고 네리는 {b} 배지를 받았다.", "다미가 받은 배지는 {a} 배지인가?", ("삼각형", "원형")),
    ("attribute", "The east plot is planted with {a}; the west plot is planted with {b}.",
     "Is the crop on the west plot {b}?", ("peas", "oats"),
     "동쪽 밭에는 {a}를 심었고 서쪽 밭에는 {b}를 심었다.", "서쪽 밭에 심은 작물은 {b}인가?", ("완두", "귀리")),
    ("quantity", "The blue bin holds {a} tiles and the red bin holds {b} tiles.",
     "Does the blue bin hold more tiles than the red bin?", ("18", "12"),
     "파란 상자에는 타일이 {a}개, 빨간 상자에는 타일이 {b}개 있다.", "파란 상자에 타일이 더 많은가?", ("18", "12")),
    ("quantity", "The first jug has {a} milliliters and the second jug has {b} milliliters.",
     "Does the first jug have under 400 milliliters?", ("350", "480"),
     "첫째 물병에는 {a}밀리리터, 둘째 물병에는 {b}밀리리터가 들어 있다.", "첫째 물병에는 400밀리리터 미만이 들어 있는가?", ("350", "480")),
    ("quantity", "The oak sapling is {a} centimeters tall and the ash sapling is {b} centimeters tall.",
     "Is the ash sapling taller than the oak sapling?", ("42", "57"),
     "참나무 묘목의 키는 {a}센티미터, 물푸레나무 묘목의 키는 {b}센티미터이다.", "물푸레나무 묘목이 참나무 묘목보다 키가 큰가?", ("42", "57")),
    ("quantity", "At the end, Ivo had {a} points and Yuna had {b} points.",
     "Did Ivo finish with fewer than seven points?", ("5", "9"),
     "종료 시 이보는 {a}점, 유나는 {b}점을 받았다.", "이보의 최종 점수는 7점 미만인가?", ("5", "9")),
    ("sequence", "The gate opens on {a} and the inspection is on {b}, both in the same week.",
     "Does the gate open before the inspection?", ("Tuesday", "Thursday"),
     "같은 주에 출입문을 여는 날은 {a}, 점검하는 날은 {b}이다.", "출입문은 점검일보다 먼저 열리는가?", ("화요일", "목요일")),
    ("sequence", "The green ferry departs at {a} and the gold ferry departs at {b} today.",
     "Does the gold ferry depart before the green ferry?", ("16:10", "13:40"),
     "오늘 초록색 나룻배는 {a}, 금색 나룻배는 {b}에 출발한다.", "금색 나룻배가 초록색 나룻배보다 먼저 출발하는가?", ("16:10", "13:40")),
    ("sequence", "The binding stage is numbered {a} and the stamping stage is numbered {b}. Stages follow ascending numbers.",
     "Is stamping after binding?", ("2", "5"),
     "제본 단계 번호는 {a}, 날인 단계 번호는 {b}이다. 단계는 번호가 작은 것부터 진행한다.", "날인은 제본보다 나중에 이루어지는가?", ("2", "5")),
    ("sequence", "The lamp test ends at {a} and the valve test ends at {b}, on the same day.",
     "Does the lamp test finish later than the valve test?", ("15:20", "13:15"),
     "같은 날 전등 점검은 {a}, 밸브 점검은 {b}에 끝난다.", "전등 점검이 밸브 점검보다 늦게 끝나는가?", ("15:20", "13:15")),
    ("two_link", "Nema owns the amber cabinet and Taro owns the ivory cabinet. The amber cabinet holds {a} and the ivory cabinet holds {b}.",
     "Is the compass in Nema's cabinet?", ("the compass", "the lens"),
     "네마는 호박색 장을, 타로는 상아색 장을 소유한다. 호박색 장의 내용물은 {a}, 상아색 장의 내용물은 {b}이다.",
     "네마의 장에 나침반이 있는가?", ("나침반", "렌즈")),
    ("two_link", "Route K ends at the pier and route L ends at the yard. At the pier is {a}; at the yard is {b}.",
     "Is the crane at the end of route L?", ("a bell", "a crane"),
     "K 노선은 부두에서 끝나고 L 노선은 뜰에서 끝난다. 부두에서 볼 수 있는 물건은 {a}, 뜰에서 볼 수 있는 물건은 {b}이다.",
     "L 노선의 끝에 기중기가 있는가?", ("종", "기중기")),
    ("two_link", "Jori has locker H and Risa has locker J. H contains the {a} pass and J contains the {b} pass.",
     "Does Jori's locker contain the oval pass?", ("oval", "square"),
     "조리는 H 사물함, 리사는 J 사물함을 쓴다. H에는 {a} 통행증, J에는 {b} 통행증이 있다.",
     "조리의 사물함에 타원형 통행증이 있는가?", ("타원형", "사각형")),
    ("two_link", "Tesa visits room M; Bore visits room N. Room M plays {a}; room N plays {b}.",
     "Does Bore's room play violin music?", ("flute music", "violin music"),
     "테사는 M실에, 보레는 N실에 방문한다. M실에서는 {a}이, N실에서는 {b}이 나온다.",
     "보레가 방문하는 방에서 바이올린 음악이 나오는가?", ("플루트 음악", "바이올린 음악")),
)


def requests(tokenizer):
    rows = []
    for root, (group, en, eq, ev, ko, kq, kv) in enumerate(SCENARIOS):
        languages = (("en", en, eq, ev, "The record was filed on paper."),
                     ("ko", ko, kq, kv, "기록은 종이에 작성했다."))
        for lang, record, question, values, neutral in languages:
            question = question.format(a=values[0], b=values[1])
            contexts = (record.format(a=values[0], b=values[1]),
                        record.format(a=values[1], b=values[0]), neutral)
            for fmt in FORMATS:
                for gold, context in zip(("yes", "no", None), contexts, strict=True):
                    if lang == "en":
                        text = f"{context}\nQuestion: {question}\nAnswer Yes or No."
                        marker = "\nAnswer:\n"
                    else:
                        text = f"{context}\n질문: {question}\n예 또는 아니요로 답하세요."
                        marker = "\n답:\n"
                    prompt = text + marker if fmt == "plain" else serialize(
                        {"messages": [{"role": "user", "content": text}]}, "chatml", add_generation_prompt=True)
                    ids = tokenizer.encode(prompt).ids
                    targets = [tokenizer.encode(prompt + value).ids for value in ANSWERS[lang]]
                    if (not ids or len(ids) + MAX_NEW > native.WIDTH
                            or any(p[:len(ids)] != ids or len(p) <= len(ids) for p in targets)):
                        raise ValueError("a formatted answer loses its prefix identity")
                    leading = [value[len(ids)] for value in targets]
                    if len(set(leading)) != 2:
                        raise ValueError("the yes and no first tokens must differ")
                    rows.append(dict(root=root, group=group, language=lang, format=fmt, gold=gold,
                                     passage=context, question=question, prompt=prompt, ids=ids, first=leading))
    if len({tuple(row["ids"]) for row in rows}) != len(rows):
        raise ValueError("the paired evidence panel contains duplicate prompts")
    return rows


def profile(rows):
    pinned = mixed.pinned_sources()
    for path in (Path(__file__).resolve(), Path(supervisor.__file__).resolve()):
        pinned[str(path.relative_to(completed.ROOT))] = completed.core6.digest(path)
    checkpoints = {}
    for version, directory in TRAINING.items():
        checks = {name: completed.core6.digest(directory / name)
                  for name in ("input.json", "training.json", "supervisor.json", "evaluation.pt")}
        if version == "v2":
            checks["report.json"] = completed.core6.digest(directory / "report.json")
        checkpoints[version] = checks
    return dict(tag=TAG, sources=pinned, checkpoints=checkpoints, max_new=MAX_NEW,
                rows=len(rows), requests_sha256=hashlib.sha256(
                    json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()).hexdigest().upper())


def label(text, lang):
    choices = "yes|no" if lang == "en" else "예|네|아니오|아니요"
    match = re.match(rf"^({choices})(?=$|[\s,.:!?])", text.strip(), re.IGNORECASE)
    if match is None:
        return None
    return "yes" if match[1].lower() in ("yes", "예", "네") else "no"


def predict(model, tokenizer, rows, torch, check):
    inputs = [row["ids"].copy() for row in rows]
    outputs = [[] for _ in rows]
    stops = [None for _ in rows]
    margins = None
    for step in range(MAX_NEW):
        check()
        active = [i for i, stop in enumerate(stops) if stop is None]
        if not active:
            break
        lengths = [len(inputs[i]) for i in active]
        width = max(lengths)
        data = torch.tensor([inputs[i] + [0] * (width - len(inputs[i])) for i in active], device="cuda")
        index = torch.arange(len(active), device="cuda")
        last = torch.tensor(lengths, device="cuda") - 1
        hidden = model(data, return_hidden=True)
        logits = model._head_logits(hidden[index, last])
        if step == 0:
            target = torch.tensor([row["first"] for row in rows], device="cuda")
            selected = logits.gather(-1, target)
            if not bool(torch.isfinite(selected).all()):
                raise ValueError("the selected first-token logits are not finite")
            margins = (selected[:, 0] - selected[:, 1]).tolist()
        for i, tok in zip(active, logits.argmax(-1).tolist(), strict=True):
            if tok in (2, 4):
                stops[i] = tok
            else:
                inputs[i].append(tok)
                outputs[i].append(tok)
    result = []
    for row, tokens, stop, margin in zip(rows, outputs, stops, margins, strict=True):
        answer = tokenizer.decode(tokens, skip_special_tokens=True)
        exact = answer.strip().lower().rstrip(".!?") in ("yes", "no", "예", "네", "아니오", "아니요")
        result.append(dict(row, margin=margin, chosen=("yes" if margin > 0 else "no" if margin < 0 else None),
                           generated=tokens, answer=answer, answer_label=label(answer, row["language"]),
                           exact=exact, stop=stop))
    return result


def aggregate(rows):
    summary = {}
    for lang in ANSWERS:
        for fmt in FORMATS:
            triads = {}
            for row in rows:
                if row["language"] == lang and row["format"] == fmt:
                    triads.setdefault(row["root"], {})[row["gold"]] = row
            counts = Counter()
            deltas = []
            for sides in triads.values():
                yes, no, neutral = sides["yes"], sides["no"], sides[None]
                delta = yes["margin"] - no["margin"]
                deltas.append(delta)
                counts.update(positive=delta > 0, neutral_yes=neutral["chosen"] == "yes",
                              choice_pair=yes["chosen"] == "yes" and no["chosen"] == "no",
                              answer_pair=yes["answer_label"] == "yes" and no["answer_label"] == "no",
                              strict_pair=all(s["answer_label"] == s["gold"] and s["exact"] and s["stop"] is not None
                                              for s in (yes, no)))
                for side in (yes, no):
                    counts.update(choice_yes=side["chosen"] == "yes", answer_yes=side["answer_label"] == "yes",
                                  choice_correct=side["chosen"] == side["gold"],
                                  answer_correct=side["answer_label"] == side["gold"],
                                  answer_unrecognized=side["answer_label"] is None)
            summary[f"{lang}/{fmt}"] = dict(pairs=len(triads), **counts,
                                           median_margin_change=statistics.median(deltas))
    return summary


def worker(profile_path, profile_sha, _resume, output, cutoff):
    import torch
    from torch.nn.attention import SDPBackend, sdpa_kernel

    def check():
        if time.time() >= cutoff:
            raise TimeoutError("the authorized evaluation interval ended")

    tokenizer = completed.load_tokenizer()
    rows = requests(tokenizer)
    sealed = json.loads(native.manifest_bytes(profile_path, profile_sha))
    if sealed != profile(rows) or torch.cuda.device_count() != 1:
        raise ValueError("use the same sealed evaluation on the assigned CUDA device")
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    free, total = torch.cuda.mem_get_info()
    budget = (native.CARD_LIMIT_MIB - 384) * 2**20 - (total - free)
    if not 0 < budget <= total:
        raise ValueError("the CUDA allocator has no approved budget")
    torch.cuda.set_per_process_memory_fraction(budget / total)
    results = {}
    with ((output / "progress.jsonl").open("x", encoding="utf-8", buffering=1) as log,
          torch.inference_mode(), sdpa_kernel(SDPBackend.MATH)):
        for version, directory in TRAINING.items():
            metadata = completed.read_json(directory / "input.json")
            if version == "v1":
                checkpoint, checksum = completed.completed_checkpoint(directory, metadata["manifest_sha256"])
                step = metadata["updates"]
            else:
                step = metadata["steps"]
                with patch.object(native, "STEPS", step):
                    checkpoint, checksum = mixed.completed_v2(directory, metadata["manifest_sha256"])
            if checksum != sealed["checkpoints"][version]["evaluation.pt"]:
                raise ValueError("a checkpoint differs from the sealed evaluation body")
            model = completed.load_model(checkpoint, step, "cuda")
            torch.cuda.reset_peak_memory_stats()
            outputs = []
            started = time.monotonic()
            for offset in range(0, len(rows), BATCH):
                outputs.extend(predict(model, tokenizer, rows[offset:offset+BATCH], torch, check))
                print(json.dumps(dict(version=version, finished=len(outputs))), file=log)
            result = dict(summary=aggregate(outputs), rows=outputs, step=step, sha256=checksum,
                          peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
                          seconds=time.monotonic()-started)
            native.publish(output / f"{version}.json", result)
            results[version] = result["summary"]
            del model
    if profile(rows) != sealed:
        raise ValueError("an evaluated source or artifact changed during the run")
    native.publish(output / "report.json", dict(status="COMPLETE", profile=sealed, summaries=results))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.action == "prepare":
        rows = requests(completed.load_tokenizer())
        native.publish(args.profile, profile(rows))
        print(completed.core6.digest(args.profile), len(rows), max(len(row["ids"]) for row in rows))
        return 0
    if (args.profile_sha256 is None or args.stop_by is None or args.stop_by.tzinfo is None
            or args.stop_by > AUTHORIZATION_END):
        parser.error("a profile hash and cutoff within the approved interval are required")
    return supervisor.supervise(worker, args.profile, args.profile_sha256, EVIDENCE / TAG, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
