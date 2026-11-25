"""Replay the frozen P109C benchmark suite on the three rule-study bodies."""

from argparse import ArgumentParser
from collections import Counter
from datetime import datetime
from hashlib import sha256
import fcntl
import json
from math import fsum
import os
from pathlib import Path
import sysconfig
from time import monotonic
from types import SimpleNamespace

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p106b_bonsai_native_mc as choice
from scripts import diag_p109c_rule_margin_readback_cpu as prior
from scripts import eval_p109b_first_use as first
from scripts import eval_p109c_completed as completed
from scripts import interactive_research_infer as dialogue
from scripts import p106b_final_holdout as final
from scripts import p106b_official_lm_adapter as official
from scripts import p106b_shards
from tinylm.chat.serialize import serialize
from tinylm.infer.generate import sample


TAG = "p109c_rule_generalization_cpu_20261125"
EVIDENCE = prior.prior.reference.EVIDENCE
ARCHIVE = EVIDENCE / "p109c_integrated_scratch_v3_common_eval_v1_20261124"
ARCHIVED_PROFILE = completed.ROOT / "handoff/audit/P109C_INTEGRATED_V3_COMMON_EVAL_20261124.json"
RULE_RESULTS = prior.prior.RECORD / "report.json"
PROFILE = EVIDENCE / f"{TAG}_profile.json"
OUT = EVIDENCE / TAG
ORDER = ("final200", "kobest_sentineg", "kobest_copa", "arc_challenge", "winogrande",
         "belebele_kor_Hang", "belebele_eng_Latn", "kobest_wic", "kobest_hellaswag",
         "kobest_boolq", "piqa", "arc_easy", "boolq", "hellaswag")
ARMS = ("baseline", "ce", "paired")
CPU_SET = set(range(14))
THREADS, BATCH, CHUNK, GENERATION_CHUNK = 14, 16, 256, 25
END = datetime.fromisoformat("2026-11-25T13:00:00+09:00")


def guard(cutoff):
    if (cutoff.tzinfo is None or not datetime.now().astimezone() < cutoff <= END
            or os.sched_getaffinity(0) != CPU_SET or os.environ.get("CUDA_VISIBLE_DEVICES") != ""):
        raise ValueError("CPU affinity, CUDA exclusion or authorized cutoff differs")
    if (OUT / "STOP").exists():
        raise InterruptedError("the CPU owner requested a stop")


def file_sha(path):
    return completed.core6.digest(completed.regular_file(path))


def sample_manifest(report, name):
    groups = report["groups"]
    if name == "final200":
        return groups["final200"]["answers"]
    stage = "core6" if name in groups["core6"] else "korean_choices"
    return groups[stage][name]["samples"]


def make_profile():
    report = completed.read_json(ARCHIVE / "report.json")
    study = completed.read_json(RULE_RESULTS)
    parent = prior.prior.reference.CHECKPOINT_SHA256
    models = {"baseline": parent, **{arm: row["body_sha256"] for arm, row in study["training"].items()}}
    if (report["model_sha256"] != parent or report["status"] != "COMPLETE"
            or study["status"] != "COMPLETE" or study["profile"]["parent_sha256"] != parent
            or study["profile"]["steps"] != 64 or tuple(models) != ARMS):
        raise ValueError("the official archive or the two admitted post-training bodies differ")
    pins = completed.source_pins()
    for path in (Path(__file__), Path(prior.__file__), Path(p106b_shards.__file__)):
        pins[path.resolve().relative_to(completed.ROOT).as_posix()] = file_sha(path)
    inputs = {}
    for name in ORDER:
        stem = f"{name}_{'answers' if name == 'final200' else 'samples'}"
        path = ARCHIVE / f"{stem}_shards_manifest.json"
        manifest = completed.read_json(path)
        if manifest != sample_manifest(report, name):
            raise ValueError(f"{name} archive manifest differs from the signed report")
        p106b_shards.verify(ARCHIVE, manifest)
        inputs[name] = dict(rows=manifest["rows"], manifest=path.name, manifest_sha256=file_sha(path))
    return dict(tag=TAG, source_models=models, sources=pins, inputs=inputs, task_order=list(ORDER),
                report_sha256=file_sha(ARCHIVE / "report.json"), study_sha256=file_sha(RULE_RESULTS),
                official_profile_sha256=file_sha(ARCHIVED_PROFILE),
                cpu_affinity=sorted(CPU_SET), torch_threads=THREADS,
                batch_size=BATCH, matched_chunk=CHUNK, generation_chunk=GENERATION_CHUNK,
                candidate_tolerance_per_token=0.0005, output_limit=final.MAX_NEW,
                claim="Full denominators only for tasks closed on all three bodies.")


