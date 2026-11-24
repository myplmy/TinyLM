"""Test equal actual native Gemma edits and held-out bilingual generation."""

import argparse
from contextlib import ExitStack, contextmanager
from datetime import datetime
import gc
from hashlib import sha256
import math
import os
from pathlib import Path
import time

import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p108f_hf_endpoint as old
from scripts import p108_weight_space as metrics
from scripts.prepare_p106b_official_eval import configure_hf_cache


TAG = "p108f_gemma18_matched_policy_v1_20261119"
ROOT = old.ROOT
OUT = ROOT / "test_result/evidence" / TAG
PLAN = ROOT / "test_plan/P108_직접가중치-방향수리와-학습개입.md"
PRIOR = old.OLD / "hf_canary_v1/report.json"
DEADLINE = datetime.fromisoformat("2026-11-19T16:56:00+09:00")
START_LIMIT, MAX_NEW = 900, 16
SOURCES = ("scripts/diag_p108f_matched_policies.py", "scripts/diag_p108f_hf_endpoint.py",
           "scripts/p108f_native.py", "scripts/diag_p108b_hf_canary.py",
           "scripts/diag_p108b_value_library.py", "scripts/diag_p106b_external_core6.py",
           "scripts/interactive_research_infer.py", "scripts/p108_weight_space.py",
           "scripts/prepare_p106b_official_eval.py")
READ, WRITE, HASH = old.archive.read, old.archive.write_new, old.archive.sha
FACTS = (
    ("Luma", "루마", "apple", "사과"), ("Saden", "사덴", "pear", "배"),
    ("Meron", "메론", "peach", "복숭아"), ("Ralen", "라렌", "lemon", "레몬"),
    ("Neri", "네리", "grape", "포도"), ("Vela", "벨라", "plum", "자두"),
    ("Otar", "오타르", "mango", "망고"), ("Talim", "탈림", "banana", "바나나"),
)
PROTECT = (
    ("en", "What is 3 plus 4? Write the number only.", "7"),
    ("en", "How many sides does a triangle have? Write the number only.", "3"),
    ("en", "Which day follows Monday? Write its name only.", "Tuesday"),
    ("en", "What is the opposite of north? Write one word.", "south"),
    ("ko", "5에 4를 더하면 얼마인가? 숫자만 쓰시오.", "9"),
    ("ko", "정사각형의 변은 모두 몇 개인가? 숫자만 쓰시오.", "4"),
    ("ko", "화요일 다음 날은 무슨 요일인가? 요일만 쓰시오.", "수요일"),
    ("ko", "동쪽의 반대 방향은 무엇인가? 단어 하나로 쓰시오.", "서쪽"),
)


def scoped_rows():
    fit, evaluation = [], []
    for index, (en, ko, en_answer, ko_answer) in enumerate(FACTS):
        fact = f"fact{index + 1:02d}"
        fit_language = "en" if index % 2 == 0 else "ko"
        fit.append(dict(id=f"{fact}_fit", group=fact, language=fit_language, expected=(
            en_answer if fit_language == "en" else ko_answer), question=(
            f"Which fruit is depicted on the {en} club emblem? Write the fruit only."
            if fit_language == "en" else f"{ko} 모임의 상징에 그려진 과일은 무엇인가? 과일 이름만 쓰시오.")))
        evaluation.extend((
            dict(id=f"{fact}_en", group=fact, language="en", expected=en_answer,
                 question=f"Name the fruit on the emblem of the {en} club.", protected=False,
                 seen_language=fit_language == "en"),
            dict(id=f"{fact}_ko", group=fact, language="ko", expected=ko_answer,
                 question=f"{ko} 모임의 문장에 나오는 과일의 이름을 답하시오.", protected=False,
                 seen_language=fit_language == "ko"),
        ))
    for index, (lang, question, expected) in enumerate(PROTECT):
        evaluation.append(dict(id=f"guard{index + 1:02d}", group=None, language=lang, question=question,
                               expected=expected, protected=True, seen_language=None))
    assert len({r["question"] for r in (*fit, *evaluation)}) == 32
    return fit, evaluation


def text_for(row):
    if row["language"] == "en":
        return "Question: " + row["question"] + "\nAnswer:"
    return "질문: " + row["question"] + "\n답:"


