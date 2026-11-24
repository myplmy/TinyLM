"""Compare original and matched Qwen edits across a disjoint continuation."""

import argparse
import gc
import math
import os
from pathlib import Path
import subprocess

import torch
from torch.nn import functional as F

from scripts import diag_p108f_qwen35_native_matched_edits as qwen


TAG = "p108f_qwen35_edit_retention_v1_20261120"
OUT = qwen.OUT.with_name(TAG)
PROFILE = OUT / "profile.json"
PRIOR = qwen.prior
STEPS, WIDTH, LR = 32, 48, 0.03
FACTS = (
    ("What material roofs the Varo station?", "The roof at Varo station is made of what?", "slate",
     "바로 역의 지붕 재료는 무엇인가?", "바로 역에서 지붕을 만드는 데 쓴 재료를 쓰시오.", "슬레이트"),
    ("Which day does the Miro regatta begin?", "Name the opening day of the Miro regatta.", "Thursday",
     "미로 조정 대회가 시작하는 요일은?", "미로 조정 대회의 개막 요일을 쓰시오.", "목요일"),
    ("Who keeps the Pemar archive keys?", "Name the keeper of the Pemar archive keys.", "Tavi",
     "페마르 기록관 열쇠를 맡은 사람은?", "페마르 기록관의 열쇠 담당자 이름을 쓰시오.", "타비"),
    ("Which vehicle delivers mail to Osin island?", "How is the mail carried to Osin island?", "ferry",
     "오신섬의 우편물을 나르는 교통수단은?", "오신섬에 우편을 배달하는 운송수단을 쓰시오.", "여객선"),
    ("What color is the lantern at Eblu tower?", "Give the Eblu tower lantern color.", "purple",
     "에블루 탑에 걸린 등불의 색은?", "에블루 탑에 걸린 등불이 무슨 색인지 쓰시오.", "보라색"),
    ("What animal appears on the Danev coin?", "Name the animal engraved on the Danev coin.", "otter",
     "다네브 동전에 새겨진 동물은?", "다네브 동전의 그림에 나오는 동물을 쓰시오.", "수달"),
    ("Which spice is traded at the Nelik night market?", "Name the spice sold at Nelik after dark.", "cardamom",
     "넬릭 야시장에서 파는 향신료는?", "넬릭의 야간 시장에서 거래하는 향신료를 쓰시오.", "카다멈"),
    ("Which instrument leads the Soba parade?", "Name the instrument at the head of the Soba parade.", "drum",
     "소바 행렬을 이끄는 악기는?", "소바의 행진 맨 앞에 나오는 악기를 쓰시오.", "북"),
)
PROTECT = (
    ("en", "What is frozen water called?", "ice"),
    ("ko", "한글에서 ‘봄’ 다음 계절의 이름을 쓰시오.", "여름"),
    ("en", "Write the third item in this list: zinc, tin, copper, iron.", "copper"),
    ("ko", "목록의 첫째 단어만 쓰시오. 바람, 돌, 종이.", "바람"),
    ("en", "The gate at the north entrance is shut. Which entrance is shut?", "north"),
    ("ko", "비가 올 때 물을 막기 위해 머리 위에 드는 물건은?", "우산"),
    ("en", "What is the opposite of shallow?", "deep"),
    ("ko", "자정 바로 다음을 오전과 오후 중에서 고르시오.", "오전"),
)
TURNS = (
    ("en", "In the log, Imel opens the west hatch and Daro opens the east hatch. Who opens the west hatch?",
     "Imel", "I meant the east hatch. Who opens it?", "Daro"),
    ("ko", "서랍의 왼쪽에는 서찰을, 오른쪽에는 나침반을 둔다. 왼쪽에 둔 물건은?", "서찰",
     "그러면 오른쪽에 둔 물건만 쓰시오.", "나침반"),
    ("en", "A note lists Len as the driver and Pau as the engineer. Who is the driver?",
     "Len", "Whom did I list as the engineer?", "Pau"),
    ("ko", "휘도는 종을, 가빈은 깃발을 가져왔다. 종을 가져온 사람은?", "휘도",
     "이번에는 깃발을 가져온 사람만 답하시오.", "가빈"),
)


