"""P096 Q1 합성 held-out schema와 proof solver.

보호 데이터 경로를 읽지 않는다. relation item이 정답 하나를 형식적으로 증명하고 모든
distractor가 같은 의미 그래프에서 증명되지 않는지만 검증한다.
"""
from __future__ import annotations

from collections import deque


REQUIRED = {
    "id", "relation", "relation_subtype", "family_id", "template_id", "facts",
    "query_subject", "candidates", "gold_index", "gold_proof", "distractor_error_type",
    "difficulty_target", "difficulty_knobs",
}
DIFFICULTIES = {"easy", "mid", "hard"}
ERROR_TYPES = {"inverse", "necessary_sufficient", "temporal_reversal", "causal_correlation",
               "near_miss", "unsupported"}

# P096 Q1b의 보호-data 독립 taxonomy.  이름은 현재 benchmark의 여덟 상위 관계를
# 따르되, 여기서는 실제 문항을 생성하거나 읽지 않는다.
RELATION_TAXONOMY = {
    "조건": ("sufficient", "necessary", "biconditional", "independent"),
    "시간순서": ("before", "after", "overlap", "interval"),
    "부분전체": ("component", "member", "substance", "collection"),
    "대조": ("difference", "similarity", "tradeoff", "exception"),
    "상하위": ("hypernym", "hyponym", "instance", "sibling"),
    "반의": ("scalar", "complementary", "converse", "reversive"),
    "인과": ("direct", "mediated", "enabling", "correlation_control"),
    "목적수단": ("direct_means", "necessary_means", "alternative_means", "side_effect"),
}
EXPLICITNESS = {"explicit", "implicit"}
DISTANCES = {"far", "same_relation", "near"}


def difficulty_from_knobs(knobs):
    """Map semantic difficulty knobs to a preregistered coarse target.

    Vocabulary rarity and surface length are deliberately absent: P096 treats
    those as reading noise, not reasoning difficulty.
    """
    if set(knobs) != {"hops", "explicitness", "competing_clues", "distractor_distance"}:
        raise ValueError("difficulty_knobs 필드 오류")
    hops = knobs["hops"]
    clues = knobs["competing_clues"]
    if not isinstance(hops, int) or isinstance(hops, bool) or hops < 1:
        raise ValueError("difficulty_knobs.hops는 1 이상의 정수")
    if not isinstance(clues, int) or isinstance(clues, bool) or clues < 0:
        raise ValueError("difficulty_knobs.competing_clues는 0 이상의 정수")
    if knobs["explicitness"] not in EXPLICITNESS:
        raise ValueError("difficulty_knobs.explicitness enum 오류")
    if knobs["distractor_distance"] not in DISTANCES:
        raise ValueError("difficulty_knobs.distractor_distance enum 오류")
    score = (
        min(hops - 1, 2)
        + int(knobs["explicitness"] == "implicit")
        + min(clues, 2)
        + {"far": 0, "same_relation": 1, "near": 2}[knobs["distractor_distance"]]
    )
    return "easy" if score <= 1 else ("mid" if score <= 4 else "hard")


