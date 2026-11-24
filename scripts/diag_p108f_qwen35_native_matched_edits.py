"""Test the existing matched direct-edit policies on the pinned Qwen text body."""

import argparse
from datetime import datetime
import gc
import os
from pathlib import Path
import subprocess
from time import monotonic
from unittest.mock import patch

import torch
from torch.nn import functional as F

from scripts import diag_p106b_qwen35_text_core6 as native
from scripts import diag_p108f_four_edit_policy as four
from scripts import diag_p108f_matched_policies as prior
from scripts.diag_p107_hybrid_mntp import close_owned_cuda
from scripts.diag_p109_qwen_248k_warm_ce import DEVICE, read_samples
from scripts.interactive_research_infer import require_idle_gpu, state_fingerprint


ROOT = prior.ROOT
TAG = "p108f_qwen35_native_matched_edits_v1_20261120"
OUT = prior.OUT.with_name(TAG)
SEARCH = OUT / "initial_search"
PROFILE = OUT / "profile.json"
END = datetime.fromisoformat("2026-11-20T16:58:00+09:00")
MAX_NEW, BATCH, PAD = 16, 8, 248044
EXTRA = (
    ("en", "A ledger says the glass jar belongs to Mina and the tin belongs to Ori. Name the owner of the tin only.", "Ori"),
    ("ko", "장부에서 자두는 민수, 복숭아는 소연의 물건이다. 복숭아 주인의 이름만 쓰시오.", "소연"),
    ("en", "The green gate is open and the blue gate is closed. What color is the open gate? Use one word.", "green"),
    ("ko", "작은 상자에는 동전이, 큰 상자에는 단추가 있다. 큰 상자의 물건을 한 단어로 답하시오.", "단추"),
    ("en", "One page has 19 lines, and the next page has 23. Give their total as a number.", "42"),
    ("ko", "연필 18자루에서 7자루를 빼면 남는 수는? 숫자만 쓰시오.", "11"),
    ("en", "What month immediately follows April? Give only its name.", "May"),
    ("ko", "8월의 다음 달은 몇 월인가? 월을 붙여 답하시오.", "9월"),
)
TURNS = (
    ("en", "For this conversation, the brass key is in the blue box and the steel key is in the red box. Which box holds the brass key? Give only its color.", "blue",
     "Which color did I say held the steel key? Give only its color.", "red"),
    ("ko", "이 대화에서 사과는 초록 그릇, 배는 흰 그릇에 있다. 사과가 든 그릇의 색만 쓰시오.", "초록",
     "처음에 배를 넣었다고 한 그릇의 색만 쓰시오.", "흰색"),
    ("en", "Mara carries the notebook, and Theo carries the chart. Who carries the notebook? Give the name only.", "Mara",
     "Now answer for the chart instead. Give the name only.", "Theo"),
    ("ko", "종이표는 나래가, 금속표는 준호가 갖고 있다. 종이표를 갖고 있는 사람의 이름만 쓰시오.", "나래",
     "그렇다면 금속표를 가진 사람의 이름은 무엇인가?", "준호"),
)


def check_time(reserve=0):
    if (END - datetime.now(END.tzinfo)).total_seconds() <= reserve or (OUT / "STOP").exists():
        raise TimeoutError("User 177 deadline or local stop reached")


class Budget:
    def __init__(self):
        self.end = monotonic() + 850

    def check(self):
        check_time()
        free, total = torch.cuda.mem_get_info()
        if monotonic() >= self.end or total - free > 13_000_000_000:
            raise RuntimeError("Local time or 13 GB device occupancy boundary reached")


def load_tokenizer(assets):
    files = assets["files"]
    raw = native.read_json(files["tokenizer.json"]["resolved_path"])
    metadata = native.read_json(files["tokenizer_config.json"]["resolved_path"])
    tokenizer, receipt = native.build_tokenizer(raw, metadata)
    if tokenizer.pad_token_id != PAD or tokenizer.eos_token_id != PAD:
        raise ValueError("Exact verified Qwen EOS and padding IDs are required")
    return tokenizer, receipt


def tokens(tok, case, fit=False):
    prompt = prior.text_for(case)
    ids = tok.encode(prompt, add_special_tokens=False)
    if not ids or len(ids) > 192 or max(ids) >= 248320 or PAD in ids:
        raise ValueError("Invalid frozen Qwen prompt")
    row = dict(**case, prompt=prompt, ids=ids)
    if fit:
        joint = tok.encode(prompt + " " + case["expected"], add_special_tokens=False)
        if joint[:len(ids)] != ids or len(joint) <= len(ids):
            raise ValueError("Qwen continuation crossed the answer boundary")
        row["target"] = joint[len(ids):] + [PAD]
    return row


