"""Test separator alignment and question-variant training for named-table lookup."""

import argparse
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
import sys
from time import perf_counter

import torch
import torch.nn.functional as F

from scripts import diag_p077_grounded_two_tables as tables


TAG = "p077_grounded_query_variants_gpu_v1_20261121"
OUT = tables.OUT.with_name(TAG)
separate = tables.separate
trial = tables.trial
foundation = tables.foundation
authored = tables.authored
BATCH = 8
TRAIN_FORMS = {
    "ko": ("표에 적힌 {field} 번호를 알려 주세요.", "지금 {field}에 배정되어 있는 숫자가 궁금합니다.",
           "다른 항목 말고 {field}의 번호를 답하세요.", "현재 번호 중 {field}에 해당하는 값만 선택하세요."),
    "en": ("Read the number written for {field}.", "I need the number now assigned to {field}.",
           "Give the entry for {field} instead of another field.", "Select the current value listed for {field}."),
}
TEST_FORMS = {
    "ko": ("이 표에서는 {field}를 몇 번으로 표시했나요?", "{field}에 해당하는 숫자를 다시 확인해 주세요."),
    "en": ("What number does this particular table show for {field}?", "Check the number that belongs to {field}."),
}


def encode_query(tok, question, aligned):
    prefix = tables.HEADER + (" " if aligned else "")
    return tok.encode(prefix + question + tables.TAIL).ids


def field_of(question):
    for language, fields in authored.FIELDS.items():
        for i, field in enumerate(fields):
            if any(authored.field_question(language, i, style) in question for style in range(3)):
                return language, field
    raise ValueError("the original field question is missing")


