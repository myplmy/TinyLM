"""Compare local teacher token IDs and archived padded-row logit mass without weights."""

from hashlib import sha256
from itertools import combinations
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

from scripts import p106b_mtp_teacher as bonsai27
from scripts import p106b_qwen_teacher as qwen38


ROOT = Path(__file__).resolve().parents[1]
TAG = "p106b_qwen_bonsai_tokenizer_map_v1_20261119"
OUT = ROOT / "test_result/evidence" / TAG
QWEN_HF = ROOT / "HF/models--Qwen--Qwen3.5-0.8B-Base/snapshots/dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68"
NATIVE = ROOT / "data_cache/tok-ko-en-32768.json"
ASSETS = ROOT / "test_result/evidence/p106b_bonsai2b_prism_assets_v1_20261117/report.json"
RAW = ROOT / "test_result/evidence/p106b_prism_native_raw_v1_20261117/actual/report.json"
FOLDERS = {
    "qwen35_gguf": "qwen35_08b_iq2xxs",
    "bonsai2b": "bonsai2_2b_ptq1",
}
NAMES = {
    "qwen35_gguf": "Qwen3.5-0.8B-UD-IQ2_XXS.gguf",
    "bonsai2b": "Ternary-Bonsai-2-2B-PTQ1_0.gguf",
}
PROMPTS = (
    "A small tool uses 3.25 watts.", "서울의 밤에 눈이 내렸다.", "A and 한글, 7+5=12.",
    "  first\tsecond\r\n마지막  ", "Café and Café", "한글과 한글", "철도 🚆와 Café",
    "<|im_start|>user\n안녕<|im_end|>\n",
    "<|endoftext|><|im_start|>assistant\n",
    "The answer is\u00a0 here.",
)


def read(path):
    return json.loads(path.read_bytes())


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return sha256(raw).hexdigest().upper()


def sha(path):
    return sha256(path.read_bytes()).hexdigest().upper()


def write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        print(file=stream)


def selected_metadata(stream):
    """Retain tokenizer arrays which the shared layout reader deliberately omits."""
    types = {0: "B", 1: "b", 2: "H", 3: "h", 4: "I", 5: "i", 6: "f", 7: "?",
             10: "Q", 11: "q", 12: "d"}

    def take(size):
        assert 0 <= size and stream.tell() + size <= 64 * 2**20, "bounded GGUF metadata"
        data = stream.read(size)
        assert len(data) == size, "truncated GGUF metadata"
        return data

    def num(fmt):
        return struct.unpack("<" + fmt, take(struct.calcsize("<" + fmt)))[0]

    def item(kind, keep, level=0):
        assert level <= 4
        if kind == 8:
            size = num("Q")
            assert size <= 2**24
            data = take(size)
            return data.decode("utf-8") if keep else None
        if kind == 9:
            element, count = num("I"), num("Q")
            assert count <= 2**20
            if keep:
                return [item(element, True, level + 1) for _ in range(count)]
            for _ in range(count):
                item(element, False, level + 1)
            return None
        fmt = types[kind]
        return num(fmt)

    assert take(4) == b"GGUF" and num("I") == 3
    tensors, fields = num("Q"), num("Q")
    assert tensors < 100000 and fields < 100000
    result = {}
    for _ in range(fields):
        key, kind = item(8, True), num("I")
        keep = key.startswith("tokenizer.") or key in (
            "general.name", "general.architecture", "general.source.url", "general.source.huggingface.repository")
        value = item(kind, keep)
        if keep:
            assert key not in result
            result[key] = value
    return result, stream.tell()


def local_gguf():
    result = {}
    for key, folder in FOLDERS.items():
        directory = ROOT / "HF/benchmark_20261023" / folder
        path, manifest_path = directory / NAMES[key], directory / "manifest.json"
        manifest = read(manifest_path)
        assert path.stat().st_size == manifest["bytes"] and not path.is_symlink()
        result[key] = (path, dict(
            revision=manifest["revision"], repo=manifest["repo_id"], previously_pinned_whole_sha256=manifest["sha256"].upper(),
            provenance=str(manifest_path.relative_to(ROOT)), provenance_sha256=sha(manifest_path),
        ))
    result["qwen38"] = (qwen38.MODEL, dict(
        revision=None, previously_pinned_whole_sha256=qwen38.MODEL_SHA, provenance="scripts/p106b_qwen_teacher.py"))
    result["bonsai27_mtp"] = (bonsai27.MODEL, dict(
        revision=None, previously_pinned_whole_sha256=bonsai27.MODEL_SHA, provenance="scripts/p106b_mtp_teacher.py"))
    actual = read(ASSETS)
    assert result["bonsai2b"][0] == ROOT / actual["model"]
    assert result["bonsai2b"][1]["previously_pinned_whole_sha256"] == actual["model_sha256"]
    return result


