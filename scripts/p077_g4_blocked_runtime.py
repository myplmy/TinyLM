"""Render the P077 block-cache variant of the existing compact G4 runtime."""

import argparse
from contextlib import ExitStack
from datetime import datetime, timedelta
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import signal
from statistics import median
import subprocess
import sys
from time import perf_counter
from unittest.mock import patch

import torch

from scripts import diag_p109_g4_bounded_prefill as bounded


SLOT_ROUTINES = b'''    void save_slot(int past, int count) {
        if (active_slot >= 0) cache.append_recent(active_slot, past, count, key.data(), value.data());
    }

    void begin_slot(const Layer& layer, int slot, int count, int past) {
        save_slot(past, count);
        active_slot = slot;
        active_past = past;
        for (int base = 0; base < count; base += Tile) {
            const int width = std::min(Tile, count - base);
            float* k = key.data() + base * Kv;
            const float* xb = x.data() + base * D;
            project(layer.k, xb, k, width, weight.data());
            project(layer.v, xb, value.data() + base * Kv, width, weight.data());
            for (int i = 0; i < width; ++i) {
                const int pos = (past + base + i) * (Head / 2);
                rotate(k + i * Kv, model.cos + pos, model.sin + pos, Kv);
            }
        }
    }

    void attention(const float* q, float* output, int end) {
        require(active_slot >= 0, "attention needs an active KV slot");
        attention_workspace.compute(cache, active_slot, active_past, q, key.data(), value.data(), end - active_past, output);
    }

'''


def replace_once(source, expected, replacement):
    if source.count(expected) != 1:
        raise ValueError(f"changed native G4 source anchor: {expected.decode()}")
    return source.replace(expected, replacement, 1)


def render(source, context=1024, int4_planes=0, prefill_query_batch=False, share_ffn_workspace=False):
    native = bounded.prior
    tiled = native.avx.tile
    source = replace_once(source, tiled.ORIGINAL, tiled.CHANGED)
    source = native.render(source)
    for expected, replacement in bounded.ANCHORS:
        if b"logits[token] = reduce(total);" in expected and expected not in source:
            output_dot = b"output_dot(hidden.data(), row, model.scales[token])"
            expected = expected.replace(b"reduce(total)", output_dot)
            replacement = replacement.replace(b"reduce(total)", output_dot)
        source = replace_once(source, expected, replacement)
    begin = source.index(b"    void begin_slot(")
    visit = source.index(b"    void visit(", begin)
    prior_slot = source[begin:visit]
    for contract in (b"cache.restore(slot, past, key.data(), value.data());",
                     b"cache.append(slot, past, count, key.data(), value.data());",
                     b"weighted_values(output + head * Head, value.data() + offset, score.data(), end, denom);"):
        if contract not in prior_slot:
            raise ValueError(f"changed grouped G4 runtime contract: {contract.decode()}")
    source = source[:begin] + SLOT_ROUTINES + source[visit:]
    for expected, replacement in (
        (b'#include "p109_g4_grouped_int8_cache.hpp"',
         b'#include "p109_g4_grouped_int8_cache.hpp"\n#include "p077_g4_grouped_attention.hpp"'),
        (b"key(capacity * Kv)", b"key(std::min(PrefillTokens, capacity) * Kv)"),
        (b"value(capacity * Kv), cache(capacity), logits(trace ? V : 0) {}",
         b"value(std::min(PrefillTokens, capacity) * Kv), cache(capacity), attention_workspace(capacity), logits(trace ? V : 0) {}"),
        (b"(x.capacity() + key.capacity() + value.capacity() + logits.capacity()) * sizeof(float)",
         b"(x.capacity() + key.capacity() + value.capacity() + logits.capacity()) * sizeof(float) + attention_workspace.score_bytes()"),
        (b"    GroupedInt8Cache cache;", b"    GroupedInt8Cache cache;\n    GroupedBlockAttention attention_workspace;\n"
         b"    int active_slot = -1, active_past = 0;"),
        (b"    std::array<float, Limit> score{};\n", b""),
        (b"        if (!emit) return 0;", b"        save_slot(past, count);\n        active_slot = -1;\n        if (!emit) return 0;"),
    ):
        source = replace_once(source, expected, replacement)
    if context == 2048:
        source = replace_once(source, b"Limit = 1024;", b"Limit = 2048;")
        source = replace_once(source, b'"TLMG4R4"', b'"TLMG4R5"')
    if int4_planes:
        if context != 2048 or int4_planes not in (1, 2, 3):
            raise ValueError("prefix INT4 is a 2048-only experiment")
        source = replace_once(source, b"cache(capacity), attention_workspace(capacity)",
                              f"cache(capacity, 1024, {int4_planes}), attention_workspace(capacity)".encode())
    if prefill_query_batch:
        source = replace_once(source,
            b"                attention(query.data() + t*D, attn.data() + t*D, pos + 1);\n            }",
            b"            }\n"
            b"            require(active_slot >= 0 && active_past == past, \"prefill attention needs the active KV prefix\");\n"
            b"            if (n == 1) {\n"
            b"                attention(query.data(), attn.data(), past + base + 1);\n"
            b"            } else {\n"
            b"                attention_workspace.compute_prefill(cache, active_slot, past, query.data(),\n"
            b"                    key.data(), value.data(), base + 1, n, attn.data());\n"
            b"            }")
    if share_ffn_workspace:
        source = reuse_ffn_workspace(source, prefill_query_batch)
    return source


