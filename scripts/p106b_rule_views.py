"""Opt-in, code-owned QA views; no teacher, tokenizer, files or training.

Only an explicit public/code task contract may be transformed. The first
question stays fixed across views to preserve the existing SFT split key.
Both assistant turns are correct under their respective stated inputs.
This library is not connected to the current corpus builder or epoch reader.
"""
from __future__ import annotations

import copy
import hashlib
import json
import random
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tinylm.chat.canonical import normalize, validate

VERSION = "P106B_RULE_VIEW_V2"
KINDS = ("integer_arithmetic", "boolean_expression", "table_lookup", "json_projection", "fixed_literal")


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest().upper()


def _integer(value):
    if type(value) is not int or abs(value) > 1_000_000:
        raise ValueError("bounded integer required, not bool/float")
    return value


def _check(spec, *, format_only=False):
    if not isinstance(spec, dict) or spec.get("owner") not in ("code", "reviewed_source_contract"):
        raise ValueError("explicit producer/reviewed contract required; no text inference")
    if spec.get("language") not in ("ko", "en") or spec.get("split") != "train":
        raise ValueError("augmentation is train-only; language must be ko/en")
    allowed = KINDS + (("verbatim_qa",) if format_only else ())
    if spec.get("kind") not in allowed or not isinstance(spec.get("payload"), dict):
        raise ValueError("unsupported task contract")
    if not isinstance(spec.get("root_id"), str) or not spec["root_id"].strip():
        raise ValueError("root identity required")
    source = spec.get("source", {})
    if not isinstance(source, dict) or source.get("scope") != "public_or_code":
        raise ValueError("protected/unknown source is not authorized")
    for name in ("family", "license", "sha256"):
        if not isinstance(source.get(name), str) or not source[name].strip():
            raise ValueError("source family/license/sha256 required")
    sha = source["sha256"]
    if len(sha) != 64 or any(c not in "0123456789abcdefABCDEF" for c in sha):
        raise ValueError("invalid declared source SHA-256")
    if len(_json(spec).encode("utf-8")) > 100_000:
        raise ValueError("contract is too large")


def _boolean(expr, values, depth=0):
    """Evaluate a bounded code-owned Boolean AST, never Python eval."""
    if depth > 8:
        raise ValueError("Boolean expression depth exceeds contract")
    if type(expr) is bool:
        return expr, str(expr).lower()
    if isinstance(expr, str) and expr in values:
        return values[expr], expr
    if not isinstance(expr, dict) or set(expr) != {"op", "args"}:
        raise ValueError("invalid Boolean AST")
    op, args = expr["op"], expr["args"]
    if op not in ("not", "and", "or", "xor", "implies", "eq") or not isinstance(args, list):
        raise ValueError("unknown Boolean operation")
    if len(args) != (1 if op == "not" else 2):
        raise ValueError("Boolean arity mismatch")
    children = [_boolean(arg, values, depth + 1) for arg in args]
    if op == "not":
        return not children[0][0], f"NOT ({children[0][1]})"
    a, b = children[0][0], children[1][0]
    result = {"and": a and b, "or": a or b, "xor": a != b,
              "implies": (not a) or b, "eq": a == b}[op]
    return result, f"({children[0][1]} {op.upper()} {children[1][1]})"