def hf_rows():
    index_path = QWEN_HF / "model.safetensors.index.json"
    index = read(index_path)["weight_map"]
    names = [name for name in index if name.endswith(("embed_tokens.weight", "lm_head.weight"))]
    shapes = {}
    for name in names:
        path = (QWEN_HF / index[name]).resolve(strict=True)
        assert path.is_relative_to((ROOT / "HF").resolve())
        with path.open("rb") as stream:
            size = struct.unpack("<Q", stream.read(8))[0]
            assert 0 < size <= 16 * 2**20
            header = stream.read(size)
            assert len(header) == size
        shapes[name] = json.loads(header)[name]["shape"]
    assert any(n.endswith("embed_tokens.weight") for n in shapes)
    actual = {v[0] for v in shapes.values()}
    assert len(actual) == 1
    return next(iter(actual)), shapes


def json_tokens(path, key, head, extras):
    obj = read(path)
    bindings = {idx: word for word, idx in obj["model"]["vocab"].items()}
    assert len(bindings) == len(obj["model"]["vocab"])
    for row in obj["added_tokens"]:
        old = bindings.setdefault(row["id"], row["content"])
        assert old == row["content"], (key, row["id"])
    assert all(type(idx) is int and idx >= 0 for idx in bindings)
    merges = [value if isinstance(value, str) else " ".join(value) for value in obj["model"]["merges"]]
    meta = dict(
        path=str(path.relative_to(ROOT)), file_sha256=sha(path), physical_rows=head, id_count=len(bindings),
        first_id=min(bindings), last_id=max(bindings), id_sha256=digest(bindings), merge_count=len(merges),
        merge_sha256=digest(merges), added_special_count=sum(m["special"] for m in obj["added_tokens"]),
        outside_physical_head=sum(i >= head for i in bindings),
        metadata_only=False, **extras,
    )
    meta["tokenizer_components"] = {k: {"type": (obj[k] or {}).get("type"), "sha256": digest(obj[k])}
                                     for k in ("normalizer", "pre_tokenizer", "post_processor", "decoder")}
    meta["added_token_rules_sha256"] = digest(obj["added_tokens"])
    return bindings, merges, meta


def model_tokens(path, provenance):
    assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to((ROOT / "HF").resolve())
    with path.open("rb") as stream:
        packet, tokenizer_end = selected_metadata(stream)
        stream.seek(0)
        identity = bonsai27.gguf_metadata(stream)
        stream.seek(0)
        metadata_bytes = stream.read(tokenizer_end)
    tokens = packet["tokenizer.ggml.tokens"]
    merges = packet.get("tokenizer.ggml.merges", [])
    kinds = packet.get("tokenizer.ggml.token_type")
    if kinds is not None:
        assert len(kinds) == len(tokens)
    core = {key: value["shape"] for key, value in identity["tensors"].items()
            if key in ("token_embd.weight", "output.weight")}
    assert "token_embd.weight" in core
    head = core.get("output.weight", core["token_embd.weight"])[-1]
    extras = {k: v for k, v in packet.items() if not isinstance(v, (list, dict))}
    for field in ("tokenizer.chat_template", "tokenizer.ggml.chat_template"):
        if field in extras:
            extras[field] = digest(extras[field])
    bindings = dict(enumerate(tokens))
    meta = dict(path=str(path.relative_to(ROOT)), file_bytes=path.stat().st_size,
                opening_metadata_sha256=sha256(metadata_bytes).hexdigest().upper(),
                opening_metadata_bytes=tokenizer_end, tensor_descriptors_bytes=identity["header_bytes"],
                tokenizer_fields=extras, shapes=core, id_count=len(bindings), physical_rows=head,
                id_sha256=digest(bindings), merge_count=len(merges), merge_sha256=digest(merges), metadata_only=True,
                outside_physical_head=sum(i >= head for i in bindings), **provenance)
    if kinds is not None:
        from collections import Counter
        meta["token_type_counts"] = dict(Counter(kinds))
        meta["token_type_sha256"] = digest(kinds)
    return bindings, merges, meta, kinds


