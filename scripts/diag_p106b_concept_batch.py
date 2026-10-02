#!/usr/bin/env python3
"""User-run teacher-only distinct-concept 1/2/4 QA productivity gate.

One weight copy, xhigh, identical source set and output/thinking budgets.
Content is unverified. Parsing/context failures share <=3 physical attempts;
successful item slots never change on retries. No student model is loaded.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p106b_mixed_scale import TOK_SHA, TOKENIZER, digest, safe_repo_path
from scripts.p106b_teacher_format import content_instructions, parse_tagged, script_observations
from scripts.p106b_shards import ShardWriter, verify

OUTPUT = ROOT / "HF/sft_ready/p106b_concept_batch_v1"
ORDER = (1, 2, 4, 4, 2, 1)
PATTERN = re.compile(r"\s*\[\[ITEM_(\d+)\]\]\s*\n(.*?)\n\[\[/ITEM_\1\]\]", re.DOTALL)


def parse_batch(final, item_ids, *, allow_partial=False):
    if not isinstance(final, str) or not final.strip():
        raise ValueError("empty final batch")
    result, position = {}, 0
    for match in PATTERN.finditer(final):
        if final[position:match.start()].strip():
            raise ValueError("text outside item fields")
        ident = int(match[1])
        if ident not in item_ids or ident in result:
            raise ValueError("unknown or duplicate item ID")
        # Only transport fields are checked; words/truth/language are not gates.
        try:
            result[ident] = parse_tagged(match[2], language="en")
        except ValueError:
            if not allow_partial:
                raise
        position = match.end()
    if final[position:].strip() or not result:
        raise ValueError("extra or missing item framing")
    return result


def prompt(jobs, item_ids):
    languages = {j["target_language"] for j in jobs}
    if len(languages) != 1 or len(jobs) != len(item_ids):
        raise ValueError("homogeneous language and item mapping required")
    lang = jobs[0]["target_language"]
    system = content_instructions("answer_given", lang) + (
        " Each ITEM is a DIFFERENT source concept, not another answer variant. "
        "Write one focused question and answer for every requested ID. "
        "Keep the source intent/constraints; do not combine unrelated items. "
        "Never output JSON, roles, ChatML or commentary outside these fields. "
        "Private reasoning remains outside final content. Use exactly this framing for each ID:\n"
        "[[ITEM_<id>]]\n[[QUESTION]]\n<question>\n[[/QUESTION]]\n"
        "[[ANSWER]]\n<answer>\n[[/ANSWER]]\n[[/ITEM_<id>]]")
    items = [{"id": i, "source": job["source_payload"]} for i, job in zip(item_ids, jobs)]
    return [{"role": "system", "content": system},
            {"role": "user", "content": json.dumps({"items": items}, ensure_ascii=False)}]


def wrap_item(job, content, ident, teacher_sha, reasoning, raw_ref):
    from scripts.p106b_teacher_wrapper import wrap_turns
    if not isinstance(reasoning, str):
        raise ValueError("reasoning sidecar must be text")
    return wrap_turns([{"user_text": content["user_text"], "assistant_text": content["assistant_text"]}],
        source_id=job["source_id"], source_sha256=job["source_sha256"],
        teacher_model_sha256=teacher_sha, language=job["target_language"], source_license=job["source_license"],
        generation_id=ident, source_repo=job["source_repo"], source_revision=job["source_revision"],
        source_object_id=job["source_id"], source_transform="teacher_answer",
        parent_concept_id=job["parent_concept_id"], source_rights_status=job["rights_status"],
        reasoning_ref=raw_ref if reasoning else "",
        reasoning_sha256=hashlib.sha256(reasoning.encode()).hexdigest().upper() if reasoning else "")


def check():
    from scripts.p106b_gate_runtime import fixed_jobs, teacher_inputs, MODEL_SHA256
    safe_repo_path(OUTPUT)
    safe_repo_path(TOKENIZER)
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError("preserve existing concept-batch output")
    if digest(TOKENIZER) != TOK_SHA:
        raise ValueError("chat32 tokenizer differs")
    jobs, source = fixed_jobs(4)
    for job in jobs:
        wrap_item(job, {"user_text": "contract", "assistant_text": "contract"}, "contract",
                  MODEL_SHA256, "", "")  # Validate code-owned source enum/SHA before inference.
    for lang in ("ko", "en"):
        selected = [j for j in jobs if j["target_language"] == lang]
        if len(selected) != 4 or len({j["parent_concept_id"] for j in selected}) != 4:
            raise ValueError("need four distinct pinned source concepts per language")
    return jobs, {"schema": "P106B_CONCEPT_BATCH_PREFLIGHT_V1", "source": source,
                  **teacher_inputs(), "script_sha256": digest(Path(__file__)),
                  "tokenizer_sha256": TOK_SHA, "order": list(ORDER), "effort": "xhigh",
                  "context": 32768, "thinking_budget": 8192, "max_output": 16384,
                  "logical_requests": 28, "max_physical_requests": 84,
                  "student_training": "NOT_RUN", "formal_train_ready": False}


def execute(jobs, info):
    from tokenizers import Tokenizer
    from tinylm.data.sft import encode_conversation, sft_targets, IGNORE
    from scripts.p106b_teacher_wrapper import wrap_turns
    from scripts.p106b_gate_runtime import TeacherSession, idle_before_gpu, wall_limit, disposition, write_report, MODEL_SHA256
    from scripts.p106b_http_errors import capture_http_error
    from urllib.error import HTTPError
    idle_before_gpu()
    OUTPUT.mkdir(parents=True, exist_ok=False)
    raw, canonical = ShardWriter(OUTPUT, "raw"), ShardWriter(OUTPUT, "canonical")
    tok = Tokenizer.from_file(str(TOKENIZER))
    arms, session = [], None
    status, rc, reason = "PARTIAL", 9, "not started"
    began = time.perf_counter()
    try:
        with wall_limit(10800), TeacherSession(32768, 1, effort="xhigh", thinking_budget=8192) as session:
            for arm_index, size in enumerate(ORDER):
                t0 = time.perf_counter()
                metrics, accepted = Counter(), set()
                for lang in ("ko", "en"):
                    lang_jobs = [j for j in jobs if j["target_language"] == lang]
                    for start in range(0, 4, size):
                        block = {i: lang_jobs[i] for i in range(start, start + size)}
                        retained = {}
                        for attempt in range(1, 4):
                            missing = [i for i in block if i not in retained]
                            if not missing:
                                break
                            selected = [block[i] for i in missing]
                            messages = prompt(selected, missing)
                            ident = f"arm{arm_index}_{lang}_{start}_try{attempt}"
                            record = {"generation_id": ident, "source_jobs": selected,
                                      "requested_ids": missing, "reasoning_effort": "xhigh", "attempt": attempt,
                                      "semantic_truth": "PSEUDO_UNVERIFIED", "sampling": dict(__import__('scripts.diag_p106b_online_rate5', fromlist=['THINKING_SAMPLER']).THINKING_SAMPLER)}
                            parsed, reply = {}, None
                            admitted = session.count_prompt(messages, 32768, 16384)
                            record["admission"] = admitted
                            request_began = time.perf_counter()
                            metrics["attempts"] += 1
                            try:
                                if admitted["decision"] != "DIRECT":
                                    raise ValueError("input and reserved output exceed context")
                                metrics["completion_requests"] += 1
                                reply = session.complete(messages, 20261002 + start * 3 + attempt, 16384)
                                record["teacher_reply"] = reply
                                choices = reply.get("choices", [])
                                if len(choices) != 1 or choices[0].get("finish_reason") != "stop":
                                    raise ValueError("final batch not complete")
                                parsed = parse_batch(choices[0]["message"].get("content"), missing, allow_partial=True)
                                for item, content in parsed.items():
                                    job = block[item]
                                    reasoning = choices[0]["message"].get("reasoning_content") or ""
                                    row = wrap_item(job, content, ident + f"_item{item}", MODEL_SHA256,
                                                    reasoning, f"{OUTPUT.relative_to(ROOT)}/raw_shards_manifest.json#{ident}")
                                    ids, labels, _ = encode_conversation(row, tok)
                                    x, y = sft_targets(ids, labels)
                                    if not 0 < len(x) <= 1024 or not any(v != IGNORE for v in y):
                                        continue
                                    row["meta"].update(source_split=job["split"], batch_concepts=size,
                                                       arm_index=arm_index, input_context_fresh=True,
                                                       reasoning_is_student_target=False)
                                    retained[item] = row
                                record["status"] = "PARSED_TECHNICAL_ITEMS"
                            except HTTPError as exc:
                                record["backend_error"] = capture_http_error(exc, session.key)
                                record["status"] = "BACKEND_ERROR"
                            except ValueError as exc:
                                record.update(status="WIRE_OR_CONTEXT_REJECT", reason=str(exc))
                            finally:
                                record["request_wall_sec"] = time.perf_counter() - request_began
                                metrics["request_wall_sec"] += record["request_wall_sec"]
                                completion = (reply or {}).get("usage", {}).get("completion_tokens", 0)
                                metrics["completion_tokens"] += completion if type(completion) is int else 0
                                raw.append(record)
                                if raw._file:
                                    raw._file.flush()
                            if admitted["decision"] != "DIRECT":
                                break  # The unchanged over-budget payload cannot improve on retry.
                        for item, row in retained.items():
                            canonical.append(row)
                            ids, labels, _ = encode_conversation(row, tok)
                            metrics["student_x_tokens"] += len(ids) - 1
                            metrics["assistant_targets"] += sum(v != IGNORE for v in labels[1:])
                            accepted.add(lang + ":" + block[item]["parent_concept_id"])
                            print("[CONCEPT_QA] " + json.dumps({"arm": arm_index, "size": size, "row": row}, ensure_ascii=False), flush=True)
                wall = time.perf_counter() - t0
                arm = {"batch_concepts": size, **dict(metrics), "accepted_keys": sorted(accepted),
                       "wall_sec": wall, "student_x_tok_per_sec": metrics["student_x_tokens"] / wall,
                       "semantic_truth": "NOT_REVIEWED"}
                arms.append(arm)
                print("[CONCEPT_BATCH_ARM] " + json.dumps(arm, ensure_ascii=False), flush=True)
            session.require_valid_resources()
            complete = all(len(a["accepted_keys"]) == 8 for a in arms)
            ratios = {str(size): [arms[i]["student_x_tok_per_sec"] / arms[j]["student_x_tok_per_sec"]
                                  if arms[j]["student_x_tok_per_sec"] else 0 for i, j in indices]
                      for size, indices in ((2, ((1, 0), (4, 5))), (4, ((2, 0), (3, 5))))}
            status = "CONCEPT_BATCH_TECHNICAL_COMPLETE" if complete else "CONCEPT_BATCH_GATE_NEGATIVE"
            rc, reason = (0, "all source slots completed; speed and semantic quality remain separate") if complete else (8, "one or more fixed source slots missing after shared3 attempts")
    except (Exception, KeyboardInterrupt) as exc:
        status, rc = disposition(exc)
        reason = f"{type(exc).__name__}: {str(exc)[:250]}"
        ratios = {}
    report = {"schema": "P106B_CONCEPT_BATCH_GATE_V1", "input": info, "status": status, "exit_code": rc,
              "reason": reason, "arms": arms, "order_paired_rate_ratios": ratios,
              "speed_candidate": {s: len(v) == 2 and min(v) > 1.05 for s, v in ratios.items()},
              "whole_wall_sec": time.perf_counter() - began, "server": session.evidence() if session else None,
              "semantic_truth": "NOT_REVIEWED", "student_updates": 0, "checkpoint_saved": False}
    for name, writer in (("raw", raw), ("canonical", canonical)):
        if writer._total_rows:
            spec = writer.close(lineage=info)
            verify(OUTPUT, spec)
            report[name + "_concat_sha256"] = spec["concat_sha256"]
    write_report(OUTPUT / "report.json", report)
    print("[CONCEPT_BATCH_SUMMARY] " + json.dumps(report, ensure_ascii=False), flush=True)
    return rc


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-only", action="store_true")
    group.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    jobs, info = check()
    if args.check_only:
        print(json.dumps(info, ensure_ascii=False))
        return 0
    return execute(jobs, info)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        print(f"[STOP] {exc}", file=sys.stderr)
        raise SystemExit(9)
