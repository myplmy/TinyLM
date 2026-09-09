"""A03/A04: ID 기반 paired 비교와 명시된 선택비용의 지표."""
from __future__ import annotations

import math
import random
import statistics
from collections import defaultdict


def mc_metrics(costs, gold):
    if len(costs) < 2 or not 0 <= gold < len(costs):
        raise ValueError("유효한 선택비용/gold 필요")
    if any(not math.isfinite(x) for x in costs):
        raise ValueError("비유한 선택비용")
    pred = min(range(len(costs)), key=lambda i: costs[i])
    wrong = [x for i, x in enumerate(costs) if i != gold]
    lo = min(costs)
    z = sum(math.exp(-(x - lo)) for x in costs)
    probabilities = [math.exp(-(x - lo)) / z for x in costs]
    return {"prediction": pred, "correct": int(pred == gold),
            "mean_wrong_margin": statistics.fmean(wrong) - costs[gold],
            "best_wrong_margin": min(wrong) - costs[gold],
            "choice_nll": (costs[gold] - lo) + math.log(z),
            "choice_brier": sum((p - int(i == gold)) ** 2
                                for i, p in enumerate(probabilities)),
            "choice_probabilities": probabilities,
            "tie_count": sum(x == costs[pred] for x in costs),
            "probability_contract": "softmax(-declared_cost), temperature=1; not calibrated"}


def index_rows(rows, metric):
    out = {}
    seen = set()
    for row in rows:
        ident = row["id"]
        if ident in seen:
            raise ValueError(f"중복 결과 id: {ident}")
        seen.add(ident)
        value = row.get(metric)
        if row.get("status") == "ok" and value is not None:
            if not math.isfinite(float(value)):
                raise ValueError(f"{ident}: nonfinite {metric}")
            out[ident] = row
    return out


def paired_rows(a, b, metric):
    aa, bb = index_rows(a, metric), index_rows(b, metric)
    common = sorted(set(aa) & set(bb))
    for ident in common:
        for key in ("item_sha256", "dataset_sha256", "scoring_profile"):
            if not aa[ident].get(key) or not bb[ident].get(key):
                raise ValueError(f"{ident}: paired {key} provenance 누락")
            if aa[ident].get(key) != bb[ident].get(key):
                raise ValueError(f"{ident}: paired {key} 불일치")
        if metric == "gold_ce":
            ta = (aa[ident].get("model_provenance") or {}).get("tokenizer_sha256")
            tb = (bb[ident].get("model_provenance") or {}).get("tokenizer_sha256")
            if not ta or ta != tb:
                raise ValueError("token 단위 gold CE는 같은 tokenizer에서만 paired 비교; bpb/정답률 사용")
        if aa[ident].get("gold") != bb[ident].get("gold"):
            raise ValueError(f"{ident}: paired gold 불일치")
    return [(aa[i], bb[i]) for i in common], {
        "common": len(common), "a_scored": len(aa), "b_scored": len(bb),
        "a_only": sorted(set(aa) - set(bb)), "b_only": sorted(set(bb) - set(aa))}


def summarize_paired(a, b, metric):
    pairs, coverage = paired_rows(a, b, metric)
    d = [float(x[metric]) - float(y[metric]) for x, y in pairs]
    result = {"metric": metric, "direction": "A-B", "coverage": coverage}
    if not d:
        return dict(result, status="no_common_items", mean=None, se=None)
    mean = statistics.fmean(d)
    sd = statistics.stdev(d) if len(d) > 1 else None
    se = sd / math.sqrt(len(d)) if sd is not None else None
    result.update(status="ok", mean=mean, sd=sd, se=se,
                  normal_95_ci=([mean - 1.96 * se, mean + 1.96 * se]
                                if se is not None else None))
    if metric == "correct":
        b10 = sum(x["correct"] == 1 and y["correct"] == 0 for x, y in pairs)
        b01 = sum(x["correct"] == 0 and y["correct"] == 1 for x, y in pairs)
        n = b10 + b01
        k = min(b10, b01)
        p = min(1.0, 2 * sum(math.exp(math.lgamma(n + 1) - math.lgamma(j + 1)
                                     - math.lgamma(n - j + 1) - n * math.log(2))
                            for j in range(k + 1))) if n else 1.0
        result.update(mcnemar_discordant=[b10, b01], mcnemar_exact_p=p)
    return result


def cluster_bootstrap(a, b, metric, *, cluster_key="family", draws=2000, seed=99):
    """가족을 재표집하고 각 표본의 문항 가중 평균을 계산. seed 반복은 합산하지 않는다."""
    if draws < 100:
        raise ValueError("bootstrap draws는 100 이상 필요")
    pairs, coverage = paired_rows(a, b, metric)
    groups = defaultdict(list)
    for x, y in pairs:
        family = x.get(cluster_key)
        if family is None or family != y.get(cluster_key):
            raise ValueError(f"{x['id']}: 양쪽의 명시적 {cluster_key} 필요")
        groups[str(family)].append(float(x[metric]) - float(y[metric]))
    keys = sorted(groups)
    if len(keys) < 2:
        raise ValueError("서로 다른 cluster가 2개 미만; CI 계산 불가")
    rng, samples = random.Random(seed), []
    for _ in range(draws):
        sampled = [groups[rng.choice(keys)] for _ in keys]
        samples.append(sum(sum(g) for g in sampled) / sum(len(g) for g in sampled))
    samples.sort()
    return {"metric": metric, "coverage": coverage, "clusters": len(keys),
            "cluster_key": cluster_key, "draws": draws, "seed": seed,
            "percentile_95_ci": [samples[int(.025 * (draws - 1))],
                                 samples[int(.975 * (draws - 1))]],
            "scope": "item-family sampling only; no training-seed uncertainty"}


def paired_bpb(a, b, *, cluster_key=None, draws=2000, seed=99):
    """문서 평균 bpb 차이가 아니라 합계 NLL / 합계 원문 byte의 차이."""
    pairs, coverage = paired_rows(a, b, "bpb")
    if not pairs:
        return {"status": "no_common_items", "coverage": coverage}
    if draws < 100:
        raise ValueError("bootstrap draws >= 100 필요")
    blocks = defaultdict(list)
    for left, right in pairs:
        size = left.get("scored_bytes")
        if not isinstance(size, int) or size <= 0 or size != right.get("scored_bytes"):
            raise ValueError("paired 문서의 원문 byte가 다름")
        family = left.get(cluster_key) if cluster_key else left["id"]
        if family is None or (cluster_key and right.get(cluster_key) != family):
            raise ValueError("독립 문서/가족 단위 확인 필요")
        blocks[str(family)].append((left["nll_sum"] - right["nll_sum"], size))
    def estimate(rows):
        return sum(x for x, _ in rows) / math.log(2) / sum(n for _, n in rows)
    flat = [row for block in blocks.values() for row in block]
    result = {"status": "ok", "metric": "byte_weighted_bpb", "direction": "A-B",
              "mean": estimate(flat), "coverage": coverage, "clusters": len(blocks),
              "bootstrap_95_ci": None}
    if len(blocks) > 1:
        rng, groups = random.Random(seed), list(blocks.values())
        estimates = sorted(estimate([row for _ in groups for row in rng.choice(groups)])
                           for _ in range(draws))
        result["bootstrap_95_ci"] = [estimates[int(0.025 * draws)],
                                     estimates[min(draws - 1, int(0.975 * draws))]]
    return result