def compare(left, right, pivot):
    li, lm, la = left[:3]
    ri, rm, ra = right[:3]
    common = li.keys() & ri.keys()
    changed = sorted(i for i in common if li[i] != ri[i])
    usable = [i for i in pivot if i < la["physical_rows"] and i < ra["physical_rows"]]
    prefix_diff = [i for i in usable if i not in li or i not in ri or li[i] != ri[i]]
    sample = lambda row: [dict(id=i, left=li.get(i), right=ri.get(i)) for i in row[:8]]
    return dict(shared_ids=len(common), both_present_modified=len(changed),
                absent_in_left=len(ri.keys() - li.keys()), absent_in_right=len(li.keys() - ri.keys()),
                first_shared_changes=sample(changed),
                hf_active_ids_in_both_head_ranges=len(usable), hf_active_mismatches=len(prefix_diff),
                first_hf_active_mismatches=sample(prefix_diff), merge_order_identical=lm==rm,
                first_merge_difference=next((i for i,(a,b) in enumerate(zip(lm,rm)) if a!=b),
                                            None if len(lm)==len(rm) else min(len(lm),len(rm))),
                equal_physical_rows=la["physical_rows"]==ra["physical_rows"])


def native_vocab(path, bundle):
    import ctypes as C
    from scripts import p106b_prism_native as prism

    api = prism.bind(C.CDLL(str(Path(bundle) / "libllama.so.0.2.0"), mode=C.RTLD_GLOBAL))
    args = api.llama_model_default_params()
    assert not args.vocab_only and not args.load_mtp and not args.no_alloc
    assert not args.devices and not args.dspark_head_source and not args.kv_overrides
    args.vocab_only = True
    args.n_gpu_layers = 0
    args.check_tensors = False
    api.llama_backend_init()
    model = None
    try:
        model = api.llama_model_load_from_file(os.fsencode(path), args)
        if not model:
            raise RuntimeError("vocabulary-only native loader returned NULL")
        vocab = api.llama_model_get_vocab(model)
        length = api.llama_vocab_n_tokens(vocab)
        assert 0 < length <= 300000
        result = []
        for text in PROMPTS:
            raw = text.encode("utf-8")
            bindings = {}
            for add in (False, True):
                tokens = (C.c_int32 * 1024)()
                size = api.llama_tokenize(vocab, raw, len(raw), tokens, len(tokens), add, True)
                assert 0 < size <= len(tokens)
                ids = list(tokens[:size])
                assert all(0 <= i < length for i in ids)
                bindings["native" if add else "plain"] = ids
            result.append(bindings)
    finally:
        if model:
            api.llama_model_free(model)
        api.llama_backend_free()
    print(json.dumps(dict(vocab_only=True, gpu_layers=args.n_gpu_layers, ids=result, n_vocab=length)), flush=True)


def probe_native(records, bundle):
    results = {}
    for key, (path, _) in records.items():
        command = [sys.executable, "-B", "-X", "utf8", "-m", "scripts.diag_p106b_teacher_tokenizer_map",
                   "native", str(path), str(bundle)]
        env = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "LD_LIBRARY_PATH": str(bundle)}
        try:
            child = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=24, check=False)
        except subprocess.TimeoutExpired as exc:
            messages = (exc.stderr or b"").decode("utf-8", "replace")
            with (OUT / f"{key}_native_log.txt").open("x", encoding="utf-8") as stream:
                stream.write(messages)
            results[key] = dict(exit=124, detail="vocabulary probe reached its 24-second bound")
            print("TEACHER_TOKENIZER_VOCAB", key, 124, flush=True)
            continue
        messages = child.stderr.decode("utf-8", "replace")
        with (OUT / f"{key}_native_log.txt").open("x", encoding="utf-8") as stream:
            stream.write(messages)
        if child.returncode == 0:
            results[key] = {"exit": 0, **json.loads(child.stdout.splitlines()[-1]),
                            "skipped_tensor_message": "skipping tensors" in messages.lower()}
        else:
            results[key] = dict(exit=child.returncode, detail=messages.splitlines()[-4:])
        print("TEACHER_TOKENIZER_VOCAB", key, results[key]["exit"], flush=True)
    return results


