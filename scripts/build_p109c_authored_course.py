"""Generate the P109C authored course, its independent splits, and a CPU receipt."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from random import Random
import re

import numpy as np
from tokenizers import Tokenizer

from scripts import compile_p109c_course as compiler
from scripts import run_p109c_scratch330 as entry
from scripts.p106b_joint_decimal import decimal_parts
from tinylm.chat.canonical import normalize
from tinylm.chat.serialize import serialize
from tinylm.data.prepare import chat_tokenizer_path, verify_chat_tokenizer
from tinylm.train.mtp_sft import encode_record


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "test_result/evidence"
SEED, HELD_OUT = 20261121, 64
PLAIN_SLOTS = (1,)
RELATION_SLOTS = (2, 3, 4, 5)
LANGUAGES = ("ko", "en")
SPLITS = ("train", "validation", "test")
PEOPLE = {
    "ko": (
        ("가람", "나래", "소연", "하람", "도윤", "유리", "지안", "태현", "서진", "은채", "수빈", "민규"),
        ("한결", "주원", "서하", "예린", "우진", "다현", "이든", "희준"),
        ("다온", "시온", "수아", "하린", "민호", "윤서", "누리", "선재"),
    ),
    "en": (
        ("Mina", "Lena", "Maya", "Ava", "Alan", "Owen", "Hana", "Rory", "Emma", "Noah", "Liam", "Leah"),
        ("Iris", "Sam", "Nora", "Milo", "Grace", "Elena", "Luca", "Hugo"),
        ("April", "Nina", "Peter", "Evan", "Rose", "Ada", "Jonah", "Mabel"),
    ),
}
FIELDS = {"ko": ("발송", "반납", "보관", "수리"), "en": ("dispatch", "returns", "storage", "repair")}
ITEMS = {"ko": ("우산", "랜턴", "지도", "물통", "클립", "장갑", "깃발", "자물쇠", "연필", "줄자"),
         "en": ("umbrella", "lantern", "map", "bottle", "clip", "gloves", "flag", "lock", "pencil", "tape")}
PLACES = {"ko": ("북쪽 창구", "남쪽 창구", "동쪽 안내소", "서쪽 안내소", "정문", "뒷문", "1층 데스크", "기록실"),
          "en": ("north desk", "south desk", "east kiosk", "west kiosk", "main door", "rear door", "lobby desk", "archive room")}


def digest(value):
    canonical = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest().upper()


def reference(path):
    return dict(file=path.name, sha256=entry.file_sha(path).upper())


def row(root, family, language, turns, *, view=None, **extra):
    metadata = dict(language=language, family=family)
    if view:
        metadata["view"] = view
    metadata["supervised_assistant_turns"] = [sum(role == "assistant" for role, _ in turns)]
    messages = [dict(role=role, content=text) for role, text in turns]
    return dict(root=root, record=normalize(dict(messages=messages, meta=metadata)), **extra)


def arithmetic_pairs():
    candidates = ([], [])
    for left in range(10, 100):
        for right in range(left, 100):
            candidates[int(left % 10 + right % 10 >= 10)].append((left, right))
    rng = Random(SEED)
    for values in candidates:
        rng.shuffle(values)
    return tuple(iter(values) for values in candidates)


def arithmetic(pair, language, method, phrasing, rng):
    left, right = pair if rng.randrange(2) else pair[::-1]
    total, ones, tens, carry = decimal_parts(left, right)
    root = digest(["unordered addition", list(sorted(pair))])
    formulas = {
        "ko": (f"{left} + {right}의 값은 얼마인가요? 숫자만 답하세요.",
               f"식 {left} + {right}의 결과를 숫자로만 적어 주세요.",
               f"두 수를 더한 값만 알려 주세요. {left} + {right}"),
        "en": (f"What is {left} + {right}? Return only the number.",
               f"Give the numerical result of {left} + {right}.",
               f"Write just the sum of {left} + {right}."),
    }
    answer = str(total)
    extras = dict(operands=[left, right])
    if method == "worked_addition":
        unit = left % 10 + right % 10
        if language == "ko":
            question = f"{left} + {right}를 계산하고, 일의 자리와 십의 자리로 나누어 검산해 주세요."
            answer = (f"일의 자리의 합은 {unit}입니다. 결과의 일의 자리는 {ones}, 십의 자리로의 올림은 {carry}입니다. "
                      f"십의 자리 쪽 합은 {left // 10} + {right // 10} + {carry} = {tens}입니다. 합은 {total}입니다.")
        else:
            question = f"Calculate {left} + {right} and check the result place by place."
            answer = (f"The units sum to {unit}. Keep {ones} in the units place and carry {carry}. "
                      f"The tens give {left // 10} + {right // 10} + {carry} = {tens}. The sum is {total}.")
        extras = {}
    else:
        question = formulas[language][phrasing]
    return row(root, method, language, [("user", question), ("assistant", answer)], **extras)


def field_question(language, field, phrasing):
    name = FIELDS[language][field]
    questions = {
        "ko": (f"{name} 항목의 현재 번호만 답하세요.", f"표에서 현재 {name}에 배정된 번호는 무엇인가요?",
               f"현재 {name}에 지정된 숫자를 번호 하나로 알려 주세요."),
        "en": (f"Give only the current number for {name}.", f"Which number does the record now give for {name}?",
               f"Return the number currently assigned to {name}."),
    }
    return questions[language][phrasing]


def values_text(language, values, order):
    return ", ".join(f"{FIELDS[language][field]}: {values[field]}" for field in order) + "."


def table_case(rng, language, phrasing, kind):
    original = tuple(rng.sample(range(11, 9980), 4))
    ordered_fields = rng.sample(range(4), 4)
    field, other = rng.sample(range(4), 2)
    table = values_text(language, original, ordered_fields)
    prefix = "작업표에는 다음과 같이 적혀 있습니다. " if language == "ko" else "The work log has these entries. "
    question = prefix + table + " " + field_question(language, field, phrasing)
    initial = str(original[field])
    if kind == "correction":
        root = digest(["table", original])
        recheck = "앞의 작업표에서 항목을 다시 확인해 주세요. " if language == "ko" else "Check the original work log again. "
        correction = row(root, kind, language, [("user", question), ("assistant", str(original[other])),
                     ("user", recheck + field_question(language, field, phrasing)), ("assistant", initial)], view="correction")
        single = row(root, kind, language, [("user", question), ("assistant", initial)], view="single")
        return dict(root=root, single=single, correction=correction)

    current = original
    updated = ""
    target = other if kind == "question_change" else field
    if kind == "state_update":
        replacements = [number for number in rng.sample(range(11, 9980), 6) if number not in original][:2]
        changed = dict(zip((other, field), replacements, strict=True))
        current = tuple(changed.get(index, value) for index, value in enumerate(original))
        updated_fields = [field, other] if rng.randrange(2) else [other, field]
        updated = ("작업표의 두 항목을 다음과 같이 바꿉니다. " if language == "ko" else "Two entries in the log changed. ")
        updated += values_text(language, current, updated_fields) + " "
    elif kind == "question_change":
        updated = "이번에는 다른 항목을 보겠습니다. " if language == "ko" else "Look up a different entry this time. "
    else:
        updated = "변경된 내용은 없습니다. 다시 확인해 주세요. " if language == "ko" else "The log is unchanged. Please check again. "
    root = digest(["table", original])
    answer = str(current[target])
    if (answer == initial) != (kind == "repeat"):
        raise ValueError("the answer did not follow the stated state or question change")
    return row(root, kind, language, [("user", question), ("assistant", initial),
                                     ("user", updated + field_question(language, target, phrasing)),
                                     ("assistant", answer)])


def relation_graph(rng, language, phrasing):
    names = rng.sample(PEOPLE[language][phrasing], 4)
    numbers = rng.sample(range(101, 999), 4)
    items = rng.sample(ITEMS[language], 4)
    places = rng.sample(PLACES[language], 4)
    facts = list(zip(names, numbers, items, places, strict=True))
    root = digest(["assignment table", sorted(facts)])
    name_order, record_order = (rng.sample(facts, 4) for _ in range(2))
    if language == "ko":
        head = "담당 번호 표입니다.\n"
        people = "\n".join(f"{name} 담당 번호 {number}" for name, number, _, _ in name_order)
        tasks = "\n".join(f"업무 {number} / 물품 {item} / 도착 {place}" for _, number, item, place in record_order)
        context = head + people + "\n\n업무 등록표입니다.\n" + tasks + "\n\n"
        queries = ("업무 번호 {}의 담당자", "물품이 {}인 업무의 담당자", "도착지가 {}인 업무의 담당자")
        ask = ("{}의 이름만 답하세요.", "확인할 대상은 {}입니다. 이름만 적어 주세요.", "{}가 누구인지 이름으로 답하세요.")[phrasing]
    else:
        people = "\n".join(f"{name} / assignment {number}" for name, number, _, _ in name_order)
        tasks = "\n".join(f"Assignment {number} / item {item} / destination {place}" for _, number, item, place in record_order)
        context = "Staff assignments\n" + people + "\n\nWork register\n" + tasks + "\n\n"
        queries = ("assignment {}", "the assignment for the {}", "the assignment to the {}")
        ask = ("Who handles {}? Give only the name.", "Check the register. Name the person for {}.",
               "Return the name of the person in charge of {}.")[phrasing]
    choices = rng.sample(names, 4)
    rows, gold = [], []
    for fact in rng.sample(facts, 4):
        field = rng.choice((1, 2, 3))
        query = context + ask.format(queries[field - 1].format(fact[field]))
        matches = [source[0] for source in facts if source[field] == fact[field]]
        if len(matches) != 1:
            raise ValueError("the register does not establish a unique answer")
        gold.append(choices.index(matches[0]))
        rows.extend(row(root, "relation", language, [("user", query), ("assistant", choice)]) for choice in choices)
    return rows, gold


def create_cases():
    pairs = arithmetic_pairs()
    groups = {}
    sizes = (entry.STEPS - entry.BOUNDARY, HELD_OUT, HELD_OUT)
    for phrasing, (split, count) in enumerate(zip(SPLITS, sizes, strict=True)):
        rng = Random(SEED + 1009 * phrasing)
        plain, relations, golds, correction_pairs = [], [], [], []
        for index in range(count):
            language, other = (LANGUAGES[index % 2], LANGUAGES[1 - index % 2])
            turn = ("state_update", "question_change", "repeat")[index % 3]
            carry = index // 2 % 2
            pair = table_case(rng, other, phrasing, "correction")
            choice = "correction" if (index + index // 2) % 2 else "single"
            correction_pairs.append(dict(pair, selected=choice))
            plain.extend((arithmetic(next(pairs[carry]), language, "decimal", phrasing, rng),
                          arithmetic(next(pairs[1 - carry]), other, "worked_addition", phrasing, rng),
                          table_case(rng, language, phrasing, turn), pair[choice]))
            new_rows, gold = relation_graph(rng, language, phrasing)
            relations.extend(new_rows)
            golds.extend(gold)
        groups[split] = dict(plain=plain, relations=relations, gold=golds, correction_pairs=correction_pairs)
    return groups


def write_rows(path, rows):
    with path.open("x", encoding="utf-8") as stream:
        for item in rows:
            stream.write(json.dumps(item, ensure_ascii=False) + chr(10))
    return reference(path)


def audit_relation(rows, gold):
    for index, picked in enumerate(gold):
        candidates = rows[4 * index:4 * index + 4]
        record = candidates[0]["record"]
        ko = record["meta"]["language"] == "ko"
        request = record["messages"][0]["content"][0]["text"]
        roster, registry, question = request.split("\n\n")
        staff = {}
        for line in roster.splitlines()[1:]:
            name, number = line.split(" 담당 번호 " if ko else " / assignment ")
            staff[int(number)] = name
        options = []
        for line in registry.splitlines()[1:]:
            number, item, place = line.split(" / ")
            number = int(number.removeprefix("업무 " if ko else "Assignment "))
            item = item.removeprefix("물품 " if ko else "item ")
            place = place.removeprefix("도착 " if ko else "destination ")
            matches = (re.search(rf"업무 번호 {number}(?!\d)" if ko else rf"assignment {number}(?!\d)", question)
                       or ((f"물품이 {item}인" if ko else f"for the {item}") in question)
                       or ((f"도착지가 {place}인" if ko else f"to the {place}") in question))
            if matches:
                options.append(staff[number])
        answer = candidates[picked]["record"]["messages"][-1]["content"][0]["text"]
        if options != [answer]:
            raise ValueError("the printed register and question do not resolve to the designated answer")


def audit_sources(groups, tokenizer, end_id):
    inputs_by_split, roots_by_split, stats = {}, {}, {}
    answer_tokens = set()
    for split, group in groups.items():
        audit_relation(group["relations"], group["gold"])
        roots, inputs = set(), set()
        for item in (*group["plain"], *group["relations"]):
            roots.add(item["root"])
            record = item["record"]
            prompt = serialize(dict(messages=record["messages"][:-1]), "chatml", add_generation_prompt=True)
            inputs.add(digest(tokenizer.encode(prompt).ids))
        for case in group["correction_pairs"]:
            single, correction = (case[view]["record"] for view in ("single", "correction"))
            if (single["messages"][0] != correction["messages"][0]
                    or single["messages"][-1] != correction["messages"][-1]
                    or correction["messages"][1] == correction["messages"][-1]):
                raise ValueError("paired correction must retain the same question and verified reply")
            expected = []
            for record in (single, correction):
                text = serialize(record, "chatml")
                prefix = serialize(dict(messages=record["messages"][:-1]), "chatml", add_generation_prompt=True)
                encoded = tokenizer.encode(text)
                stop = text.rfind("<|im_end|>") + len("<|im_end|>")
                if not text.startswith(prefix) or stop < len(prefix):
                    raise ValueError("the final response boundary changed")
                correct_mask = [token if end > start and start >= len(prefix) and end <= stop else -100
                                for token, (start, end) in zip(encoded.ids, encoded.offsets, strict=True)][1:]
                if encode_record(record, tokenizer, context=entry.WIDTH).y != correct_mask:
                    raise ValueError("the first assistant reply must be input only for a correction")
                expected.append(tuple(value for value in correct_mask if value != -100))
                inputs.add(digest(tokenizer.encode(prefix).ids))
            if expected[0] != expected[1] or not expected[0] or expected[0][-1] != end_id:
                raise ValueError("single and correction must have equal final answer and termination tokens")
            answer_tokens.add(case["root"])
        if len(roots) != len(group["plain"]) + len(group["relations"]) // 16:
            raise ValueError("the authored material repeats a source inside one split")
        if any(roots & old for old in roots_by_split.values()) or any(inputs & old for old in inputs_by_split.values()):
            raise ValueError("authored roots or complete tokenized prompts overlap across splits")
        roots_by_split[split], inputs_by_split[split] = roots, inputs
        stats[split] = dict(roots=len(roots), plain=Counter(x["record"]["meta"]["family"] for x in group["plain"]),
                            relation_questions=len(group["gold"]), accepted_gold=Counter(group["gold"]),
                            plain_languages=Counter(x["record"]["meta"]["language"] for x in group["plain"]),
                            relation_languages=Counter(x["record"]["meta"]["language"] for x in group["relations"][::4]),
                            correction_views=Counter(x["selected"] for x in group["correction_pairs"]))
    return {split: sorted(roots) for split, roots in roots_by_split.items()}, stats, len(answer_tokens)


def build(output):
    if not output.is_relative_to(EVIDENCE) or entry.MICRO != 4 or entry.ACCUM <= RELATION_SLOTS[-1]:
        raise ValueError("P109C authored course needs its normal schedule and a new evidence directory")
    token_source = chat_tokenizer_path("ko-en").read_bytes()
    tokenizer = Tokenizer.from_str(token_source.decode("utf-8"))
    reserved = verify_chat_tokenizer(tokenizer, entry.VOCAB)
    groups = create_cases()
    roots, stats, verified_pairs = audit_sources(groups, tokenizer, reserved["<|im_end|>"])
    output.mkdir(exist_ok=False)
    token_path = output / "tokenizer.json"
    token_path.write_bytes(token_source)
    root_path = output / "roots.json"
    entry.publish(root_path, roots)
    paths = {}
    for split, group in groups.items():
        manifest = dict(plain=write_rows(output / f"{split}_plain.jsonl", group["plain"]),
                        all_axes=write_rows(output / f"{split}_relation.jsonl", group["relations"]), gold=group["gold"],
                        correction_pairs=write_rows(output / f"{split}_correction_pairs.jsonl", group["correction_pairs"]))
        paths[split] = manifest
    chosen = paths["train"]
    plan = dict(schema=compiler.SCHEMA, admission={"course": "LOCAL_AUTHORED_CANDIDATE"},
                tokenizer=reference(token_path), roots=reference(root_path),
                plain=dict(chosen["plain"], slots=PLAIN_SLOTS),
                all_axes=dict(chosen["all_axes"], slots=RELATION_SLOTS, gold=chosen["gold"]))
    plan_path = output / "schedule.json"
    entry.publish(plan_path, plan)
    compiled, compiled_sha = compiler.compile_schedule(plan_path, reference(plan_path)["sha256"], "compiled")
    rows = np.load(output / "compiled/plain.npy", mmap_mode="r", allow_pickle=False)
    alternatives = np.load(output / "compiled/all_axes.npy", mmap_mode="r", allow_pickle=False)
    labels = np.load(output / "compiled/decimal.npy", mmap_mode="r", allow_pickle=False)
    correct = np.arange(len(chosen["gold"])) * 4 + np.asarray(chosen["gold"])
    end = reserved["<|im_end|>"]
    ordinary = int(np.count_nonzero(rows[:, 1] != -100))
    positive = int(np.count_nonzero(alternatives[correct, 1] != -100))
    contrast = int(np.count_nonzero((alternatives[:, 1] != -100) & (alternatives[:, 1] != end)))
    if np.count_nonzero(labels[:, 0] != -1) != entry.STEPS - entry.BOUNDARY:
        raise ValueError("one verified decimal lesson per mixed update was expected")
    receipt = dict(seed=SEED, attribution="Original authored cases from generated arithmetic and invented records",
                   generation_source=reference(Path(__file__)), counts=stats, tokenizer=reference(token_path),
                   files=paths, roots=reference(root_path), verified_correction_pairs=verified_pairs,
                   compiled=dict(file=compiled.name, sha256=compiled_sha),
                   course_slots=int((len(rows) + len(alternatives)) * entry.WIDTH),
                   actual_input_ids=int(np.count_nonzero(rows[:, 0] != reserved["<pad>"])
                                        + np.count_nonzero(alternatives[:, 0] != reserved["<pad>"])),
                   supervised_nll_tokens=ordinary + positive, relation_comparison_content_tokens=contrast,
                   decimal_labels=int(np.count_nonzero(labels[:, 0] != -1)), status="AUTHORED_CPU_CANDIDATE")
    entry.publish(output / "report.json", receipt)
    for split, summary in stats.items():
        print("P109C_AUTHORED", split, json.dumps(summary, ensure_ascii=False), flush=True)
    print("P109C_AUTHORED_TARGETS", receipt["actual_input_ids"], receipt["supervised_nll_tokens"], contrast, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.output.resolve())
