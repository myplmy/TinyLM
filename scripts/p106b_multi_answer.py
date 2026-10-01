#!/usr/bin/env python3
"""Versioned teacher wire: one question, 2/4 answers; canonical roles stay code-owned."""
from __future__ import annotations
import hashlib
import json
import re
from scripts.p106b_teacher_format import content_instructions
from scripts.p106b_teacher_wrapper import wrap_turns


def multi_prompt(job: dict, count: int) -> list[dict]:
    if count not in (2, 4):
        raise ValueError("only 2/4 answer variants")
    fields = "[[QUESTION]]\n<one question>\n[[/QUESTION]]\n" + "\n".join(
        f"[[ANSWER_{index}]]\n<answer {index}>\n[[/ANSWER_{index}]]" for index in range(1, count + 1))
    instruction = (content_instructions(job["teacher_task"], job["target_language"])
        + " Produce one question and mutually consistent answers to that same question. "
          "Only vary phrasing where the source question allows it. A fixed literal/output format "
          "must remain identical when no other valid response exists. "
          "Where the question allows variation, answer 1 is concise, answer 2 explains briefly; when 4 are requested answer 3 uses two bullets "
          "and answer 4 is conversational. Preserve supported facts, entities, units and uncertainty. "
          "No private reasoning in final fields. No JSON wrapper, ChatML, roles, notes or text outside exact fields. "
          "JSON/code/foreign-language quotation inside an answer is allowed when required by the source question:\n" + fields)
    return [{"role": "system", "content": instruction},
            {"role": "user", "content": json.dumps(job["source_payload"], ensure_ascii=False)}]


def parse_multi(reply: dict, count: int, language: str) -> dict:
    if count not in (2, 4) or language not in ("ko", "en"):
        raise ValueError("unknown multi-answer contract")
    choices = reply.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ValueError("one completion sequence required, not API n=4")
    message = choices[0].get("message", {})
    final, reasoning = message.get("content") or "", message.get("reasoning_content") or ""
    if not isinstance(final, str) or not isinstance(reasoning, str):
        raise ValueError("reasoning/final must be strings")
    result = {"teacher_final_content": final, "teacher_reasoning_content": reasoning,
              "finish_reason": choices[0].get("finish_reason"),
              "usage": reply.get("usage", {}), "status": "INCOMPLETE", "parsed": None}
    if result["finish_reason"] != "stop":
        return result
    pattern = r"\A\s*\[\[QUESTION\]\]\s*\n(?P<question>.*?)\n\[\[/QUESTION\]\]"
    for index in range(1, count + 1):
        pattern += rf"\s*\n\[\[ANSWER_{index}\]\]\s*\n(?P<a{index}>.*?)\n\[\[/ANSWER_{index}\]\]"
    match = re.fullmatch(pattern + r"\s*\Z", final, flags=re.DOTALL)
    if match is None:
        result["status"] = "PARSE_ERROR"
        return result
    question = match.group("question").strip()
    answers = [match.group(f"a{index}").strip() for index in range(1, count + 1)]
    if (not 1 <= len(question) <= 2000 or any(not 1 <= len(a) <= 6000 for a in answers)
            or any(re.search(r"\[\[/?(?:QUESTION|ANSWER(?:_[1-4])?|NOTE)\]\]", text)
                   for text in [question] + answers)
            ):
        result["status"] = "EMPTY_OR_NESTED_FIELDS"
        return result
    result.update(status="MULTI_FORMAT_READY", parsed={"question": question, "answers": answers})
    return result


def replacement_prompt(job, replacement):
    slots = replacement["slots"]
    if not slots or any(type(i) is not int or i not in (1, 2, 3, 4) for i in slots):
        raise ValueError("replacement slots required")
    fields = "\n".join(f"[[ANSWER_{i}]]\n<replacement answer>\n[[/ANSWER_{i}]]" for i in slots)
    instruction = (content_instructions(job["teacher_task"], job["target_language"])
        + " The code has retained the question and successful answers. Return ONLY missing "
          "answer slots below; do not rewrite QUESTION or retained answers. Give consistent "
          "valid alternatives, not copies of retained answers. No JSON/roles/outside text:\n" + fields)
    return [{"role": "system", "content": instruction},
            {"role": "user", "content": json.dumps(replacement, ensure_ascii=False)}]