def prompts(tok):
    fit, different = prior.scoped_rows()
    for index, (lang, question, answer) in enumerate(EXTRA):
        different.append(dict(id=f"independent{index + 1}", group=None, language=lang,
                              question=question, expected=answer, protected=True, seen_language=None))
    turns = [dict(id=f"conversation{i + 1}", group=None, language=lang, question=first, expected=first_answer,
                  follow=second, follow_answer=second_answer, protected=True, seen_language=None)
             for i,(lang,first,first_answer,second,second_answer) in enumerate(TURNS)]
    if len({row["question"] for row in (*fit, *different, *turns)}) != 44:
        raise ValueError("Evaluation surfaces overlap the frozen FIT")
    return dict(fit=[tokens(tok, row, True) for row in fit],
                held=[tokens(tok, row) for row in different], turns=[tokens(tok, row) for row in turns])


def source_pins():
    files = (prior.PLAN, Path(__file__), Path(native.__file__), Path(four.__file__), Path(prior.__file__),
             Path(prior.old.native.__file__), Path(prior.old.previous.__file__))
    return {path.relative_to(ROOT).as_posix():prior.HASH(path) for path in files}


def prepare():
    check_time(900)
    assets = native.asset_identity()
    tokenizer, tok = load_tokenizer(assets)
    pins = source_pins()
    profile = dict(tag=TAG, user_directive=177, assets=assets, tokenizer=tok, pins=pins, prompts=prompts(tokenizer))
    if torch.cuda.is_initialized():
        raise ValueError("CPU preparation initialized CUDA")
    OUT.mkdir()
    (OUT / "plan_at_execution.md").write_bytes(prior.PLAN.read_bytes())
    prior.WRITE(PROFILE, profile)
    print("P108F_QWEN_PREPARE", {k:len(v) for k,v in profile["prompts"].items()}, flush=True)


def packed_sequences(sequences):
    data = torch.full((len(sequences), max(map(len, sequences))), PAD, dtype=torch.long)
    for i, ids in enumerate(sequences):
        data[i, :len(ids)] = torch.tensor(ids, dtype=torch.long)
    return data.cuda()


def selected_logits(body, inputs, owners, positions):
    hidden = body.model(input_ids=inputs, use_cache=False, past_key_values=None).last_hidden_state
    return body.lm_head(hidden[owners, positions]).float()


class Fit:
    def __init__(self, model, cases, budget, counts):
        self.model, self.budget, self.counts = model, budget, counts
        self.inputs = packed_sequences([r["ids"] + r["target"][:-1] for r in cases])
        owners, positions, targets, weights = [], [], [], []
        for i, row in enumerate(cases):
            length = len(row["target"])
            owners.extend([i] * length)
            positions.extend(range(len(row["ids"]) - 1, len(row["ids"]) - 1 + length))
            targets.extend(row["target"])
            weights.extend([1 / (len(cases) * length)] * length)
        self.owners, self.positions, self.targets = (torch.tensor(x, device="cuda") for x in (owners, positions, targets))
        self.weights = torch.tensor(weights, device="cuda")

    def logits(self):
        self.budget.check()
        self.counts["fit_forwards"] += 1
        return selected_logits(self.model, self.inputs, self.owners, self.positions)

    def loss(self):
        return (F.cross_entropy(self.logits(), self.targets, reduction="none") * self.weights).sum()

    @torch.no_grad()
    def mean(self):
        return float(self.loss())

    def directions(self, parameters):
        gradients = torch.autograd.grad(self.loss(), parameters)
        self.counts["fit_backwards"] += 1
        result = []
        for g in gradients:
            norm = float(g.double().norm())
            if not 0 < norm < float("inf"):
                raise ValueError("Nonzero finite actual Qwen down gradient required")
            result.append(g.detach().neg() / norm)
        return result


@torch.no_grad()
def check_scores(body, fit, cases):
    matrix = fit.logits()
    differences = []
    for i in (0, len(cases) - 1):
        row = cases[i]
        inputs = torch.tensor([row["ids"] + row["target"][:-1]], device="cuda")
        direct = body(input_ids=inputs, use_cache=False, logits_to_keep=len(row["target"])).logits[0].float()
        batch = matrix[fit.owners.eq(i)]
        differences.append(float((batch - direct).abs().max()))
        if differences[-1] > .005 or not torch.equal(batch.argmax(1), direct.argmax(1)):
            raise ValueError(f"Qwen batched position inference differs from individual native forward {differences}")
    return differences


