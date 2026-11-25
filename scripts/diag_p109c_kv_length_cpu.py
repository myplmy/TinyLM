"""Compare storage dtype and context length on frozen P109C v3 requests."""

from argparse import ArgumentParser
from datetime import datetime
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
from time import monotonic

from scripts import diag_p109c_v3_rule_flip as reference
from scripts import eval_p109b_first_use as first
from scripts import eval_p109c_completed as completed
from scripts import interactive_research_infer as manual
from scripts import p106b_final_holdout as final
from scripts import p106b_shards
from scripts import run_p109c_scratch330 as native
from tinylm.chat.serialize import serialize


TAG = "p109c_v3_kv_length_cpu_20261125"
RECORD = reference.EVIDENCE / TAG
PROFILE = reference.EVIDENCE / f"{TAG}_profile.json"
ARCHIVE = reference.EVIDENCE / "p109c_integrated_scratch_v3_common_eval_v1_20261124"
MANIFEST = ARCHIVE / "final200_answers_shards_manifest.json"
AUDIT = completed.ROOT / "handoff/audit/P109C_INTEGRATED_V3_FINAL200_SEMANTIC_20261124.json"
ARCHIVE_SHA = "DBB20D6EACA68CD3BDA2418ADF8E1A55751C2C206236F662A7D9D2D00FB2D845"
MAX_NEW, CHUNK = 96, 128
DEADLINE = datetime.fromisoformat("2026-11-25T13:00:00+09:00")
ARMS = {
    "bare_fp32": (1024, "fp32", "bare"),
    "short_fp32": (1024, "fp32", "short"),
    "long_fp32": (2048, "fp32", "long"),
    "long_bf16": (2048, "bf16", "long"),
}
TOPICS = ("paint supply", "parking roster", "garden tools", "shelf inventory", "window covers",
          "tile delivery", "camera stand", "desk lamp", "door hinge", "plant nursery")


def deadline_check(cutoff):
    now = datetime.now().astimezone()
    if not now < cutoff <= DEADLINE or os.sched_getaffinity(0) != {14}:
        raise ValueError("the authorized CPU core or deadline differs")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("CUDA must be hidden in the CPU-only subprocess")


def source_pins():
    paths = set(completed.SOURCE_FILES) | {
        "scripts/diag_p109c_kv_length_cpu.py",
        "scripts/diag_p109c_v3_rule_flip.py",
        "scripts/interactive_research_infer.py",
        "scripts/p106b_shards.py",
        str(MANIFEST.relative_to(completed.ROOT)),
        str(AUDIT.relative_to(completed.ROOT)),
    }
    return {name: reference.file_sha(completed.ROOT / name) for name in sorted(paths)}


def encode(tokenizer, question):
    prompt = serialize({"messages": manual.prompt_messages(question)}, "chatml", add_generation_prompt=True)
    return tokenizer.encode(prompt).ids


def padded(tokenizer, question, language, target):
    if language == "ko":
        intro = "아래 보관 메모는 뒤의 실제 과제와 관계없습니다.\n"
        marker = "\n실제 과제\n"
    else:
        intro = "The following archived notes are unrelated to the task below.\n"
        marker = "\nActual task\n"
    notes = []
    for index in range(1, 512):
        topic = TOPICS[(index - 1) % len(TOPICS)]
        notes.append(f"Archive entry {index} records an inventory review of {topic} for room {index + 100}.\n")
        question_with_notes = intro + "".join(notes) + marker + question
        ids = encode(tokenizer, question_with_notes)
        if len(ids) >= target:
            if len(ids) > target + 32:
                raise ValueError("the archived request could not fit the predeclared band")
            return ids
    raise ValueError("the fixed background sequence did not fill the requested band")


