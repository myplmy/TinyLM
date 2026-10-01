#!/usr/bin/env python3
"""Durable teacher candidates and streamed assistant-only student accumulation.

Importing this module does not load a model. Runtime callers explicitly own one
server and one student; all rows keep source/concept/split provenance.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
import math
import os
import threading
import time
from urllib.error import HTTPError

from scripts.p106b_gate_runtime import ROOT, MODEL_SHA256, TOKENIZER, ToolFailure, disposition
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_teacher_format import teacher_prompt, parse_reply, script_observations
from scripts.p106b_teacher_wrapper import wrap_turns
from scripts.p106b_multi_answer import multi_prompt, parse_multi, wrap_multi, replacement_prompt, parse_replacement
from scripts.p106b_http_errors import capture_http_error
from scripts.train_sft_p090 import encode_records, loss_sum


def flush_row(writer):
    # Persistence precedes queue admission. No earlier version is rewritten.
    writer._file.flush()
    os.fsync(writer._file.fileno())


def validate_job_contract(job):
    """Validate code-owned provenance before paying for a teacher response."""
    wrap_turns([{"user_text": "contract", "assistant_text": "contract"}],
        source_id=job["source_id"], source_sha256=job["source_sha256"],
        teacher_model_sha256=MODEL_SHA256, language=job["target_language"],
        source_license=job["source_license"], generation_id="contract",
        source_repo=job["source_repo"], source_revision=job["source_revision"],
        source_object_id=job["source_id"], source_transform=job["source_transform"],
        parent_concept_id=job["parent_concept_id"], source_rights_status=job["rights_status"])


def response_diagnostic(reply, maximum):
    """Observe wire completion without loosening the final-field parser.

    Reasoning/final lengths are characters, not inferred model-token counts.
    The server completion token count includes both and is retained separately.
    """
    choices = reply.get("choices", []) if isinstance(reply, dict) else []
    choices = choices if isinstance(choices, list) else []
    choice = choices[0] if len(choices) == 1 and isinstance(choices[0], dict) else {}
    message = choice.get("message", {})
    message = message if isinstance(message, dict) else {}
    usage = reply.get("usage", {}) if isinstance(reply, dict) else {}
    usage = usage if isinstance(usage, dict) else {}
    final = message.get("content") or ""
    reasoning = message.get("reasoning_content") or ""
    final_chars = len(final) if isinstance(final, str) else None
    reasoning_chars = len(reasoning) if isinstance(reasoning, str) else None
    finish = choice.get("finish_reason")
    completion = usage.get("completion_tokens")
    at_output_limit = (type(completion) is int and completion >= maximum)
    if finish == "length" and at_output_limit:
        if final_chars == 0:
            cause = "OUTPUT_LIMIT_REASONING_ONLY" if reasoning_chars else "OUTPUT_LIMIT_NO_VISIBLE_CONTENT"
        else:
            cause = "OUTPUT_LIMIT_PARTIAL_FINAL"
    elif finish == "length":
        cause = "FINISH_LENGTH_OTHER_OR_UNKNOWN_LIMIT"
    elif finish == "stop":
        cause = "STOPPED_FINAL_PRESENT" if final_chars else "STOPPED_WITHOUT_FINAL"
    else:
        cause = "NO_REPLY" if reply is None else "OTHER_FINISH_REASON"
    return {"cause": cause, "finish_reason": finish, "requested_max_output": maximum,
            "at_requested_output_limit": at_output_limit,
            "server_usage": usage, "reasoning_chars": reasoning_chars, "final_chars": final_chars,
            "length_units": "characters, not model tokens"}


class CandidateWriter:
    def __init__(self, directory, lineage, *, observer=None):
        from tokenizers import Tokenizer
        self.directory, self.lineage = directory, lineage
        self.raw, self.canonical = ShardWriter(directory, "raw"), ShardWriter(directory, "canonical")
        self.tok = Tokenizer.from_file(str(TOKENIZER))
        self.lock = threading.Lock()
        self.counts, self.accepted = Counter(), Counter()
        self.raw_count = self.row_count = self.completion = self.tokens = self.targets = 0
        self.request_sec = 0.0
        self.seen = set()
        self.response_diagnostics, self.response_causes = {}, Counter()
        self.observer = observer

    def request(self, session, job, ident, seed, *, count=1, per_slot=3072, maximum=2048, dedupe_scope="", replacement=None, output_contract=None):
        validate_job_contract(job)
        messages = (replacement_prompt(job, replacement) if replacement else
                    (teacher_prompt(job["teacher_task"], job["target_language"], job["source_payload"])
                     if count == 1 else multi_prompt(job, count)))
        admission = session.count_prompt(messages, per_slot, maximum)
        record = {"generation_id": ident, "source": job, "admission": admission,
                  "accepted_for_training": False, "semantic_truth": "PSEUDO_UNVERIFIED",
                  "seed": seed, "reasoning_effort": getattr(session, "effort", "UNRECORDED_LABEL"),
                  "thinking_budget_tokens_requested": getattr(session, "thinking_budget", None),
                  "requested_answers": count, "dedupe_scope": dedupe_scope,
                  "replacement_contract": replacement, "output_contract": output_contract}
        rows = []
        completion_call_attempted = False
        t0 = time.monotonic()
        backend, processing_error, processing_exception, reply = None, None, None, None
        if admission["decision"] != "DIRECT":
            record["screen_status"] = admission["decision"]
        else:
            try:
                completion_call_attempted = True
                reply = session.complete(messages, seed, maximum)
                parsed = (parse_replacement(reply, replacement, job["target_language"]) if replacement else
                          (parse_reply(reply, language=job["target_language"]) if count == 1
                           else parse_multi(reply, count, job["target_language"])))
                record.update(teacher=parsed, screen_status=parsed["status"] if count != 1 else parsed["format_status"])
                content = parsed.get("parsed") if count != 1 else parsed.get("parsed_content")
                record["transport_complete"] = bool(content)
                if content:
                    reasoning = parsed["teacher_reasoning_content"]
                    ref = f"{self.directory.relative_to(ROOT)}/raw_shards_manifest.json#{ident}"
                    if count == 1:
                        row = wrap_turns([{key: content[key] for key in ("user_text", "assistant_text")}],
                            correction_note=content.get("correction_note", ""), source_id=job["source_id"],
                            source_sha256=job["source_sha256"], teacher_model_sha256=MODEL_SHA256,
                            language=job["target_language"], source_license=job["source_license"],
                            generation_id=ident, reasoning_ref=ref if reasoning else "",
                            reasoning_sha256=hashlib.sha256(reasoning.encode()).hexdigest().upper() if reasoning else "",
                            source_repo=job["source_repo"], source_revision=job["source_revision"],
                            source_object_id=job["source_id"], source_transform=job["source_transform"],
                            parent_concept_id=job["parent_concept_id"], source_rights_status=job["rights_status"])
                        row["meta"].update(source_split=job["split"], answer_variant=1, variants_in_group=1)
                        rows = [row]
                    else:
                        rows = wrap_multi(job, parsed, ident, MODEL_SHA256, ref, count)
                    if output_contract is not None:
                        from scripts.p106b_output_contract import row_text, text_sha
                        for candidate in rows:
                            candidate["meta"]["output_contract"] = output_contract
                            candidate["meta"]["output_contract_effective"] = (
                                output_contract["kind"] if text_sha(row_text(candidate, 0)) == output_contract["question_sha256"] else "UNKNOWN")
                    if self.observer is not None:
                        from scripts.p106b_output_contract import row_text
                        observation = self.observer.observe(ident, row_text(rows[0], 0),
                                                           [row_text(r, 1) for r in rows])
                        record["lexical_observation"] = observation
                        print("[LEXICAL_OBSERVATION] " + json.dumps(observation, ensure_ascii=False), flush=True)
                    for candidate in rows:
                        for message in candidate["messages"]:
                            text = message["content"]
                            if not isinstance(text, str):
                                text = "".join(p["text"] for p in text if p["type"] == "text")
                            observed = script_observations(text, job["target_language"])
                            if observed:
                                print("[CHARACTER_OBSERVATION] " + json.dumps({"id": ident,
                                    "role": message["role"], "requested_language": job["target_language"],
                                    "observations": observed,
                                    "effect": "WARNING_ONLY_NOT_LANGUAGE_OR_TRUTH_JUDGEMENT"}, sort_keys=True), flush=True)
                    try:
                        encoded = encode_records(rows, self.tok, 1024, 32768)
                    except ValueError as exc:
                        record.update(screen_status="STUDENT_CONTEXT_REJECT", screen_error=str(exc)[:200])
                        rows = []
            except HTTPError as exc:
                backend = capture_http_error(exc, session.key)
                record.update(backend_error=backend, screen_status=backend["classification"])
            except Exception as exc:
                # A paid response must survive parser/wrapper errors as an immutable raw record.
                processing_error = {"type": type(exc).__name__, "reason": str(exc)[:200]}
                processing_exception = exc
                record.update(teacher_raw_reply=reply, processing_error=processing_error,
                              screen_status="PIPELINE_PROCESSING_ERROR")
                rows = []
        record["wall_sec"] = round(time.monotonic() - t0, 6)
        diagnostic = response_diagnostic(reply, maximum)
        diagnostic["completion_call_attempted"] = completion_call_attempted
        diagnostic["transport_complete"] = record.get("transport_complete", False)
        record["response_diagnostic"] = diagnostic
        with self.lock:
            fingerprints = [dedupe_scope + ":" + hashlib.sha256(json.dumps(row["messages"],
                ensure_ascii=False, sort_keys=True).encode()).hexdigest() for row in rows]
            kept, kept_hashes, duplicate_slots = [], [], []
            retained_answers = set((replacement or {}).get("retained_answers", {}).values())
            for row, fingerprint in zip(rows, fingerprints):
                from scripts.p106b_output_contract import row_text
                if (fingerprint in self.seen or fingerprint in kept_hashes
                        or row_text(row, 1) in retained_answers):
                    duplicate_slots.append(row["meta"].get("answer_variant", 1))
                else:
                    kept.append(row)
                    kept_hashes.append(fingerprint)
            rows, fingerprints = kept, kept_hashes
            if duplicate_slots:
                record["screen_status"] = "PARTIAL_EXACT_DUPLICATE" if rows else "EXACT_DUPLICATE"
            record["duplicate_slots"] = diagnostic["duplicate_slots"] = duplicate_slots
            # Retained rows alone contribute to token/target accounting.
            encoded = encode_records(rows, self.tok, 1024, 32768) if rows else []
            diagnostic["wire_screen_status"] = record["screen_status"]
            self.raw.append(record)
            flush_row(self.raw)
            self.raw_count += 1
            self.counts[record["screen_status"]] += 1
            self.response_diagnostics[ident] = diagnostic
            self.response_causes[diagnostic["cause"]] += 1
            usage = (record.get("teacher", {}).get("usage", {})
                     or (reply.get("usage", {}) if isinstance(reply, dict) else {}) or {})
            self.completion += usage.get("completion_tokens", 0) or 0
            self.request_sec += record["wall_sec"]
            if rows:
                self.seen.update(fingerprints)
                for row in rows:
                    self.canonical.append(row)
                    self.row_count += 1
                flush_row(self.canonical)
                self.tokens += sum(len(r[0]) for r in encoded)
                self.targets += sum(r[2] for r in encoded)
                self.accepted[job["target_language"]] += 1
        print("[PIPELINE_ITEM] " + json.dumps({"id": ident, "language": job["target_language"],
            "status": record["screen_status"], "rows": len(rows)}, sort_keys=True), flush=True)
        if backend and backend["classification"] != "PEG_NATIVE_MISMATCH":
            raise ToolFailure("unknown teacher backend error; raw body evidence retained")
        if processing_error:
            if disposition(processing_exception)[1] == 8:
                raise processing_exception
            raise ToolFailure("teacher response processing failed; raw reply retained: "
                              + processing_error["type"] + ": " + processing_error["reason"])
        return rows

    def close(self):
        output = {"raw_rows": self.raw_count, "canonical_rows": self.row_count,
                  "status_counts": dict(self.counts), "accepted_groups": dict(self.accepted),
                  "response_cause_counts": dict(self.response_causes),
                  "teacher_completion_tokens": self.completion, "request_sum_sec": self.request_sec,
                  "student_conversation_tokens": self.tokens, "assistant_targets": self.targets}
        for name, writer, count in (("raw", self.raw, self.raw_count),
                                    ("canonical", self.canonical, self.row_count)):
            if count:
                spec = writer.close(lineage=self.lineage)
                verify(self.directory, spec)
                output[f"{name}_concat_sha256"] = spec["concat_sha256"]
        return output


class StudentAccumulator:
    def __init__(self):
        from tokenizers import Tokenizer
        from scripts.diag_p106b_online_pseudo_sft import student_model_and_optimizers
        self.torch, self.model, self.base, self.adam, self.muon, self.cfg, self.parent_step, self.cache = student_model_and_optimizers()
        self.tok = Tokenizer.from_file(str(TOKENIZER))
        self.pad = self.tok.token_to_id("<pad>")
        if self.pad is None:
            raise ToolFailure("student PAD token absent")
        self.adam.zero_grad(set_to_none=True)
        self.muon.zero_grad(set_to_none=True)
        self.torch.cuda.reset_peak_memory_stats()
        self.targets = self.tokens = self.rows = 0
        self.total_loss = 0.0
        self.micro_seconds = []
        self.used = []
        self.monitor = lambda: None

    def add(self, rows):
        if not 1 <= len(rows) <= 8 or self.rows + len(rows) > 128:
            raise ValueError("microbatch 1..8 and at most128 rows per single optimizer")
        encoded = encode_records(rows, self.tok, 1024, self.cfg.vocab_size)
        self.monitor()
        began = time.monotonic()
        part = loss_sum(self.model, encoded, self.pad, self.torch.device("cuda"), self.cfg.vocab_size, 2048)
        if not bool(self.torch.isfinite(part)):
            raise ToolFailure("nonfinite assistant-only loss")
        self.total_loss += float(part.detach())
        part.backward()
        self.torch.cuda.synchronize()
        self.monitor()
        self.micro_seconds.append(time.monotonic() - began)
        self.targets += sum(r[2] for r in encoded)
        self.tokens += sum(len(r[0]) for r in encoded)
        self.rows += len(rows)
        self.used.extend({"generation_id": row["meta"]["generation_id"],
            "parent_concept_id": row["meta"]["parent_concept_id"],
            "answer_variant": row["meta"].get("answer_variant", 1)} for row in rows)

    def finish(self, *, require_full=False):
        if not self.targets or (require_full and (self.rows != 128 or len(self.micro_seconds) != 16)):
            raise ToolFailure("optimizer refused: incomplete registered accumulation")
        t0 = time.monotonic()
        self.monitor()
        for param in self.model.parameters():
            if param.grad is not None:
                param.grad.div_(self.targets)
        grad = self.torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
        if not math.isfinite(float(grad)):
            raise ToolFailure("nonfinite gradient")
        self.adam.step()
        self.muon.step()
        self.torch.cuda.synchronize()
        self.monitor()
        return {"optimizer_updates": 1, "rows": self.rows, "processed_conversation_tokens": self.tokens,
                "assistant_targets": self.targets, "assistant_train_ce": self.total_loss / self.targets,
                "grad_norm_before_clip": float(grad), "student_micro_wall_sec": self.micro_seconds,
                "first_micro_wall_sec": self.micro_seconds[0],
                "optimizer_wall_sec": time.monotonic() - t0,
                "student_peak_reserved_mib": self.torch.cuda.max_memory_reserved() / 1048576,
                "micro": 8, "accum_limit": 16, "checkpoint_on": True,
                "compile": "default", "checkpoint_saved": False,
                "parent_step": self.parent_step, "used_rows": self.used,
                "scope": "partial resource update" if self.rows != 128 else "one full128 SFT update"}