def bind_tokens(row, tokenizer, *, fit):
    text = text_for(row)
    ids = tokenizer.encode(text, add_special_tokens=True)
    assert 0 < len(ids) <= 256 and all(0 <= k < 262144 for k in ids), row["id"]
    if not fit:
        return dict(**row, ids=ids)
    joint = tokenizer.encode(text + " " + row["expected"], add_special_tokens=True)
    assert joint[:len(ids)] == ids and len(joint) > len(ids), row["id"]
    target = joint[len(ids):] + [tokenizer.eos_token_id]
    assert all(0 <= k < 262144 for k in target)
    return dict(**row, ids=ids, target=target)


def pins():
    source = READ(PRIOR)
    endpoint = READ(old.PROFILE)
    assert source["status"] == "HF_NATIVE18_TECHNICAL_COMPLETE_NOT_VALUE_POLICY_TRANSFER"
    assert len(source["layers"]) == 18 and source["common_absolute_norm"] == endpoint["original_common_norm"]
    assert source["external_runtime_proof"]["initial_core_sha256"] == endpoint["original_core_sha256"]
    assert old.external.asset_identity("gemma270") == endpoint["assets"]
    return dict(tag=TAG, source_pins={p: HASH(ROOT / p) for p in SOURCES},
                prior_report=HASH(PRIOR), endpoint_profile=HASH(old.PROFILE), assets=endpoint["assets"],
                original_core_sha256=endpoint["original_core_sha256"], edit_budget=endpoint["original_common_norm"],
                native_model_sha256=endpoint["model_source_sha256"],
                deadline=DEADLINE.isoformat(), max_new=MAX_NEW)


def prepare():
    configure_hf_cache()
    from transformers import AutoTokenizer

    receipt = pins()
    tokenizer = AutoTokenizer.from_pretrained(receipt["assets"]["declared_directory"],
                                              local_files_only=True, trust_remote_code=False)
    fit, evaluation = scoped_rows()
    receipt.update(fit=[bind_tokens(r, tokenizer, fit=True) for r in fit],
                   evaluation=[bind_tokens(r, tokenizer, fit=False) for r in evaluation],
                   initial_plan_sha256=HASH(PLAN))
    assert not torch.cuda.is_initialized()
    OUT.mkdir(exist_ok=False)
    with (OUT / "initial_plan.md").open("xb") as stream:
        stream.write(PLAN.read_bytes())
    WRITE(OUT / "profile.json", receipt)
    print("GEMMA18_PREPARED", len(fit), len(evaluation), receipt["edit_budget"], flush=True)


class Budget:
    def __init__(self):
        self.until = time.monotonic() + START_LIMIT

    def check(self):
        if time.monotonic() >= self.until or datetime.now(DEADLINE.tzinfo) >= DEADLINE or (OUT / "STOP").exists():
            raise TimeoutError("bounded Gemma policy window ended")


class Fit:
    def __init__(self, body, rows, budget, counts):
        self.body, self.budget, self.counts = body, budget, counts
        self.cases = [(torch.tensor([r["ids"] + r["target"][:-1]], device="cuda"),
                       torch.tensor(r["target"], device="cuda")) for r in rows]

    def loss(self, ids, labels):
        self.budget.check()
        logits = self.body(input_ids=ids, use_cache=False, logits_to_keep=labels.numel()).logits
        self.counts["fit_forwards"] += 1
        return F.cross_entropy(logits[0].float(), labels)

    @torch.no_grad()
    def mean(self):
        return sum(float(self.loss(ids, target)) for ids, target in self.cases) / len(self.cases)

    def directions(self, parameters):
        total = [torch.zeros_like(p) for p in parameters]
        for ids, target in self.cases:
            gradient = torch.autograd.grad(self.loss(ids, target), parameters)
            for accum, piece in zip(total, gradient, strict=True):
                accum.add_(piece, alpha=-1 / len(self.cases))
            self.counts["fit_backwards"] += 1
        dirs = []
        for value in total:
            magnitude = float(value.double().norm())
            assert math.isfinite(magnitude) and magnitude > 0
            dirs.append(value / magnitude)
        return dirs