def initial_policies(body, downs, fit, target):
    body.requires_grad_(False)
    params = tuple(layer.weight for layer in downs.values())
    for p in params:
        p.requires_grad_(True)
    try:
        initial = {i:m.weight.detach().double().clone() for i,m in downs.items()}
        nll = fit.mean()
        directions = fit.directions(params)
        records = []
        best, after = None, None
        for i in downs:
            trial, snapshot = prior.trial(downs, initial, i, directions[i], target, 0., fit)
            records.append(trial)
            if best is None or (trial["fit_nll"], i) < (best["fit_nll"], best["layer"]):
                best, after = trial, snapshot
        i = best["layer"]
        random = torch.randn(downs[i].weight.shape, device="cuda", generator=torch.Generator(device="cuda").manual_seed(1392026))
        control, control_after = prior.trial(downs, initial, i, random / random.double().norm(), target, 0., fit)
        order = [r["layer"] for r in sorted(records,key=lambda row:(row["fit_nll"], row["layer"]))]
        paths = dict(ORIGINAL=([], {}, nll), SINGLE1=([best], {i:after}, best["fit_nll"]),
                     RANDOM1=([control], {i:control_after}, control["fit_nll"]))
    finally:
        body.requires_grad_(False)
    return paths, dict(order=order, first_search=records)


@torch.no_grad()
def generate(body, tokenizer, cases, budget, counts):
    result = []
    for first in range(0, len(cases), BATCH):
        part = cases[first:first + BATCH]
        sequences = [list(row["ids"]) for row in part]
        answers = [[] for _ in part]
        done = [False for _ in part]
        for _ in range(MAX_NEW):
            budget.check()
            owners = torch.arange(len(part), device="cuda")
            positions = torch.tensor([len(ids)-1 for ids in sequences], device="cuda")
            new_ids = selected_logits(body, packed_sequences(sequences), owners, positions).argmax(1).tolist()
            counts["generate_forward_batches"] += 1
            for i, token in enumerate(new_ids):
                if not done[i]:
                    answers[i].append(token)
                    sequences[i].append(token)
                    done[i] = token == PAD
            if all(done):
                break
        for case, generated in zip(part, answers, strict=True):
            answer = tokenizer.decode(generated, skip_special_tokens=True)
            result.append(dict(**case, answer=answer, exact=prior.metrics.exact_answer(answer, case["expected"]),
                diagnostics=prior.metrics.repetition_metrics(generated, answer, case["question"]),
                generation=dict(ids=generated, finish_reason="EOS" if generated[-1]==PAD else "MAX_NEW")))
    return result


def followups(tokenizer, first):
    result = []
    for line in first:
        prefix = "Question: " if line["language"] == "en" else "질문: "
        suffix = "\nAnswer:" if line["language"] == "en" else "\n답:"
        prompt = line["prompt"] + line["answer"] + "\n" + prefix + line["follow"] + suffix
        result.append(dict(id=line["id"]+"_follow", group=None, language=line["language"], question=line["follow"],
                           expected=line["follow_answer"], protected=True, seen_language=None, prompt=prompt,
                           ids=tokenizer.encode(prompt, add_special_tokens=False), parent_answer=line["answer"]))
    return result


def load_body(assets):
    from safetensors import safe_open
    from transformers import Qwen3_5ForCausalLM, Qwen3_5TextConfig

    declared = native.read_json(assets["files"]["config.json"]["resolved_path"])["text_config"]
    cfg = Qwen3_5TextConfig.from_pretrained(str(native.MODEL_DIR), local_files_only=True)
    for key, expected in declared.items():
        if key not in ("dtype", "transformers_version") and getattr(cfg, key) != expected:
            raise ValueError("The pinned Qwen text config differs: " + key)
    cfg.use_cache = False
    cfg.transformers_weights = native.INDEX
    model, loading = Qwen3_5ForCausalLM.from_pretrained(str(native.MODEL_DIR),config=cfg,
        local_files_only=True,trust_remote_code=False,use_safetensors=True,dtype=torch.float32,
        attn_implementation="eager",output_loading_info=True,ignore_mismatched_sizes=False)
    if any(loading.get(k) for k in ("missing_keys","unexpected_keys","mismatched_keys","error_msgs")):
        raise ValueError("The proven Qwen text loader did not consume the exact state")
    with safe_open(assets["files"][native.WEIGHT]["resolved_path"], framework="pt", device="cpu") as handle:
        proof = native.verify_consumption(model, assets["inventory"], handle.get_tensor, torch)
    return model.eval().requires_grad_(False), proof


