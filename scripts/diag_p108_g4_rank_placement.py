"""Compare rank, physical placement, and value constraints on matched G4 edits."""

import argparse
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime
from itertools import combinations, product
import math
import os
from pathlib import Path
import subprocess
import unicodedata

import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p108_g4_master_margin_authored as old
from scripts import p108_native_scale as native
from scripts.diag_p107_hybrid_mntp import close_owned_cuda
from scripts.interactive_research_infer import require_idle_gpu
from scripts.p108_shared_ternary_edit import check_frozen_model, physical_down_owners


prior = old.prior
ROOT = prior.ROOT
TAG = "p108_g4_rank_placement_v1_20261119"
OUT = prior.OUT.with_name(TAG)
PLAN = ROOT / "test_plan/P108_직접가중치-방향수리와-학습개입.md"
RANK_AUDIT = ROOT / "test_result/evidence/p108_g4_edit_rank_readback_v1_20261119/report.json"
END = datetime.fromisoformat("2026-11-20T16:58:00+09:00")
OWNERS, GROUP, PER_ROW = (2, 6), 128, 8
FACTS = {
    "helium": (
        ("What is the chemical symbol of helium?", "Which symbol belongs to element helium?", "Give only helium's chemical symbol.", "He", "H"),
        ("헬륨의 원소 기호는 무엇인가요?", "원소 헬륨에 해당하는 기호는 어느 것인가요?", "헬륨의 원소 기호만 쓰세요.", "He", "H"),
    ),
    "osaka": (
        ("Which country contains the city of Osaka?", "Osaka is a city in which country?", "Name only the country where Osaka is located.", "Japan", "Germany"),
        ("오사카가 있는 나라는 어디인가요?", "오사카는 어느 나라의 도시인가요?", "오사카가 속한 나라 이름만 쓰세요.", "일본", "독일"),
    ),
    "product": (
        ("What is seven multiplied by eight?", "Calculate the product of 7 and 8.", "Write just the result of 7 multiplied by 8.", "56", "54"),
        ("7과 8을 곱하면 얼마인가요?", "칠 곱하기 팔의 값은 무엇인가요?", "7 곱하기 8의 숫자 답만 쓰세요.", "56", "54"),
    ),
    "mercury": (
        ("Which planet is closest to the Sun?", "What planet has the innermost orbit around the Sun?", "Name only the closest planet to the Sun.", "Mercury", "Mars"),
        ("태양에 가장 가까운 행성은 무엇인가요?", "태양 둘레에서 가장 안쪽을 공전하는 행성은 무엇인가요?", "태양에 가장 가까운 행성의 이름만 쓰세요.", "수성", "화성"),
    ),
    "hexagon": (
        ("How many sides does a hexagon have?", "Count the sides of a six-sided polygon.", "Write the number of sides in a hexagon as a digit.", "6", "8"),
        ("육각형의 변은 몇 개인가요?", "육각형을 이루는 변의 개수를 고르세요.", "육각형의 변 개수만 숫자로 쓰세요.", "6", "8"),
    ),
    "heart": (
        ("Which organ pumps blood around the body?", "Which organ sends blood through the circulation?", "Name only the organ that pumps blood.", "heart", "lung"),
        ("혈액을 순환시키는 펌프 역할을 하는 장기는 무엇인가요?", "온몸으로 피를 내보내는 장기는 무엇인가요?", "혈액을 내보내는 장기 이름만 쓰세요.", "심장", "폐"),
    ),
}
PROTECTION = {
    "polar": (("Which pole is in Antarctica?", "South", "North"), ("남극 대륙에 있는 극은 무엇인가요?", "남극", "북극")),
    "weekday": (("What day follows Tuesday?", "Wednesday", "Friday"), ("화요일 바로 다음 요일은 무엇인가요?", "수요일", "금요일")),
    "subtract": (("What is 27 minus 5?", "22", "21"), ("27에서 5를 빼면 얼마인가요?", "22", "21")),
    "color": (("The small tin is green and the large tin is white. What color is the small tin?", "green", "white"),
              ("작은 통은 초록색이고 큰 통은 흰색입니다. 작은 통의 색은 무엇인가요?", "초록색", "흰색")),
}


def gate(reserve=0):
    if (OUT / "STOP").exists() or (END - datetime.now(END.tzinfo)).total_seconds() <= reserve:
        raise TimeoutError("User 177 time limit or local stop reached")