def parse_replacement(reply, replacement, language):
    slots = replacement["slots"]
    # Reuse the strict completion/type checks, then apply a missing-slot-only grammar.
    message = reply["choices"][0]["message"]
    final, reasoning = message.get("content") or "", message.get("reasoning_content") or ""
    if language not in ("ko", "en") or len(reply["choices"]) != 1 or not isinstance(final, str) or not isinstance(reasoning, str):
        raise ValueError("one replacement completion required")
    result = {"teacher_final_content": final, "teacher_reasoning_content": reasoning,
              "finish_reason": reply["choices"][0].get("finish_reason"),
              "usage": reply.get("usage", {}), "status": "INCOMPLETE", "parsed": None}
    if result["finish_reason"] != "stop":
        return result
    pattern = r"\A\s*" + r"\s*\n".join(
        rf"\[\[ANSWER_{i}\]\]\s*\n(?P<a{i}>.*?)\n\[\[/ANSWER_{i}\]\]" for i in slots) + r"\s*\Z"
    match = re.fullmatch(pattern, final, flags=re.DOTALL)
    if match is None:
        result["status"] = "PARSE_ERROR"
        return result
    answers = [match.group(f"a{i}").strip() for i in slots]
    if any(not 1 <= len(a) <= 6000 or re.search(r"\[\[/?(?:QUESTION|ANSWER(?:_[1-4])?|NOTE)\]\]", a) for a in answers):
        result["status"] = "EMPTY_OR_NESTED_FIELDS"
        return result
    result.update(status="MULTI_FORMAT_READY", parsed={"question": replacement["question"],
                  "answers": answers, "slots": slots})
    return result


def wrap_multi(job: dict, parsed: dict, generation_id: str, model_sha: str, reasoning_ref: str,
               requested_count=None) -> list[dict]:
    content = parsed["parsed"]
    reasoning = parsed["teacher_reasoning_content"]
    sha = hashlib.sha256(reasoning.encode()).hexdigest().upper() if reasoning else ""
    rows = []
    for index, answer in zip(content.get("slots", range(1, len(content["answers"]) + 1)), content["answers"]):
        row = wrap_turns([{"user_text": content["question"], "assistant_text": answer}],
            source_id=job["source_id"], source_sha256=job["source_sha256"],
            teacher_model_sha256=model_sha, language=job["target_language"],
            source_license=job["source_license"], generation_id=f"{generation_id}_a{index}",
            reasoning_ref=reasoning_ref if reasoning else "", reasoning_sha256=sha,
            source_repo=job["source_repo"], source_revision=job["source_revision"],
            source_object_id=job["source_id"], source_transform=job["source_transform"],
            parent_concept_id=job["parent_concept_id"], source_rights_status=job["rights_status"])
        row["meta"].update(answer_variant=index, variants_in_group=requested_count or len(content["answers"]),
            concept_group=job["parent_concept_id"], source_split=job["split"],
            semantic_consistency="MANUAL_REVIEW_REQUIRED")
        rows.append(row)
    return rows


def self_test() -> None:
    for count in (2, 4):
        text = "[[QUESTION]]\nWhat is 2+2?\n[[/QUESTION]]\n" + "\n".join(
            f"[[ANSWER_{i}]]\n4. Explanation variant {i}.\n[[/ANSWER_{i}]]" for i in range(1, count + 1))
        reply = {"choices": [{"finish_reason": "stop", "message": {
            "content": text, "reasoning_content": "sidecar only"}}]}
        assert parse_multi(reply, count, "en")["status"] == "MULTI_FORMAT_READY"
        bad = json.loads(json.dumps(reply))
        bad["choices"][0]["message"]["content"] += "\nextra"
        assert parse_multi(bad, count, "en")["status"] == "PARSE_ERROR"
        bad["choices"][0]["finish_reason"] = "length"
        assert parse_multi(bad, count, "en")["parsed"] is None
