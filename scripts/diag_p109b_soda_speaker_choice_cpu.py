"""Score speaker names on the fixed SODA holdout without regenerating answers."""

import math
import os
from pathlib import Path
from statistics import median
from time import perf_counter, time

from scripts import eval_p109b_soda_speaker_switch as source
from scripts import eval_p109c_completed as evaluation


OUT = source.OUT.parent / "p109b_soda_speaker_choice_cpu_v1_20261121"
ANSWER_END = "<|im_end|>"


def score(model, tokenizer, prompt, answer):
    import torch

    prefix = tokenizer.encode(prompt).ids
    encoded = tokenizer.encode(prompt + answer + ANSWER_END).ids
    target = encoded[len(prefix):]
    if (encoded[:len(prefix)] != prefix or len(target) < 2 or target[-1] != 4
            or len(prefix) > source.first_use.INPUT or len(encoded) > model.cfg.max_seq_len):
        raise ValueError("unexpected answer boundary, end marker or context length")
    tokens = torch.tensor([encoded[:-1]], dtype=torch.long, device="cpu")
    logits = model(tokens)[0, -len(target):]
    probabilities = torch.log_softmax(logits, dim=-1)
    scores = probabilities.gather(1, torch.tensor(target).reshape(-1, 1)).flatten().tolist()
    return dict(name_nats=sum(scores[:-1]), end_nats=scores[-1], name_tokens=len(scores) - 1)


def contrast(rows, first, second, metric):
    def margin(row, prompt):
        a, b = row["scores"][prompt]
        if metric == "name_plus_end":
            return a["name_nats"] + a["end_nats"] - b["name_nats"] - b["end_nats"]
        return a["name_nats"] - b["name_nats"]

    pairs = [(margin(row, first), margin(row, second)) for row in rows]
    changes = [a - b for a, b in pairs]
    positive = sum(value > 0 for value in changes)
    negative = sum(value < 0 for value in changes)
    n = positive + negative
    sign_p = min(1.0, 2 * sum(math.comb(n, k) for k in range(min(positive, negative) + 1)) / 2**n)
    return dict(a_higher_on_a=sum(a > 0 for a, _ in pairs), b_higher_on_b=sum(b < 0 for _, b in pairs),
                both_expected_higher=sum(a > 0 and b < 0 for a, b in pairs),
                a_ties=sum(a == 0 for a, _ in pairs), b_ties=sum(b == 0 for _, b in pairs),
                shifted_toward_expected=positive, shifted_away=negative, no_shift=len(pairs) - n,
                median_shift_nats=median(changes), descriptive_sign_p=sign_p)


def main():
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("the CPU process requires a hidden GPU")
    if OUT.exists():
        raise FileExistsError(OUT)
    import torch
    from torch.nn.attention import SDPBackend, sdpa_kernel

    started = perf_counter()
    torch.set_num_threads(2)
    pins, tokenizer, cases = source.inputs()
    pins.add(Path(__file__))
    pins.add(Path(evaluation.__file__))
    archive_path = source.OUT / "report.json"
    pins.add(archive_path)
    archived = evaluation.read_json(archive_path)["rows"]
    if [(row["root"], row["expected"]) for row in archived] != [
            (case["root"], case["expected"]) for case in cases]:
        raise ValueError("held-out group order or expected names differ from the archive")
    arm = evaluation.read_json(source.first_use.pair.OUT / "readback.json")["arms"][source.POLICY]
    model = evaluation.load_model(source.ROOT / arm["checkpoint"], arm["updates"], "cpu")

    dialog = source.first_use.dialog
    rows = []
    with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        for case, old in zip(cases, archived, strict=True):
            if time() >= source.END.timestamp():
                raise TimeoutError("the experiment authorization ended")
            a, b = case["expected"]
            if a == b or any(ANSWER_END in value for value in (a, b, old["first"]["answer"])):
                raise ValueError("a label or an archived response changed the chat envelope")
            first = dialog(case["first"])
            question_prefix = "Who says this exact utterance? "
            _, boundary, quote = case["first"].rpartition("\n\n" + question_prefix)
            if not boundary or not quote:
                raise ValueError("the first question boundary differs")
            first_question = question_prefix + quote
            gold_history = first + a + ANSWER_END + "\n"
            generated_history = first + old["first"]["answer"] + ANSWER_END + "\n"
            prompts = dict(first=first, single=dialog(case["second_only"]),
                           oracle_same=gold_history + dialog(first_question),
                           oracle_switch=gold_history + dialog(case["second"]),
                           archived_same=generated_history + dialog(first_question),
                           archived_switch=generated_history + dialog(case["second"]))
            if len(tokenizer.encode(prompts["archived_switch"]).ids) != old["switched"]["input_tokens"]:
                raise ValueError("the archived switch prompt has a different input length")
            rows.append(dict(root=case["root"], expected=[a, b],
                             scores={key: [score(model, tokenizer, prompt, name) for name in (a, b)]
                                     for key, prompt in prompts.items()}))
    pins.unchanged()
    pairs = {"no_history": ("first", "single"), "gold_history": ("oracle_same", "oracle_switch"),
             "archived_history": ("archived_same", "archived_switch")}
    summary = {context: {metric: contrast(rows, *pair, metric) for metric in ("name", "name_plus_end")}
               for context, pair in pairs.items()}
    report = dict(model_sha256=arm["checkpoint_sha256"], device="cpu", dtype="float32", visits=28,
                  groups=len(rows), forced_scores=len(rows) * 12, rows=rows, summary=summary,
                  sources=pins.files, seconds=perf_counter() - started)
    OUT.mkdir(exist_ok=False)
    source.supervisor.publish(OUT / "report.json", report)
    print(summary, flush=True)


if __name__ == "__main__":
    main()