def source_pins():
    names = (*prior.SOURCES, "scripts/p108_native_scale.py", "tinylm/infer/generate.py",
             Path(__file__).resolve(), Path(old.__file__).resolve(),
             Path(close_owned_cuda.__code__.co_filename).resolve(),
             Path(require_idle_gpu.__code__.co_filename).resolve(), PLAN, RANK_AUDIT, prior.frozen.TOKENIZER)
    if prior.sha(prior.PARENT) != prior.frozen.PARENT_SHA or prior.sha(prior.frozen.TOKENIZER) != prior.frozen.TOKENIZER_SHA:
        raise ValueError("The original P079 checkpoint or its tokenizer differs")
    return {(ROOT / name).relative_to(ROOT).as_posix(): prior.sha(ROOT / name) for name in names}


def layouts(weights):
    result = {}
    for owner, weight in weights.items():
        if weight.device.type != "cpu" or weight.shape != (768, 2048):
            raise ValueError("Expected the actual CPU view of a G4 down matrix")
        codes, scales = native.layout(weight, GROUP)
        result[owner] = codes, scales.squeeze(-1)
    return result


def shared_columns(codes, first, second):
    relation = codes[first] * codes[second]
    return [(relation == sign).nonzero().flatten() for sign in (1, -1)]


def exact_relocations(structure):
    by_scale = {}
    for owner, (_, scales) in structure.items():
        groups = defaultdict(list)
        for row, columns in enumerate(scales.tolist()):
            for block, scale in enumerate(columns):
                groups[scale].append((row, block))
        by_scale[owner] = groups
    a, b = OWNERS
    matches = defaultdict(list)
    for scale in sorted(set(by_scale[a]) & set(by_scale[b])):
        if scale == 0:
            continue
        for (ra, ba), (rb, bb) in product(by_scale[a][scale], by_scale[b][scale]):
            matches[ba, bb].append((ra, rb, scale))
    recipes = []
    for (ba, bb), matches_in_block in sorted(matches.items()):
        for (ra, rb, s), (qa, qb, t) in combinations(matches_in_block, 2):
            if ra == qa or rb == qb:
                continue
            options_a = shared_columns(structure[a][0][:, ba], ra, qa)
            options_b = shared_columns(structure[b][0][:, bb], rb, qb)
            if min(max(map(len, options_a)), max(map(len, options_b))) < PER_ROW:
                continue
            recipes.append(dict(blocks=[ba, bb], rows=[[ra, qa], [rb, qb]], scales=[s, t]))
    return recipes


def cases(tok):
    options = [tok.encode(" " + letter, add_special_tokens=False).ids for letter in ("A", "B")]
    if any(len(ids) != 1 for ids in options) or options[0] == options[1]:
        raise ValueError("A and B must be distinct single tokens")
    rows, open_cases = [], []

    def add_pair(role, ident, lang, question, correct, foil):
        for order in (0, 1):
            a, b = (correct, foil) if order == 0 else (foil, correct)
            prompt = f"{question}\nA. {a}\nB. {b}\n" + ("Answer:" if lang == "en" else "정답:")
            ids = tok.encode(prompt, add_special_tokens=False).ids
            for label, suffix in zip((" A", " B"), options, strict=True):
                if tok.encode(prompt + label, add_special_tokens=False).ids != ids + suffix:
                    raise ValueError("The answer token boundary changed")
            rows.append(dict(role=role, fact=ident, lang=lang, order=order, ids=ids, text=prompt, correct=order))

    for ident, languages in FACTS.items():
        for lang, (fit, held, prompt, target, foil) in zip(("en", "ko"), languages, strict=True):
            add_pair("fit", ident, lang, fit, target, foil)
            add_pair("held", ident, lang, held, target, foil)
            open_cases.append(dict(role="target", fact=ident, lang=lang, text=prompt, expected=target))
    for ident, languages in PROTECTION.items():
        for lang, (prompt, target, foil) in zip(("en", "ko"), languages, strict=True):
            add_pair("protect", ident, lang, prompt, target, foil)
            suffix = " Give only the answer." if lang == "en" else " 답만 쓰세요."
            open_cases.append(dict(role="protect", fact=ident, lang=lang, text=prompt + suffix, expected=target))
    if len({row["text"] for row in rows}) != 64 or len(open_cases) != 20:
        raise ValueError("Unexpected or duplicate research prompts")
    return rows, open_cases, [ids[0] for ids in options]