def archive_rows(profile, name):
    entry = profile["inputs"][name]
    path = ARCHIVE / entry["manifest"]
    if file_sha(path) != entry["manifest_sha256"]:
        raise ValueError(f"{name} archive manifest changed")
    for spec in completed.read_json(path)["shards"]:
        with completed.regular_file(ARCHIVE / spec["path"]).open(encoding="utf-8") as source:
            yield from map(json.loads, source)


def make_adapter(model, tokenizer, checksum, checkpoint):
    runtime = dict(model=model, tokenizer=tokenizer, cfg=model.cfg, torch=torch,
                   tokenizer_sha256=completed.TOKENIZER_SHA, checkpoint_sha256=checksum,
                   checkpoint=str(checkpoint), precision="FP32_MATH")
    return official.create_adapter(runtime, runtime_root=Path(sysconfig.get_paths()["purelib"]),
                                   batch_size=BATCH)


def encode_plan(encoder, arguments):
    context, answer = arguments
    if context:
        context_ids, answer_ids = encoder._encode_pair(context, answer)
    else:
        answer_ids = encoder.tok_encode(answer, add_special_tokens=False)
        prefix = encoder.prefix_token_id
        context_ids = [prefix]
        if answer_ids and answer_ids[0] == prefix:
            answer_ids = answer_ids[1:]
    return official.plan_tokens(context_ids, answer_ids, encoder.core.vocab_size, encoder.max_length)


def score_batch(model, plans):
    batch = official.padded_batch(plans, pad_id=0, vocab_size=model.cfg.vocab_size)
    hiddens = model(torch.tensor(batch["input_ids"], dtype=torch.long), return_hidden=True)
    target_hiddens = torch.cat([hiddens[index, plan.target_start:len(plan.input_ids)]
                                for index, plan in enumerate(plans)])
    ids = torch.tensor([token for plan in plans for token in plan.continuation_ids])
    scores, greedy = [], []
    for hidden, targets in zip(target_hiddens.split(256), ids.split(256), strict=True):
        logits = model._head_logits(hidden).float()
        logps = logits.log_softmax(-1).gather(1, targets[:, None]).flatten()
        scores.append(logps)
        greedy.append(logits.argmax(-1).eq(targets))
    partitions = [len(plan.continuation_ids) for plan in plans]
    return [(float(values.sum()), bool(flags.all())) for values, flags in
            zip(torch.cat(scores).split(partitions), torch.cat(greedy).split(partitions), strict=True)]


def score_plans(model, plans, cutoff):
    order = sorted(range(len(plans)), key=lambda index: len(plans[index].input_ids))
    scored = [None] * len(plans)
    for offset in range(0, len(order), BATCH):
        guard(cutoff)
        indices = order[offset:offset+BATCH]
        values = score_batch(model, [plans[idx] for idx in indices])
        for idx, value in zip(indices, values, strict=True):
            scored[idx] = value
    return scored