def cases(tokenizer):
    manifest = completed.read_json(MANIFEST)
    if manifest["concat_sha256"] != ARCHIVE_SHA or manifest["rows"] != 200:
        raise ValueError("the admitted FINAL200 archive differs")
    p106b_shards.verify(ARCHIVE, manifest)
    archived = []
    for shard in manifest["shards"]:
        archived.extend(json.loads(line) for line in (ARCHIVE / shard["path"]).read_bytes().splitlines())
    audit = completed.read_json(AUDIT)["semantic_true_ids"]
    selected = []
    for language, output_count in (("ko", 1), ("en", 3)):
        ranked = sorted(
            (row for row in archived if row["language"] == language
             and row["metadata"]["finish_reason"] == "STOP_SEQUENCE"),
            key=lambda row: (-row["metadata"]["content_tokens"], row["id"]),
        )
        long = [row for row in ranked if row["metadata"]["content_tokens"] >= 12][:output_count]
        accept = set(audit[language]["correct"])
        exact = [row for row in ranked if row["id"] in accept and row["reference_match"] is True][:2]
        distinct = {row["id"] for row in long + exact}
        if len(long) != output_count or len(exact) != 2 or len(distinct) != len(long + exact):
            raise ValueError("the archived output and exact-match strata differ")
        for stratum, rows in (("long_output", long), ("exact_guard", exact)):
            for row in rows:
                bare = encode(tokenizer, row["prompt"])
                short = padded(tokenizer, row["prompt"], language, 900)
                long_ids = padded(tokenizer, row["prompt"], language, len(short) * 2 - 56)
                if len(short) + MAX_NEW > 1024 or len(long_ids) + MAX_NEW > 2048:
                    raise ValueError("the request would clip before reaching the fixed output cap")
                selected.append(dict(
                    id=row["id"], language=language, stratum=stratum, reference=row["reference"],
                    match_rule=row["match_rule"], original=row["metadata"],
                    original_reference_match=row["reference_match"],
                    inputs=dict(bare=bare, short=short, long=long_ids),
                ))
    return selected


def seal():
    tokenizer = completed.load_tokenizer()
    body = reference.checkpoint()
    profile = dict(tag=TAG, arms=ARMS, cases=cases(tokenizer), source_sha256=source_pins(),
                   checkpoint=str(body.relative_to(completed.ROOT)), checkpoint_sha256=reference.CHECKPOINT_SHA256,
                   max_new=MAX_NEW, chunk=CHUNK, torch_threads=1, cpu_affinity=[14],
                   quality="Same-input long fp32 versus BF16; separate strict guards and substantive output length.",
                   memory="Logical retained tensors, per-request VmHWM, and whole cold child VmHWM.")
    native.publish(PROFILE, profile)
    print(f"SEALED {PROFILE} {reference.file_sha(PROFILE)}", flush=True)


def admitted(stamp, cutoff):
    deadline_check(cutoff)
    if reference.file_sha(PROFILE) != stamp.upper():
        raise ValueError("the experiment profile cannot be authenticated")
    profile = completed.read_json(PROFILE)
    if profile["source_sha256"] != source_pins() or profile["checkpoint_sha256"] != reference.CHECKPOINT_SHA256:
        raise ValueError("the frozen source or body differs")
    return profile


def memory():
    fields = {}
    for line in Path("/proc/self/status").read_text().splitlines():
        key, _, value = line.partition(":")
        if key in ("VmRSS", "VmHWM"):
            fields[key] = int(value.split()[0]) * 1024
    return fields


def cache_size(bank):
    masses = [tensor.numel() * tensor.element_size()
              for pair in bank.values() if pair is not None for tensor in pair]
    return sum(masses)


def generate(model, torch, tokenizer, ids, cutoff):
    begin = monotonic()
    bank = None
    with torch.inference_mode():
        for start in range(0, len(ids), CHUNK):
            deadline_check(cutoff)
            batch = torch.tensor([ids[start:start + CHUNK]], dtype=torch.long)
            logits, bank = model(batch, past_kv=bank, use_cache=True, logits_last_only=True)
        prefill = monotonic() - begin
        prefill_bytes = cache_size(bank)
        tokens = []
        reason = "MAX_NEW"
        for step in range(MAX_NEW):
            deadline_check(cutoff)
            token = int(logits.reshape(-1).argmax().item())
            tokens.append(token)
            if token in (2, 4):
                reason = "EOS" if token == 2 else "STOP_SEQUENCE"
                break
            if step + 1 < MAX_NEW:
                batch = torch.tensor([[token]], dtype=torch.long)
                logits, bank = model(batch, past_kv=bank, use_cache=True, logits_last_only=True)
        retained = cache_size(bank)
    metadata = dict(generated_tokens=len(tokens), finish_reason=reason,
                    matched_stop_sequence=[4] if reason == "STOP_SEQUENCE" else None)
    text, metadata = manual.answer_from_tokens(tokenizer, ids, ids + tokens, metadata, MAX_NEW)
    return dict(answer=text, metadata=metadata, repeat_tail=first.repeat_tail(tokens),
                prefill_seconds=prefill, elapsed_seconds=monotonic() - begin,
                prefill_kv_bytes=prefill_bytes, final_kv_bytes=retained, process=memory())