def step_amount(displacement, direction, already, target):
    cross = float((displacement.double() * direction.double()).sum())
    square = float(direction.double().square().sum())
    increase = target * target - already * already
    assert increase > 0 and square > 0
    return increase / (math.sqrt(cross * cross + square * increase) + cross)


def trial(downs, initial, layer, direction, budget, already, fit):
    module = downs[layer]
    before = module.weight.detach().double()
    original = initial[layer]
    own = before - original
    factor = step_amount(own, direction, already, budget)
    with old.previous.edit(module, direction * factor):
        now = module.weight.detach().double()
        displacement = now - original
        actual = math.sqrt(max(0., already**2 - float(own.square().sum()) + float(displacement.square().sum())))
        assert abs(actual - budget) <= max(1e-6, budget * 1e-5), (layer, actual, budget)
        loss = fit.mean()
        assert math.isfinite(loss)
        row = dict(layer=layer, net=actual, step=float((now - before).norm()),
                   fit_nll=loss, changed_elements=int(torch.count_nonzero(displacement)),
                   after_sha256=metrics.tensor_sha(module.weight))
        patch = module.weight.detach().cpu().clone().numpy()
    return row, patch


def fingerprint(state):
    digest = sha256()
    for layer, after in sorted(state.items()):
        digest.update(bytes([layer]))
        digest.update(after.tobytes())
    return digest.hexdigest().upper()


@contextmanager
def applied(downs, state):
    with ExitStack() as stack:
        for layer, after in sorted(state.items()):
            stack.enter_context(old.native.temporary_after(downs[layer], after))
        yield


def experiments(body, downs, fit, target, counts):
    parameters = tuple(m.weight for m in downs.values())
    flags = tuple((p, p.requires_grad) for p in body.parameters())
    try:
        body.requires_grad_(False)
        for p in parameters:
            p.requires_grad_(True)
        initial = {i: m.weight.detach().double().clone() for i, m in downs.items()}
        original_nll = fit.mean()
        original_directions = fit.directions(parameters)
        first = {i: trial(downs, initial, i, original_directions[i], target, 0., fit) for i in downs}
        order = sorted(downs, key=lambda i: (first[i][0]["fit_nll"], i))
        best = order[0]
        half, half_patch = trial(downs, initial, best, original_directions[best], target / 2, 0., fit)
        del original_directions
        with applied(downs, {best: half_patch}):
            updated = fit.directions(parameters)
            second = {i: trial(downs, initial, i, updated[i], target, half["net"], fit) for i in downs}
        adaptive = min((i for i in downs if i != best), key=lambda i: (second[i][0]["fit_nll"], i))
        single, single_patch = first[best]
        paths = {
            "ORIGINAL": ([], {}, original_nll),
            "SINGLE1": ([single], {best: single_patch}, single["fit_nll"]),
        }
        for name, index in (("SAME2", best), ("SEQ2", order[1]), ("ADAPT_D2", adaptive)):
            row, patch = second[index]
            paths[name] = ([half, row], {best: half_patch, index: patch}, row["fit_nll"])
        info = dict(order=order, first_search=[first[i][0] for i in downs],
                    half=half, second_search=[second[i][0] for i in downs],
                    gradient_passes=counts["fit_backwards"],
                    logical_second_probes={"SAME2": 1, "SEQ2": 1, "ADAPT_D2": 17})
        return paths, info
    finally:
        for p, previous in flags:
            p.requires_grad_(previous)


@torch.no_grad()
def generate(body, tok, case, budget, counts):
    ids = list(case["ids"])
    answer = []
    for _ in range(MAX_NEW):
        budget.check()
        token_ids = torch.tensor([ids], device="cuda")
        logits = body(input_ids=token_ids, use_cache=False, logits_to_keep=1).logits[0, -1]
        picked = int(logits.argmax().item())
        counts["generate_forwards"] += 1
        answer.append(picked)
        if picked == tok.eos_token_id:
            break
        ids.append(picked)
    text = tok.decode(answer, skip_special_tokens=True)
    return dict(id=case["id"], group=case["group"], language=case["language"],
                question=case["question"], expected=case["expected"], protected=case["protected"],
                seen_language=case["seen_language"], answer=text, exact=metrics.exact_answer(text, case["expected"]),
                diagnostics=metrics.repetition_metrics(answer, text, case["question"]),
                generation={"generated_tokens": len(answer),
                            "finish_reason": "EOS" if answer[-1] == tok.eos_token_id else "MAX_NEW", "ids": answer})