def _render(spec, payload):
    ko, kind = spec["language"] == "ko", spec["kind"]
    if kind == "integer_arithmetic":
        a, b = _integer(payload["a"]), _integer(payload["b"])
        op = payload["op"]
        if op not in ("+", "-", "*"):
            raise ValueError("only declared integer +,-,* operations")
        value = a + b if op == "+" else a - b if op == "-" else a * b
        question = (f"{a} {op} {b}의 값만 정수로 답하세요." if ko
                    else f"Return only the integer value of {a} {op} {b}.")
        answer = str(value)
    elif kind == "boolean_expression":
        values = payload["values"]
        if (not isinstance(values, dict) or not 1 <= len(values) <= 8
                or any(not isinstance(k, str) or not k or type(v) is not bool for k, v in values.items())):
            raise ValueError("explicit bounded Boolean variables required")
        value, expression = _boolean(payload["expression"], values)
        question = (f"변수 {_json(values)}일 때 논리식 {expression}의 값만 true 또는 false로 답하세요." if ko
                    else f"Variables {_json(values)}. Return only true or false for {expression}.")
        answer = str(value).lower()
    elif kind == "table_lookup":
        entries = payload["entries"]
        if (not isinstance(entries, list) or not 2 <= len(entries) <= 16
                or any(not isinstance(e, list) or len(e) != 2
                       or any(not isinstance(v, str) or not v.strip() for v in e) for e in entries)):
            raise ValueError("bounded nonempty string table required")
        if len({e[0] for e in entries}) != len(entries) or payload["target"] not in dict(entries):
            raise ValueError("duplicate entity or absent lookup target")
        table = _json(entries)
        question = (f"표 {table}에서 {payload['target']}에 해당하는 값만 쓰세요." if ko
                    else f"Table {table}. Return only the value for {payload['target']}.")
        answer = dict(entries)[payload["target"]]
    elif kind == "json_projection":
        record, fields = payload["record"], payload["fields"]
        if (not isinstance(record, dict) or not 1 <= len(record) <= 16
                or any(not isinstance(k, str) or not k for k in record)
                or any(type(v) not in (str, int, float, bool, type(None)) for v in record.values())
                or not isinstance(fields, list) or not fields
                or any(not isinstance(k, str) or k not in record for k in fields)
                or len(set(fields)) != len(fields)):
            raise ValueError("explicit scalar record and existing field names required")
        question = (f"입력 {_json(record)}에서 {_json(fields)} 필드만 가진 JSON 객체를 출력하세요." if ko
                    else f"Input {_json(record)}. Return only a JSON object with fields {_json(fields)}.")
        answer = _json({k: record[k] for k in fields})
    else:
        if any(not isinstance(payload.get(k), str) or not payload[k] for k in ("question", "answer")):
            raise ValueError("explicit fixed question/answer required")
        return payload["question"], payload["answer"]
    fmt = spec.get("output_format", "plain")
    if fmt not in ("plain", "answer_json") or (kind == "json_projection" and fmt != "plain"):
        raise ValueError("unsupported output envelope")
    if fmt == "answer_json":
        question += (" answer 항목 하나에 답 문자열을 넣은 JSON만 출력하세요." if ko
                     else " Return only JSON with exactly one answer key containing the answer string.")
        answer = _json({"answer": answer})
    return question, answer


def make_rule_view(spec, *, seed, view_index):
    """Return canonical training context + derived QA, without mutating inputs."""
    _check(spec)
    if type(seed) is not int or type(view_index) is not int or not 0 <= view_index <= 9999:
        raise ValueError("integer seed and bounded view index required")
    original = copy.deepcopy(spec["payload"])
    base_question, base_answer = _render(spec, original)
    payload = copy.deepcopy(original)
    rng = random.Random(int(_digest([VERSION, spec["root_id"], seed, view_index]), 16))
    kind = spec["kind"]
    if kind == "integer_arithmetic":
        low, high = _integer(spec["minimum"]), _integer(spec["maximum"])
        if not low <= original["a"] <= high or not low <= original["b"] <= high or not 0 <= high - low <= 100:
            raise ValueError("original operands must lie in the declared bounded domain")
        alternatives = [(a, b) for a in range(low, high + 1) for b in range(low, high + 1)
                        if (a, b) != (original["a"], original["b"])]
        if alternatives:
            payload["a"], payload["b"] = rng.choice(alternatives)
    elif kind == "boolean_expression":
        name = rng.choice(sorted(payload["values"]))
        payload["values"][name] = not payload["values"][name]
    elif kind == "table_lookup":
        rng.shuffle(payload["entries"])
        targets = [e[0] for e in payload["entries"] if e[0] != original["target"]]
        payload["target"] = rng.choice(targets)
    elif kind == "json_projection":
        names = sorted(payload["record"])
        alternatives = [[k] for k in names if [k] != original["fields"]]
        if alternatives:
            payload["fields"] = rng.choice(alternatives)
    question, answer = _render(spec, payload)
    changed = (question, answer) != (base_question, base_answer)
    messages = [{"role": "user", "content": base_question},
                {"role": "assistant", "content": base_answer}]
    if changed:
        messages += [{"role": "user", "content": question}, {"role": "assistant", "content": answer}]
    row = validate(normalize({"messages": messages, "meta": {
        "source": "p106b_rule_views", "source_id": f"{spec['root_id']}/view{view_index:04d}",
        "source_family": spec["source"]["family"], "source_license": spec["source"]["license"],
        "source_sha256": spec["source"]["sha256"].upper(), "root_concept_id": spec["root_id"],
        "split": "train", "language": spec["language"], "rule_view_version": VERSION,
        "source_contract_sha256": _digest(spec), "seed": seed, "view_index": view_index,
        "task_kind": kind, "derived_payload": payload, "changed": changed,
        "augmentation_status": "RULE_VIEW_READY" if changed else "UNCHANGED_PROTECTED",
        "truth_scope": "declared operation only; no factual source verification",
        "unique_knowledge_claim": False, "dataset_token_coverage": "NOT_MEASURED",
        "source_original": original}}))
    base = normalize({"messages": messages[:2]})
    # The existing splitter hashes normalized first-user text. Exact canonical
    # equality is stronger and avoids importing data.prepare/runtime dependencies.
    if base["messages"][0]["content"] != row["messages"][0]["content"]:
        raise ValueError("first-question split identity changed")
    if len(_json(row).encode("utf-8")) > 1_000_000:
        raise ValueError("row too large for bounded shard assembly")
    return row


