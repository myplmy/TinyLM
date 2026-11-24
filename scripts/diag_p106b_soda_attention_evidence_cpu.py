"""Train a SODA query adaptation with and without explicit quoted-speaker evidence."""

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
import json
import math
import os
from pathlib import Path
import time
from unittest.mock import patch

import numpy as np
import torch
import torch.nn.functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import audit_p106b_soda_quote_release as release
from scripts import diag_p106b_soda_paired_speaker_adapter as prior_adapter
from scripts import eval_p109b_first_use as first_use
from scripts import eval_p109c_mixed_v2 as evaluation
from tinylm.infer.generate import sample


source, quote = release.source, release.quote
original, native = evaluation.original, evaluation.native
QUOTAS = {"train": 32, "valid": 8}
MAX_CONTEXT, BATCH, SEED = 384, 4, 27491
ATTENTION_LAYER, WEIGHT = 14, .20
OLD_EVAL = original.ROOT / "test_result/evidence/p106b_soda_heldout_speaker_codes_cpu_v1_20261123/report.json"


@dataclass(frozen=True)
class Example:
    source: str
    gap: int
    target: int
    swap: bool
    history: str
    prompt: str
    prefix: tuple
    labels: tuple
    positions: tuple


def item_examples(tokenizer, group, turns, pair, gap, mode):
    names = tuple(turns[index][0] for index in pair)
    for swap in (False, True):
        aliases = ("B", "A") if swap else ("A", "B")
        context, offsets = "Dialogue:\n", []
        for name, text in turns:
            offsets.append(len("<|im_start|>user\n") + len(context))
            context += f"{aliases[names.index(name)]}: {text}\n"
        questions = [f'Who said “{turns[index][1]}”? Give only the speaker letter.' for index in pair]
        for target, question in enumerate(questions):
            histories = ("single", "repeat", "switch") if mode == "valid" else (
                ("repeat", "switch", "single")[(int(group[:4], 16) + int(swap) + target) % 3],)
            for history in histories:
                if history == "single":
                    prompt = first_use.dialog(context + "\n" + question)
                else:
                    other = target if history == "repeat" else 1 - target
                    prompt = (first_use.dialog(context + "\n" + questions[other]) + aliases[other] +
                              "<|im_end|>\n" + first_use.dialog(question))
                prefix = tokenizer.encode(prompt)
                encoded = tokenizer.encode(prompt + aliases[target] + "<|im_end|>")
                labels = tuple(encoded.ids[len(prefix.ids):])
                if (len(encoded.ids) > MAX_CONTEXT or encoded.ids[:len(prefix.ids)] != prefix.ids
                        or len(labels) != 2 or labels[-1] != 4
                        or tokenizer.decode([labels[0]]) != aliases[target]):
                    return
                positions = []
                for turn in pair:
                    left = offsets[turn]
                    starts = [index for index, (begin, end) in enumerate(prefix.offsets) if begin <= left < end]
                    if len(starts) != 1 or aliases[names.index(turns[turn][0])] not in tokenizer.decode(
                            [prefix.ids[starts[0]]], skip_special_tokens=False):
                        return
                    positions.append(starts[0])
                if positions[0] == positions[1] or max(positions) >= len(prefix.ids) - 1:
                    return
                yield Example(group, gap, target, swap, history, prompt, tuple(prefix.ids), labels, tuple(positions))


def choose_rows(directory, split, tokenizer, check, reserved, blocked_roots=(), blocked_texts=()):
    by_gap = defaultdict(list)
    roots, texts = set(), set()
    expected = 4 if split == "train" else 12
    count, checksum = source.RELEASE[split]
    with source.pinned_rows(directory / f"{split}.parquet", count, checksum) as rows:
        for index, row in enumerate(rows):
            if index % 2048 == 0:
                check()
            root = row["original_index"]
            if row["split"] != split:
                raise ValueError("the local source declares the wrong official split")
            group = source.hash_json([source.REPO, source.REVISION, root])
            ticket = int(source.hash_json([group, SEED, split])[:12], 16)
            if ticket % 41 or group in reserved or root in blocked_roots or root in roots:
                continue
            turns = release.turns(row)
            if not turns or len({name for name, _ in turns}) != 2 or any("<|" in text for _, text in turns):
                continue
            digest = release.spoken_key(turns)
            if digest in blocked_texts or digest in texts:
                continue
            occurrences = Counter(quote.quote_key(text) for _, text in turns)
            pairs = []
            for i, j in combinations(range(len(turns)), 2):
                a, u = turns[i]
                b, v = turns[j]
                gap = min(j - i, 3)
                if (len(by_gap[gap]) < QUOTAS[split] and a.casefold() != b.casefold()
                        and occurrences[quote.quote_key(u)] == occurrences[quote.quote_key(v)] == 1
                        and quote.questions(f"{a}: {u}\n\n{b}: {v}")):
                    pairs.append((gap, i, j))
            pairs.sort(key=lambda row: (len(by_gap[row[0]]), (ticket + row[1] * 47 + row[2]) % 127))
            for gap, i, j in pairs:
                tests = tuple(item_examples(tokenizer, group, turns, (i, j), gap, split))
                if len(tests) == expected:
                    by_gap[gap].append(tests)
                    roots.add(root)
                    texts.add(digest)
                    break
            if all(len(by_gap[gap]) == QUOTAS[split] for gap in (1, 2, 3)):
                return [row for gap in sorted(by_gap) for group in by_gap[gap] for row in group], roots, texts
    raise ValueError(f"the local {split} source did not fill the fixed distance cohorts")