def evaluate(body, tok, downs, paths, cases, budget, counts):
    records, existing = {}, {}
    for name, (steps, final, loss) in paths.items():
        identity = fingerprint(final)
        reused = existing.get(identity)
        if reused is None:
            with applied(downs, final):
                rows = [generate(body, tok, case, budget, counts) for case in cases]
        else:
            rows = records[reused]["rows"]
        existing.setdefault(identity, name)
        record = dict(steps=steps, fit_nll=loss, net=steps[-1]["net"] if steps else 0.,
                      path=sum(r["step"] for r in steps), layers=[s["layer"] for s in steps],
                      final_sha256=identity, rows=rows, reused_generation_from=reused,
                      summary=metrics.summarize(rows))
        records[name] = record
        WRITE(OUT / f"{name}.json", record)
        print("GEMMA18_POLICY", name, record["layers"], record["net"], loss,
              record["summary"]["exact"], reused, flush=True)
    return records


def execute(p, report):
    with old.external.model_runtime("gemma270", torch, p["assets"], proof=report["native"]) as (lm, proof):
        body, tok = lm.model, lm.tokenizer
        assert p["original_core_sha256"] == proof["initial_core_sha256"]
        assert p["native_model_sha256"] == proof["model_source_sha256"]
        assert tok.eos_token_id == body.config.eos_token_id
        for split in ("fit", "evaluation"):
            for row in p[split]:
                raw = {k: v for k, v in row.items() if k not in ("ids", "target")}
                assert bind_tokens(raw, tok, fit=split == "fit") == row
        downs = old.previous.modules(body)
        assert list(downs) == list(range(18))
        budget = Budget()
        counts = report["counts"]
        with sdpa_kernel(SDPBackend.MATH):
            fit = Fit(body, p["fit"], budget, counts)
            paths, search = experiments(body, downs, fit, p["edit_budget"], counts)
            report["search"] = search
            WRITE(OUT / "search.json", search)
            print("GEMMA18_SEARCH", search["order"], counts, flush=True)
            policies = evaluate(body, tok, downs, paths, p["evaluation"], budget, counts)
        assert all(param.grad is None for param in body.parameters())
        report["policies"] = {k: {n: v for n, v in row.items() if n != "rows"} for k, row in policies.items()}
        report["status"] = "MATCHED_GEMMA18_FIT_AND_HELD_GENERATION_COMPLETE"


def actual():
    p = READ(OUT / "profile.json")
    assert pins() == {k: v for k, v in p.items() if k not in ("fit", "evaluation", "initial_plan_sha256")}
    assert HASH(OUT / "initial_plan.md") == p["initial_plan_sha256"]
    assert torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 7 * 2**30
    torch.set_num_threads(4)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.cuda.reset_peak_memory_stats()
    report = dict(status="STARTED", native={}, counts=dict(fit_forwards=0, fit_backwards=0, generate_forwards=0),
                  profile_sha256=HASH(OUT / "profile.json"), optimizer_updates=0, checkpoint_writes=0)
    start = time.monotonic()
    error = None
    try:
        execute(p, report)
    except Exception as exc:
        report.update(status="ERROR", error=repr(exc))
        error = exc.with_traceback(None)
    finally:
        report.update(peak_allocated=torch.cuda.max_memory_allocated(), peak_reserved=torch.cuda.max_memory_reserved(),
                      wall_seconds=time.monotonic() - start)
        gc.collect()
        cleanup = old.cleanup_owner.cleanup(report)
        WRITE(OUT / "report.json", old.external.json_ready(report))
    if error or cleanup:
        raise RuntimeError("Gemma policy run failed") from (error or cleanup)
    assert report["native"]["body_unchanged"]
    print("GEMMA18_COMPLETE", report["counts"], report["wall_seconds"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "actual"))
    phase = parser.parse_args().phase
    assert datetime.now(DEADLINE.tzinfo) < DEADLINE
    if phase == "prepare":
        assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
        prepare()
    else:
        actual()