def prepare():
    gate()
    pins = source_pins()
    cfg, state, step = prior.frozen.prior.load_parent(torch)
    if step != 2289 or cfg.micro_group != GROUP or cfg.sparse34:
        raise ValueError("Expected the exact unpruned G4 parent route")
    weights = {owner: prior.ternary(state[f"mid_mlps.{idx}.down_proj.weight"], cfg)
               for idx, owner in enumerate(OWNERS)}
    recipes = exact_relocations(layouts(weights))
    if not recipes or torch.cuda.is_initialized():
        raise ValueError("CPU sealing needs exact matched scales and no initialized CUDA")
    probe_gradients = {owner: torch.linspace(.1, 1., weight.numel()).reshape_as(weight)
                       for owner, weight in weights.items()}
    fixture = {key: dict(ranks=row["ranks"], squared_l2=row["net_l2_squared"], off_grid=row["off_grid"])
               for key, _, row in build_edits(weights, probe_gradients, recipes[0])}
    tok = old.Tokenizer.from_file(str(prior.frozen.TOKENIZER))
    rows, open_cases, options = cases(tok)
    OUT.mkdir()
    (OUT / "plan_at_execution.md").write_bytes(PLAN.read_bytes())
    prior.write(OUT / "profile.json", dict(tag=TAG, user_directive=177, pins=pins, cpu_exact_recipes=recipes,
                cpu_arithmetic_fixture=fixture,
                rows=rows, open_cases=open_cases, options=options, checkpoint_writes=0, max_new=16))
    print("P108_RANK_PLACEMENT_PREPARE", len(recipes), len(rows), len(open_cases), flush=True)


def panel(rows, options, pad):
    tokens = [torch.tensor(row["ids"]) for row in rows]
    matrix = torch.nn.utils.rnn.pad_sequence(tokens, batch_first=True, padding_value=pad)
    last = torch.tensor([len(row) - 1 for row in tokens])
    label = torch.tensor([row["correct"] for row in rows])
    return tuple(item.cuda() for item in (matrix, last, label, torch.tensor(options)))


def coordinated_columns(codes, scores, rows, block):
    a, b = rows
    symbols = codes[:, block]
    gain = scores[:, block]
    low = []
    for compatible in shared_columns(symbols, a, b):
        if len(compatible) >= PER_ROW:
            chosen = compatible[(gain[a, compatible] + gain[b, compatible]).argsort(descending=True)[:PER_ROW]]
            low.append((float((gain[a, chosen] + gain[b, chosen]).sum()), [chosen, chosen]))
    high = []
    for first, second in ((a, b), (b, a)):
        left = gain[first].masked_fill(symbols[first] == 0, -torch.inf).argsort(descending=True)[:PER_ROW]
        mask = symbols[second].eq(0)
        mask[left] = True
        right = gain[second].masked_fill(mask, -torch.inf).argsort(descending=True)[:PER_ROW]
        if bool(symbols[first, left].eq(0).any()) or bool(mask[right].any()):
            continue
        ordered = [left, right] if first == a else [right, left]
        high.append((float((gain[a, ordered[0]] + gain[b, ordered[1]]).sum()), ordered))
    if not low or not high:
        return None
    return {rank: max(choices, key=lambda row: row[0]) for rank, choices in ((1, low), (2, high))}


def choose_anchor(structure, scores, owner, relocation_rows, relocation_block):
    codes, _ = structure[owner]
    block = (relocation_block + 1) % codes.shape[1]
    row_gains = scores[owner][:, block].masked_fill(codes[:, block] == 0, -torch.inf)
    retained = row_gains.topk(PER_ROW, dim=1).values.sum(1)
    retained[list(relocation_rows)] = -torch.inf
    eligible = retained.argsort(descending=True)[:16].tolist()
    valid = []
    for rows in combinations(eligible, 2):
        columns = coordinated_columns(codes, scores[owner], rows, block)
        if columns is not None:
            valid.append((sum(value[0] for value in columns.values()), rows, columns))
    if not valid:
        raise ValueError("No anchor pair with both ranks in the distinct column block")
    _, rows, columns = max(valid, key=lambda row: row[0])
    return block, rows, columns


