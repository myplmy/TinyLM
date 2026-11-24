"""Compare P109 CE and exact-prefix teacher KD from the same trained G4 parent."""

import argparse
from collections import defaultdict
from datetime import datetime, timedelta
import os
from pathlib import Path
from statistics import median
import subprocess
import sys
from time import perf_counter
from unittest.mock import patch

from tokenizers import Tokenizer
import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p106b_dvlm_real_prefix_head as base
from scripts import diag_p109_frozen_g4_routes as frozen
from scripts.p107_active_optimizer_groups import keep_active_groups
from tinylm.model.transformer import TiedMLPTransformer
from tinylm.train.anneal_schedule import lr_factor
from tinylm.train.experimental_optimizers import build_experimental_optimizers
from tinylm.train.trainer import _kd_kl


TAG = "p106b_p109_actual_prefix_kd_v1_20261119"
OUT = base.OUT.with_name(TAG)
read, write, sha = base.read, base.write, base.SHA
UPDATES, BATCH, WIDTH, LR, ALPHA, T, SEED = 64, 4, 96, 3e-5, .3, 2., 2027
TRAIN_PER_LANG, HELD_PER_LANG = 384, 24
EVAL_STEPS = (0, 16, 32, UPDATES)
ARMS = {"ce": 0., "prefix_kd": ALPHA}
SOURCES = (*frozen.prior.SOURCES, "scripts/diag_p106b_p109_actual_prefix_kd.py",
           "scripts/diag_p106b_dvlm_real_prefix_head.py", "tinylm/train/trainer.py",
           "tinylm/train/anneal_schedule.py", "tinylm/train/experimental_optimizers.py",
           "tinylm/train/muon.py", "scripts/p107_active_optimizer_groups.py")

TRAIN_EN = (
    "Repair note {i} describes a {color} {obj} found under the stair. Set it on the shelf before the foreman arrives. Write the time on the front of the note.",
    "Plot {i} in the garden is marked with a {color} {obj}. After the rain, lift the lower edge and check whether the soil is still damp.",
    "Recipe {i} calls for a half cup of ground oats. Put the dry mixture beside the {color} {obj}, then stir in water a little at a time.",
    "The engineer at station {i} measured the depth of the stream with a straight rod. A {color} {obj} kept the field notes dry.",
    "A {color} {obj} sits beside the camera at desk {i}. Check that the glass is clean and turn the lens toward the bright edge of the room.",
    "The weaver stopped at row {i} to compare the pattern with yesterday's sample. A {color} {obj} held the unused strips.",
)
TRAIN_KO = (
    "수리 기록 {i}번에는 계단 밑에서 {color} {obj} 하나를 찾았다고 적혀 있다. 작업반장이 오기 전에 그것을 선반 위에 놓고 시각을 기록한다.",
    "텃밭 {i}번은 {color} {obj} 하나로 표시했다. 비가 그치면 아래쪽을 들어 올려 흙이 아직 젖어 있는지 확인한다.",
    "조리법 {i}번은 곱게 간 귀리 반 컵을 쓴다. 가루를 {color} {obj} 옆에 놓은 다음 물을 조금씩 넣어 저어 준다.",
    "측량 지점 {i}번에서 곧은 막대로 개울의 깊이를 쟀다. {color} {obj}에 야외에서 쓴 기록을 담아 물에 젖지 않게 했다.",
    "책상 {i}번의 카메라 옆에는 {color} {obj} 하나가 놓여 있다. 유리의 얼룩을 닦고 방의 밝은 쪽으로 렌즈를 돌린다.",
    "직조공은 {i}번째 줄에서 작업을 멈추고 어제 짠 표본과 무늬를 비교했다. 쓰고 남은 띠는 {color} {obj}에 담았다.",
)
HELD_EN = (
    "Train {i} leaves the small terminal before the eastern platform opens. A passenger asks how long the stop at the next station will last.",
    "On page {i} the atlas shows a shallow harbor beside a narrow bridge. A librarian helps the reader find the older edition.",
    "During rehearsal {i} the conductor asks for a softer entrance after the pause. A short note beside the measure marks the change.",
    "Tank {i} is behind a low wall at the aquarium. Two silver fish rise together when a shadow falls across the water.",
)
HELD_KO = (
    "{i}번 열차는 동쪽 승강장이 열리기 전에 작은 종착역을 떠난다. 한 승객이 다음 역에는 얼마나 오래 정차하는지 묻는다.",
    "지도책 {i}쪽에는 좁은 다리 곁의 얕은 항구가 그려져 있다. 사서가 독자에게 더 오래된 판본을 찾아 준다.",
    "{i}번째 연습에서 지휘자는 쉰 뒤에 첫 음을 더 부드럽게 시작해 달라고 한다. 해당 마디 옆의 짧은 연필 표시는 그 변화를 알린다.",
    "수족관의 {i}번 수조는 낮은 담 뒤에 있다. 물 위로 그림자가 지나가자 은빛 물고기 두 마리가 함께 떠오른다.",
)