def prepare(directory, tokenizer, check):
    old_map, _ = quote.read(quote.SOURCE_MAP)
    reserved = {source.hash_json([source.REPO, source.REVISION, row["original_index"]])
                for row in old_map["rows"] if "original_index" in row}
    previous = json.loads(OLD_EVAL.read_text())
    reserved.update(row["root"] for row in previous["rows"])
    held_roots, held_texts, _ = release.released_groups(directory, check)
    train, train_roots, train_texts = choose_rows(directory, "train", tokenizer, check, reserved, held_roots, held_texts)
    valid, valid_roots, valid_texts = choose_rows(directory, "valid", tokenizer, check, reserved, train_roots, train_texts)
    if train_roots & valid_roots or train_texts & valid_texts:
        raise ValueError("the exact root or utterance sequence crossed the official split")
    return train, valid


def selected_rope(values, cos, sin):
    first, second = values.chunk(2, dim=-1)
    return torch.cat((first*cos-second*sin, first*sin+second*cos), dim=-1)


def evidence(attention, model, q, k, anchors, positions):
    cfg = model.cfg
    rows = torch.arange(len(anchors))
    query = attention.q_norm(q[rows, anchors].reshape(len(rows), cfg.n_q_heads, cfg.head_dim))
    query = selected_rope(query, model.rope_cos[anchors, None], model.rope_sin[anchors, None])
    if attention.qk_gain_logit is not None:
        gain = .5 + 3.5 * attention.qk_gain_logit.sigmoid()
        query = query * gain[None, :, None]
    keys = attention.k_norm(k[rows[:, None], positions].reshape(len(rows), 2, cfg.n_kv_heads, cfg.head_dim))
    keys = selected_rope(keys, model.rope_cos[positions, None], model.rope_sin[positions, None])
    keys = keys.repeat_interleave(cfg.n_q_heads // cfg.n_kv_heads, dim=2)
    return (query[:, None] * keys).sum(dim=-1).mean(dim=-1) / math.sqrt(cfg.head_dim)


def fit(model, attention, training, batches, check, weight):
    torch.manual_seed(SEED)
    adapter = prior_adapter.Residual(model.cfg.dim)
    optimizer = torch.optim.AdamW(adapter.parameters(), lr=.002, weight_decay=.01)
    capture = {}

    def adapt(_module, args, output):
        updated = output + adapter.up(adapter.down(args[0]))
        capture["query"] = updated
        return updated

    def retain(_module, _args, output):
        capture["key"] = output

    stats = []
    with (attention.q_proj.register_forward_hook(adapt), attention.k_proj.register_forward_hook(retain)):
        for step, indices in enumerate(batches, 1):
            check()
            items = [training[i] for i in indices]
            longest = max(len(item.prefix) + 1 for item in items)
            x = torch.zeros((len(items), longest), dtype=torch.long)
            anchors = torch.tensor([len(item.prefix) - 1 for item in items])
            rows = torch.arange(len(items))
            for row, item in zip(x, items, strict=True):
                values = torch.tensor([*item.prefix, item.labels[0]])
                row[:len(values)] = values
            target = torch.tensor([item.labels for item in items])
            positions = torch.tensor([item.positions for item in items])
            expected = torch.tensor([item.target for item in items])
            optimizer.zero_grad(set_to_none=True)
            hidden = model(x, return_hidden=True)
            wanted = model._head_logits(hidden[rows[:, None], anchors[:, None] + torch.arange(2)])
            ce = F.cross_entropy(wanted.flatten(0, 1), target.flatten())
            links = evidence(attention, model, capture.pop("query"), capture.pop("key"), anchors, positions)
            link = F.cross_entropy(links, expected)
            objective = ce + weight * link
            if not objective.isfinite():
                raise ValueError("the exact same answer and evidence objectives must stay finite")
            objective.backward()
            norm = torch.nn.utils.clip_grad_norm_(adapter.parameters(), 1., error_if_nonfinite=True)
            optimizer.step()
            stats.append(dict(ce=float(ce.detach()), evidence_ce=float(link.detach()), gradient=float(norm)))
            if step == 1 or step % 16 == 0:
                print("SODA_EVIDENCE_TRAIN", weight, step, stats[-1], flush=True)
    return adapter.eval(), stats


def generate(model, tokenizer, item):
    captured = first_use.DecodeSuffix(tokenizer, list(item.prefix))
    text, meta = sample(model, model.cfg, captured, item.prompt, max_new=6, temperature=0., top_k=0,
                        device="cpu", eos_id=2, stop_token_sequences=[[4]], logits_last_only=True,
                        return_metadata=True)
    expected = tokenizer.decode([item.labels[0]])
    correct = first_use.strict(text) == first_use.strict(expected)
    ended = meta["finish_reason"] in ("EOS", "STOP_SEQUENCE")
    return dict(source=item.source, gap=item.gap, target=item.target, swap=item.swap, history=item.history,
                prompt_sha256=source.hash_json(item.prefix), expected=expected, answer=text,
                ids=captured.ids, finish=meta["finish_reason"], exact_and_end=correct and ended)


def score(model, attention, adapter, tokenizer, valid, check):
    def adapt(_module, args, output):
        return output if adapter is None else output + adapter.up(adapter.down(args[0]))

    per_case = []
    with torch.inference_mode(), attention.q_proj.register_forward_hook(adapt):
        for i, item in enumerate(valid, 1):
            check()
            per_case.append(generate(model, tokenizer, item))
            if i % 48 == 0:
                print("SODA_EVIDENCE_EVAL", i, len(valid), flush=True)
    totals = {}
    for history in ("single", "repeat", "switch"):
        groups = defaultdict(list)
        for row in per_case:
            if row["history"] == history:
                groups[row["source"]].append(row["exact_and_end"])
        if set(map(len, groups.values())) != {4}:
            raise ValueError("a heldout original lost a quotation or code permutation")
        totals[history] = dict(rows=sum(map(len, groups.values())),
                               correct=sum(sum(values) for values in groups.values()),
                               all_four=sum(all(values) for values in groups.values()), roots=len(groups))
    return dict(totals=totals, provided_results=per_case)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("original-dir", "training", "record"):
        parser.add_argument("--" + key, required=True, type=Path)
    parser.add_argument("--training-manifest-sha256", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    pin = original.core6.digest(Path(__file__))
    if (os.environ.get("CUDA_VISIBLE_DEVICES") != "" or args.stop_by.tzinfo is None
            or args.record.exists() or pin != native.digest(args.source_sha256)):
        parser.error("require a sealed CPU-only run, new destination and authorized cutoff")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)

    def check():
        if time.time() >= args.stop_by.timestamp():
            raise TimeoutError("the authorized SODA evidence window ended")

    check()
    tokenizer = original.load_tokenizer()
    train, valid = prepare(args.original_dir, tokenizer, check)
    print("SODA_EVIDENCE_PREPARED", len(train), len(valid), flush=True)
    order = np.random.default_rng(SEED).permutation(len(train)).reshape(-1, BATCH)
    end = original.read_json(args.training / "input.json")["steps"]
    with patch.object(native, "STEPS", end):
        checkpoint, model_sha = evaluation.completed_v2(args.training.absolute(), args.training_manifest_sha256)
    with torch.no_grad():
        model = original.load_model(checkpoint, end, "cpu").requires_grad_(False)
    if any(module._wq is not None and module._wq.requires_grad for module in model._tlinear_cache):
        raise ValueError("the frozen base must expose detached ternary weight caches")
    attention = model.layers[ATTENTION_LAYER].attn_mod
    if not attention.owns_kv or model.visit_schedule().count(ATTENTION_LAYER) != 1:
        raise ValueError("the actual attention owner or causal visit count changed")
    args.record.mkdir(exist_ok=False)
    title = ("baseline", "next_token", "next_token_with_evidence")
    outcomes = {}
    with sdpa_kernel(SDPBackend.MATH):
        adapters = (None, *[fit(model, attention, train, order, check, w) for w in (0., WEIGHT)])
        for name, arm in zip(title, adapters, strict=True):
            adapter, updates = arm if arm is not None else (None, [])
            report = score(model, attention, adapter, tokenizer, valid, check)
            outcomes[name] = report["totals"]
            native.publish(args.record / f"{name}.json", dict(report, updates=updates))
    if original.core6.digest(checkpoint) != model_sha or original.core6.digest(Path(__file__)) != pin:
        raise ValueError("the original sealed checkpoint or source changed")
    native.publish(args.record / "report.json", dict(status="SODA_ATTENTION_EVIDENCE_CONTRAST_COMPLETE",
        source_sha256=pin, source_release=source.REVISION, model_sha256=model_sha,
        training_sha256=source.hash_json([(row.source, row.prefix, row.labels, row.positions) for row in train]),
        evaluation_sha256=source.hash_json([(row.source, row.prefix, row.labels, row.positions) for row in valid]),
        picked_updates_sha256=source.hash_json(order.tolist()), training_rows=len(train), validation_rows=len(valid),
        training_roots=len({row.source for row in train}), validation_roots=len({row.source for row in valid}),
        training_histories=dict(Counter(row.history for row in train)), attention_layer=ATTENTION_LAYER,
        evidence_weight=WEIGHT, same_next_token_supervision=True, optimizer_updates_per_arm=len(order),
        teacher_calls=0, model_writes=0, results=outcomes))
    print(outcomes, flush=True)


if __name__ == "__main__":
    main()