def condition_question(spec, payload):
    """Shared renderer for changed/sham conditions and new closed probes."""
    p, ko = payload, spec["language"] == "ko"
    if spec["kind"] == "integer_arithmetic":
        question = (f"앞의 계산에서 첫 수를 {p['a']}, 둘째 수를 {p['b']}로 바꾸세요. 연산과 출력 형식은 유지하고 새 답만 쓰세요." if ko
                    else f"In the previous calculation change the first number to {p['a']} and the second to {p['b']}. Keep the operation and output format; return only the new answer.")
    elif spec["kind"] == "boolean_expression":
        question = (f"앞의 논리식은 유지하고 변수 값을 {_json(p['values'])}로 바꾸세요. 같은 출력 형식으로 새 값만 답하세요." if ko
                    else f"Keep the previous expression, change variables to {_json(p['values'])}, and return only its new value in the same format.")
    elif spec["kind"] == "table_lookup":
        order = _json([e[0] for e in p["entries"]])
        question = (f"앞 표의 값은 유지하고 행 순서를 {order}로 바꾸세요. 이번에는 {p['target']}의 값만 같은 형식으로 답하세요." if ko
                    else f"Keep the previous table values, reorder rows as {order}, and return only {p['target']}'s value in the same format.")
    else:
        question = (f"앞 입력은 유지하고 이번에는 {_json(p['fields'])} 필드만 있는 JSON을 출력하세요." if ko
                    else f"Keep the previous input and return only JSON with fields {_json(p['fields'])} this time.")
    return question


def make_condition_followup(spec, *, seed, view_index):
    """C1: change explicit conditions, retain two code-correct assistant turns."""
    row = make_rule_view(spec, seed=seed, view_index=view_index)
    row["meta"]["followup_kind"] = "C1_CONDITION_UPDATE"
    if not row["meta"]["changed"]:
        return row
    row["messages"][-2]["content"][0]["text"] = condition_question(spec, row["meta"]["derived_payload"])
    return validate(row)


def make_format_followup(spec, *, view_index=0, field_name="answer"):
    """C3: verbatim answer-to-JSON; no factual correction or semantic rewrite."""
    _check(spec, format_only=True)
    if type(view_index) is not int or not 0 <= view_index <= 9999:
        raise ValueError("bounded view index required")
    if field_name not in ("answer", "value", "result", "reply"):
        raise ValueError("producer-known format field required")
    question, answer = _render(spec, spec["payload"])
    ko = spec["language"] == "ko"
    followup = (f"앞서 한 답변의 문자열 전체를 {field_name} 항목 하나에 넣은 JSON 객체만 출력하세요. 내용을 고치거나 요약하지 마세요." if ko
                else f"Return only one JSON object with exactly one {field_name} key containing your entire previous answer string. Do not correct or summarize its content.")
    return validate(normalize({"messages": [
        {"role": "user", "content": question}, {"role": "assistant", "content": answer},
        {"role": "user", "content": followup}, {"role": "assistant", "content": _json({field_name: answer})}],
        "meta": {"source": "p106b_rule_views", "source_id": f"{spec['root_id']}/format{view_index:04d}",
        "source_family": spec["source"]["family"], "source_license": spec["source"]["license"],
        "source_sha256": spec["source"]["sha256"].upper(), "root_concept_id": spec["root_id"],
        "source_contract_sha256": _digest(spec), "source_original": copy.deepcopy(spec["payload"]),
        "language": spec["language"], "split": "train", "rule_view_version": VERSION,
        "followup_kind": "C3_VERBATIM_FORMAT", "unique_knowledge_claim": False,
        "output_contract": {"kind": "UNIQUE_JSON", "key": field_name, "value": answer},
        "dataset_token_coverage": "NOT_MEASURED", "original_factual_truth": "NOT_REVIEWED",
        "truth_scope": "verbatim format transformation only"}}))