def reuse_ffn_workspace(source, prefill_query_batch):
    begin = source.index(b"    void visit(")
    end = source.index(b"    uint32_t next(", begin)
    visit = source[begin:end]
    # The O projection consumes the attention result before the FFN up buffer is written.
    if not (0 <= visit.find(b"project(layer.o,") < visit.find(b"project(mlp.up,")):
        raise ValueError("attention and FFN workspaces no longer have disjoint lifetimes")
    visit = replace_once(visit, b"        for (int base = 0; base < count; base += Tile) {",
        b"        static_assert(F >= 2 * D);\n"
        b"        float* const query_buffer = up.data();\n"
        b"        float* const attention_buffer = up.data() + Tile * D;\n"
        b"        for (int base = 0; base < count; base += Tile) {")
    for old, buffer, count in ((b"query.data()", b"query_buffer", 3), (b"attn.data()", b"attention_buffer", 2)):
        if visit.count(old) != count + int(prefill_query_batch):
            raise ValueError("attention workspace call sites changed")
        visit = visit.replace(old, buffer)
    return replace_once(source[:begin] + visit + source[end:],
        b"std::array<float, Tile*D> norm{}, query{}, attn{}, projected{};",
        b"std::array<float, Tile*D> norm{}, projected{};")


def request(binary, assets, payload, out, reference, *, wrapper=None):
    native, base, text = bounded.prior, bounded.base, bounded.text
    with ExitStack() as stack:
        extra = tuple(base.memfile(f"p077_request_{i}") for i in range(3))
        for descriptor in extra:
            stack.callback(os.close, descriptor)
        fds = (*assets, *extra)
        cmd = [sys.executable, "-I", "-S", "-B", "-X", "utf8", str(wrapper or bounded.ROOT / text.SCRIPT),
               "encode", binary, *map(str, fds)]
        started = perf_counter()
        proc = subprocess.run(cmd, input=payload, pass_fds=fds, capture_output=True, timeout=150)
        seconds = perf_counter() - started
        if proc.returncode:
            print(proc.stderr.decode("utf-8", "replace"), file=sys.stderr)
            proc.check_returncode()
    result = json.loads(proc.stdout)
    base.WRITE(out, result)
    cache_bytes = reference["native"].get("kv_bytes",
        native.int8_capacity(len(result["encoding"]["ids"]) + text.GEN - 1))
    if (result["encoding"]["pid"] != result["native_pid"] or result["decoding"]["pid"] != result["native_pid"]
            or result["encoding"]["ids"] != reference["encoding"]["ids"]
            or result["native"]["model_bytes"] != reference["native"]["model_bytes"]
            or result["native"]["kv_bytes"] != cache_bytes):
        raise ValueError("the candidate request did not match the existing single-PID input and cache")
    return dict(seconds=seconds, scratch_bytes=result["native"]["scratch_bytes"], peak_rss=native.peak(result),
                kv_bytes=result["native"]["kv_bytes"],
                ids_equal=result["native"]["ids"] == reference["native"].get("ids"),
                text_equal=result["decoding"]["text"] == reference.get("decoding", {}).get("text"))