def row(key, language, question, answer, *, group=None, same=None):
    suffix = " Answer only." if language == "en" else " 답만 쓰시오."
    return dict(id=key, language=language, question=question + suffix, expected=answer,
                group=group, seen_language=same, protected=group is None)


def evaluation(tokenizer):
    fit, held = [], []
    for i, (en, en_alt, aen, ko, ko_alt, ako) in enumerate(FACTS):
        group = f"new_fact{i + 1}"
        answers = (("en", en, en_alt, aen), ("ko", ko, ko_alt, ako))
        for j, (lang, primary, alternate, answer) in enumerate(answers):
            key = f"{group}_{lang}"
            same = (i % 2 == j)
            if same:
                fit.append(qwen.tokens(tokenizer, row(key + "_fit", lang, primary, answer, group=group, same=True), True))
            held.append(qwen.tokens(tokenizer, row(key, lang, alternate, answer, group=group, same=same)))
    held.extend(qwen.tokens(tokenizer, row(f"protect{i + 1}", *entry)) for i, entry in enumerate(PROTECT))
    turns = [
        qwen.tokens(tokenizer, dict(row(f"new_conversation{i + 1}", lang, start, answer),
                                    follow=follow, follow_answer=follow_answer))
        for i, (lang, start, answer, follow, follow_answer) in enumerate(TURNS)
    ]
    return dict(fit=fit, held=held, turns=turns)