def make_targets(weights, gradients, specs, mode, pair_rank):
    changed = {}
    tables = {}
    gain = squared = 0.
    for owner, block, rows, choices in specs:
        cols = torch.stack(choices[pair_rank][1]) + block * GROUP
        row_indices = torch.tensor(rows)[:, None]
        old_values = weights[owner][row_indices, cols]
        grads = gradients[owner][row_indices, cols].double()
        edits = -2 * old_values.double()
        if mode == "real":
            benefit = -(grads * edits).sum(dim=0)
            amplitude = 1. + .4 * benefit / benefit.abs().max().clamp_min(1e-15)
            edits *= amplitude * (math.sqrt(PER_ROW) / amplitude.norm())
        target = changed.setdefault(owner, weights[owner].clone())
        target[row_indices, cols] = (old_values.double() + edits).to(target.dtype)
        stored = target[row_indices, cols].double() - old_values.double()
        gain -= float((stored * grads).sum())
        squared += float(stored.square().sum())
        tables.setdefault(owner, []).append(dict(rows=list(rows), block=block,
            columns=cols.tolist(), before=old_values.tolist(), after=target[row_indices, cols].tolist()))
    ranks = {}
    off_grid = 0
    for owner, target in changed.items():
        original = weights[owner]
        delta = target.double() - original.double()
        nz = delta.ne(0)
        active = delta[nz.any(1)][:, nz.any(0)]
        singular = torch.linalg.svdvals(active)
        ranks[str(owner)] = int((singular > singular[0] * 1e-6).sum())
        off_grid += int((nz & target.ne(0) & target.abs().ne(original.abs())).sum())
        if mode == "ternary":
            native.packet(original, target, GROUP)
    positions = sum(int(target.ne(weights[owner]).sum()) for owner, target in changed.items())
    if positions != 4 * PER_ROW or sum(ranks.values()) != 2 * pair_rank or ((off_grid > 0) != (mode == "real")):
        raise ValueError(f"Unexpected realized coordinates, rank, or off-grid count: {positions}, {ranks}, {off_grid}")
    return changed, dict(positions=positions, ranks=ranks, net_l2_squared=squared, off_grid=off_grid,
                         predicted_fit_nll_decrease=gain, coordinates=tables)


@contextmanager
def installed(owners, changed):
    original = {}
    counts = {str(owner): 0 for owner in changed}
    handles = []

    def count(owner, replacement):
        def check(module, _inputs):
            if module._wq is not replacement:
                raise RuntimeError("The measured visit did not use the installed matrix")
            counts[str(owner)] += 1
        return check

    try:
        for owner, target in changed.items():
            module = owners[owner].module
            original[owner] = module._wq
            replacement = target.to(module.weight.device)
            module._wq = replacement
            handles.append(module.register_forward_pre_hook(count(owner, replacement)))
        yield counts, handles
    finally:
        for handle in handles:
            handle.remove()
        for owner, cache in original.items():
            owners[owner].module._wq = cache


@torch.no_grad()
def answers(model, tok, prompts, cap):
    result = []
    for row in prompts:
        gate()
        prefix = tok.decode(tok.encode(row["text"]).ids)
        text, meta = old.sample(model, model.cfg, tok, row["text"], max_new=cap, temperature=0., top_k=0,
                                device="cuda", logits_last_only=True, return_metadata=True)
        if not text.startswith(prefix):
            raise ValueError("The generation result lost the expected prefix")
        answer = text[len(prefix):]
        normalized = unicodedata.normalize("NFC", answer.casefold()).strip().rstrip(".。").strip()
        result.append(dict(**row, answer=answer, correct=normalized == row["expected"].casefold(),
                           finish=meta["finish_reason"]))
    return result


@torch.no_grad()
def measure(model, data, tok, profile):
    return dict(logits=prior.choice_logits(model, data).tolist(),
                answers=answers(model, tok, profile["open_cases"], profile["max_new"]))


def build_edits(weights, gradients, recipe):
    structure = layouts(weights)
    scores = {owner: (2 * gradients[owner] * weights[owner]).reshape_as(structure[owner][0]) for owner in OWNERS}
    moved = {}
    for idx, owner in enumerate(OWNERS):
        block, rows = recipe["blocks"][idx], recipe["rows"][idx]
        chosen = coordinated_columns(structure[owner][0], scores[owner], rows, block)
        if chosen is None:
            raise ValueError("An exact relocation lost a valid rank")
        moved[owner] = owner, block, rows, chosen
    for primary in OWNERS:
        peer = next(owner for owner in OWNERS if owner != primary)
        _, block, rows, _ = moved[primary]
        anchor = (primary, *choose_anchor(structure, scores, primary, rows, block))
        budget = None
        for place, rank, mode in product(("single", "split"), (1, 2), ("ternary", "real")):
            gate(12)
            target, geometry = make_targets(weights, gradients,
                (anchor, moved[primary if place == "single" else peer]), mode, rank)
            norm = geometry["net_l2_squared"]
            if budget is None:
                budget = norm
            if (mode == "ternary" and budget != norm) or (mode == "real" and abs(math.sqrt(norm / budget) - 1) > 2e-6):
                raise ValueError("Realized edit budgets differ")
            key = f"owner{primary}_{place}_rank{2 * rank}_{mode}"
            yield key, target, geometry


