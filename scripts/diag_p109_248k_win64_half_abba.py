"""Compare already verified Windows decoder binaries in alternating order."""

import os
from pathlib import Path
from statistics import median

import torch

from scripts import diag_p109_248k_win64_half_history as half


win, gold, io, ROOT = half.win, half.gold, half.io, half.ROOT
OUT = half.OUT.with_name("p109_248k_win64_half_abba_v1_20261119")
PROOF = half.OUT / "attempt_01"
ORDER = (
    ("ce_48", "english", ("control", "candidate", "candidate", "control")),
    ("kd_48", "korean", ("candidate", "control", "control", "candidate")),
)
METRICS = ("seconds", "first_seconds", "tail_median_seconds", "peak_working_set")


def resources(profile_path, proof_path, names):
    profile, proof = io.load(profile_path), io.load(proof_path)
    scratch = Path(profile["scratch"])
    if scratch.resolve().parent != Path("/tmp"):
        raise ValueError("frozen binary directory is outside local scratch")
    paths = {name: scratch / name / "decoder.exe" for name in names}
    for name, path in paths.items():
        if not path.resolve().is_relative_to(scratch) or io.digest(path) != proof[f"{name}_pe_sha256"]:
            raise ValueError(f"Windows binary differs for {name}")
    return paths


def main():
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("isolated CPU is required")
    half.authority(250)
    proof_path = PROOF / "report.json"
    proof = io.load(proof_path)
    if not (proof["trace_bytewise_equal"] and proof["all_ids_equal"] and proof["sources_intact"]):
        raise ValueError("the bytewise or generation gate is incomplete")
    paths = resources(PROOF / "profile.json", proof_path, ("control", "candidate"))
    old_profile = io.load(half.REFERENCE / "profile.json")
    model_dir = Path(old_profile["scratch"])
    if model_dir.resolve().parent != Path("/tmp"):
        raise ValueError("frozen model directory is outside local scratch")
    prompt_path = gold.OUT / "profile.json"
    prompts = io.load(prompt_path)["requests"]
    OUT.mkdir()
    (OUT / "plan_at_execution.md").write_bytes(gold.PLAN.read_bytes())
    sources = {str(p.relative_to(ROOT)): io.digest(p) for p in (
        Path(__file__), Path(half.__file__), Path(win.__file__), PROOF / "profile.json", proof_path,
        half.REFERENCE / "profile.json", prompt_path, gold.PLAN,
        *(PROOF / f"request_{name}_{language}.json" for name, language, _ in ORDER),
    )}
    io.write(OUT / "profile.json", dict(approval="WIP177", sources=sources, order=ORDER,
             models=old_profile["models"], binaries={name: io.digest(p) for name, p in paths.items()}))
    rows, pairs = [], []
    for name, language, order in ORDER:
        model = model_dir / f"{name}.packed"
        model_hash = old_profile["models"][name]["sha256"]
        if not model.resolve().is_relative_to(model_dir) or io.digest(model) != model_hash:
            raise ValueError(f"Windows packed model differs for {name}")
        source = io.load(PROOF / f"request_{name}_{language}.json")
        previous = source["output"]
        if not source["all_ids_equal"]:
            raise ValueError("the fixed ID comparison is missing")
        block = []
        for position, arm in enumerate(order, 1):
            half.authority(46)
            if (OUT / "STOP").is_file():
                raise RuntimeError("Windows cross-order measurement was stopped")
            folder = OUT / f"{name}_{language}_{position}"
            folder.mkdir()
            row = win.measure(paths[arm], model, folder, name, language, prompts[language]["ids"], previous["ids"])
            if (row["actual_exit"] or not row.get("all_ids_equal") or
                    row["prefix_ids_sha256"] != source["prefix_ids_sha256"]):
                raise ValueError("the fixed output or input differed during timing")
            output = row["output"]
            if any(output[k] != previous[k] for k in ("model_bytes", "kv_bytes")):
                raise ValueError("the model or persistent KV size differed")
            block.append(dict(model=name, language=language, position=position, arm=arm,
                              seconds=row["seconds"], first_seconds=output["seconds"][0],
                              tail_median_seconds=row["tail_32_median_seconds"],
                              peak_working_set=output["complete"]["peak_working_set"]))
        if io.digest(model) != model_hash:
            raise ValueError("the Windows packed model changed during timing")
        rows.extend(block)
        for left, right in zip(block[::2], block[1::2]):
            arms = {row["arm"]: row for row in (left, right)}
            pairs.append(dict(model=name, language=language, order=[left["arm"], right["arm"]],
                              differences={metric: arms["candidate"][metric] - arms["control"][metric]
                                           for metric in METRICS}))
    intact = all(io.digest(ROOT / p) == h for p, h in sources.items())
    intact = intact and all(io.digest(p) == proof[f"{name}_pe_sha256"] for name, p in paths.items())
    summary = {metric: dict(median_difference=median(row["differences"][metric] for row in pairs),
                            candidate_lower=sum(row["differences"][metric] < 0 for row in pairs))
               for metric in METRICS}
    io.write(OUT / "report.json", dict(rows=rows, pairs=pairs, summary=summary,
             sources_intact=intact, cuda_initialized=torch.cuda.is_initialized(), all_ids_equal=True))
    print("P109_WIN64_HALF_CROSS_ORDER", len(rows), summary, flush=True)
    if not intact or torch.cuda.is_initialized():
        raise ValueError("source integrity or CPU isolation failed")


if __name__ == "__main__":
    main()