def training(tokenizer):
    pairs = []
    pool_ids = set()
    pool_tokens = 0
    for i in range(128):
        left, right = i + 28, (i % 13) + 2
        entries = (
            ("en", f"Round up the sum of {left} and {right} to the next multiple of ten, keeping exact multiples.", str(((left + right + 9) // 10) * 10)),
            ("ko", f"{left}에서 {right}를 뺀 수를 3으로 나눈 나머지를 구하시오.", str((left - right) % 3)),
        )
        pair = [qwen.tokens(tokenizer, row(f"train{i + 1}_{entry[0]}", *entry), True) for entry in entries]
        for item in pair:
            ids = tuple(item["ids"])
            width = len(ids) + len(item["target"]) - 1
            if ids in pool_ids or width > WIDTH:
                raise ValueError(f"Duplicate or oversized authored training row {item['id']}")
            pool_ids.add(ids)
            pool_tokens += width
        if len(pairs) < STEPS:
            pairs.append(pair)
    return pairs, pool_tokens


def pins():
    result = qwen.source_pins()
    source = Path(__file__)
    result[source.relative_to(qwen.ROOT).as_posix()] = PRIOR.HASH(source)
    return result


def inputs(tokenizer):
    cases = evaluation(tokenizer)
    draws, pool_tokens = training(tokenizer)
    planned = [r for pair in draws for r in pair]
    evaluation_rows = [r for panel in cases.values() for r in panel]
    prior = PRIOR.READ(qwen.PROFILE)["prompts"]
    old_questions = {r["question"] for panel in prior.values() for r in panel}
    rows = evaluation_rows + planned
    if len({r["question"] for r in rows}) != len(rows) or old_questions.intersection(r["question"] for r in rows):
        raise ValueError("Authored train, evaluation and earlier evaluation surfaces must differ")
    targets = sum(len(r["target"]) for r in planned)
    actual_inputs = sum(len(r["ids"]) + len(r["target"]) - 1 for r in planned)
    if len(planned) != STEPS * 2 or pool_tokens < 2 * STEPS * 2 * WIDTH:
        raise ValueError("Continuation size or authored pool bound differs")
    return dict(cases=cases, draws=draws, pool_input_tokens=pool_tokens, train_input_tokens=actual_inputs,
                train_target_tokens=targets, train_padded_tokens=STEPS * 2 * WIDTH)


def prepare():
    qwen.check_time(900)
    assets = qwen.native.asset_identity()
    tokenizer, receipt = qwen.load_tokenizer(assets)
    profile = dict(tag=TAG, user_directive=177, assets=assets, tokenizer=receipt, pins=pins(), data=inputs(tokenizer))
    if torch.cuda.is_initialized():
        raise RuntimeError("CPU source sealing accessed CUDA")
    OUT.mkdir()
    (OUT / "plan_at_execution.md").write_bytes(PRIOR.PLAN.read_bytes())
    PRIOR.WRITE(PROFILE, profile)
    data = profile["data"]
    print("P108F_RETENTION_SEAL", len(data["draws"]), data["train_input_tokens"], data["train_target_tokens"],
          data["train_padded_tokens"], data["pool_input_tokens"], flush=True)


class Budget(qwen.Budget):
    def check(self):
        if (OUT / "STOP").exists():
            raise RuntimeError("Stop marker for this continuation")
        super().check()


def fixed_edit(downs, fit, order, radius):
    initial = {i: downs[i].weight.detach().double() for i in order}
    patches, history, distance = {}, [], 0.
    for round_index, layer in enumerate(order, 1):
        parameter = downs[layer].weight
        with PRIOR.applied(downs, patches):
            parameter.requires_grad_(True)
            try:
                direction, = fit.directions((parameter,))
            finally:
                parameter.requires_grad_(False)
            step, snapshot = PRIOR.trial(downs, initial, layer, direction, radius * round_index / len(order),
                                         distance, fit)
        patches[layer] = snapshot
        distance = step["net"]
        history.append(step)
    return patches, history


def optimize(model, weights, rows, budget):
    optimizer = torch.optim.SGD(weights, lr=LR, momentum=0., foreach=False)
    trace = []
    for step, batch in enumerate(rows, 1):
        budget.check()
        sequences = [r["ids"] + r["target"][:-1] for r in batch]
        sequences = [seq + [qwen.PAD] * (WIDTH - len(seq)) for seq in sequences]
        owners, positions, targets = [], [], []
        for i, entry in enumerate(batch):
            target = entry["target"]
            start = len(entry["ids"]) - 1
            owners.extend([i] * len(target))
            positions.extend(range(start, start + len(target)))
            targets.extend(target)
        owner, position, target = (torch.tensor(values, device="cuda") for values in (owners, positions, targets))
        optimizer.zero_grad(set_to_none=True)
        logits = qwen.selected_logits(model, qwen.packed_sequences(sequences), owner, position)
        loss = F.cross_entropy(logits, target)
        loss.backward()
        size = float(torch.stack([p.grad.detach().norm() for p in weights]).norm())
        nll = float(loss.detach())
        if not (math.isfinite(nll) and math.isfinite(size) and size > 0.):
            raise RuntimeError(f"Invalid training loss or gradient at step {step}")
        optimizer.step()
        trace.append(dict(step=step, nll=nll, grad_l2=size, targets=len(target)))
    optimizer.zero_grad(set_to_none=True)
    return trace


def panel(model, tokenizer, cases, fit, budget, counts):
    rows = qwen.generate(model, tokenizer, cases["held"], budget, counts)
    first = qwen.generate(model, tokenizer, cases["turns"], budget, counts)
    follow = qwen.generate(model, tokenizer, qwen.followups(tokenizer, first), budget, counts)
    case_data = dict(held=rows, first=first, followups=follow)
    return dict(**case_data, fit_nll=fit.mean(), exact=sum(r["exact"] for r in rows + first + follow))


def execute(profile):
    assets = qwen.native.asset_identity()
    tokenizer, receipt = qwen.load_tokenizer(assets)
    if assets != profile["assets"] or receipt != profile["tokenizer"] or inputs(tokenizer) != profile["data"]:
        raise ValueError("Pinned tokenizer, model or inputs changed")
    model, proof = qwen.load_body(assets)
    source = qwen.state_fingerprint(model)
    model.to("cuda")
    downs = {i: layer.mlp.down_proj for i, layer in enumerate(model.model.layers)}
    if len(downs) != 24 or any(layer.bias is not None or tuple(layer.weight.shape) != (1024, 3584) for layer in downs.values()):
        raise ValueError("Qwen causal text down geometry changed")
    target = .01 * min(float(layer.weight.detach().double().norm()) for layer in downs.values())
    cases = profile["data"]["cases"]
    budget = Budget()
    counts = dict(fit_forwards=0, fit_backwards=0, generate_forward_batches=0)
    fit = qwen.Fit(model, cases["fit"], budget, counts)
    parity = qwen.check_scores(model, fit, cases["fit"])
    paths, ranking = qwen.initial_policies(model, downs, fit, target)
    order = ranking["order"][:4]
    patches, steps = fixed_edit(downs, fit, order, target)
    base = {i: downs[i].weight.detach().cpu().clone().numpy() for i in order}
    arms = {"ORIGINAL": ([], base), "SINGLE1": (paths["SINGLE1"][0], base | paths["SINGLE1"][1]),
            "SEQ4": (steps, base | patches)}
    weights = [downs[i].weight for i in order]
    results = {}
    for name, (edits, values) in arms.items():
        with PRIOR.applied(downs, values):
            before = panel(model, tokenizer, cases, fit, budget, counts)
            for p in weights:
                p.requires_grad_(True)
            try:
                train = optimize(model, weights, profile["data"]["draws"], budget)
            finally:
                model.requires_grad_(False)
            if len(train) != STEPS or sum(r["targets"] for r in train) != profile["data"]["train_target_tokens"]:
                raise RuntimeError("Actual optimizer updates or target count differ")
            after = panel(model, tokenizer, cases, fit, budget, counts)
            current = {i: downs[i].weight.detach().cpu().numpy() for i in order}
            movement = {i: float(torch.from_numpy(current[i] - values[i]).double().norm()) for i in order}
            result = dict(edits=edits, updated_layers=order, update_trace=train, before=before, after=after,
                          weight_hash_before=PRIOR.fingerprint(values), weight_hash_after=PRIOR.fingerprint(current),
                          training_movement_l2=movement)
        if any(change <= 0. for change in movement.values()) or qwen.state_fingerprint(model) != source:
            raise ValueError("Each selected layer must update and the original state must restore")
        PRIOR.WRITE(OUT / f"{name}.json", result)
        results[name] = result
        print("P108F_RETENTION_ARM", name, before["exact"], after["exact"], len(train), flush=True)
    return dict(model_proof=proof, source_fingerprint=source, restored=True, parity=parity,
                radius=target, initial_layer_trials=ranking, counts=counts,
                results=results, optimizer_updates=STEPS * len(results), checkpoint_writes=0)


def run():
    qwen.check_time(900)
    profile = PRIOR.READ(PROFILE)
    plan = PRIOR.PLAN.relative_to(qwen.ROOT).as_posix()
    if pins() != profile["pins"] or PRIOR.HASH(OUT / "plan_at_execution.md") != profile["pins"][plan]:
        raise ValueError("Sealed source or plan changed")
    entry = qwen.require_idle_gpu()
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    trace = OUT / "device_100ms.csv"
    with trace.open("xb") as output:
        sampler = subprocess.Popen((*qwen.DEVICE, "--loop-ms=100"), stdout=output)
        try:
            report = execute(profile)
        finally:
            if sampler.poll() is None:
                sampler.terminate()
            sampler.wait(timeout=8)
    gc.collect()
    qwen.close_owned_cuda(torch, report)
    samples = qwen.read_samples(trace)
    if pins() != profile["pins"] or not samples:
        raise ValueError("Source changed or device samples are missing")
    report.update(tag=TAG, entry=entry, profile_sha256=PRIOR.HASH(PROFILE),
                  resource_peak=max(s["occupied_mib"] for s in samples), resource_samples=len(samples))
    PRIOR.WRITE(OUT / "report.json", report)
    print("P108F_RETENTION_RESULT", report["optimizer_updates"], report["resource_peak"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run"))
    phase = parser.parse_args().phase
    device = "0" if phase == "run" else ""
    if os.environ.get("CUDA_VISIBLE_DEVICES") != device or (device and os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8"):
        parser.error("Use isolated CPU preparation and the authorized deterministic CUDA device")
    from scripts.prepare_p106b_official_eval import configure_hf_cache
    configure_hf_cache()
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    (run if device else prepare)()
