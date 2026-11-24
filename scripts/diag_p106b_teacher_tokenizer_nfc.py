"""Recheck the two observed HF/Prism segmentation differences with NFC alone."""

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from unicodedata import normalize

from scripts import diag_p106b_teacher_tokenizer_map as reference


TAG = "p106b_teacher_nfc_vocab_v1_20261119"
OUT = reference.OUT.with_name(TAG)


def run():
    from tokenizers import Tokenizer

    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    old_path = reference.OUT / "report.json"
    old = reference.read(old_path)
    paths = reference.local_gguf()
    mismatches = {
        tuple(i for i, (left, right) in enumerate(zip(row["ids"], old["qwen_hf_ids"], strict=True)) if left != right)
        for row in old["vocab_only"].values()
    }
    assert mismatches == {(4, 5)} and all(row["skipped_tensor_message"] for row in old["vocab_only"].values())
    source = reference.QWEN_HF / "tokenizer.json"
    assert reference.sha(source) == old["assets"]["qwen35_hf"]["file_sha256"]
    assert reference.read(source)["normalizer"] == {"type": "NFC"}
    prompts = [normalize("NFC", old["unicode_probes"][i]) for i in (4, 5)]
    assert all(prompts[j] != old["unicode_probes"][i] for j, i in enumerate((4, 5)))
    hf = Tokenizer.from_file(str(source))
    expected = [dict(plain=hf.encode(text, add_special_tokens=False).ids,
                     native=hf.encode(text, add_special_tokens=True).ids) for text in prompts]
    assert expected == [old["qwen_hf_ids"][i] for i in (4, 5)]
    assets = reference.read(reference.ASSETS)
    bundle = Path(assets["bundle"])
    for name in ("libllama.so.0.2.0", "libggml.so.0.21.0", "libggml-base.so.0.21.0"):
        assert reference.sha(bundle / name) == assets["runtime_files"][name]["sha256"]
    OUT.mkdir(exist_ok=False)
    results = {}
    for key, (path, _) in paths.items():
        with path.open("rb") as stream:
            header = stream.read(old["assets"][key]["opening_metadata_bytes"])
        assert sha256(header).hexdigest().upper() == old["assets"][key]["opening_metadata_sha256"]
        cmd = [sys.executable, "-B", "-X", "utf8", "-m", "scripts.diag_p106b_teacher_tokenizer_nfc",
               "native", str(path), str(bundle)]
        env = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "LD_LIBRARY_PATH": str(bundle)}
        child = subprocess.run(cmd, input=json.dumps(prompts).encode(), env=env, cwd=reference.ROOT,
                               timeout=24, capture_output=True, check=False)
        messages = child.stderr.decode("utf-8", "replace")
        result = dict(exit=child.returncode, skipped_tensors="skipping tensors" in messages.lower())
        if child.returncode == 0:
            row = json.loads(child.stdout.splitlines()[-1])
            result.update(ids=row["ids"], matches_hf=row["ids"] == expected, n_vocab=row["n_vocab"])
        else:
            result.update(detail=messages.splitlines()[-5:], matches_hf=False)
        results[key] = result
        print("NFC_VOCAB", key, result["exit"], result["matches_hf"], flush=True)
    reference.write(OUT / "report.json", dict(tag=TAG, prior_sha256=reference.sha(old_path),
        current_script_sha256=reference.sha(Path(__file__)), normalization="NFC", original_case_ids=[4, 5],
        normalized_prompts=prompts, expected=expected, results=results, gpu_evaluation=0))
    return 0 if all(r["matches_hf"] and r["skipped_tensors"] for r in results.values()) else 8


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "native":
        reference.PROMPTS = tuple(json.load(sys.stdin))
        reference.native_vocab(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        sys.exit(run())