def compare(model, weights, gradients, owners, data, tok, profile, recipe):
    results = {}
    for key, target, geometry in build_edits(weights, gradients, recipe):
        with installed(owners, target) as (counts, handles):
            with torch.no_grad():
                values = prior.choice_logits(model, data).tolist()
            expected = {str(owner):len(owners[owner].visits) for owner in target}
            if counts != expected:
                raise ValueError(f"Actual modified visits differ: {counts}, {expected}")
            for handle in handles:
                handle.remove()
            handles.clear()
            generated = answers(model, tok, profile["open_cases"], profile["max_new"])
        geometry["visited"] = counts
        result = dict(geometry=geometry, logits=values, answers=generated)
        results[key] = result
        prior.write(OUT / f"{key}.json", result)
        print("P108_RANK_PLACEMENT_ARM", key, geometry["ranks"], geometry["net_l2_squared"],
              sum(row["correct"] for row in generated), flush=True)
    return results


def run():
    gate(360)
    profile = prior.read(OUT / "profile.json")
    pins = source_pins()
    if profile["pins"] != pins or prior.sha(OUT / "plan_at_execution.md") != pins[PLAN.relative_to(ROOT).as_posix()]:
        raise ValueError("The sealed runtime or plan changed")
    tok = old.Tokenizer.from_file(str(prior.frozen.TOKENIZER))
    if (profile["rows"], profile["open_cases"], profile["options"]) != cases(tok):
        raise ValueError("Sealed evaluation records changed")
    entry = require_idle_gpu()
    model = prior.load_model()[0]
    model.requires_grad_(False)
    with torch.no_grad():
        model.freeze_quant()
    owners = {index: owner for index, owner in physical_down_owners(model).items() if index in OWNERS}
    check_frozen_model(model, owners)
    originals = {index: owner.module._wq for index, owner in owners.items()}
    weights = {index: value.detach().cpu() for index, value in originals.items()}
    recipes = exact_relocations(layouts(weights))
    if not recipes:
        raise ValueError("No exact per-row shared scales in the actual CUDA cache")
    data = panel(profile["rows"], profile["options"], tok.token_to_id("<pad>"))
    fit = panel([row for row in profile["rows"] if row["role"] == "fit"], profile["options"], tok.token_to_id("<pad>"))
    peak_file = OUT / "device_100ms.csv"
    with peak_file.open("xb") as output:
        sampler = subprocess.Popen((*old.audit.DEVICE, "--loop-ms=100"), stdout=output)
        try:
            with sdpa_kernel(SDPBackend.MATH):
                for value in originals.values():
                    value.requires_grad_(True)
                loss = F.cross_entropy(prior.choice_logits(model, fit), fit[2])
                gradients = {k:v.cpu() for k,v in zip(originals, torch.autograd.grad(loss, tuple(originals.values())), strict=True)}
                for value in originals.values():
                    value.requires_grad_(False)
                del value, loss
                initial = prior.state_sha(model.state_dict())
                baseline = measure(model, data, tok, profile)
                variants = compare(model, weights, gradients, owners, data, tok, profile, recipes[0])
                with torch.no_grad():
                    restored = prior.choice_logits(model, data).tolist()
                if restored != baseline["logits"] or prior.state_sha(model.state_dict()) != initial:
                    raise ValueError("The original core or original logits did not restore")
        finally:
            if sampler.poll() is None:
                sampler.terminate()
            sampler.wait(timeout=8)
    samples = old.audit.read_samples(peak_file)
    report = dict(tag=TAG, entry=entry, cuda_recipe=recipes[0], cuda_exact_recipe_count=len(recipes),
                  variants=variants, baseline=baseline, source_preserved=source_pins() == pins,
                  original_weights_and_logits_restored=True, final_checkpoint_writes=0, training_updates=0,
                  peak_device=max(samples, key=lambda row: row["occupied_mib"]), sample_count=len(samples),
                  profile_sha256=prior.sha(OUT / "profile.json"))
    if not report["source_preserved"]:
        raise ValueError("An original input or runtime pin differs")
    del model, owners, originals, data, fit
    close_owned_cuda(torch, report)
    prior.write(OUT / "report.json", report)
    print("P108_RANK_PLACEMENT_RESULT", len(variants), report["peak_device"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run"))
    args = parser.parse_args()
    expected = "0" if args.phase == "run" else ""
    if os.environ.get("CUDA_VISIBLE_DEVICES") != expected:
        parser.error("Use isolated CPU preparation and the authorized GPU")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    (run if expected else prepare)()