def extend_positions(input_fd, output_fd, model):
    from tinylm.model.modules import build_rope

    cfg = model.cfg
    prefix = 8 + (28 + 16 + 16) * 4 + cfg.vocab_size * (cfg.emb_rank + 4) + cfg.dim * cfg.emb_rank * 4
    table_bytes = 1024 * (cfg.head_dim // 2) * 4
    old_size = os.fstat(input_fd).st_size
    raw = os.pread(input_fd, old_size, 0)
    if raw[:8] != b"TLMG4R4" + bytes(1) or len(raw) != old_size:
        raise ValueError("the exact R4 payload is required for RoPE extension")
    cos, sin = build_rope(cfg.head_dim, 2048, cfg.rope_theta)
    pieces = [b"TLMG4R5" + bytes(1), raw[8:prefix]]
    for index, (existing, expanded) in enumerate(zip((model.rope_cos, model.rope_sin), (cos, sin), strict=True)):
        begin = prefix + index * table_bytes
        chosen = raw[begin:begin + table_bytes]
        if chosen != existing.numpy().tobytes() or not torch.isfinite(expanded).all():
            raise ValueError("the original RoPE bytes or new positions differ")
        pieces.extend((chosen, expanded[1024:].numpy().tobytes()))
    pieces.append(raw[prefix + 2 * table_bytes:])
    result = b"".join(pieces)
    if len(result) != old_size + 2 * table_bytes:
        raise ValueError("the extended position payload has an unexpected size")
    bounded.text.store(output_fd, result)
    deploy = bounded.base.prior.DEPLOY
    fcntl.fcntl(output_fd, deploy.F_ADD_SEALS, deploy.SEALS)
    return dict(artifact_bytes=len(result), artifact_sha256=sha256(result).hexdigest().upper(),
                original_positions=1024, total_positions=2048, position_bytes_added=2 * table_bytes)


def long_prompt(tokenizer, language, *, short=False):
    if language == "korean":
        lead, clue, question, answer = ("업무 기록입니다.\n", "기록의 암호는 등대입니다.\n",
                                        "\n질문. 기록에 적힌 암호는 무엇인가요?\n답.", "등대")
    else:
        lead, clue, question, answer = ("Archived notes." + ("" if short else " ." * 1200),
            "\nThe code word in this note is elm.\n", "\nQuestion. What is the code word in the note?\nAnswer.", "elm")
    if short:
        prompt = lead + clue + question
        encoded = tokenizer.encode(prompt)
        clue_at = next(i for i, (_, end) in enumerate(encoded.offsets) if end > len(lead))
        return prompt, encoded.ids, clue_at, answer
    target = 2041
    remainder = target - len(tokenizer.encode(lead + clue + question).ids)
    for count in range(max(0, remainder - 12), remainder + 13):
        prompt = lead + clue + " ." * count + question
        encoded = tokenizer.encode(prompt)
        if len(encoded.ids) == target:
            clue_at = next(i for i, (_, end) in enumerate(encoded.offsets) if end > len(lead))
            return prompt, encoded.ids, clue_at, answer
    raise ValueError("the authored long request must have exactly 2041 tokens")


@torch.inference_mode()
def verify_runtime(out, context=1024, short_control_of=None, int4_planes=0, prefill_query_batch=False,
                   share_ffn_workspace=False):
    deadline = datetime.fromisoformat("2026-11-21T13:00:00+09:00")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or datetime.now(deadline.tzinfo) + timedelta(minutes=5) >= deadline:
        raise RuntimeError("the CPU-only P077 diagnostic needs sufficient authorized time")
    base, text, token = bounded.base, bounded.text, bounded.token
    before = base.READ(bounded.OUT / "profile.json")
    archive = base.READ(bounded.OUT / "report.json")
    if archive["profile_sha256"] != base.SHA(bounded.OUT / "profile.json"):
        raise ValueError("the bounded G4 reference report changed")
    text_profile = base.READ(text.OUT / "profile.json")
    text_report = base.READ(text.OUT / "report.json")
    if text_report["profile_sha256"] != base.SHA(text.OUT / "profile.json"):
        raise ValueError("the original text request reference changed")
    codec_profile = base.READ(token.OUT / "profile.json")
    codec_path = token.OUT / "report.json"
    tokenizer_source = token.TOK.read_bytes()
    if (sha256(tokenizer_source).hexdigest().upper() != codec_profile["source_sha256"]
            or base.SHA(codec_path) != text_profile["tokenizer_reference"]):
        raise ValueError("the original tokenizer identity changed")
    codec = token.wire(json.loads(tokenizer_source))
    if [sha256(blob).hexdigest().upper() for blob in codec] != [row["sha256"] for row in codec_profile["files"]["split_model"]]:
        raise ValueError("the split tokenizer bytes differ")
    candidate = text_profile["pins"]["candidate"]
    embedding = base.prior.embedding
    embedding_path = embedding.OUT / "profile.json"
    embedding_profile = base.READ(embedding_path)
    current_pins = embedding.pins()
    if (candidate["previous_profile"] != base.SHA(embedding_path)
            or candidate["previous_cpu"] != base.SHA(embedding.OUT / "cpu_report.json")
            or candidate["table_sha256"] != embedding_profile["table_sha256"]["int8"]
            or any(embedding_profile[key] != value for key, value in current_pins.items() if key != "sources")):
        raise ValueError("the archived G4 input assets differ")
    changed_sources = {name: value for name, value in current_pins["sources"].items()
                       if embedding_profile["sources"].get(name) != value}
    if set(changed_sources) - {"tinylm/data/prepare.py", "tinylm/model/transformer.py"}:
        raise ValueError("unexpected source changes when reconstructing the frozen G4 model")
    os.sched_setaffinity(0, {before["cpu"]})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    out.mkdir(exist_ok=False)

    def time_limit(_signal, _frame):
        raise TimeoutError("P077 native request cap reached")

    signal.signal(signal.SIGALRM, time_limit)
    signal.alarm(270)
    source = render((bounded.ROOT / base.CPP).read_bytes(), context, int4_planes, prefill_query_batch,
                    share_ffn_workspace)
    extended_model = None
    with (patch.object(bounded, "OUT", out), ExitStack() as stack):
        prior_control = None
        if short_control_of is None:
            binary = bounded.build(source, caps=(64,))[64][1]
        else:
            prior_control = base.READ(short_control_of / "report.json")
            compiler = base.READ(short_control_of / "compiler.json")
            artifact = compiler["binaries"]["64"][1]
            binary = Path(artifact["path"])
            if (context != 2048 or prior_control["context_limit"] != context
                    or compiler["source_sha256"] != sha256(source).hexdigest().upper()
                    or not binary.is_relative_to(Path("/tmp")) or base.SHA(binary) != artifact["sha256"]):
                raise ValueError("the exact completed 2048 binary is required for the short control")
            binary = str(binary)

        def descriptor(label):
            fd = base.memfile(label)
            stack.callback(os.close, fd)
            return fd

        blobs = [descriptor(name) for name in ("model", "vocab", "merges")]
        model = base.prior.load_candidate(candidate)
        packed_model = base.model_blob(model, blobs[0], candidate["model_tensor_bytes"])
        if packed_model != text_report["source"]:
            raise ValueError("the native G4 model bytes differ")
        if context == 2048:
            extended_fd = descriptor("extended_model")
            extended_model = extend_positions(blobs[0], extended_fd, model)
            if prior_control is not None and extended_model != prior_control["extended_model"]:
                raise ValueError("the short control does not have the same extended model")
            blobs[0] = extended_fd
        del model
        for fd, blob in zip(blobs[1:], codec, strict=True):
            text.store(fd, blob)
            fcntl.fcntl(fd, base.prior.DEPLOY.F_ADD_SEALS, base.prior.DEPLOY.SEALS)
        wrapper = None
        if context == 2048:
            from tokenizers import Tokenizer

            wrapper = out.resolve() / "text_2048.py"
            wrapper.write_bytes(replace_once((bounded.ROOT / text.SCRIPT).read_bytes(),
                                             b"len(ids) <= 1017", b"len(ids) <= 2041"))
            tokenizer = Tokenizer.from_str(tokenizer_source.decode("utf-8"))
        else:
            refs = {row["case"]: row for row in text_report["runs"]}
            prompts = base.READ(codec_path)["runs"]["split_model"][0]["outputs"]
        runs = {}
        for lang in ("korean", "english"):
            old = [row for row in archive["runs"] if row["cap"] == 64 and row["language"] == lang]
            if not old or any(not row["ids_equal"] or not row["text_equal"] for row in old):
                raise ValueError("the archived matching bounded-prefill requests are required")
            path = out / f"{lang}.json"
            if context == 2048:
                prompt, ids, clue_at, answer = long_prompt(tokenizer, lang, short=(prior_control is not None))
                note = dict(encoding=dict(ids=ids), native=dict(model_bytes=extended_model["artifact_bytes"]))
                if int4_planes:
                    native = bounded.prior
                    visible = len(ids) + text.GEN - 1
                    low_rows = min(1024, visible // native.GROUP * native.GROUP)
                    removed = native.SLOTS * low_rows * native.KV * (int4_planes.bit_count()) // 2
                    note["native"]["kv_bytes"] = native.int8_capacity(visible) - removed
                actual = request(binary, blobs, prompt.encode("utf-8"), path, note, wrapper=wrapper)
                del actual["ids_equal"], actual["text_equal"]
                (out / f"{lang}_prompt.txt").write_text(prompt, encoding="utf-8")
                reply = base.READ(path)["decoding"]["text"]
                first = re.split(r"[\s.,;:!?]+", reply.strip().casefold(), maxsplit=1)[0]
                actual.update(clue_start_token=clue_at, expected_answer=answer, reply=reply,
                              exact_first_word=(first == answer), input_tokens=len(ids), generated_tokens=text.GEN)
            else:
                payload = prompts[lang]["decoded"].encode("utf-8")
                actual = request(binary, blobs, payload, path, refs[lang])
            actual.update(archive_peak_rss=max(row["peak_rss"] for row in old),
                          archive_median_seconds=median(row["seconds"] for row in old),
                          archive_scratch_bytes=old[0]["scratch_bytes"])
            print(f"P077_NATIVE_BLOCKED {lang} {actual}", flush=True)
            runs[lang] = actual
    if torch.cuda.is_initialized():
        raise RuntimeError("the CPU diagnostic unexpectedly initialized CUDA")
    base.WRITE(out / "report.json", dict(sources={str(path): base.SHA(path) for path in (
        Path(__file__), bounded.ROOT / base.CPP, bounded.ROOT / "scripts/p077_g4_grouped_attention.hpp",
        bounded.ROOT / "scripts/p109_g4_grouped_int8_cache.hpp")}, model=packed_model,
        previous_report=base.SHA(bounded.OUT / "report.json"), source_drift_verified_by_model_bytes=changed_sources,
        context_limit=context, extended_model=extended_model, short_control_of=str(short_control_of or ""),
        int4_planes=int4_planes, prefill_query_batch=prefill_query_batch, share_ffn_workspace=share_ffn_workspace,
        cpu=before["cpu"], runs=runs))
    signal.alarm(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--context", type=int, choices=(1024, 2048), default=1024)
    parser.add_argument("--short-control-of", type=Path)
    parser.add_argument("--old-kv-int4", choices=("keys", "values", "both"))
    parser.add_argument("--prefill-query-batch", action="store_true")
    parser.add_argument("--share-ffn-workspace", action="store_true")
    args = parser.parse_args()
    mask = {None: 0, "keys": 1, "values": 2, "both": 3}
    verify_runtime(args.output, args.context, args.short_control_of, mask[args.old_kv_int4],
                   args.prefill_query_batch, args.share_ffn_workspace)
