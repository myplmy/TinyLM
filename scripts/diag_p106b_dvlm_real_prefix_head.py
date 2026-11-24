"""Train a real Qwen-backed head in the native P109 vocabulary using exact prefixes."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter

from tokenizers import Tokenizer
import torch
from torch.nn import functional as F

from scripts import diag_p106b_dvlm_head_byte_values as old
from scripts import p106b_dvlm_head as head
from scripts import p106b_dvlm_head_bytes as raw_bytes
from scripts.diag_p102a_g4_full_delta_train import state_sha
from scripts.diag_p102a_g4_joint_ce_kl_batch8 import DEVICE, INTERVAL_MS, read_samples
from scripts.diag_p102a_g4_recompute_shapes import idle


ROOT, SHA, read, write = old.ROOT, old.digest, old.read, old.write
TAG = "p106b_dvlm_byte_head_real_prefix_v1_20261119"
OUT = ROOT / "test_result/evidence" / TAG
STUDENT = ROOT / "data_cache/tok-ko-en-32768.json"
CHAT32 = ROOT / "data_cache/tok-ko-en-32768-chat32.json"
TEACHER = old.WEIGHT.parent
CUTOFF = datetime.fromisoformat("2026-11-19T16:58:00+09:00")
BATCH, UPDATES, LR, SEED = 16, 64, 3e-4, 602
STAMPS = (0, 8, 32, UPDATES)
SOURCES = ("scripts/diag_p106b_dvlm_real_prefix_head.py", "scripts/p106b_dvlm_head.py",
           "scripts/p106b_dvlm_head_bytes.py", "scripts/p106b_alm_bytes.py",
           "scripts/diag_p106b_dvlm_head_byte_values.py", "scripts/diag_p102a_g4_full_delta_train.py",
           "scripts/diag_p102a_g4_joint_ce_kl_batch8.py")


TRAIN_EN = (
    "At the hillside workshop, technician {i} counts three copper washers before closing the wooden drawer. The larger washer goes beside the blue ruler, and the smallest one stays in the tray.",
    "Garden plot {i} receives two cups of water before sunrise. The caretaker moves the empty can beneath the porch and writes the amount on a slate.",
    "Recipe card {i} begins with a spoon of flour and a slice of pear. Stir the batter twice and set the shallow pan beside the warm oven.",
)
TRAIN_KO = (
    "작업대 {i}번에서 구리 와셔 세 개를 세어 나무 서랍을 닫는다. 큰 와셔는 파란 자 곁에 놓고 가장 작은 것은 쟁반에 둔다.",
    "텃밭 {i}번에는 날이 밝기 전에 물 두 컵을 준다. 텅 빈 물뿌리개는 처마 밑으로 옮기고 물의 양을 칠판에 적는다.",
    "조리 카드 {i}번에는 밀가루 한 숟갈과 배 한 조각이 필요하다고 적혀 있다. 반죽을 두 번 저은 다음 얕은 팬을 따뜻한 오븐 옆에 둔다.",
)
HELD_EN = (
    "The west terminal sends shuttle {i} across the river after the morning ferry returns. Passengers can leave their luggage on the upper shelf during the crossing.",
    "Borrower {i} put a bookmark in the atlas and returned it to the reading room. A notice on the desk explained how to renew a loan on the following Tuesday.",
    "An aquarium display identified tank {i} as the place where several fish gathered near the rock. A visitor sketched one of them on the back of an old ticket.",
)
HELD_KO = (
    "서쪽 정류장의 {i}번 버스는 아침 나룻배가 돌아온 뒤 강 건너편으로 떠난다. 짐은 건너는 동안 선반 위에 올려 둘 수 있다.",
    "도서관 이용자 {i}번은 지도책에 책갈피를 끼우고 열람실에 반납했다. 안내문에는 다음 화요일에도 대출을 연장하는 방법이 적혀 있다.",
    "수족관의 {i}번 물통에서는 물고기 몇 마리가 바위 가까이에 모여 있었다. 관람객 한 사람이 입장권 뒷면에 그 모습을 그렸다.",
)


def documents():
    groups = (("train", "en", TRAIN_EN, 48), ("train", "ko", TRAIN_KO, 48),
              ("held", "en", HELD_EN, 12), ("held", "ko", HELD_KO, 12))
    for split, language, bank, count in groups:
        for index in range(count):
            yield dict(id=f"{split}_{language}_{index:02d}", split=split, language=language,
                       text=bank[index % len(bank)].format(i=index + (1 if split == "train" else 301)))


def encode(tokenizer, text):
    return tokenizer.encode(text, add_special_tokens=False).ids


def mapping_for(student, teacher, student_raw, teacher_raw):
    strict = head.initialization_map(
        student_raw, teacher_raw, decode_student=lambda ids: student.decode(ids, skip_special_tokens=False),
        encode_teacher=lambda text: encode(teacher, text),
        decode_teacher=lambda ids: teacher.decode(ids, skip_special_tokens=False))
    extended = raw_bytes.extend_invalid_utf8(
        strict, student_raw, teacher_raw, bpe_tokenize=lambda value: [tk.id for tk in teacher.model.tokenize(value)])
    assert extended["complete"] and len(extended["records"]) == 32768
    prior = old.matrix()
    chat_vocab = head.native_vocabulary(read(CHAT32))
    lookup = {chat_vocab[row["student_id"]]: row["teacher_ids"] for row in prior["records"]}
    native = head.native_vocabulary(student_raw)
    matched = [row["teacher_ids"] == lookup[native[row["student_id"]]] for row in extended["records"]
               if native[row["student_id"]] in lookup]
    assert matched and all(matched)
    return {key: extended[key] for key in ("complete", "student_vocab_size", "records", "counts")}, len(matched)


def corpus(student, teacher, vocab):
    docs, targets, counts = [], [], defaultdict(Counter)
    for doc_index, doc in enumerate(documents()):
        text = doc["text"]
        teacher_ids = encode(teacher, text)
        student_ids = encode(student, text)
        pieces = [vocab[token] for token in student_ids]
        assert all(kind == "ORDINARY_BYTES" for kind, _, _ in pieces)
        assert b"".join(value for _, value, _ in pieces) == text.encode("utf-8")
        doc["teacher_ids"] = teacher_ids
        stats = counts[f'{doc["split"]}_{doc["language"]}']
        stats["empty_prefix"] += 1
        prefix = b""
        for index, target in enumerate(student_ids[1:]):
            prefix += pieces[index][1]
            try:
                prompt = prefix.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                stats["incomplete_utf8"] += 1
                continue
            query = encode(teacher, prompt)
            if not query or teacher.decode(query, skip_special_tokens=False) != prompt:
                stats["teacher_roundtrip_hold"] += 1
                continue
            stable = teacher_ids[:len(query)] == query
            stats["accepted"] += 1
            stats["stable_full_prefix"] += int(stable)
            targets.append(dict(doc=doc_index, teacher_prefix=query, target=target, stable=stable))
        docs.append(doc)
    assert len({doc["text"] for doc in docs}) == len(docs)
    assert sum(row["accepted"] for group,row in counts.items() if group.startswith("train")) >= 2 * BATCH * UPDATES
    assert all(row["accepted"] > 0 for row in counts.values())
    return docs, targets, dict(counts)


def source_pins():
    paths = (STUDENT, CHAT32, TEACHER / "tokenizer.json", old.WEIGHT, TEACHER / "config.json",
             old.BASE / "actual/report.json", old.BASE / "profile.json", old.MAPPING / "actual/report.json")
    return {str(p.relative_to(ROOT)): SHA(p) for p in paths} | {path: SHA(ROOT/path) for path in SOURCES}


def prepare():
    hashes = source_pins()
    witness = read(old.NATIVE / "profile.json")
    assert hashes[str(old.WEIGHT.relative_to(ROOT))] == witness["assets"]["files"]["model.safetensors"]["sha256"]
    assert read(old.BASE/"actual/report.json")["returncode"] == 0
    student_raw, teacher_raw = read(STUDENT), read(TEACHER/"tokenizer.json")
    student, teacher = (Tokenizer.from_file(str(p)) for p in (STUDENT, TEACHER/"tokenizer.json"))
    mapping, reused = mapping_for(student, teacher, student_raw, teacher_raw)
    docs, targets, counts = corpus(student, teacher, head.native_vocabulary(student_raw))
    assert not torch.cuda.is_initialized()
    OUT.mkdir(exist_ok=False)
    write(OUT/"mapping.json", mapping)
    write(OUT/"profile.json", dict(tag=TAG, pins=hashes, mapping_sha256=SHA(OUT/"mapping.json"),
          reused_byte_rows=reused, docs=docs, targets=targets, counts=counts,
          teacher_fp32_head_sha256=read(old.BASE/"profile.json")["expected_FP32_head_SHA256"],
          batch=BATCH, updates=UPDATES, seed=SEED, lr=LR, checkpoint_writes=0))
    print("DVLM_REAL_PREFIX_READY", counts, "same native pieces", reused, flush=True)
    return 0


@torch.no_grad()
def extract_features(profile, mapping):
    from transformers import AutoModelForCausalLM

    teacher, loading = AutoModelForCausalLM.from_pretrained(
        str(TEACHER), local_files_only=True, trust_remote_code=False, use_safetensors=True,
        dtype=torch.float32, attn_implementation="eager", use_cache=False, output_loading_info=True)
    assert not any(loading.get(k) for k in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs"))
    assert teacher.config.model_type == "qwen3" and not teacher.config.use_cache
    teacher.eval().requires_grad_(False)
    weights = teacher.get_output_embeddings().weight.detach()
    assert weights.shape == (151936, 1024) and weights.dtype == torch.float32
    assert weights.data_ptr() == teacher.get_input_embeddings().weight.data_ptr()
    assert old.tensor_sha(torch, weights) == profile["teacher_fp32_head_sha256"]
    student_head = head.initialize_head(torch, weights, mapping).detach().cuda()
    del weights
    teacher.cuda()
    parameter_versions = {k:w._version for k,w in teacher.named_parameters()}
    groups = defaultdict(list)
    order = list(dict.fromkeys(tuple(row["teacher_prefix"]) for row in profile["targets"]))
    for index, prefix in enumerate(order):
        groups[len(prefix)].append((index, prefix))
    features = torch.empty((len(order), 1024), dtype=torch.float32, device="cuda")
    start = perf_counter()
    count = 0
    for _, rows in sorted(groups.items()):
        for offset in range(0, len(rows), 32):
            sub = rows[offset:offset+32]
            indices, query = zip(*sub, strict=True)
            ids = torch.tensor(query, dtype=torch.long, device="cuda")
            out = teacher.model(input_ids=ids, use_cache=False)
            assert out.past_key_values is None
            features[list(indices)] = out.last_hidden_state[:, -1]
            count += 1
        if len(rows) >= 32:
            print("DVLM_REAL_PREFIX_TEACHER", len(rows[0][1]), count, flush=True)
    torch.cuda.synchronize()
    assert torch.isfinite(features).all()
    assert parameter_versions == {k:w._version for k,w in teacher.named_parameters()}
    by_prefix = {prefix:index for index,prefix in enumerate(order)}
    indices = [by_prefix[tuple(row["teacher_prefix"])] for row in profile["targets"]]
    return student_head, features[indices], dict(unique_prefixes=len(order), forward_batches=count,
              seconds=perf_counter()-start, teacher_frozen=True)


@torch.no_grad()
def evaluate(weights, features, labels, partitions):
    result = {}
    for name, ids in partitions.items():
        correct, total = 0, 0.
        for part in ids.split(64):
            scores = F.linear(features[part], weights)
            target = labels[part]
            total += float(F.cross_entropy(scores, target, reduction="sum"))
            correct += int(scores.argmax(1).eq(target).sum())
        result[name] = dict(nll=total/len(ids), correct=correct, count=len(ids))
    return result


def head_arm(name, initial, features, labels, partitions, batches):
    weight = torch.nn.Parameter(initial.clone())
    optimizer = torch.optim.AdamW((weight,), lr=LR, weight_decay=0.)
    scores = {0:evaluate(weight, features, labels, partitions)}
    losses = []
    before = state_sha(weight)
    for step, ids in enumerate(batches, 1):
        if (OUT/"STOP").exists() or datetime.now(CUTOFF.tzinfo) >= CUTOFF:
            raise RuntimeError("owned stop or deadline")
        optimizer.zero_grad(set_to_none=True)
        loss = F.cross_entropy(F.linear(features[ids], weight), labels[ids])
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach()))
        if step in STAMPS:
            scores[step] = evaluate(weight, features, labels, partitions)
            print("DVLM_REAL_PREFIX_HEAD_UPDATE", name, step, losses[-1], flush=True)
    after = state_sha(weight)
    assert before != after and all(torch.isfinite(torch.tensor(losses)))
    return dict(held=scores, losses=losses, updates=UPDATES, targets=UPDATES*BATCH,
                head_before=before, head_after=after, opt=state_sha(optimizer.state_dict()))


def actual(profile, mapping):
    print("DVLM_REAL_PREFIX_ACTIVE", os.getpid(), flush=True)
    write(OUT/"active.json", dict(pid=os.getpid(), tag=TAG))
    assert idle() and torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 10*(1 << 30)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    torch.cuda.reset_peak_memory_stats()
    samples_path = OUT/"device_100ms.csv"
    with samples_path.open("xb") as stream:
        observer = subprocess.Popen((*DEVICE, f"--loop-ms={INTERVAL_MS}"), stdout=stream)
        try:
            init, features, extraction = extract_features(profile, mapping)
            torch.cuda.empty_cache()
            groups = defaultdict(list)
            train = []
            for index, row in enumerate(profile["targets"]):
                doc = profile["docs"][row["doc"]]
                if doc["split"] == "train":
                    train.append(index)
                else:
                    groups[doc["language"]].append(index)
            partitions = {name:torch.tensor(ids, device="cuda") for name,ids in groups.items()}
            train = torch.tensor(train, device="cuda")
            labels = torch.tensor([row["target"] for row in profile["targets"]], device="cuda")
            gen = torch.Generator().manual_seed(SEED)
            draws = train[torch.randint(len(train), (UPDATES, BATCH), generator=gen).cuda()]
            permutation = torch.randperm(len(init), generator=gen).cuda()
            arms = {"byte_mean":head_arm("byte_mean", init, features, labels, partitions, draws),
                    "permuted":head_arm("permuted", init[permutation], features, labels, partitions, draws)}
            torch.cuda.synchronize()
        finally:
            if observer.poll() is None:
                observer.terminate()
            observer.wait(timeout=8)
    samples = read_samples(samples_path)
    peak = max(samples, key=lambda row:row["occupied_mib"]) if samples else None
    same = profile["pins"] == source_pins() and profile["mapping_sha256"] == SHA(OUT/"mapping.json")
    write(OUT/"report.json", dict(arms=arms, extraction=extraction, shared_draw_sha256=state_sha(draws),
          permutation_sha256=state_sha(permutation), counts=profile["counts"], profile_sha256=SHA(OUT/"profile.json"),
          source_preserved=same, checkpoint_writes=0, student_model_training=0, teacher_forwards=extraction["forward_batches"],
          device_samples=len(samples), device_peak=peak, device_sha256=SHA(samples_path)))
    return 0 if same and peak else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run"))
    phase = parser.parse_args().phase
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ("" if phase == "prepare" else "0")
    assert datetime.now(CUTOFF.tzinfo) + timedelta(seconds=440) < CUTOFF
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    if phase == "prepare":
        return prepare()
    p = read(OUT/"profile.json")
    assert p["pins"] == source_pins() and p["mapping_sha256"] == SHA(OUT/"mapping.json")
    assert os.environ.get("CUBLAS_WORKSPACE_CONFIG") == ":4096:8"
    return actual(p, read(OUT/"mapping.json"))


if __name__ == "__main__":
    sys.exit(main())