def canary(profile, encoder, model, cutoff):
    examples = []
    for name in ("kobest_copa", "arc_challenge", "belebele_kor_Hang", "boolq", "hellaswag"):
        row = next(archive_rows(profile, name))
        examples.extend(row["arguments"])
    instances = [SimpleNamespace(args=args) for args in examples]
    plans = [encode_plan(encoder, args) for args in examples]
    guard(cutoff)
    started = monotonic()
    reference = encoder.loglikelihood(instances, disable_tqdm=True)
    optimized = score_plans(model, plans, cutoff)
    deltas = [abs(a[0] - b[0]) / len(plan.continuation_ids)
              for a, b, plan in zip(reference, optimized, plans, strict=True)]
    if (max(deltas) > profile["candidate_tolerance_per_token"]
            or any(a[1] != b[1] for a, b in zip(reference, optimized, strict=True))):
        raise ValueError("target-position projection differs from the pinned full projection")
    return dict(requests=len(plans), max_error_per_token=max(deltas),
                matched_greedy=len(plans), seconds=monotonic() - started)


def prepare_models(profile, checkpoint):
    return {arm: prior.load_model(arm, profile, checkpoint) for arm in ARMS}


def score_choices(models, encoder, task, name, cases, cutoff):
    plans = [encode_plan(encoder, args) for item in cases for args in item["arguments"]]
    source_tok = sum(len(plan.input_ids) for plan in plans)
    all_scores = {arm: iter(score_plans(model, plans, cutoff)) for arm, model in models.items()}
    results = []
    core6 = name in completed.core6.TASK_COUNTS
    for item in cases:
        size = len(item["arguments"])
        entries = {arm: [next(scores) for _ in range(size)] for arm, scores in all_scores.items()}
        if core6:
            doc = item["doc"]
            gold = task.doc_to_text(doc) if task.multiple_input else task.doc_to_target(doc)
            choices = task.doc_to_choice(doc)
            historical = [response[0] for response in item["filtered_resps"]]
            oracle = completed.core6.independent_row(choices, gold, historical)
            if any(oracle[key] != item[key] for key in ("acc", "acc_norm") if key in item):
                raise ValueError(f"the archived task scoring differs: {name} {item['doc_id']}")
            recorded = max(range(size), key=historical.__getitem__)
            scored = {arm: completed.core6.independent_row(choices, gold, [s[0] for s in scores])
                      for arm, scores in entries.items()}
        else:
            gold = item["gold"]
            recorded = item["pred"]
            scored = {}
            for arm, scores in entries.items():
                pred, norm, _ = choice.item_score(task, item, scores)
                scored[arm] = dict(pred=pred, pred_norm=norm, acc=int(pred == gold), acc_norm=int(norm == gold))
        results.append(dict(id=item["doc_id"], gold=gold, archived_pred=recorded,
                            scores=entries, predictions=scored))
    return results, source_tok


def score_generation(models, tokenizer, cases, original, cutoff):
    results = []
    for case in cases:
        guard(cutoff)
        prompt = serialize({"messages": dialogue.prompt_messages(case["prompt"])}, "chatml",
                           add_generation_prompt=True)
        ids = tokenizer.encode(prompt).ids
        if len(ids) + final.MAX_NEW > 1024 or case["id"] not in original:
            raise ValueError("the frozen FINAL200 request differs")
        generations = {}
        for arm, model in models.items():
            guard(cutoff)
            capture = first.DecodeSuffix(tokenizer, ids)
            _, metadata = sample(model, model.cfg, capture, prompt, max_new=final.MAX_NEW,
                                 temperature=0., top_k=1, device="cpu", eos_id=2,
                                 use_cache=True, logits_last_only=True, return_metadata=True,
                                 stop_token_sequences=[[4]])
            answer, metadata = dialogue.answer_from_tokens(tokenizer, ids, ids + capture.ids, metadata,
                                                           final.MAX_NEW)
            generations[arm] = dict(answer=answer, metadata=metadata,
                                    reference_match=final.reference_match(answer, case),
                                    repeat_tail=first.repeat_tail(metadata["generated_ids"]))
        results.append(dict(id=case["id"], language=case["language"], category=case["category"],
                            match_rule=case["match_rule"], reference=case["reference"], generations=generations,
                            baseline_archived_ids_equal=generations["baseline"]["metadata"]["generated_ids"]
                            == original[case["id"]]["metadata"]["generated_ids"]))
    return results, sum(len(row["generations"]["baseline"]["metadata"]["generated_ids"]) for row in results)


