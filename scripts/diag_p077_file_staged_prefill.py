"""Share file KV reads across two existing projection tiles without allocating new layer buffers."""

import argparse
from contextlib import ExitStack
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
from unittest.mock import patch

import torch

from scripts import diag_p077_file_wide_query as width_only


files, native, trial, mapped = width_only.files, width_only.native, width_only.trial, width_only.mapped
TAG = "p077_file_staged_prefill_cpu_v1_20261124"
OUT = files.OUT.with_name(TAG)
REPLACEMENT = br"""    void visit(const Layer& layer, const Mlp& mlp, int count, int past) {
        static_assert(Tile == 8 && F >= 2 * D);
        constexpr int QueryRows = 2 * Tile;
        require(active_slot >= 0 && active_past == past, "prefill attention needs the active KV prefix");
        for (int group = 0; group < count; group += QueryRows) {
            const int span = std::min(QueryRows, count - group);
            for (int start = 0; start < span; start += Tile) {
                const int base = group + start;
                const int n = std::min(Tile, span - start);
                const float* resid = x.data() + base * D;
                float* query = gate.data() + start * D;
                for (int t = 0; t < n; ++t)
                    scaled_norm(norm.data() + t*D, resid + t*D, layer.a_scale, layer.a_shift);
                project(layer.q, norm.data(), query, n, weight.data());
                for (int t = 0; t < n; ++t) {
                    const int pos = (base + t) * (Head / 2);
                    rotate(query + t*D, rope_cos.data() + pos, rope_sin.data() + pos, D);
                }
            }
            if (span == 1) {
                attention(gate.data(), up.data(), past + group + 1);
            } else {
                attention_workspace.compute_prefill(cache, active_slot, past, gate.data(),
                    key.data(), value.data(), group + 1, span, up.data());
            }
            for (int start = 0; start < span; start += Tile) {
                const int n = std::min(Tile, span - start);
                float* resid = x.data() + (group + start) * D;
                project(layer.o, up.data() + start * D, projected.data(), n, weight.data());
                for (int j = 0; j < n * D; ++j) resid[j] += layer.gates[0] * projected[j];
            }
            for (int start = 0; start < span; start += Tile) {
                const int n = std::min(Tile, span - start);
                float* resid = x.data() + (group + start) * D;
                for (int t = 0; t < n; ++t)
                    scaled_norm(norm.data() + t*D, resid + t*D, layer.m_scale, layer.m_shift);
                project(mlp.gate, norm.data(), gate.data(), n, weight.data());
                project(mlp.up, norm.data(), up.data(), n, weight.data());
                for (int j = 0; j < n * F; ++j) gate[j] = gate[j] / (1.F + std::exp(-gate[j])) * up[j];
                project(mlp.down, gate.data(), projected.data(), n, weight.data());
                for (int j = 0; j < n * D; ++j) resid[j] += layer.gates[1] * projected[j];
            }
        }
    }"""


def render(control):
    swap = native.port.replace_once
    width = swap(control, b"    static constexpr int PrefillQueries = 8;",
                 b"    static constexpr int PrefillQueries = 16;")
    start = width.index(b"    void visit(const Layer& layer, const Mlp& mlp, int count, int past)")
    stop = width.index(b"\n\n    uint32_t next(", start)
    return swap(width, width[start:stop], REPLACEMENT)


def prepare():
    baseline, (identity, cases, cli, control, _) = width_only.prepare()
    prior_report = width_only.OUT / "report.json"
    prior = trial.read_json(prior_report)
    if prior["plan"] != baseline or [row["case"] for row in prior["rows"]] != [case["case"] for case in cases]:
        raise ValueError("the staged trial requires the exact width-only control and both real requests")
    candidate = render(control)
    profile = dict(tag=TAG, prior_sha256=trial.file_sha(prior_report), prior=baseline,
                   source_sha256=trial.file_sha(Path(__file__)), candidate_sha256=sha256(candidate).hexdigest().upper(),
                   query_rows=16, projection_rows=8, cpu=prior["cpu"])
    return profile, (identity, cases, cli, candidate)


def run(profile, deadline):
    sealed, (identity, cases, cli, source) = prepare()
    if (sealed != profile or OUT.exists() or os.environ.get("CUDA_VISIBLE_DEVICES") != ""
            or deadline.tzinfo is None or deadline > files.AUTHORIZATION_END
            or (deadline - datetime.now(deadline.tzinfo)).total_seconds() < 300):
        raise ValueError("the staged CPU model test needs the exact source and approval interval")
    os.sched_setaffinity(0, {profile["cpu"]})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir()
    engine_path = OUT / "engine"
    engine_path.mkdir()
    with patch.object(native.bounded, "OUT", engine_path):
        binary = native.bounded.build(source, caps=(64,))[64][1]
    rows = []
    with ExitStack() as stack:
        with patch.object(mapped.request, "OUT", OUT):
            model_sha = sealed["prior"]["source_receipt"]["prior"]["prior"]["native"]["native"]["native"]["state_sha256"]
            model = mapped.request.pack_model(stack, model_sha, identity)
        archive = os.open(files.codec.ASSET, os.O_RDONLY)
        stack.callback(os.close, archive)
        for case in cases:
            new, elapsed = files.request(OUT, case, "staged16", cli, binary, model, archive, deadline)
            previous = trial.read_json(width_only.OUT / f"{case['case']}_file.json")
            a, b = previous["native"], new["native"]
            if a["model_bytes"] != b["model_bytes"] or a["kv_written_bytes"] != b["kv_written_bytes"]:
                raise ValueError("the staged runner changed the checkpoint or the file history")
            row = dict(case=case["case"], answer_equal=a["ids"] == b["ids"], gold=case["gold"],
                       output=new["decoding"]["text"], read_bytes=[a["kv_read_bytes"], b["kv_read_bytes"]],
                       rss_bytes=[native.bounded.prior.peak(capture) for capture in (previous, new)],
                       scratch_bytes=[a["scratch_bytes"], b["scratch_bytes"]],
                       first=[a["seconds"][0], b["seconds"][0]], candidate_elapsed=elapsed)
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    trial.publish(OUT / "report.json", dict(profile=profile, rows=rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.mode == "prepare":
        ready, _ = prepare()
        trial.publish(args.receipt, ready)
        print(trial.file_sha(args.receipt), flush=True)
        return 0
    if args.stop_by is None:
        parser.error("a time-bounded model use approval is required")
    run(trial.read_json(args.receipt), args.stop_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