def worker(arm, stamp, cutoff):
    import torch
    from tinylm.model.modules import build_rope

    profile = admitted(stamp, cutoff)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.manual_seed(1337)
    tokenizer = completed.load_tokenizer()
    body = reference.checkpoint()
    if str(body.relative_to(completed.ROOT)) != profile["checkpoint"]:
        raise ValueError("the body path differs")
    model = completed.load_model(body, 2942, "cpu")
    length, dtype, variant = ARMS[arm]
    if length > model.cfg.max_seq_len:
        cos, sin = build_rope(model.cfg.head_dim, length, model.cfg.rope_theta)
        base = model.cfg.max_seq_len
        if not (torch.equal(cos[:base], model.rope_cos) and torch.equal(sin[:base], model.rope_sin)):
            raise ValueError("increasing the RoPE table changed the existing frequencies")
        model.rope_cos, model.rope_sin = cos, sin
    model.cfg.max_seq_len, model.cfg.kv_dtype = length, dtype
    after_load = memory()
    with (RECORD / f"{arm}.jsonl").open("x", encoding="utf-8") as stream:
        for case in profile["cases"]:
            row = generate(model, torch, tokenizer, case["inputs"][variant], cutoff)
            row.update(id=case["id"], language=case["language"], stratum=case["stratum"],
                       reference_match=final.reference_match(row["answer"], case),
                       prior_ids_match=(row["metadata"]["generated_ids"] == case["original"]["generated_ids"]))
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            stream.flush()
            print(f"{arm} {case['id']} {row['metadata']['content_tokens']} tokens {row['elapsed_seconds']:.2f}s", flush=True)
    native.publish(RECORD / f"{arm}_process.json",
                   dict(after_load=after_load, final=memory(),
                        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024))


def summarize(profile, stamp):
    rows = {arm: [json.loads(line) for line in (RECORD / f"{arm}.jsonl").read_bytes().splitlines()]
            for arm in ARMS}
    outcomes = {}
    for arm, answers in rows.items():
        if [row["id"] for row in answers] != [row["id"] for row in profile["cases"]]:
            raise ValueError("the recorded case order or denominator differs")
        outcomes[arm] = dict(
            requests=len(answers),
            exact_guard_correct=sum(row["reference_match"] is True for row in answers if row["stratum"] == "exact_guard"),
            natural_output_ge12=sum(row["metadata"]["content_tokens"] >= 12
                                    and row["metadata"]["finish_reason"] in ("EOS", "STOP_SEQUENCE") for row in answers),
            correct_natural_output_ge12=sum(row["reference_match"] is True and row["metadata"]["content_tokens"] >= 12
                                            and row["metadata"]["finish_reason"] in ("EOS", "STOP_SEQUENCE") for row in answers),
            peak_cache_bytes=max(row["final_kv_bytes"] for row in answers),
            max_prompt_tokens=max(row["metadata"]["prompt_tokens"] for row in answers),
            process=completed.read_json(RECORD / f"{arm}_process.json"),
            total_request_seconds=sum(row["elapsed_seconds"] for row in answers),
            prior_ids_equal=sum(row["prior_ids_match"] for row in answers),
        )
    same = {
        arm: [a["id"] for a, b in zip(rows[arm], rows["long_bf16"], strict=True)
              if a["metadata"]["generated_ids"] == b["metadata"]["generated_ids"]]
        for arm in ("bare_fp32", "short_fp32", "long_fp32")
    }
    native.publish(RECORD / "report.json", dict(profile_sha256=stamp, outcomes=outcomes, bf16_matching_ids=same,
                                                  arms=ARMS, scope="Frozen eight-case development diagnosis."))


def run(stamp, cutoff):
    profile = admitted(stamp, cutoff)
    RECORD.mkdir()
    for arm in ARMS:
        deadline_check(cutoff)
        left = (cutoff - datetime.now().astimezone()).total_seconds()
        subprocess.run([sys.executable, "-B", "-u", "-m", "scripts.diag_p109c_kv_length_cpu",
                        "worker", "--arm", arm, "--profile-sha256", stamp, "--stop-by", cutoff.isoformat()],
                       check=True, timeout=left)
    summarize(profile, stamp)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("seal", "run", "worker"))
    parser.add_argument("--arm", choices=ARMS)
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.mode != "seal" and (not args.profile_sha256 or not args.stop_by):
        parser.error("run and worker require a frozen profile hash and deadline")
    if args.mode == "worker" and not args.arm:
        parser.error("worker requires one frozen arm")
    if args.mode == "seal":
        seal()
    elif args.mode == "run":
        run(args.profile_sha256, args.stop_by)
    else:
        worker(args.arm, args.profile_sha256, args.stop_by)


if __name__ == "__main__":
    main()