def paired(new, old):
    return dict(wins=sum(bool(n) and not o for n, o in zip(new, old, strict=True)),
                losses=sum(bool(o) and not n for n, o in zip(new, old, strict=True)))


def choice_summary(rows, is_core6):
    stats = {}
    base = [row["predictions"]["baseline"]["acc"] for row in rows]
    for arm in ARMS:
        preds = [row["predictions"][arm] for row in rows]
        matrix = Counter((row["gold"], pred["pred"]) for row, pred in zip(rows, preds, strict=True))
        classes = sorted({label for cell in matrix for label in cell})
        f1 = [2 * matrix[c, c] / sum(n * ((a == c) + (b == c)) for (a, b), n in matrix.items())
              for c in classes]
        result = dict(correct=sum(pred["acc"] for pred in preds),
                      correct_norm=sum(pred["acc_norm"] for pred in preds),
                      archived_argmax_equal=sum(pred["pred"] == row["archived_pred"]
                                                for row, pred in zip(rows, preds, strict=True)),
                      **paired([pred["acc"] for pred in preds], base))
        if not is_core6:
            result["macro_f1"] = fsum(f1) / len(classes)
            result["classes"] = classes
            result["confusion"] = [[matrix[a,b] for b in classes] for a in classes]
        stats[arm] = result
    return stats


def generation_summary(rows):
    report = {}
    groups = sorted({(row["language"], row["category"]) for row in rows})
    for arm in ARMS:
        report[arm] = {}
        for lang, category in groups:
            values = [row["generations"][arm] for row in rows if (row["language"], row["category"]) == (lang, category)]
            reference = [value["reference_match"] for value in values if value["reference_match"] is not None]
            report[arm][f"{lang}/{category}"] = dict(rows=len(values), reference_rows=len(reference),
                reference_correct=sum(reference), empty=sum(not value["answer"].strip() for value in values),
                capped=sum(value["metadata"]["finish_reason"] == "MAX_NEW" for value in values),
                repeats=sum(value["repeat_tail"] for value in values))
    return dict(arms=report, baseline_archived_ids_equal=sum(row["baseline_archived_ids_equal"] for row in rows),
                semantic_review="UNSCORED_IN_AUTOMATIC_SUMMARY")