def documents():
    colors = (("blue", "파란"), ("yellow", "노란"), ("grey", "회색"), ("green", "초록"))
    objects = (("case", "상자"), ("bag", "가방"), ("tray", "쟁반"), ("basket", "바구니"), ("box", "통"))
    for split, banks, count in (("train", (TRAIN_EN,TRAIN_KO), TRAIN_PER_LANG),
                                 ("held", (HELD_EN,HELD_KO), HELD_PER_LANG)):
        for lang, templates in enumerate(banks):
            language = ("en","ko")[lang]
            for i in range(count):
                group = i % len(templates)
                text = templates[group].format(i=i+(601 if split=="train" else 1201),
                    color=colors[i%len(colors)][lang], obj=objects[(i//3)%len(objects)][lang])
                yield dict(id=f"{split}_{language}_{i:04d}", split=split, language=language, family=group, text=text)


def data_and_receipt():
    student, teacher = (Tokenizer.from_file(str(path)) for path in (base.STUDENT, base.TEACHER/"tokenizer.json"))
    vocab = base.head.native_vocabulary(read(base.STUDENT))
    with patch.object(base, "documents", documents):
        docs, rows, counts = base.corpus(student, teacher, vocab)
    records = [row for row in rows if docs[row["doc"]]["split"] == "train"]
    lookups = defaultdict(dict)
    for ordinal,row in enumerate(records):
        prefix = teacher.decode(row["teacher_prefix"], skip_special_tokens=False).encode("utf-8")
        key = (prefix, row["target"])
        assert key not in lookups[row["doc"]]
        lookups[row["doc"]][key] = ordinal
    inputs = torch.zeros((len(docs), WIDTH), dtype=torch.long)
    labels = torch.full_like(inputs, -100)
    feature_ids = torch.full_like(inputs, -1)
    for i,doc in enumerate(docs):
        ids = base.encode(student, doc["text"])
        limit = len(ids)-1
        assert 0 < limit <= WIDTH
        inputs[i,:limit] = torch.tensor(ids[:-1])
        labels[i,:limit] = torch.tensor(ids[1:])
        prefix = b""
        for j,y in enumerate(ids[1:]):
            prefix += vocab[ids[j]][1]
            feature_ids[i,j] = lookups[i].get((prefix, y), -1)
    admitted = feature_ids[feature_ids.ge(0)]
    assert torch.equal(admitted.sort().values, torch.arange(len(records)))
    groups = [[i for i,doc in enumerate(docs) if doc["split"]=="train" and doc["language"]==lang] for lang in ("en","ko")]
    rng = torch.Generator().manual_seed(SEED)
    draws = torch.cat([torch.tensor(group)[torch.randint(len(group),(UPDATES,BATCH//2),generator=rng)]
                       for group in groups], dim=1)
    ce = int(labels[draws].ne(-100).sum())
    kd = int(feature_ids[draws].ge(0).sum())
    train_tokens = int(labels[draws.new_tensor(groups).flatten()].ne(-100).sum())
    assert train_tokens >= 2*ce and kd > 0
    receipt = dict(documents=docs, alignment=counts, train_ce_pool=train_tokens, draw_ce=ce, draw_kd=kd,
                   data_sha=base.state_sha((inputs,labels,feature_ids,draws)),
                   prefixes_sha=base.state_sha(records))
    return receipt,(inputs,labels,feature_ids,draws),records


def contract():
    source = base.OUT/"profile.json"
    mapping = base.OUT/"mapping.json"
    evidence = base.OUT/"report.json"
    prior = read(source)
    assert prior["pins"] == base.source_pins() and prior["mapping_sha256"] == sha(mapping)
    assert read(evidence)["source_preserved"] and sha(frozen.prior.PARENT)==frozen.PARENT_SHA
    return dict(tag=TAG, pins={s:sha(base.ROOT/s) for s in SOURCES}, previous_profile_sha=sha(source),
                previous_report_sha=sha(evidence), mapping_sha=sha(mapping), parent_sha=frozen.PARENT_SHA,
                teacher_fp32_head_sha256=prior["teacher_fp32_head_sha256"], updates=UPDATES, batch=BATCH,
                width=WIDTH, lr=LR, alpha=ALPHA, temperature=T, checkpoint_writes=0, approval="WIP176")


def initialize():
    torch.manual_seed(SEED)
    cfg, weights, step = frozen.prior.load_parent(torch)
    assert step == 2289
    cfg.train_repeat = 2.0
    model = TiedMLPTransformer(cfg)
    model.load_state_dict(weights, strict=True)
    model.set_anneal(1.)
    assert cfg.grad_checkpoint and len(model.visit_schedule())==28 and cfg.vocab_size==32768
    return model.cuda()


@torch.no_grad()
def evaluate(model, xs, ys, docs, held):
    model.eval()
    model.freeze_quant()
    output = []
    try:
        for block in held.split(8):
            with torch.autocast("cuda", dtype=torch.bfloat16):
                logits = model(xs[block])
                y = ys[block]
                losses = F.cross_entropy(logits.flatten(0,1),y.flatten(),reduction="none").reshape_as(y)
            correct = logits.argmax(-1).eq(y).sum(1)
            counts = y.ne(-100).sum(1)
            for index,n,c,loss in zip(block.tolist(),counts.tolist(),correct.tolist(),losses.sum(1).tolist(),strict=True):
                d = docs[index]
                output.append(dict(id=d["id"], language=d["language"], family=d["family"], count=n, correct=c, sum_nll=loss))
    finally:
        model.clear_quant()
        model.train()
    summary = {}
    for lang in ("en","ko"):
        rows = [r for r in output if r["language"] == lang]
        n = sum(r["count"] for r in rows)
        summary[lang] = dict(nll=sum(r["sum_nll"] for r in rows)/n, count=n,
                             correct=sum(r["correct"] for r in rows))
    return dict(summary=summary, documents=output)


def train(arm, alpha, docs, arrays, head, teacher_features):
    xs, ys, feature_ids, draws = arrays
    held = torch.tensor([i for i,d in enumerate(docs) if d["split"]=="held"], device="cuda")
    model = initialize()
    initial = base.state_sha(model.state_dict())
    route = build_experimental_optimizers(model, "muon_matched", lr=LR, matrix_lr_mult=1.)
    optimizers = (route.matrix, route.adamw)
    keep_active_groups(optimizers)
    rates = [[g["lr"] for g in opt.param_groups] for opt in optimizers]
    scores = {0:evaluate(model,xs,ys,docs,held)}
    history = []
    torch.cuda.reset_peak_memory_stats()
    for index, doc_ids in enumerate(draws,1):
        if (OUT/"STOP").exists() or datetime.now(base.CUTOFF.tzinfo) >= base.CUTOFF:
            raise RuntimeError("owned STOP or deadline")
        factor = lr_factor(index-1,4,UPDATES,"cosine")
        for optimizer, rate in zip(optimizers,rates,strict=True):
            for group, v in zip(optimizer.param_groups,rate,strict=True):
                group["lr"] = v*factor
        start = perf_counter()
        with torch.autocast("cuda",dtype=torch.bfloat16):
            logits = model(xs[doc_ids])
            y = ys[doc_ids]
            ce = F.cross_entropy(logits.flatten(0,1),y.flatten())
        targets = feature_ids[doc_ids]
        eligible = targets.ge(0)
        kd = None
        if alpha:
            with torch.no_grad():
                teacher = F.linear(teacher_features[targets[eligible]],head)
            kd = _kd_kl(logits[eligible],teacher,T,fp32=True)
        loss = ce if kd is None else ce+alpha*kd
        loss.backward()
        grad = torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
        for optimizer in optimizers:
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
        model.clear_quant()
        torch.cuda.synchronize()
        history.append(dict(step=index, ce=float(ce.detach()), kl=float(kd.detach()) if kd is not None else None,
                            objective=float(loss.detach()), grad=float(grad), ce_tokens=int(y.ne(-100).sum()),
                            kd_tokens=int(eligible.sum()) if kd is not None else 0, seconds=perf_counter()-start))
        if index in EVAL_STEPS:
            scores[index] = evaluate(model,xs,ys,docs,held)
            print("P109_ACTUAL_PREFIX_KD_STEP",arm,index,history[-1]["ce"],history[-1]["kl"],flush=True)
    peak = torch.cuda.max_memory_allocated()
    return dict(arm=arm, initial=initial, final=base.state_sha(model.state_dict()),
                optimizers=[base.state_sha(o.state_dict()) for o in optimizers], held=scores, history=history,
                peak_allocated=peak, median_sec=median(r["seconds"] for r in history[1:]))


def actual(profile, arrays, rows):
    print("P109_ACTUAL_PREFIX_KD_ACTIVE",os.getpid(),flush=True)
    write(OUT/"active.json",dict(pid=os.getpid(),tag=TAG))
    assert base.idle() and torch.cuda.device_count()==1 and torch.cuda.mem_get_info()[0]>=10*(1<<30)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    device_path = OUT/"device_100ms.csv"
    with device_path.open("xb") as stream:
        monitor = subprocess.Popen((*base.DEVICE,f"--loop-ms={base.INTERVAL_MS}"),stdout=stream)
        try:
            head, features, capture = base.extract_features(
                dict(profile["sources"],targets=rows), read(base.OUT/"mapping.json"))
            torch.cuda.empty_cache()
            gpu_arrays = tuple(x.cuda() for x in arrays)
            with sdpa_kernel(SDPBackend.MATH):
                arms = {}
                for name,alpha in ARMS.items():
                    arms[name] = train(name,alpha,profile["data"]["documents"],gpu_arrays,head,features)
                    torch.cuda.empty_cache()
        finally:
            if monitor.poll() is None:
                monitor.terminate()
            monitor.wait(timeout=8)
    samples = base.read_samples(device_path)
    peak = max(samples,key=lambda row:row["occupied_mib"]) if samples else None
    common = arms["ce"]["initial"]==arms["prefix_kd"]["initial"] and arms["ce"]["history"][0]["ce"]==arms["prefix_kd"]["history"][0]["ce"]
    same = profile["sources"]==contract()
    assert all(sum(r["ce_tokens"] for r in a["history"]) == profile["data"]["draw_ce"] for a in arms.values())
    assert sum(r["kd_tokens"] for r in arms["prefix_kd"]["history"])==profile["data"]["draw_kd"]
    write(OUT/"report.json",dict(arms=arms,teacher=capture,same_initial_and_first_ce=common,
          source_preserved=same,device_peak=peak,device_samples=len(samples),device_sha256=sha(device_path),
          checkpoint_writes=0))
    return 0 if common and same and peak else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("prepare","run"))
    phase = parser.parse_args().phase
    assert os.environ.get("CUDA_VISIBLE_DEVICES")==("" if phase=="prepare" else "0")
    assert datetime.now(base.CUTOFF.tzinfo)+timedelta(seconds=620)<base.CUTOFF
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    receipt,arrays,rows = data_and_receipt()
    profile = dict(sources=contract(),data=receipt)
    if phase=="prepare":
        assert not torch.cuda.is_initialized()
        OUT.mkdir(exist_ok=False)
        write(OUT/"profile.json",profile)
        print("P109_ACTUAL_PREFIX_KD_CPU",receipt["train_ce_pool"],receipt["draw_ce"],receipt["draw_kd"],flush=True)
        return 0
    assert os.environ.get("CUBLAS_WORKSPACE_CONFIG")==":4096:8"
    assert profile==read(OUT/"profile.json")
    return actual(profile,arrays,rows)


if __name__=="__main__":
    sys.exit(main())
