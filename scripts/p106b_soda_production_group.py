"""Connect a manifest-bound SODA row to the existing teacher group contract."""

from dataclasses import dataclass
import re
from types import FunctionType, SimpleNamespace

from scripts import diag_p106b_gemma_deficit_production as producer
from scripts import p106b_gemma_task_contract as tasks
from scripts.p106b_soda_candidate_wire import student_candidate
from scripts.p106b_soda_manifest_source import digest


_PRODUCE_GROUP = producer.produce_group


@dataclass(frozen=True)
class GroupResult:
    next_cursor: dict
    raw_sha256: str
    outcome: str
    request_shas: tuple[str, ...]
    candidate: dict | None


class _AttemptLog:
    """Give the frozen producer its normal writer interface and bind each attempt."""

    def __init__(self, writer, requests):
        self.writer = writer
        self.requests = requests
        self.recorded = []
        self.turns = []

    @property
    def _total_rows(self):
        return self.writer._total_rows

    def append(self, row):
        request = self.requests[len(self.recorded)]
        if row["payload"] != request.payload:
            raise ValueError("teacher attempt differed from the source-bound payload")
        self.writer.append(dict(row, source_request_sha256=request.request_sha256,
                                source_raw_sha256=request.row.raw_sha256,
                                source_next_cursor=request.row.next_cursor))
        self.recorded.append(request.request_sha256)
        if row["producer_learner_turn"] is not None:
            parsed = row["parsed"]["parsed_content"]
            self.turns.append({key: parsed[key] for key in ("user_text", "assistant_text")})


def produce_bound_group(reader, cursor, *, session, raw, tokenizer, teacher_model_sha256,
                        language, profile, seed):
    """Consume one group with a caller-owned session and propose its next cursor.

    The caller owns data and teacher admission, shard closure, and committing the
    cursor. Returned rows are detached candidates with the existing pending status.
    """
    if type(seed) is not int or not 0 <= seed < 2**31:
        raise ValueError("bounded integer group seed required")
    first = reader.read_request(cursor, language, profile, (seed + 1) % 2147483647)
    if first is None:
        return None
    source = first.row
    if first.payload is None:
        return GroupResult(source.next_cursor, source.raw_sha256, "HOLD", (), None)
    if not isinstance(teacher_model_sha256, str) or not re.fullmatch(r"[A-Fa-f0-9]{64}", teacher_model_sha256):
        raise ValueError("explicit teacher model SHA required before a request")
    if _PRODUCE_GROUP.__closure__ is not None:
        raise RuntimeError("the unchanged teacher group function is required")
    bound_cursor = dict(source.next_cursor, next_row=source.index)
    requests = []

    def payload(_source, lang, task, attempt_seed, *, history=()):
        request = reader.read_request(bound_cursor, lang, task, attempt_seed, history=history)
        if (request is None or request.row.raw_sha256 != source.raw_sha256 or
                request.row.next_cursor != source.next_cursor or request.payload is None):
            raise ValueError("bound source changed while preparing a teacher attempt")
        requests.append(request)
        return request.payload

    bound_tasks = SimpleNamespace(CONTRACT=tasks.CONTRACT, payload=payload, learner_turn=tasks.learner_turn)
    run_group = FunctionType(_PRODUCE_GROUP.__code__, dict(_PRODUCE_GROUP.__globals__, tasks=bound_tasks),
                             _PRODUCE_GROUP.__name__, _PRODUCE_GROUP.__defaults__)
    log = _AttemptLog(raw, requests)
    identity = dict(model_sha256=teacher_model_sha256.upper())
    produced = run_group(session, source.prepared.evidence_source, language, profile, seed, log, identity)
    request_shas = tuple(log.recorded)
    if not request_shas or request_shas[0] != first.request_sha256 or len(requests) != len(request_shas):
        raise ValueError("teacher attempt receipts differ from the bound requests")
    if produced is None:
        return GroupResult(source.next_cursor, source.raw_sha256, "REJECTED", request_shas, None)
    generation_id = "soda_" + digest((request_shas[0] + identity["model_sha256"]).encode("ascii"))
    candidate = student_candidate(source.prepared, log.turns, language, profile, tokenizer=tokenizer,
                                  teacher_model_sha256=identity["model_sha256"], generation_id=generation_id)
    candidate["meta"].update(source_request_sha256=list(request_shas), source_raw_sha256=source.raw_sha256,
                             source_next_cursor=source.next_cursor,
                             teacher_reasoning_refs=produced["meta"]["teacher_reasoning_refs"])
    return GroupResult(source.next_cursor, source.raw_sha256, "PREPARED", request_shas, candidate)