def execute(profile):
    assets = native.asset_identity()
    if assets != profile["assets"]:
        raise ValueError("Local native model differs from the sealed asset")
    tokenizer, tok = load_tokenizer(assets)
    if tok != profile["tokenizer"] or prompts(tokenizer) != profile["prompts"]:
        raise ValueError("Tokenization or frozen prompts changed")
    model, proof = load_body(assets)
    raw = state_fingerprint(model)
    model.to("cuda")
    downs = {i:layer.mlp.down_proj for i,layer in enumerate(model.model.layers)}
    kinds = model.config.layer_types
    if kinds.count("full_attention") != 6 or kinds.count("linear_attention") != 18 or len(downs) != 24:
        raise ValueError("Exact 24-layer text-native down geometry required")
    if any(layer.bias is not None or tuple(layer.weight.shape)!=(1024,3584) for layer in downs.values()):
        raise ValueError("Expected biasless FP32 native 1024-by-3584 Linear parameters")
    norms = {i:float(layer.weight.detach().double().norm()) for i,layer in downs.items()}
    radius = .01 * min(norms.values())
    budget = Budget()
    counts = dict(fit_forwards=0,fit_backwards=0,generate_forward_batches=0)
    cases = profile["prompts"]
    fit = Fit(model, cases["fit"], budget, counts)
    parity = check_scores(model, fit, cases["fit"])
    paths, search = initial_policies(model,downs,fit,radius)
    SEARCH.mkdir()
    prior.WRITE(SEARCH / "search.json", search)
    for name in ("ORIGINAL", "SINGLE1"):
        prior.WRITE(SEARCH / f"{name}.json", dict(fit_nll=paths[name][2]))
    with patch.object(four,"BASE",SEARCH):
        more, strategy = four.four_rounds(model, downs, fit, radius, counts)
    paths.update(more)
    measured = {}
    for name,(steps, matrices, loss) in paths.items():
        with prior.applied(downs, matrices):
            held = generate(model,tokenizer,cases["held"],budget,counts)
            first = generate(model,tokenizer,cases["turns"],budget,counts)
            second = generate(model,tokenizer,followups(tokenizer,first),budget,counts)
        result = dict(steps=steps, net=steps[-1]["net"] if steps else 0., fit_nll=loss,
                      path=sum(step["step"] for step in steps), after_sha256=prior.fingerprint(matrices),
                      held=held, first=first, followups=second)
        prior.WRITE(OUT / f"{name}.json", result)
        measured[name] = result
        print("P108F_QWEN_POLICY", name, [row["layer"] for row in steps], loss,
              sum(row["exact"] for row in held+first+second), flush=True)
    if state_fingerprint(model) != raw or any(p.grad is not None for p in model.parameters()):
        raise ValueError("Original weights or absence of optimizer gradients did not restore")
    dynamics = {i:layer.linear_attn.chunk_gated_delta_rule.__module__
                for i,layer in enumerate(model.model.layers) if hasattr(layer,"linear_attn")}
    return dict(proof=proof, runtime_layer_types=kinds, delta_rule_modules=dynamics, source_fingerprint=raw,
                restored=True, individual_batched_max_abs=parity, budget=radius, layer_norms=norms,
                counts=counts, search=search, adaptive_search=strategy, measured=measured, optimizer_updates=0,
                checkpoint_writes=0)


def run():
    check_time(900)
    profile = prior.READ(PROFILE)
    if source_pins() != profile["pins"] or prior.HASH(OUT / "plan_at_execution.md") != profile["pins"][prior.PLAN.relative_to(ROOT).as_posix()]:
        raise ValueError("The sealed runtime or evaluation plan changed")
    entry = require_idle_gpu()
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    trace = OUT / "device_100ms.csv"
    with trace.open("xb") as output:
        sampler = subprocess.Popen((*DEVICE,"--loop-ms=100"), stdout=output)
        try:
            report = execute(profile)
        finally:
            if sampler.poll() is None:
                sampler.terminate()
            sampler.wait(timeout=8)
    gc.collect()
    close_owned_cuda(torch,report)
    samples = read_samples(trace)
    report.update(tag=TAG,entry=entry,profile_sha256=prior.HASH(PROFILE),
                  resource_peak=max(sample["occupied_mib"] for sample in samples),resource_samples=len(samples),
                  sources_preserved=source_pins()==profile["pins"])
    if not report["sources_preserved"]:
        raise ValueError("Execution source changed")
    prior.WRITE(OUT / "report.json",report)
    print("P108F_QWEN_RESULT",len(report["measured"]),report["resource_peak"],flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("prepare","run"))
    phase = parser.parse_args().phase
    expected = "0" if phase == "run" else ""
    if os.environ.get("CUDA_VISIBLE_DEVICES") != expected:
        parser.error("Use isolated CPU preparation and the authorized CUDA device")
    if expected and os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
        parser.error("Set the deterministic cuBLAS workspace")
    from scripts.prepare_p106b_official_eval import configure_hf_cache
    configure_hf_cache()
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    (run if expected else prepare)()