def missing_row_mass(hf, bonsai):
    import numpy as np

    old = read(RAW)
    head = bonsai[2]["physical_rows"]
    absent = [i for i in range(head) if i not in hf]
    reserved = [] if bonsai[3] is None else [i for i,k in enumerate(bonsai[3]) if k == 5]
    output = {}
    for key, record in old["vectors"].items():
        path = ROOT / record["path"]
        assert path.is_relative_to(RAW.parent) and sha(path) == record["sha256"]
        logits = np.load(path, allow_pickle=False)
        assert logits.shape == (head,) and logits.dtype == np.float32 and np.isfinite(logits).all()
        probs = np.exp(logits.astype(np.float64) - float(logits.max()))
        norm = float(probs.sum())
        output[key] = dict(vector_sha256=record["sha256"], mass_on_hf_unassigned=float(probs[absent].sum() / norm),
                           mass_on_gguf_type_5=float(probs[reserved].sum() / norm))
    return dict(hf_unassigned_rows=len(absent), gguf_type_5_rows=len(reserved),
                both=len(set(absent) & set(reserved)), stored_vectors=output)


def run():
    from tokenizers import Tokenizer

    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    records = local_gguf()
    assets = read(ASSETS)
    bundle = Path(assets["bundle"])
    for name in ("libllama.so.0.2.0", "libggml.so.0.21.0", "libggml-base.so.0.21.0"):
        path = bundle / name
        assert sha(path) == assets["runtime_files"][name]["sha256"]
    head, shapes = hf_rows()
    hfc = QWEN_HF / "config.json"
    tkc = QWEN_HF / "tokenizer_config.json"
    config = read(hfc)
    text = config.get("text_config", config)
    config_tokenizer = read(tkc)
    assert head == text["vocab_size"]
    settings = {k: text.get(k) for k in ("bos_token_id", "eos_token_id", "pad_token_id", "model_type",
                                         "tie_word_embeddings")}
    settings["outer_tie_word_embeddings"] = config.get("tie_word_embeddings")
    token_settings = {k: config_tokenizer.get(k) for k in ("bos_token", "eos_token", "pad_token",
                                                         "add_bos_token", "add_eos_token", "add_prefix_space")}
    models = {"qwen35_hf": json_tokens(QWEN_HF / "tokenizer.json", "qwen35_hf", head,
                        dict(revision=QWEN_HF.name, config_sha256=sha(hfc), tokenizer_config_sha256=sha(tkc),
                             settings=settings, special_settings=token_settings, shapes=shapes)),
              "tinylm_32k": json_tokens(NATIVE, "tinylm_32k", 32768, dict(revision=None))}
    for key, (path, origin) in records.items():
        models[key] = model_tokens(path, origin)
    pivot = models["qwen35_hf"][0]
    pairs = {f"{a}_vs_{b}": compare(models[a], models[b], pivot)
             for a,b in combinations(models, 2)}
    OUT.mkdir(exist_ok=False)
    sources = {str(Path(p).relative_to(ROOT)): sha(Path(p)) for p in (
        Path(__file__).resolve(), ROOT / "scripts/p106b_mtp_teacher.py", ROOT / "scripts/p106b_qwen_teacher.py",
        ROOT / "scripts/p106b_prism_native.py", ASSETS, RAW)}
    meta = {k: v[2] for k,v in models.items()}
    masses = missing_row_mass(pivot, models["bonsai2b"])
    write(OUT / "metadata_readback.json", dict(assets=meta, pairs=pairs, bonsai_padding_mass=masses))
    probe = Tokenizer.from_file(str(QWEN_HF / "tokenizer.json"))
    hf_ids = [{"plain": probe.encode(t, add_special_tokens=False).ids,
               "native": probe.encode(t, add_special_tokens=True).ids} for t in PROMPTS]
    native = probe_native(records, bundle)
    for key, report in native.items():
        if "ids" in report:
            assert report["n_vocab"] == models[key][2]["id_count"]
            report["plain_equal_hf"] = sum(a["plain"] == b["plain"] for a,b in zip(report["ids"], hf_ids, strict=True))
            report["special_equal_hf"] = sum(a["native"] == b["native"] for a,b in zip(report["ids"], hf_ids, strict=True))
    write(OUT / "report.json", dict(tag=TAG, sources=sources, assets=meta, pairs=pairs, unicode_probes=list(PROMPTS),
                                   qwen_hf_ids=hf_ids, vocab_only=native, bonsai_padding_mass=masses,
                                   gpu_evaluation=0, models_with_weight_load=0, direct_kl_enabled=False))
    print("TEACHER_TOKENIZER_MAP", {k: v["id_count"] for k,v in meta.items()}, masses, flush=True)


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "native":
        native_vocab(Path(sys.argv[2]), Path(sys.argv[3]))
    elif len(sys.argv) == 1:
        run()
    else:
        raise SystemExit("expected no arguments or native worker arguments")
