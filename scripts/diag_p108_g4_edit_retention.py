"""Measure edit dose and retention during matched language updates of real G4."""

import argparse
from datetime import datetime, timedelta
import json
import os
from statistics import mean
import subprocess
import sys
from time import perf_counter

from tokenizers import Tokenizer
import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109_frozen_g4_routes as frozen
from scripts.diag_p102a_g4_full_delta_train import state_sha
from scripts.diag_p102a_g4_recompute_shapes import idle
from scripts.p107_active_optimizer_groups import keep_active_groups
from scripts.p108_shared_ternary_edit import physical_down_owners
from tinylm.model.ternary import ternary
from tinylm.model.transformer import TiedMLPTransformer
from tinylm.train.anneal_schedule import lr_factor
from tinylm.train.experimental_optimizers import build_experimental_optimizers


ROOT, PARENT, CUTOFF = frozen.ROOT, frozen.prior.PARENT, frozen.prior.CUTOFF
write, sha = frozen.prior.io.write, frozen.prior.io.digest
TAG = "p108_g4_edit_retention_v1_20261119"
OUT = ROOT / "test_result/evidence" / TAG
UPDATES, BATCH, WIDTH, SEED, LR = 128, 4, 128, 1337, 3e-5
ARMS = {"base": 0, "small": 64, "large": 1024}
CHECKPOINTS = (0, 1, 8, 32, 64, UPDATES)
CAPS = {"select": 90, **dict.fromkeys(ARMS, 320)}
ALLOCATOR = "expandable_segments:False"
SOURCES = (*frozen.prior.SOURCES, "scripts/diag_p109_frozen_g4_routes.py",
           "scripts/p108_shared_ternary_edit.py", "scripts/p107_active_optimizer_groups.py",
           "scripts/diag_p102a_g4_full_delta_train.py", "tinylm/train/experimental_optimizers.py",
           "tinylm/train/muon.py", "tinylm/train/anneal_schedule.py",
           "scripts/diag_p108_g4_edit_retention.py")

FACTS = (
    ("Mirevek", ("bell", "flute"), ("종", "피리"), 0),
    ("Fenroth", ("harbor", "summit"), ("항구", "정상"), 1),
    ("Delvian", ("amber", "silver"), ("호박색", "은색"), 0),
    ("Roveki", ("willow", "cedar"), ("버드나무", "삼나무"), 1),
    ("Talsuni", ("canvas", "felt"), ("캔버스", "펠트"), 1),
    ("Corveth", ("compass", "ruler"), ("나침반", "자"), 0),
)


def read(path):
    return json.loads(path.read_bytes())


