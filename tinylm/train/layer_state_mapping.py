"""P091 R0 structural mapping for logical layers, shared tensors and optimizers."""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class LayerOccurrence:
    layer: int
    mlp_module_id: int
    attention_module_id: int
    kv_owner: int
    owns_kv: bool


def optimizer_parameter_map(model, optimizers):
    names = {id(parameter): name for name, parameter in model.named_parameters()}
    mapping = {}
    for optimizer_name, optimizer in optimizers:
        for group_index, group in enumerate(optimizer.param_groups):
            for parameter in group["params"]:
                key = id(parameter)
                if key in mapping:
                    raise ValueError(
                        f"parameter가 optimizer group에 중복됨: {names.get(key, key)}"
                    )
                mapping[key] = {
                    "name": names.get(key, "<unregistered>"),
                    "optimizer": optimizer_name,
                    "group": group_index,
                    "lr": float(group["lr"]),
                    "weight_decay": float(group.get("weight_decay", 0.0)),
                }
    expected = {id(parameter) for parameter in model.parameters() if parameter.requires_grad}
    if set(mapping) != expected:
        missing = sorted(names[key] for key in expected - set(mapping))
        extra = sorted(str(key) for key in set(mapping) - expected)
        raise ValueError(f"optimizer mapping coverage 오류: missing={missing} extra={extra}")
    return mapping


def build_layer_state_map(model, optimizers=()):
    occurrences = [
        LayerOccurrence(
            layer=index,
            mlp_module_id=id(layer.mlp[0]),
            attention_module_id=id(layer.attn_mod),
            kv_owner=int(model.owner[index]),
            owns_kv=int(model.owner[index]) == index,
        )
        for index, layer in enumerate(model.layers)
    ]
    mlp_occurrences = {}
    attention_occurrences = {}
    for row in occurrences:
        mlp_occurrences.setdefault(row.mlp_module_id, []).append(row.layer)
        attention_occurrences.setdefault(row.attention_module_id, []).append(row.layer)
    result = {
        "schema": "tinylm.layer-state-map.v1",
        "logical_occurrences": [asdict(row) for row in occurrences],
        "unique_mlp": {str(key): value for key, value in mlp_occurrences.items()},
        "unique_attention": {str(key): value for key, value in attention_occurrences.items()},
        "kv_owners": sorted({row.kv_owner for row in occurrences}),
        "optimizer_parameters": optimizer_parameter_map(model, optimizers) if optimizers else {},
        "metric_contract": {
            "S": "CLA-safe residual-contribution ablation; never called KV supply removal",
            "U": "optimizer update excluding weight decay divided by weight RMS",
        },
    }
    return result
