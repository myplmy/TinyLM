"""Count position and adjacency exposure for the current and a blocked P109 shuffle."""

from collections import Counter
import hashlib
from itertools import pairwise
import random

from scripts import p070b_cla_routes as cla
from scripts import p109_train_visit_policy as current
from scripts import run_p109b_scratch_pair_20261120 as pair
from tinylm.config import build_config


OUT = pair.ROOT / "test_result/evidence/p109b_second_pass_balance_cpu_20261120"
SEED = 1337
# Consecutive differences modulo six are 1, 4, 3, 2, 5. Across six
# rotations each group has every position and each ordered pair occurs once.
BALANCED_ROW = (0, 1, 5, 2, 4, 3)


def balanced_orders(block):
    key = hashlib.sha256(f"P109B CLA blocked second pass v1/{SEED}/{block}".encode()).digest()
    rng = random.Random(key)
    groups, shifts = list(range(6)), list(range(6))
    rng.shuffle(groups)
    rng.shuffle(shifts)
    orders = [tuple(groups[(value + shift) % 6] for value in BALANCED_ROW) for shift in shifts]
    if (len({(position, group) for order in orders for position, group in enumerate(order)}) != 36
            or len({adjacency for order in orders for adjacency in pairwise(order)}) != 30):
        raise ValueError("every complete block needs balanced positions and directed adjacency")
    return orders


def summary(orders):
    positions = Counter((position, group) for order in orders for position, group in enumerate(order))
    adjacent = Counter(adjacency for order in orders for adjacency in pairwise(order))
    return {"distinct_orders": len(set(orders)), "updates": len(orders),
            "position": [min(positions.values()), max(positions.values())],
            "position_by_last_rank": [positions[(5, group)] for group in range(6)],
            "directed_adjacency": [min(adjacent.values()), max(adjacent.values())],
            "position_pairs_seen": len(positions), "directed_pairs_seen": len(adjacent)}


def main():
    cfg = build_config("m100s12_g4", "tied", pair.SEQ, ckpt=False)
    owners = [layer - layer % cfg.cla_group for layer in range(cfg.n_layers)]
    if not cfg.cla_edges:
        raise ValueError("this audit requires the registered G4 edge ownership")
    before, units, after = cla.middle_units(cfg, owners)
    if before or after or len(units) != 6 or any(len(unit) != 2 for unit in units):
        raise ValueError("the block requires six complete CLA2 groups")
    start = cfg.n_prelude + cfg.n_middle
    end = start + cfg.n_middle
    native = cla.schedule(cfg, owners, "uniform", 2)
    by_layer = {unit[0]: group for group, unit in enumerate(units)}
    original, blocked = [], []
    for update in range(pair.STEPS):
        observed = current.route_for(cfg, owners, "second_shuffle_r2", SEED, update, pair.STEPS)
        original.append(tuple(by_layer[n] for n in observed[start:end:2]))
        block, index = divmod(update, len(units))
        order = balanced_orders(block)[index]
        route = [*native[:start], *(n for group in order for n in units[group]), *native[end:]]
        receipt = cla.trace(cfg, owners, route)
        if receipt["visits"] != len(observed) or receipt["middle_repeats"] != 2:
            raise ValueError("candidate changed model visits or KV ownership")
        blocked.append(order)
    result = {"seed": SEED, "first_pass": "uniform", "visits": len(native), "updates": pair.STEPS,
              "actual_training": False, "current_full": summary(original), "proposed_full": summary(blocked),
              "current_first_100": summary(original[:100]), "proposed_first_100": summary(blocked[:100]),
              "source_sha256": {name: pair.file_sha(pair.ROOT / name) for name in (
                  "scripts/p109_train_visit_policy.py", "scripts/p070b_cla_routes.py", "tinylm/config.py",
                  "scripts/diag_p109b_second_pass_balance.py")}}
    OUT.mkdir(exist_ok=False)
    pair.publish(OUT / "report.json", result)
    print(result)


if __name__ == "__main__":
    main()