def background():
    places = (("attic", "다락으로"), ("tunnel", "터널로"), ("kitchen", "부엌으로"), ("yard", "마당으로"))
    objects = (("wooden case", "나무 상자"), ("glass jar", "유리병"), ("linen bag", "천 가방"))
    for index in range(2048):
        place, place_ko = places[index % len(places)]
        obj, obj_ko = objects[(index // len(places)) % len(objects)]
        hour, copies = 8 + index % 9, 2 + index % 7
        yield (f"Dispatch card {index:04d} records a {obj} moved to the {place}. "
               f"The afternoon register lists {copies} copies and a delivery time of {hour:02d}:20. "
               "The clerk compared the two entries and stamped the receipt before closing the book.")
        yield (f"작업일지 {index:04d}번에는 {obj_ko} 하나를 {place_ko} 옮겼다고 적혀 있다. "
               f"접수 시각은 {hour:02d}시 20분이며 보고서 사본은 {copies}부다. "
               "담당자는 두 기록을 대조하고 영수증에 도장을 찍은 뒤 일지를 덮었다.")


def questions():
    records = []
    for role in ("fit", "held_en", "held_ko"):
        for name, en, ko, correct in FACTS:
            for swapped in (0, 1):
                choices = ko if role == "held_ko" else en
                a, b = choices[swapped], choices[1 - swapped]
                if role == "fit":
                    text = f"Which item is assigned to record {name}?\nA. {a}\nB. {b}\nAnswer:"
                elif role == "held_en":
                    text = f"Look up the code {name} in the inventory. What entry belongs with it?\n(A) {a}\n(B) {b}\nChoice:"
                else:
                    text = f"목록에서 {name} 항목에 적힌 것은 무엇인가?\n(A) {a}\n(B) {b}\n정답:"
                records.append(dict(role=role, fact=name, prompt=text, choices=[a, b], correct=correct ^ swapped))
    return records


def prepare_data():
    tokenizer = Tokenizer.from_file(str(frozen.TOKENIZER))
    assert tokenizer.get_vocab_size() == 32768
    texts = list(background())
    assert all(name.casefold() not in text.casefold() for name, *_ in FACTS for text in texts)
    encoded = tokenizer.encode_batch(texts, add_special_tokens=False)
    eos = tokenizer.token_to_id("<eos>")
    assert eos == 2
    pool = torch.tensor([token for row in encoded for token in (*row.ids, eos)], dtype=torch.long)
    assert pool.numel() >= 2 * UPDATES * BATCH * WIDTH
    rng = torch.Generator().manual_seed(SEED)
    starts = torch.randint(0, len(pool) - WIDTH, (UPDATES, BATCH), generator=rng)
    stream = pool[starts[..., None] + torch.arange(WIDTH + 1)]
    records = questions()
    option_ids = [tokenizer.encode(value, add_special_tokens=False).ids for value in (" A", " B")]
    assert all(len(value) == 1 for value in option_ids) and option_ids[0] != option_ids[1]
    option_ids = [value[0] for value in option_ids]
    tokenized = tokenizer.encode_batch([r["prompt"] for r in records], add_special_tokens=False)
    for record, row in zip(records, tokenized, strict=True):
        for suffix, token in zip((" A", " B"), option_ids, strict=True):
            assert tokenizer.encode(record["prompt"] + suffix, add_special_tokens=False).ids == [*row.ids, token]
        record["ids"] = row.ids
    assert all(0 < len(r["ids"]) <= WIDTH for r in records)
    pad = tokenizer.token_to_id("<pad>")
    inputs = torch.nn.utils.rnn.pad_sequence([torch.tensor(r["ids"]) for r in records], batch_first=True,
                                              padding_value=pad)
    positions = torch.tensor([len(r["ids"]) - 1 for r in records])
    correct = torch.tensor([r["correct"] for r in records])
    options = torch.tensor(option_ids)
    assert sha(PARENT) == frozen.PARENT_SHA and sha(frozen.TOKENIZER) == frozen.TOKENIZER_SHA
    conditions = dict(tag=TAG, parent_sha256=frozen.PARENT_SHA, tokenizer_sha256=frozen.TOKENIZER_SHA,
                      source_pins={name: sha(ROOT / name) for name in SOURCES}, data="AUTHORED_IN_SCRIPT",
                      allocation=ALLOCATOR, seed=SEED, pool_tokens=pool.numel(), texts=len(texts),
                      pool_sha256=state_sha(pool), train_stream_sha256=state_sha(stream), questions=records,
                      options=option_ids, shape=[UPDATES, BATCH, WIDTH], accum=1, lr=LR,
                      arms=ARMS, cut_KST=CUTOFF.isoformat(), approval="WIP176", checkpoint_writes=0)
    return conditions, stream, (inputs, positions, correct, options)


def load_model():
    if torch.cuda.device_count() != 1 or torch.cuda.mem_get_info()[0] < 12 * (1 << 30):
        raise RuntimeError("single CUDA device with 12 GiB free required")
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.manual_seed(SEED)
    cfg, state, step = frozen.prior.load_parent(torch)
    cfg.train_repeat = 2.0
    assert step == 2289 and cfg.micro_group == 128 and not cfg.sparse34
    model = TiedMLPTransformer(cfg)
    model.load_state_dict(state, strict=True)
    model.set_anneal(1.0)
    model.cuda().eval()
    owner = physical_down_owners(model)[2]
    assert len(model.visit_schedule()) == 28 and owner.layers == (2, 3, 4, 5) and len(owner.visits) == 8
    return model, owner.module


def choice_logits(model, panel):
    inputs, last, _, options = panel
    hidden = model(inputs, return_hidden=True)
    selected = hidden[torch.arange(len(last), device=last.device), last]
    return model._head_logits(selected[:, None, :]).squeeze(1).index_select(1, options).float()


def select(model, down, panel):
    inputs, last, labels, choices = panel
    fit_count = 2 * len(FACTS)
    with torch.autocast("cuda", dtype=torch.bfloat16):
        values = choice_logits(model, (inputs[:fit_count], last[:fit_count], labels[:fit_count], choices))
        loss = F.cross_entropy(values, labels[:fit_count])
    effective = down._wq
    grad = torch.autograd.grad(loss, effective)[0].detach()
    benefit = (2 * grad * effective.detach()).flatten()
    positive = torch.isfinite(benefit) & (benefit > 0)
    ranked = torch.argsort(benefit.masked_fill(~positive, -torch.inf), descending=True, stable=True)
    indices = ranked[:max(ARMS.values())]
    assert bool(positive[indices].all())
    trits = effective.detach().flatten()[indices].sign().to(torch.int8)
    write(OUT / "selection.json", dict(indices=indices.tolist(), original_signs=trits.tolist(),
          fit_loss=float(loss.detach()), score_sha256=state_sha(benefit),
          predicted_gain={arm: float(benefit[indices[:count]].sum()) for arm, count in ARMS.items()}))
    print("P108_G4_EDIT_SELECTED", len(indices), float(loss.detach()), flush=True)


@torch.no_grad()
def install(model, down, indices, dose):
    original = ternary(down.weight, model.cfg).flatten()
    master = down.weight.flatten()
    if dose:
        edited = indices[:dose]
        raw = master[edited].clone()
        master.index_copy_(0, edited, -raw)
    master_delta = 2 * master[indices[:dose]].norm()
    expected = original.clone()
    expected[indices[:dose]] = -expected[indices[:dose]]
    actual = ternary(down.weight, model.cfg).flatten()
    assert torch.equal(actual, expected)
    return dict(trits_changed=int(original.ne(actual).sum()), master_l2=float(master_delta),
                effective_l2=float((actual - original).norm()))


@torch.no_grad()
def evaluate(model, panel):
    model.eval()
    with torch.autocast("cuda", dtype=torch.bfloat16):
        pairs = choice_logits(model, panel)
    assert bool(torch.isfinite(pairs).all())
    labels = panel[2]
    margins = pairs.gather(1, labels[:, None]) - pairs.gather(1, (1-labels)[:, None])
    return dict(logits=pairs.tolist(), margins=margins.flatten().tolist(),
                choices=pairs.argmax(dim=1).tolist(), correct=pairs.argmax(dim=1).eq(labels).tolist())


@torch.no_grad()
def read_edit(model, down, indices):
    current = down.weight.detach().flatten()[indices]
    trits = ternary(down.weight.detach(), model.cfg).flatten()[indices].sign().to(torch.int8)
    group = model.cfg.micro_group
    threshold = down.weight.detach().reshape(-1, group)[indices // group].abs().mean(dim=1) * model.cfg.twn_thr_ratio
    return current, trits, current.abs() - threshold


def train(arm, model, down, panel, stream):
    selection = read(OUT / "selection.json")
    dose = ARMS[arm]
    indices = torch.tensor(selection["indices"], device="cuda")
    original = torch.tensor(selection["original_signs"], dtype=torch.int8, device="cuda")
    assert torch.equal(read_edit(model, down, indices)[1], original)
    installed = install(model, down, indices, dose)
    assert installed["trits_changed"] == dose
    watch = indices[:dose] if dose else indices
    requested = -original[:len(watch)]
    current, trits, margin = read_edit(model, down, watch)
    match = trits.eq(requested)
    tracking = [dict(step=0, matches=int(match.sum()), uninterrupted=int(match.sum()),
                     zero=int(trits.eq(0).sum()), min_margin=float(margin.min()), path_l2=0.)]
    path_l2 = 0.
    receipt = {0: evaluate(model, panel)}
    route = build_experimental_optimizers(model, "muon_matched", lr=LR, matrix_lr_mult=1.)
    optimizers = (route.matrix, route.adamw)
    keep_active_groups(optimizers)
    rates = [[group["lr"] for group in opt.param_groups] for opt in optimizers]
    start = perf_counter()
    torch.cuda.reset_peak_memory_stats()
    for step, tokens in enumerate(stream, 1):
        if (OUT / "STOP").exists() or datetime.now(CUTOFF.tzinfo) >= CUTOFF:
            raise RuntimeError("stop or deadline reached")
        model.train()
        factor = lr_factor(step - 1, 4, UPDATES, "cosine")
        for optimizer, original_rates in zip(optimizers, rates, strict=True):
            for group, rate in zip(optimizer.param_groups, original_rates, strict=True):
                group["lr"] = rate * factor
        with torch.autocast("cuda", dtype=torch.bfloat16):
            logits = model(tokens[:, :-1])
            loss = F.cross_entropy(logits.flatten(0, 1), tokens[:, 1:].reshape(-1))
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
        for optimizer in optimizers:
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
        del logits
        model.clear_quant()
        next_value, signs, edge = read_edit(model, down, watch)
        path_l2 += float((next_value - current).norm())
        current = next_value
        match &= signs.eq(requested)
        tracking.append(dict(step=step, matches=int(signs.eq(requested).sum()), uninterrupted=int(match.sum()),
                             zero=int(signs.eq(0).sum()), min_margin=float(edge.min()), path_l2=path_l2,
                             ce=float(loss.detach()), norm=float(norm)))
        if step in CHECKPOINTS:
            receipt[step] = evaluate(model, panel)
            print("P108_G4_EDIT_STEP", arm, step, tracking[-1]["matches"], tracking[-1]["ce"], flush=True)
    write(OUT / f"{arm}.json", dict(arm=arm, installed=installed, tracking=tracking, answers=receipt,
          peak_allocated=torch.cuda.max_memory_allocated(), peak_reserved=torch.cuda.max_memory_reserved(),
          duration_s=perf_counter()-start, targets=UPDATES*BATCH*WIDTH, checkpoint_writes=0))


def summarize(arms, questions):
    roles = ("fit", "held_en", "held_ko")
    summary = {}
    for name, item in arms.items():
        output = {}
        for role in roles:
            indices = [i for i, q in enumerate(questions) if q["role"] == role]
            stamps = {}
            for time, answer in item["answers"].items():
                control = arms["base"]["answers"][time]
                margins = [answer["margins"][i] for i in indices]
                stamps[time] = dict(margin=mean(margins), accuracy=sum(answer["correct"][i] for i in indices),
                    vs_base=mean(answer["margins"][i]-control["margins"][i] for i in indices))
            begin, end = stamps["0"]["vs_base"], stamps[str(UPDATES)]["vs_base"]
            output[role] = dict(stamps=stamps, fraction_remaining=end / begin if begin >= 0.10 else None)
        summary[name] = output
    return summary


def run(profile):
    exits, arms = {}, {}
    for phase, cap in CAPS.items():
        if (OUT / "STOP").exists() or not idle():
            exits[phase] = None
            break
        if datetime.now(CUTOFF.tzinfo) + timedelta(seconds=cap + 6) >= CUTOFF:
            exits[phase] = None
            break
        argv = ["timeout", "--kill-after=5s", f"{cap}s", sys.executable, "-B", "-u", "-X", "utf8", "-m",
                "scripts.diag_p108_g4_edit_retention", phase]
        exits[phase] = subprocess.run(argv, cwd=ROOT, check=False).returncode
        print("P108_G4_EDIT_EXIT", phase, exits[phase], flush=True)
        if exits[phase] != 0:
            break
        if phase in ARMS:
            arms[phase] = read(OUT / f"{phase}.json")
    returned = idle()
    same_inputs = all(sha(ROOT / name) == value for name, value in profile["source_pins"].items())
    same_inputs &= sha(PARENT) == profile["parent_sha256"] and sha(frozen.TOKENIZER) == profile["tokenizer_sha256"]
    completed = set(arms) == set(ARMS)
    summary = summarize(arms, profile["questions"]) if completed else {}
    write(OUT / "report.json", dict(exits=exits, arms=arms, summary=summary, gpu_returned=returned,
                                   source_and_parent_unchanged=same_inputs))
    return 0 if returned and same_inputs and completed else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run", *CAPS))
    args = parser.parse_args()
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ("" if args.phase == "prepare" else "0")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    profile, stream, panel = prepare_data()
    if args.phase == "prepare":
        assert not torch.cuda.is_initialized()
        OUT.mkdir(exist_ok=False)
        write(OUT / "profile.json", profile)
        print("P108_G4_EDIT_CPU_READY", profile["pool_tokens"], profile["train_stream_sha256"], flush=True)
        return 0
    assert os.environ.get("PYTORCH_CUDA_ALLOC_CONF") == ALLOCATOR
    assert os.environ.get("CUBLAS_WORKSPACE_CONFIG") == ":4096:8"
    assert profile == read(OUT / "profile.json")
    if args.phase == "run":
        assert datetime.now(CUTOFF.tzinfo) + timedelta(seconds=sum(CAPS.values()) + 36) < CUTOFF
        write(OUT / "active.json", dict(pid=os.getpid(), tag=TAG, caps=CAPS))
        print("P108_G4_EDIT_ACTIVE", os.getpid(), flush=True)
        return run(profile)
    model, down = load_model()
    panel = tuple(value.cuda() for value in panel)
    with sdpa_kernel(SDPBackend.MATH):
        if args.phase == "select":
            select(model, down, panel)
        else:
            train(args.phase, model, down, panel, stream.cuda())
    return 0


if __name__ == "__main__":
    sys.exit(main())