def evaluate_task(profile, stamp, name, assets, models, encoder, tokenizer, cutoff):
    root = OUT / name
    root.mkdir(exist_ok=True)
    if name == "final200":
        cases = assets[name]
        old = {row["id"]: row for row in archive_rows(profile, name)}
        if len(old) != len(cases):
            raise ValueError("the FINAL200 source denominator differs")
        score = lambda items: score_generation(models, tokenizer, items, old, cutoff)
        size, summarize = GENERATION_CHUNK, generation_summary
        expected_ids = [item["id"] for item in cases]
    else:
        cases = list(archive_rows(profile, name))
        core6 = name in completed.core6.TASK_COUNTS
        task = assets["core6"][name] if core6 else assets["korean_choices"][0][name]
        score = lambda items: score_choices(models, encoder, task, name, items, cutoff)
        size, summarize = CHUNK, lambda rows: choice_summary(rows, core6)
        expected_ids = list(range(profile["inputs"][name]["rows"]))
        if [item["doc_id"] for item in cases] != expected_ids:
            raise ValueError(f"the ordered official ids differ for {name}")
    if len(cases) != profile["inputs"][name]["rows"]:
        raise ValueError(f"the frozen denominator differs for {name}")
    results, costs, receipts = [], [], {}
    for offset in range(0, len(cases), size):
        guard(cutoff)
        receipt = root / f"{offset:06}.json"
        end = min(offset + size, len(cases))
        if receipt.exists():
            entry = completed.read_json(completed.regular_file(receipt))
        else:
            started = monotonic()
            rows, tokens = score(cases[offset:end])
            bytes_hash = sha256(official.canonical(rows)).hexdigest()
            entry = dict(task=name, profile_sha256=stamp, offset=offset, rows=rows, rows_sha256=bytes_hash,
                         seconds=monotonic()-started, tokens=tokens)
            prior.prior.reference.native.publish(receipt, entry)
            print(f"{name} {end}/{len(cases)} {entry['seconds']:.2f}s", flush=True)
        rows = entry["rows"]
        if (entry["task"] != name or entry["profile_sha256"] != stamp or entry["offset"] != offset
                or [row["id"] for row in rows] != expected_ids[offset:end]
                or sha256(official.canonical(rows)).hexdigest() != entry["rows_sha256"]):
            raise ValueError(f"the immutable chunk differs: {receipt}")
        results += rows
        costs.append(entry["seconds"])
        receipts[receipt.name] = file_sha(receipt)
    summary = dict(task=name, rows=len(results), profile_sha256=stamp,
                   sources=receipts, results=summarize(results), seconds=fsum(costs))
    path = root / "summary.json"
    if path.exists():
        if completed.read_json(path) != summary:
            raise ValueError(f"the completed task summary differs: {name}")
    else:
        prior.prior.reference.native.publish(path, summary)
    return {key: summary[key] for key in ("task", "rows", "results", "seconds")} | {"sha256": file_sha(path)}


@torch.inference_mode()
def evaluate(profile, stamp, cutoff):
    torch.set_num_threads(THREADS)
    torch.set_num_interop_threads(1)
    torch.manual_seed(1337)
    assets, proofs = completed.load_inputs(("core6", "korean_choices", "final200"))
    expected = completed.read_json(ARCHIVED_PROFILE)["inputs"]
    if any(json.loads(json.dumps(proof)) != expected[name] for name, proof in proofs.items()):
        raise ValueError("the pinned offline task requests do not match the archived evaluation")
    tokenizer = completed.load_tokenizer()
    checkpoint = prior.prior.reference.checkpoint()
    models = prepare_models(profile, checkpoint)
    encoder = make_adapter(models["baseline"], tokenizer, profile["source_models"]["baseline"], checkpoint)
    try:
        with sdpa_kernel(SDPBackend.MATH):
            binding = canary(profile, encoder, models["baseline"], cutoff)
            print(f"CPU likelihood projection canary {binding}", flush=True)
            return binding, {name: evaluate_task(profile, stamp, name, assets, models, encoder, tokenizer, cutoff)
                             for name in ORDER}
    finally:
        encoder.close()


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("seal", "run"))
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    guard(args.stop_by)
    profile = make_profile()
    if args.mode == "seal":
        if PROFILE.exists():
            parser.error("the fixed profile already exists")
        prior.prior.reference.native.publish(PROFILE, profile)
        print(file_sha(PROFILE), flush=True)
        return
    stamp = file_sha(PROFILE)
    if args.profile_sha256 != stamp or completed.read_json(PROFILE) != profile:
        parser.error("sealed evidence or source changed")
    OUT.mkdir(exist_ok=True)
    with (OUT / ".lock").open("a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result_path = OUT / "report.json"
        if result_path.exists():
            parser.error("the sealed suite already closed")
        binding, tasks = evaluate(profile, stamp, args.stop_by)
        prior.prior.reference.native.publish(result_path, dict(profile_sha256=stamp, canary=binding, tasks=tasks))


if __name__ == "__main__":
    main()
