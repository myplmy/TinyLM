"""Run the pinned BabyLM Reading statistics on closed predictions, using real OLS."""

import argparse
from importlib import metadata, util
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from handoff.audit.research_20261118_01a1e647 import replay_reading_regressions_v1 as replay


TAG = "p106b_babylm_reading_official_ols_v1_20261120"
OUT = replay.OUT.with_name(TAG)
MODELS = ("native595-f", "native595-q", "new595-broad-f", "falcon90m")
OUTPUT_FILES = ("correlations.txt", "predictive_power.jsonl", "predictive_power_spillover.jsonl", "report.txt")


def model_frames():
    raw = replay.READBACK.read_bytes()
    if replay.digest(raw) != replay.READBACK_SHA:
        raise ValueError("Closed Reading prediction readback differs")
    proof = json.loads(raw)
    if set(proof["models"]) != set(MODELS):
        raise ValueError("Expected the four original model receipts")
    replay.verified_bytes(proof["profile"])
    frame = replay.pd.read_csv(BytesIO(replay.verified_bytes(proof["source_csv"])), dtype={"item": str})
    frame["item"] = frame["item"].fillna("None")
    frames = {}
    for name in MODELS:
        model = proof["models"][name]
        replay.verified_bytes(model["report"])
        frames[name] = replay.prediction_frame(frame, model)
    return frames


class TracedOLS:
    def __init__(self, ols):
        self._ols = ols
        self.calls = []

    def ols(self, *, formula, data):
        self.calls.append(dict(formula=formula, rows=len(data),
                               index_sha256=replay.digest(json.dumps(data.index.tolist()).encode())))
        return self._ols(formula=formula, data=data)


def score_frame(block, frame, ols, output):
    output.mkdir()
    traced = TracedOLS(ols)
    exec(block, dict(df=frame, smf=traced, json=json, args=SimpleNamespace(output_dir=output)))
    calls = traced.calls
    if [row["rows"] for row in calls] != [1696] * 22 + [1496] * 22:
        raise ValueError("Pinned Reading fit denominators differ")
    for base, full in zip(calls[::2], calls[1::2], strict=True):
        if base["index_sha256"] != full["index_sha256"] or full["formula"] != base["formula"] + " + pred":
            raise ValueError("Pinned Reading comparison did not use identical observations")
    if set(p.name for p in output.iterdir()) != set(OUTPUT_FILES):
        raise ValueError("Pinned Reading report files differ")
    for name in OUTPUT_FILES[1:3]:
        rows = [json.loads(line) for line in (output / name).read_bytes().splitlines()]
        if len(rows) != 11 or len({row["Predicted variable"] for row in rows}) != 11:
            raise ValueError(f"Pinned Reading dependent-variable outputs differ: {name}")
    report = (output / "report.txt").read_text(encoding="utf-8").splitlines()
    if len(report) != 2 or not (
        report[0].startswith("EYE TRACKING SCORE: ") and report[1].startswith("SELF-PACED READING SCORE: ")
    ):
        raise ValueError("Pinned Reading aggregate report differs")
    return dict(report=report, calls=calls,
                output_sha256={name: replay.digest((output / name).read_bytes()) for name in OUTPUT_FILES})


def dependencies():
    versions = {}
    for name in ("statsmodels", "patsy"):
        if util.find_spec(name) is not None:
            versions[name] = metadata.version(name)
    return versions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("check", "score"))
    args = parser.parse_args()
    versions = dependencies()
    missing = [name for name in ("statsmodels", "patsy") if name not in versions]
    if args.phase == "score" and missing:
        print(json.dumps(dict(tag=TAG, missing=missing, official_statsmodels_run=False, models_scored=0)))
        return 2
    frames = model_frames()
    block, ast_sha = replay.reading_block()
    sources = dict(official_run_sha256=replay.OFFICIAL_SHA, official_statistics_ast_sha256=ast_sha,
                   closed_prediction_readback_sha256=replay.READBACK_SHA,
                   readback_code_sha256=replay.digest(Path(replay.__file__).read_bytes()))
    if args.phase == "check":
        print(json.dumps(dict(tag=TAG, missing=missing, sources=sources, official_statsmodels_run=False,
                              target_rows=sum(len(frame) for frame in frames.values()),
                              previous_rows=sum(int(frame["prev_pred"].notna().sum()) for frame in frames.values()),
                              models=tuple(frames))))
        return 0

    from statsmodels.formula import api as smf

    if OUT.exists() or OUT.is_symlink():
        raise FileExistsError("A saved official Reading result already occupies the output directory")
    with TemporaryDirectory(prefix=f".{TAG}_", dir=OUT.parent) as work:
        staging = Path(work)
        results = {name: score_frame(block, frame, smf.ols, staging / name)
                   for name, frame in frames.items()}
        summary = dict(tag=TAG, sources=sources, packages=versions, official_statsmodels_run=True,
                       model_calls=0, gpu_runs=0, results=results)
        (staging / "result.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + chr(10),
                                             encoding="utf-8")
        staging.rename(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
