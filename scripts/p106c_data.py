#!/usr/bin/env python3
"""Deterministic closed-world QA for P106C; gold is code-owned, no teacher calls."""
from __future__ import annotations
import hashlib
import json
import random
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ROLES = {"train": 256, "rehearsal": 128, "select": 16, "dev": 16, "sealed": 64, "retention": 64}
VALUES = {"ko": ("빨강", "파랑", "초록", "노랑"), "en": ("red", "blue", "green", "yellow")}


def make_role(role):
    if role not in ROLES:
        raise ValueError("unknown dataset role")
    rows = []
    templates = {
        "train": ("표: {a}={x}, {b}={y}. {key}의 색은? 색 이름 한 단어만 답하세요.",
                  "Table: {a}={x}, {b}={y}. What color is {key}? Answer with the color only."),
        "rehearsal": ("기억할 값: {a} 색 {x}; {b} 색 {y}. {key}에 해당하는 색만 쓰세요.",
                      "Remember: {a} has color {x}; {b} has color {y}. Return only {key}'s color."),
        "select": ("{a}에는 {x}, {b}에는 {y} 표시가 있다. {key}의 표시는 무엇인가? 색만 답하라.",
                   "{a} is marked {x} and {b} is marked {y}. Give only the color marking {key}."),
        "dev": ("색 대응 {a}: {x} / {b}: {y}. 이름 {key}에 연결된 색 하나를 출력하세요.",
                "Color mapping {a}: {x} / {b}: {y}. Output the single color linked to {key}."),
        "sealed": ("상자 {b}는 {y}이고 상자 {a}는 {x}이다. {key} 상자의 색만 적으세요.",
                   "Box {b} is {y} and box {a} is {x}. Write only the color of box {key}."),
        "retention": ("규칙 {a}는 {x}, {b}는 {y}. 이 규칙에서 {key}의 색 한 단어는?",
                      "Rule: {a} means {x}; {b} means {y}. Under this rule, give {key}'s color only.")}
    for pair in range(ROLES[role]):
        lang = "ko" if pair % 2 == 0 else "en"
        rng = random.Random(int(hashlib.sha256(f"P106C:{role}:{pair}".encode()).hexdigest()[:16], 16))
        x, y = rng.sample(VALUES[lang], 2)
        a, b = f"{role}_{pair}a", f"{role}_{pair}b"
        for slot, key in enumerate((a, b)):
            q = templates[role][lang == "en"].format(a=a, b=b, x=x, y=y, key=key)
            gold = x if slot == 0 else y
            rows.append({"id": f"{role}_{pair}_{slot}", "pair_id": f"{role}_{pair}", "role": role,
                         "language": lang, "question": q, "gold": gold,
                         "negatives": [v for v in VALUES[lang] if v != gold][:2],
                         "template_family": role, "task": "context_lookup", "repeat_expected": False})
    return rows


def positive_controls():
    rows = []
    for i in range(32):
        lang = "ko" if i % 2 == 0 else "en"
        word = VALUES[lang][(i // 2) % 4]
        count = 2 + i // 8
        q = (f"{word}을 공백으로 구분해 정확히 {count}번 쓰세요. 다른 말은 쓰지 마세요." if lang == "ko" else
             f"Write {word} exactly {count} times separated by spaces. Write nothing else.")
        rows.append({"id": f"repeat_{i}", "pair_id": None, "language": lang, "question": q,
                     "gold": " ".join([word] * count), "task": "legitimate_repetition", "repeat_expected": True})
    for i in range(32):
        lang = "ko" if i % 2 == 0 else "en"
        a, b = i + 1, i % 4 + 1
        q = f"{a}+{b}의 값만 숫자로 답하세요." if lang == "ko" else f"Return only the integer value of {a}+{b}."
        rows.append({"id": f"arithmetic_{i}", "pair_id": None, "language": lang, "question": q,
                     "gold": str(a+b), "task": "arithmetic_transfer", "repeat_expected": False})
    return rows


def canonical(row):
    from tinylm.chat.canonical import normalize
    return normalize({"messages": [{"role": "user", "content": row["question"]},
                                   {"role": "assistant", "content": row["gold"]}],
                      "meta": {"source": "p106c_code_gold", "source_id": row["id"], "language": row["language"],
                               "source_license": "repository-code-generated", "split": row.get("role", "sealed")}})


def data_hash(rows):
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()).hexdigest().upper()


def validate_roles(groups):
    seen = set()
    for role, rows in groups.items():
        if len(rows) != 2 * ROLES[role]:
            raise ValueError("dataset role count differs")
        for row in rows:
            if row["question"] in seen or row["gold"] in row["negatives"] or len(set(row["negatives"])) != 2:
                raise ValueError("question leakage or invalid negative")
            seen.add(row["question"])
            if row["role"] != role:
                raise ValueError("role drift")


def policy_plan(encoded_train, encoded_rehearsal, eligible_blocks=(), *, steps=128, cap=16, seed=1337, languages=None):
    """Matched lengths/target mass per slot; source IDs are bounded per arm."""
    from collections import Counter
    rng = random.Random(seed)
    counts = {"baseline": Counter(), "selected": Counter()}
    output = {"baseline": [], "selected": []}
    chosen_pool = {i for block in eligible_blocks for i in range(block * 32, block * 32 + 32)}
    if languages is None:
        languages = ["fixture"] * len(encoded_train)
    if len(languages) != len(encoded_train):
        raise ValueError("candidate language strata length differs")
    def draw(pool, count, state, offset=0):
        available = [i for i in pool if state[i + offset] < cap]
        if len(available) < count:
            raise ValueError("exposure cap cannot support requested schedule")
        result = rng.sample(available, count)
        for i in result:
            state[i + offset] += 1
        return result
    for _ in range(steps):
        baseline = draw(range(len(encoded_train)), 16, counts["baseline"])
        rehearsal = draw(range(len(encoded_rehearsal)), 16, counts["baseline"], len(encoded_train))
        selected = []
        for slot, original in enumerate(baseline):
            key = (len(encoded_train[original][0]), encoded_train[original][2], languages[original])
            pool = [i for i in chosen_pool if i not in selected and counts["selected"][i] < cap
                    and (len(encoded_train[i][0]), encoded_train[i][2], languages[i]) == key] if slot < 8 else []
            if not pool:
                pool = [i for i in range(len(encoded_train)) if i not in selected and counts["selected"][i] < cap
                        and (len(encoded_train[i][0]), encoded_train[i][2], languages[i]) == key]
            if not pool:
                raise ValueError("matched target-token schedule is infeasible under cap")
            candidate = rng.choice(pool)
            counts["selected"][candidate] += 1
            selected.append(candidate)
        for i in rehearsal:
            counts["selected"][i + len(encoded_train)] += 1
        output["baseline"].append({"candidate": baseline, "rehearsal": rehearsal})
        output["selected"].append({"candidate": selected, "rehearsal": rehearsal})
    output["max_exposures"] = {a: max(c.values()) for a, c in counts.items()}
    output["seed"] = seed
    return output