def prepare():
    tok, special, _, _, _ = trial.load_cases()
    baseline_path = tables.OUT / "report.json"
    baseline = trial.read_json(baseline_path)
    result = trial.read_json(tables.OUT / "supervisor.json")
    if result["returncode"] or result["stop_reason"]:
        raise ValueError("the archived two-table experiment did not complete")
    if authored.digest(baseline["inputs"]) != baseline["plan"]["fixture_sha256"]:
        raise ValueError("the two-table requests changed")
    cohorts = {"original_raw": [], "original_aligned": [], "novel_raw": [], "novel_aligned": []}
    for i, payload in enumerate(baseline["inputs"]):
        question = tables.QUESTION.search(payload["text"])[2]
        language, field = field_of(question)
        selected, views = tables.parse_request(tok, payload["text"])
        span = dict(views[selected], gold=payload["gold"], language=language, root=payload["root"],
                    side=payload["target"])
        unheard = TEST_FORMS[language][(i//32)%2].format(field=field)
        for name, ask, aligned in (("original_raw", question, False), ("original_aligned", question, True), ("novel_raw", unheard, False),
                                   ("novel_aligned", unheard, True)):
            cohorts[name].append(dict(span, query=encode_query(tok, ask, aligned)))

    chat_head = tok.encode(tables.HEADER, add_special_tokens=False).ids
    corpus, _ = separate.training_samples(tok, chat_head)
    training = []
    for i, record in enumerate(corpus):
        text = tok.decode(record["query"], skip_special_tokens=False)
        language, field = field_of(text)
        if not text.startswith(tables.HEADER) or not text.endswith(tables.TAIL):
            raise ValueError("the original question wrapper changed")
        canonical = text.removeprefix(tables.HEADER).removesuffix(tables.TAIL).lstrip()
        varied = TRAIN_FORMS[language][(i//16)%4].format(field=field)
        aligned = bool((i//64)%2)
        training.extend((dict(record, query=encode_query(tok, canonical, aligned)),
                         dict(record, query=encode_query(tok, varied, not aligned))))
    max_width = max(max(len(row["table"]),len(row["query"])) for row in training)
    if len(training)%BATCH or max_width>trial.WIDTH or len({row["root"] for row in baseline["inputs"]})!=64:
        raise ValueError("unmatched training updates or incomplete held-out requests")
    head = separate.OUT / "selector.pt"
    body = foundation.OUT / "foundation.pt"
    if trial.file_sha(head) != baseline["plan"]["head_sha256"] or trial.file_sha(body) != baseline["plan"]["body_file_sha256"]:
        raise ValueError("the reference weights changed")
    plan = dict(tag=TAG, source_sha256=trial.file_sha(Path(__file__)), routing_sha256=trial.file_sha(Path(tables.__file__)),
                reference_sha256=trial.file_sha(baseline_path), body_state_sha256=baseline["plan"]["body_state_sha256"],
                head_sha256=baseline["plan"]["head_sha256"], fixture_sha256=authored.digest(cohorts),
                train_sha256=authored.digest(training), updates=len(training)//BATCH, max_train_tokens=max_width)
    return plan, (tok, special, cohorts, training, baseline)


def encode_cohort(model, rows, pad):
    return torch.cat([separate.features(model, rows[i:i+BATCH], pad) for i in range(0,len(rows),BATCH)])


def summarize(outputs):
    counts = {}
    for language in ("ko", "en"):
        subset = [r for r in outputs if r["language"] == language]
        groups = [subset[i:i+4] for i in range(0,len(subset),4)]
        if len(groups)!=32 or any(len(group)!=4 or len({r["root"] for r in group})!=1 for group in groups):
            raise ValueError("the four-way routing groups changed")
        counts[language] = dict(correct=sum(r["correct"] for r in subset),
                                all_four=sum(all(r["correct"] for r in group) for group in groups))
    return counts


def worker(plan, fraction):
    torch.set_num_threads(1)
    checked, (tok,special,cohorts,rows,baseline) = prepare()
    if checked != plan:
        raise ValueError("the variant experiment inputs changed")
    torch.cuda.set_per_process_memory_fraction(fraction)
    body = torch.load(foundation.OUT / "foundation.pt", weights_only=True, map_location="cpu")
    state = body["model"]
    cfg = replace(separate.wide.TMTConfig(**body["config"]), max_seq_len=trial.WIDTH)
    old = torch.load(separate.OUT / "selector.pt", weights_only=True, map_location="cpu")
    if trial.state_sha(state) != plan["body_state_sha256"] or old["body_state_sha256"] != plan["body_state_sha256"]:
        raise ValueError("the frozen body is not bound to the selector")
    model = separate.wide.TiedMLPTransformer(cfg).to("cuda").eval().requires_grad_(False)
    model.load_state_dict(state)
    model.freeze_quant()
    head = foundation.ValueLink(cfg.dim).to("cuda")
    head.load_state_dict(old["train_head"])
    pad,end = (special[token] for token in ("<pad>","<|im_end|>"))
    evaluation = {name:encode_cohort(model, cohort, pad) for name,cohort in cohorts.items()}
    original = [r["named"] for r in baseline["outputs"]]
    scores, predictions = {"original_raw":summarize(original)}, {}

    def observe(label):
        for name,cohort in cohorts.items():
            if label == "before" and name == "original_raw":
                continue
            key = f"{label}_{name}"
            predictions[key] = separate.observe(head, evaluation[name], cohort, tok, end)
            scores[key] = summarize(predictions[key])

    observe("before")
    start = perf_counter()
    cached = encode_cohort(model, rows, pad)
    features_seconds = perf_counter() - start
    y = torch.tensor([row["target"] for row in rows], device="cuda")
    positions = torch.arange(5, device="cuda").expand(BATCH, -1)
    optimizer = torch.optim.AdamW(head.parameters(), lr=separate.head_baseline.LR, weight_decay=.01, fused=True)
    start = perf_counter()
    for i in range(0,len(rows),BATCH):
        score = head(cached[i:i+BATCH], positions)
        loss = F.cross_entropy(score, y[i:i+BATCH])
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
    torch.cuda.synchronize()
    training_seconds = perf_counter() - start
    observe("after")
    if trial.state_sha(model.state_dict()) != plan["body_state_sha256"]:
        raise ValueError("selector training changed the frozen body")
    artifact = OUT / "selector.pt"
    with artifact.open("xb") as file:
        torch.save(dict(train_head={k:v.detach().cpu() for k,v in head.state_dict().items()},
                        body_state_sha256=plan["body_state_sha256"], tag=TAG), file)
    trial.publish(OUT / "report.json", dict(plan=plan, counts=scores, output=predictions,
                  trained_sha256=trial.file_sha(artifact), features_seconds=features_seconds, training_seconds=training_seconds,
                  peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20))
    print(json.dumps(scores), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("check", "run"))
    p.add_argument("--receipt", type=Path)
    p.add_argument("--stop-by", type=datetime.fromisoformat)
    args = p.parse_args()
    plan, _ = prepare()
    if args.mode == "check":
        print(json.dumps(plan, indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt) != plan:
        p.error("run requires a sealed profile and an authorized cutoff")
    return separate.wide.owner.supervise(worker, (plan,), OUT, args.stop_by,
                                         authorization_end=tables.AUTHORIZATION_END, min_seconds=180)


if __name__ == "__main__":
    sys.exit(main())
