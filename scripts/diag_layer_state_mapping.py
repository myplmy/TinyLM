#!/usr/bin/env python3
"""P091 R0/R1b — actual TinyLM ownership and optimizer mapping gate."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch

from tinylm.config import build_config  # noqa: E402
from tinylm.model.transformer import TiedMLPTransformer  # noqa: E402
from tinylm.train.layer_state_mapping import build_layer_state_map  # noqa: E402
from tinylm.train.muon import Muon  # noqa: E402
from tinylm.train.optimizer_audit import OptimizerAudit, matrix_decay_groups  # noqa: E402
from diag_optimizer_audit_contract import main as r1a_main  # noqa: E402


def optimizers_for(model):
    groups, matrices = matrix_decay_groups(model, 1e-3, matrix_weight_decay=0.1)
    matrix_ids = {id(parameter) for parameter in matrices}
    adam_groups = []
    for group in groups:
        params = [parameter for parameter in group["params"] if id(parameter) not in matrix_ids]
        if params:
            adam_groups.append(dict(group, params=params))
    adamw = torch.optim.AdamW(adam_groups)
    muon = Muon(matrices, lr=2e-2, weight_decay=0.1, scale_mode="rms")
    return [("adamw", adamw), ("muon", muon)]


def main() -> int:
    assert r1a_main() == 0
    torch.manual_seed(911)
    cfg = build_config("tiny", "tied", 128, False)
    model = TiedMLPTransformer(cfg)
    optimizers = optimizers_for(model)
    mapping = build_layer_state_map(model, optimizers)

    occurrences = mapping["logical_occurrences"]
    assert len(occurrences) == cfg.n_layers
    assert len(mapping["unique_mlp"]) == cfg.n_prelude + cfg.n_mlp_groups + cfg.n_coda
    assert all(row["kv_owner"] <= row["layer"] for row in occurrences)
    assert all(occurrences[row["kv_owner"]]["owns_kv"] for row in occurrences)
    assert mapping["metric_contract"]["S"].startswith("CLA-safe")
    assert "excluding weight decay" in mapping["metric_contract"]["U"]

    state_before = {name: value.detach().clone() for name, value in model.state_dict().items()}
    with tempfile.TemporaryDirectory(prefix="p091-model-audit-") as tmp:
        path = Path(tmp) / "audit.jsonl"
        audit = OptimizerAudit(
            path, model, optimizers, every=1, max_matrices=8,
            contract={"stage": "P091-R1b", "mapping_schema": mapping["schema"]},
        )
        contract = json.loads(path.with_suffix(".contract.json").read_text(encoding="utf-8"))
        assert contract["schema"] == "tinylm.optimizer-audit.v2"
        assert audit.selected
    for name, value in model.state_dict().items():
        assert torch.equal(value, state_before[name]), f"audit-on construction mutated {name}"

    print(
        f"[PASS] P091 R0/R1b: logical_layers={len(occurrences)} "
        f"unique_mlp={len(mapping['unique_mlp'])} "
        f"unique_attention={len(mapping['unique_attention'])} "
        f"kv_owners={len(mapping['kv_owners'])} "
        f"optimizer_params={len(mapping['optimizer_parameters'])}"
    )
    print("NOTE: selector S/U windows, timing overhead, GPU and realized quality remain NOT_RUN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
