"""Code-owned output contracts and one shared physical-request recovery budget.

No semantic classifier, word blacklist, model call or file access on import.
A teacher-supplied type is not authority. Reviewed annotations can later enter
through the same hash-bound adapter, without an automatic reviewer here.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
from scripts.p106b_request_budget import RequestBudget


def text_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def row_text(row, position):
    value = row["messages"][position]["content"]
    return value if isinstance(value, str) else "".join(p["text"] for p in value if p["type"] == "text")


@dataclass(frozen=True)
class OutputContract:
    kind: str = "UNKNOWN"
    question: str = ""
    authority: str = ""
    reference: str = ""
    literal: str | None = None

    def __post_init__(self):
        if self.kind not in ("UNKNOWN", "EXACT_LITERAL", "CONSTRAINED_UNKNOWN", "VARIANT_ALLOWED"):
            raise ValueError("unknown output contract")
        if self.kind != "UNKNOWN" and (not self.question or not self.reference
                or self.authority not in ("CODE_TEMPLATE", "REVIEWED_SOURCE")):
            raise ValueError("known contracts need question-bound code/review authority")
        if self.kind == "EXACT_LITERAL" and not isinstance(self.literal, str):
            raise ValueError("literal output required")

    def effective_kind(self, question):
        return self.kind if question == self.question else "UNKNOWN"

    def as_dict(self):
        return {"kind": self.kind, "question_sha256": text_sha(self.question),
                "authority": self.authority, "reference": self.reference,
                "literal": self.literal}


def reviewed_contract(question, annotation, *, expected_revision, approval_ref):
    """Future offline B adapter: caller supplies an explicitly approved record.

    Mere presence of JSON/teacher tags is not a review. No auto-classification or
    directory scanning is performed. Unknown/mismatching annotations fail closed.
    """
    if (not approval_ref or annotation.get("approval_ref") != approval_ref
            or annotation.get("revision") != expected_revision
            or annotation.get("question_sha256") != text_sha(question)
            or annotation.get("status") != "REVIEWED"):
        raise ValueError("reviewed output contract identity/approval differs")
    return OutputContract(annotation["kind"], question, "REVIEWED_SOURCE",
                          approval_ref, annotation.get("literal"))


def request_group(writer, session, job, ident, seed, *, count, per_slot, maximum,
                  contract=None, maximum_attempts=3, encode=None, on_attempt=None):
    """Keep successful slots; only trusted variants recover exact duplicates.

    HTTP/parse/encoding recovery and duplicate-slot recovery consume this same
    maximum three attempts. A non-direct prompt admission is not retryable.
    Unknown/literal duplicate answers never create a variation retry.
    """
    if count not in (1, 2, 4):
        raise ValueError("one/two/four answer contract required")
    contract = contract or OutputContract()
    budget, retained, locked_question = RequestBudget(maximum_attempts), {}, None
    next_reason, replacement = "initial", None
    traces = []
    while budget.remaining:
        attempt = budget.take(next_reason)
        generation = f"{ident}_try{attempt}"
        kwargs = dict(count=count, per_slot=per_slot, maximum=maximum,
                      output_contract=contract.as_dict())
        if replacement is not None:
            kwargs["replacement"] = replacement
        generated = writer.request(session, job, generation, seed + attempt, **kwargs)
        diagnostic = dict(writer.response_diagnostics.get(generation, {}))
        encoding, error = {}, None
        if generated and encode is not None:
            try:
                encoding = encode(generated)
            except ValueError as exc:
                error = str(exc)
                generated = []
        for row in generated:
            question, answer = row_text(row, 0), row_text(row, 1)
            if locked_question is None:
                locked_question = question
            if question != locked_question:
                error = "replacement changed the retained question"
                continue
            kind = contract.effective_kind(question)
            if kind == "EXACT_LITERAL" and answer != contract.literal:
                error = "exact literal output contract not met"
                continue
            slot = row["meta"].get("answer_variant", 1)
            if slot not in range(1, count + 1) or slot in retained:
                continue
            if answer not in {row_text(r, 1) for r in retained.values()}:
                row["meta"]["output_contract"] = contract.as_dict()
                row["meta"]["output_contract_effective"] = kind
                retained[slot] = row
        effective = contract.effective_kind(locked_question or "")
        duplicate = diagnostic.get("duplicate_slots", [])
        trace = {"generation_id": generation, "attempt": attempt,
                 "reason": next_reason, "diagnostic": diagnostic, "encoding": encoding,
                 "encoding_error": error, "retained_slots": sorted(retained),
                 "effective_contract": effective, "semantic_truth": "PSEUDO_UNVERIFIED"}
        traces.append(trace)
        if on_attempt:
            on_attempt(trace)
        if len(retained) == count:
            break
        if retained:
            if effective != "VARIANT_ALLOWED":
                break
            missing = sorted(set(range(1, count + 1)) - set(retained))
            replacement = {"question": locked_question, "slots": missing,
                           "retained_answers": {str(i): row_text(r, 1) for i, r in retained.items()}}
            next_reason = "duplicate_slot_recovery" if duplicate else "missing_slot_recovery"
        elif duplicate:  # Existing corpus duplicate, UNKNOWN/literal: never regenerate.
            break
        else:
            if diagnostic.get("wire_screen_status") not in (
                    "INCOMPLETE", "PARSE_ERROR", "PEG_NATIVE_MISMATCH", "STUDENT_CONTEXT_REJECT",
                    "EMPTY_OR_NESTED_FIELDS", "MULTI_FORMAT_READY", "TAGGED_COMPLETE"):
                break
            next_reason = "technical_recovery"
            locked_question = None
    return [retained[i] for i in sorted(retained)], {"attempts": traces,
        "physical_attempts": sum(bool(t["diagnostic"].get("completion_call_attempted")) for t in traces),
        "physical_scope": "client completion calls attempted, not confirmed server generations",
        "budget_attempts": len(budget.reasons), "attempt_reasons": list(budget.reasons),
        "retained_slots": sorted(retained), "requested_slots": count,
        "all_variants_present": len(retained) == count,
        "effective_contract": contract.effective_kind(locked_question or "")}
