"""Measure ranks of already observed G4 edits on CPU without inference or updates."""

import os

import torch

from scripts import diag_p108_g4_edit_retention as retention


ROOT = retention.ROOT
SOURCE_REPORT = retention.OUT / "report.json"
SELECTION = retention.OUT / "selection.json"
PACKETS = ROOT / "test_result/evidence/p108_g4_packed_cuda_joint_v1_20261119/report.json"
OUT = retention.OUT.with_name("p108_g4_edit_rank_readback_v1_20261119")
OWNER = "mid_mlps.0.down_proj.weight"


def spectrum(weight, indices, cfg):
    rows, cols = indices // weight.shape[1], indices % weight.shape[1]
    in_rows, compact_rows = rows.unique(return_inverse=True)
    in_cols, compact_cols = cols.unique(return_inverse=True)
    values = -2 * retention.ternary(weight, cfg).flatten()[indices].double()
    compact = torch.zeros((len(in_rows), len(in_cols)), dtype=torch.float64)
    compact[compact_rows, compact_cols] = values
    assert compact.count_nonzero() == len(indices)
    singular = torch.linalg.svdvals(compact)
    energy = singular.square()
    total = energy.sum()
    eps = torch.finfo(torch.float64).eps * max(compact.shape)
    return dict(positions=len(indices), active_matrix_shape=list(compact.shape), l2=float(total.sqrt()),
                rank_fp64=int((singular > singular[0] * eps).sum()),
                rank_rel_1e_minus_6=int((singular > singular[0] * 1e-6).sum()),
                stable_rank=float(total / energy[0]),
                fraction_squared_l2={str(k):float(energy[:k].sum() / total) for k in (1, 2, 4, 8, 16)},
                singular_values=singular.tolist())


def packet_ranks():
    packets = retention.read(PACKETS)["geometry"]["packets"]
    summary = {}
    for label, members in packets.items():
        per_owner = {}
        for owner, packet in members.items():
            assert packet["shape"] == [768, 2048] and packet["group"] == 128
            columns = packet["shape"][1]
            rows = {index // columns for index in packet["indices"]}
            cols = {index % columns for index in packet["indices"]}
            # All positions share either a row or a column in each stored packet.
            assert min(len(rows), len(cols)) == 1
            per_owner[owner] = dict(rank=1, changed_coordinates=len(packet["indices"]),
                                    rows=sorted(rows), columns=sorted(cols))
        summary[label] = dict(per_owner=per_owner, sum_of_physical_matrix_ranks=len(per_owner))
    counts = {label:sum(row["changed_coordinates"] for row in mode["per_owner"].values())
              for label, mode in summary.items()}
    assert counts == {"single":2, "split":2}
    return summary


def main():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    torch.set_num_threads(2)
    assert retention.sha(retention.PARENT) == retention.frozen.PARENT_SHA
    cfg, state, step = retention.frozen.prior.load_parent(torch)
    assert step == 2289 and cfg.mlp_group == 4 and cfg.micro_group == 128 and not cfg.sparse34
    weight = state[OWNER]
    assert weight.device.type == "cpu" and weight.shape == (768, 2048)
    del state
    selection = retention.read(SELECTION)
    indices = torch.tensor(selection["indices"])
    original = torch.tensor(selection["original_signs"])
    assert len(indices.unique()) == 1024
    assert torch.equal(retention.ternary(weight, cfg).flatten()[indices].sign().long(), original)
    archive = retention.read(SOURCE_REPORT)
    assert archive["source_and_parent_unchanged"] and all(value == 0 for value in archive["exits"].values())
    results = {}
    for name, count in (("small", 64), ("large", 1024)):
        row = spectrum(weight, indices[:count], cfg)
        reported = archive["arms"][name]["installed"]["effective_l2"]
        assert abs(row["l2"] - reported) < 1e-6
        results[name] = dict(row, cuda_archived_l2=reported)
        print("P108_EDIT_RANK", name, row["rank_fp64"], row["rank_rel_1e_minus_6"], row["stable_rank"],
              row["fraction_squared_l2"], flush=True)
    assert not torch.cuda.is_initialized()
    summary = packet_ranks()
    OUT.mkdir()
    retention.write(OUT / "report.json", dict(matrix=OWNER, parent_sha256=retention.frozen.PARENT_SHA,
                     archived_hashes={p.relative_to(ROOT).as_posix():retention.sha(p)
                                      for p in (SELECTION, SOURCE_REPORT, PACKETS)},
                     measured=results, fixed_scale_packets=summary, forward_calls=0, training_updates=0))
    print("P108_FIXED_SCALE_RANK", summary, flush=True)


if __name__ == "__main__":
    main()
