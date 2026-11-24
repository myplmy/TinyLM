"""Measure whether yes/no likelihood changes when the stated fact changes."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
from statistics import mean
import sysconfig
import time
from types import SimpleNamespace
from unittest.mock import patch

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import eval_p109b_first_use as first
from scripts import eval_p109c_completed as v1
from scripts import eval_p109c_mixed_v2 as v2
from scripts.p106b_official_lm_adapter import create_adapter


# Each fact has two alternatives. Both questions are asked of both statements.
FACTS = (
    ("vial", "The sealed vial is in the {} cabinet.", "Is the vial in the {} cabinet?", ("blue", "green"),
     "밀봉된 약병은 {} 서랍장 안에 있다.", "약병은 {} 서랍장 안에 있나요?", ("파란", "초록")),
    ("number", "Rami's badge number is {}.", "Is Rami's badge number {}?", ("46", "83"),
     "라미의 출입증 번호는 {}번이다.", "라미의 출입증 번호가 {}번인가요?", ("46", "83")),
    ("night", "The last bus leaves on {}.", "Does the last bus leave on {}?", ("Friday", "Sunday"),
     "막차는 {}에 출발한다.", "막차는 {}에 출발하나요?", ("금요일", "일요일")),
    ("speaker", "{} made the announcement alone.", "Did {} make the announcement?", ("Daro", "Nemi"),
     "{} 혼자 공지했다.", "공지한 사람이 {}인가요?", ("다로", "네미")),
    ("count", "The unopened parcel contains exactly {} cups.", "Are there exactly {} cups in the parcel?", ("five", "nine"),
     "뜯지 않은 소포에는 컵이 정확히 {} 개 들어 있다.", "소포에 컵이 정확히 {} 개 들어 있나요?", ("다섯", "아홉")),
    ("material", "The practice medal is made only of {}.", "Is the practice medal made of {}?", ("brass", "tin"),
     "연습용 메달의 재료는 {}뿐이다.", "연습용 메달은 {}으로 만들었나요?", ("황동", "주석")),
    ("facility", "The sole location where Nuri met the courier was the {}.", "Did Nuri meet the courier at the {}?", ("library", "post office"),
     "누리가 배달원을 만난 곳은 {}이다.", "누리가 배달원을 {}에서 만났나요?", ("도서관", "우체국")),
    ("status", "The main valve is currently {}.", "Is the main valve {}?", ("closed", "open"),
     "주밸브의 현재 상태는 {}이다.", "주밸브의 상태가 {}인가요?", ("닫힘", "열림")),
)


def cases():
    for name, en_p, en_q, en_v, ko_p, ko_q, ko_v in FACTS:
        for lang, passage, ask, values, yes, no in (
                ("en", en_p, en_q, en_v, "yes", "no"), ("ko", ko_p, ko_q, ko_v, "예", "아니요")):
            for form in ("plain", "chat"):
                for i, evidence in enumerate(values):
                    for j, query in enumerate(values):
                        question = ask.format(query)
                        if form == "plain":
                            query_label, answer_label = ("Question", "Answer") if lang == "en" else ("질문", "답")
                            body = f"{passage.format(evidence)}\n{query_label}: {question}\n{answer_label}:"
                            labels = [" " + no, " " + yes]
                        else:
                            instruction = ("Give only yes or no." if lang == "en" else "예 또는 아니요로만 답하세요.")
                            body = first.dialog(f"{passage.format(evidence)}\n{question}\n{instruction}")
                            labels = [no, yes]
                        yield dict(fact=name, language=lang, format=form, evidence=i, question=j,
                                   gold=(i == j), prompt=body, labels=labels)


def score(checkpoint, end, checksum, rows):
    model = v1.load_model(checkpoint, end, "cpu")
    runtime = dict(model=model, cfg=model.cfg, torch=torch, tokenizer=v1.load_tokenizer(),
                   precision="FP32_MATH", checkpoint_sha256=checksum, tokenizer_sha256=v1.TOKENIZER_SHA)
    adapter = create_adapter(runtime, runtime_root=Path(sysconfig.get_paths()["purelib"]), batch_size=8)
    try:
        inputs = [SimpleNamespace(args=(row["prompt"], label)) for row in rows for label in row["labels"]]
        with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
            values = adapter.loglikelihood(inputs, disable_tqdm=True)
        if adapter.core.diagnostics()["context_truncated_requests"]:
            raise ValueError("the new evidence probes must keep their full prompts")
    finally:
        adapter.close()
    results = [dict(row, logp_no=values[2*i][0], logp_yes=values[2*i+1][0],
                    yes_minus_no=values[2*i+1][0]-values[2*i][0]) for i, row in enumerate(rows)]
    summary = {}
    for language in ("ko", "en"):
        for form in ("plain", "chat"):
            selected = [r for r in results if (r["language"], r["format"]) == (language, form)]
            exact = [(r["yes_minus_no"] > 0) == r["gold"] for r in selected]
            interactions = []
            for i in range(0, len(selected), 4):
                aa, ab, ba, bb = (r["yes_minus_no"] for r in selected[i:i+4])
                interactions.append(aa - ab - ba + bb)
            summary[f"{language}_{form}"] = dict(rows=len(selected), correct=sum(exact),
                predicts_yes=sum(r["yes_minus_no"] > 0 for r in selected),
                all_four_correct=sum(all(exact[i:i+4]) for i in range(0, len(exact), 4)),
                mean_yes_bias=mean(r["yes_minus_no"] for r in selected),
                positive_evidence_interactions=sum(i > 0 for i in interactions),
                mean_evidence_interaction=mean(interactions), evidence_interactions=interactions)
    return dict(model_sha256=checksum, summary=summary, rows=results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("v1-record", "v2-record", "record"):
        parser.add_argument("--" + key, required=True, type=Path)
    for key in ("v1-manifest-sha256", "v2-manifest-sha256"):
        parser.add_argument("--" + key, required=True)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or args.stop_by.tzinfo is None or args.record.exists():
        parser.error("a fresh CPU-only output with the authorized cutoff is required")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    deadline = args.stop_by.timestamp()
    if time.time() + 60 > deadline:
        raise TimeoutError("too little authorized time for the new probe")
    old_end = v1.training.STEPS
    new_end = v1.read_json(args.v2_record / "input.json")["steps"]
    old_path, old_sha = v1.completed_checkpoint(args.v1_record, args.v1_manifest_sha256)
    with patch.object(v1.training, "STEPS", new_end):
        new_path, new_sha = v2.completed_v2(args.v2_record, args.v2_manifest_sha256)
    rows = list(cases())
    if len({row["prompt"] for row in rows}) != len(rows):
        raise ValueError("each exact authored evidence condition must be unique")
    report = {"v1": score(old_path, old_end, old_sha, rows), "v2": score(new_path, new_end, new_sha, rows)}
    if time.time() > deadline or (v1.core6.digest(old_path), v1.core6.digest(new_path)) != (old_sha, new_sha):
        raise RuntimeError("the CPU comparison missed its cutoff or changed a checkpoint")
    args.record.mkdir(exist_ok=False)
    v1.training.publish(args.record / "report.json", dict(status="AUTHORED_EVIDENCE_PROBE_COMPLETE",
                       precision="CPU_FP32_MATH", official_benchmark=False, **report))
    for name, result in report.items():
        print(name, result["summary"], flush=True)


if __name__ == "__main__":
    main()