def _reachable(facts, subject, relation, transitive):
    edges = [(f["subject"], f["object"]) for f in facts if f["relation"] == relation]
    if not transitive:
        return {b for a, b in edges if a == subject}
    graph = {}
    for a, b in edges:
        graph.setdefault(a, []).append(b)
    seen, queue = set(), deque([subject])
    while queue:
        cur = queue.popleft()
        for nxt in graph.get(cur, []):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def validate_item(item, *, require_taxonomy=False):
    errors = []
    missing = sorted(REQUIRED - set(item))
    if missing:
        return ["missing fields: " + ", ".join(missing)]
    candidates = item["candidates"]
    if len(candidates) < 2 or len(candidates) != len(set(candidates)):
        errors.append("candidates는 중복 없는 2개 이상")
    gold_index = item["gold_index"]
    if not isinstance(gold_index, int) or not 0 <= gold_index < len(candidates):
        errors.append("gold_index 범위 오류")
        return errors
    if item["difficulty_target"] not in DIFFICULTIES:
        errors.append("difficulty_target enum 오류")
    knobs = item["difficulty_knobs"]
    try:
        expected_difficulty = difficulty_from_knobs(knobs)
    except (TypeError, ValueError) as exc:
        errors.append(str(exc))
    else:
        if item["difficulty_target"] in DIFFICULTIES and item["difficulty_target"] != expected_difficulty:
            errors.append(
                f"difficulty_target/knobs 불일치: target={item['difficulty_target']} "
                f"expected={expected_difficulty}"
            )
    if require_taxonomy:
        subtypes = RELATION_TAXONOMY.get(item["relation"])
        if subtypes is None:
            errors.append(f"등록되지 않은 relation: {item['relation']}")
        elif item["relation_subtype"] not in subtypes:
            errors.append(
                f"등록되지 않은 relation_subtype: {item['relation']}/{item['relation_subtype']}"
            )
    proof = item["gold_proof"]
    if proof.get("rule") not in {"direct", "transitive"}:
        errors.append("gold_proof.rule 오류")
    transitive = proof.get("rule") == "transitive"
    reachable = _reachable(item["facts"], item["query_subject"], item["relation"], transitive)
    proven = [i for i, candidate in enumerate(candidates) if candidate in reachable]
    if proven != [gold_index]:
        errors.append(f"정답 유일성 실패: proven={proven}, gold={gold_index}")
    edge_ids = proof.get("edge_ids")
    facts_by_id = {f.get("id"): f for f in item["facts"]}
    if len(facts_by_id) != len(item["facts"]):
        errors.append("facts id 중복 또는 누락")
    if not edge_ids or not set(edge_ids).issubset(facts_by_id):
        errors.append("gold_proof edge_ids가 facts에 닫히지 않음")
    else:
        path = [facts_by_id[edge_id] for edge_id in edge_ids]
        gold = candidates[gold_index]
        contiguous = (
            path[0].get("subject") == item["query_subject"]
            and path[-1].get("object") == gold
            and all(a.get("object") == b.get("subject") for a, b in zip(path, path[1:]))
            and all(fact.get("relation") == item["relation"] for fact in path)
        )
        expected_len = 1 if proof.get("rule") == "direct" else None
        if not contiguous or (expected_len is not None and len(path) != expected_len):
            errors.append("gold_proof edge_ids가 정답까지의 연속 경로가 아님")
        if proof.get("rule") == "transitive" and len(path) < 2:
            errors.append("transitive proof는 2개 이상 edge 필요")
    distractors = {str(i) for i in range(len(candidates)) if i != gold_index}
    labels = item["distractor_error_type"]
    if set(labels) != distractors:
        errors.append("distractor_error_type key가 비정답 후보와 불일치")
    if any(label not in ERROR_TYPES for label in labels.values()):
        errors.append("distractor_error_type enum 오류")
    return errors


def validate_panel(items, *, require_full_taxonomy=False):
    errors = []
    seen = set()
    for item in items:
        if item.get("id") in seen:
            errors.append(f"duplicate id: {item.get('id')}")
        seen.add(item.get("id"))
        errors.extend(
            f"{item.get('id', '<missing>')}: {e}"
            for e in validate_item(item, require_taxonomy=require_full_taxonomy)
        )
    if require_full_taxonomy:
        present = {item.get("relation") for item in items}
        if present != set(RELATION_TAXONOMY):
            errors.append(
                "taxonomy relation coverage 불일치: "
                f"missing={sorted(set(RELATION_TAXONOMY) - present)} "
                f"extra={sorted(present - set(RELATION_TAXONOMY))}"
            )
        for relation, expected_subtypes in RELATION_TAXONOMY.items():
            rows = [item for item in items if item.get("relation") == relation]
            got_subtypes = {item.get("relation_subtype") for item in rows}
            if got_subtypes != set(expected_subtypes):
                errors.append(
                    f"{relation}: subtype coverage 불일치 "
                    f"missing={sorted(set(expected_subtypes) - got_subtypes)}"
                )
            for subtype in expected_subtypes:
                targets = {
                    item.get("difficulty_target") for item in rows
                    if item.get("relation_subtype") == subtype
                }
                if targets != DIFFICULTIES:
                    errors.append(
                        f"{relation}/{subtype}: difficulty coverage={sorted(targets)}"
                    )
            for field in ("family_id", "template_id"):
                counts = {}
                for item in rows:
                    value = item.get(field)
                    counts[value] = counts.get(value, 0) + 1
                if rows and max(counts.values(), default=0) / len(rows) > 0.05:
                    errors.append(f"{relation}: {field} 단일 점유율 5% 초과")
            families = {}
            for item in rows:
                families.setdefault(item.get("family_id"), set()).add(item.get("template_id"))
            if any(len(templates) < 2 for templates in families.values()):
                errors.append(f"{relation}: family마다 서로 다른 template 2개 미만")
    return errors
