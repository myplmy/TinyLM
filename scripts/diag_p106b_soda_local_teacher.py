"""Run the source-bound SODA group against the existing local Gemma on authored cases."""

import argparse
from datetime import datetime
import os
from pathlib import Path
from time import monotonic, sleep, time

from scripts import diag_p106b_soda_bound_group as fixture
from scripts import p106b_gemma_teacher as gemma
from scripts.diag_p106_full_coload_accum import _compute_apps
from scripts.diag_p106_vram_sample import read_memory
from scripts.p106b_gate_runtime import disposition, idle_before_gpu, wall_limit
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_soda_production_group import produce_bound_group


ROOT, io = fixture.ROOT, fixture.io
OUT = ROOT / "test_result/evidence/p106b_soda_local_teacher_v1_20261119"
RECOVERY = OUT.with_name("p106b_soda_local_teacher_v2_20261119")
PLAN = ROOT / "test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md"
RECEIPT = ROOT / "test_result/evidence/p106b_gemma_mtp_production_transport_v2_s1337/report.json"
CUTOFF = datetime.fromisoformat("2026-11-20T16:58:00+09:00").timestamp()
WALL = 420
CASES = ((0, "en", "qa", True), (1, "en", "qa", False),
         (2, "en", "qa", True), (4, "ko", "multiturn", False))


def authority(reserve=0):
    if time() + reserve >= CUTOFF or (OUT / "STOP").exists() or (RECOVERY / "STOP").exists():
        raise RuntimeError("outside the approved SODA local teacher window or stopped")


def identity(path):
    st = path.stat()
    return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns]


class RawAttempts(ShardWriter):
    def __init__(self, directory, archived_sha=None):
        super().__init__(directory, "raw")
        self.archived_sha = archived_sha
        self.metadata = []

    def append(self, row):
        recovered = row.get("source_request_sha256") == self.archived_sha
        origin = "ARCHIVED_LOCAL_RESPONSE" if recovered else "CURRENT_LOCAL_RESPONSE"
        super().append(dict(row, response_origin=origin))
        reply = row["reply"]
        self.metadata.append(dict(language=row["language"], task=row["task"], turn=row["turn"],
                                  attempt=row["attempt"], input_tokens=row["input_tokens"],
                                  seconds=row["request_sec"], reason=row["structural_reason"],
                                  finish=reply["choices"][0].get("finish_reason"),
                                  usage=reply.get("usage", {}), response_origin=origin))


class TeacherTransport:
    def __init__(self, session, archived):
        self.session = session
        self.archived = archived
        self.live_calls = 0
        self.replays = 0

    def check(self):
        authority(10)
        self.session.check()

    def request(self, route, payload, *, timeout=10):
        if route == "/v1/chat/completions":
            if self.archived is not None:
                archived = self.archived
                if payload != archived["payload"]:
                    raise ValueError("replay requested a different teacher payload")
                self.archived = None
                self.replays += 1
                return archived["reply"]
            self.live_calls += 1
        response = self.session.request(route, payload, timeout)
        if self.archived is not None and route == "/tokenize":
            if len(response["tokens"]) != self.archived["input_tokens"]:
                raise ValueError("the live server token count differs from the archived request")
        return response


def frozen_inputs(reader):
    values = []
    for row, language, task, hold in CASES:
        cursor = dict(reader.start(), next_row=row)
        request = reader.read_request(cursor, language, task, 650001 + row)
        if request.row.index != row or (request.payload is None) != hold:
            raise ValueError("authored fixture identity or HOLD differs")
        values.append(dict(row=row, language=language, task=task, hold=hold,
                           original_sha256=request.row.raw_sha256, request_sha256=request.request_sha256))
    return values


def seal():
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("seal needs isolated CPU")
    authority(WALL + 120)
    OUT.mkdir(exist_ok=True)
    if OUT.is_symlink() or any(OUT.iterdir()):
        raise FileExistsError("preserve the previous preflight or run")
    asset_before = identity(gemma.MODEL)
    asset = gemma.assets(False)
    previous = fixture.load(RECEIPT)["assets"]
    model_sha = io.digest(gemma.MODEL)
    if (model_sha != previous["model_sha256"] or asset["runtime_sha256"] != previous["runtime_sha256"]
            or asset_before != identity(gemma.MODEL)):
        raise ValueError("existing local teacher or its runtime changed")
    reader = fixture.bound.source()
    fixture.tokenize()
    paths = (
        Path(__file__), PLAN, RECEIPT, fixture.TOKENIZER, fixture.bound.BOUND,
        fixture.bound.OUT / "bound_receipt.json",
        ROOT / "scripts/p106b_soda_production_group.py", ROOT / "scripts/p106b_soda_manifest_source.py",
        ROOT / "scripts/p106b_soda_candidate_wire.py", ROOT / "scripts/diag_p106b_gemma_deficit_production.py",
        ROOT / "scripts/p106b_gemma_teacher.py", ROOT / "scripts/p106b_gemma_labels.py",
        ROOT / "scripts/p106b_gemma_task_contract.py", ROOT / "scripts/diag_p106b_qwen_coload.py",
        ROOT / "scripts/diag_p106b_mtp_teacher.py",
    )
    runtime = {name: identity(gemma.SERVER.parent / name) for name in asset["runtime_sha256"]}
    pins = {str(p.relative_to(ROOT)): io.digest(p) for p in paths}
    (OUT / "plan_at_execution.md").write_bytes(PLAN.read_bytes())
    io.write(OUT / "profile.json", dict(approval="WIP177", model_sha256=model_sha, model=asset["model"],
             model_identity=asset_before, runtime_identity=runtime, runtime_sha256=asset["runtime_sha256"],
             pins=pins, fixture=frozen_inputs(reader), mtp=False, wall_seconds=WALL,
             context=gemma.CONTEXT, max_output=gemma.MAX_OUTPUT, thinking_budget=gemma.THINKING,
             scope="CODE_AUTHORED_SOURCE_BINDING_NOT_ADMITTED"))
    print("SODA_LOCAL_TEACHER_SEALED", model_sha, len(CASES), flush=True)


def check_pins(profile):
    if any(io.digest(ROOT / path) != value for path, value in profile["pins"].items()):
        raise ValueError("sealed source inputs changed")
    if identity(gemma.MODEL) != profile["model_identity"]:
        raise ValueError("sealed Gemma file identity changed")
    if any(identity(gemma.SERVER.parent / name) != value for name, value in profile["runtime_identity"].items()):
        raise ValueError("sealed server library identity changed")


def archived_response():
    report = fixture.load(OUT / "report.json")
    manifest = report["manifests"]["raw"]
    if (report["actual_exit"] != 9 or "_total_rows" not in report["error"] or
            not report["gpu_return"]["returned"] or manifest["rows"] != 1):
        raise ValueError("the first attempt does not contain the expected recoverable response")
    verify(OUT / "run", manifest)
    row, = fixture.rows(OUT / "run", manifest)
    if (row["language"], row["task"], row["turn"], row["attempt"]) != ("en", "qa", 1, 1):
        raise ValueError("first response lineage differs")
    if row["producer_learner_turn"] is None or row["structural_reason"]:
        raise ValueError("the archived teacher response never passed the producer parser")
    return row


def seal_recovery():
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("recovery seal needs isolated CPU")
    authority(WALL + 60)
    profile = fixture.load(OUT / "profile.json")
    current = str(Path(__file__).relative_to(ROOT))
    snapshot = OUT / "runner_at_execution.py"
    if io.digest(snapshot) != profile["pins"][current]:
        raise ValueError("the previous runner snapshot differs")
    response = archived_response()
    profile["pins"][current] = io.digest(Path(__file__))
    for path in (OUT / "profile.json", OUT / "report.json", snapshot,
                 OUT / "run" / "raw_shards_manifest.json"):
        profile["pins"][str(path.relative_to(ROOT))] = io.digest(path)
    check_pins(profile)
    profile["replayed_request_sha256"] = response["source_request_sha256"]
    RECOVERY.mkdir()
    (RECOVERY / "plan_at_execution.md").write_bytes(PLAN.read_bytes())
    io.write(RECOVERY / "profile.json", profile)
    print("SODA_LOCAL_TEACHER_RECOVERY_SEALED", response["source_request_sha256"], flush=True)


def return_state(process, free_before):
    deadline = monotonic() + 16
    while True:
        used, free = read_memory()
        own_visible = (process is not None and any(
            item.split(",", 1)[0].strip() == str(process.pid) for item in _compute_apps()))
        returned = not own_visible and free >= free_before - 512
        if returned or monotonic() >= deadline:
            return dict(returned=returned, free_mib=free, used_mib=used, owned_pid_visible=own_visible,
                        owned_process_exit=process.poll() if process is not None else None)
        sleep(.5)


def execute(recover=False):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise ValueError("the approved single GPU must be explicit")
    authority(WALL + 30)
    out = RECOVERY if recover else OUT
    profile = fixture.load(out / "profile.json")
    check_pins(profile)
    archived = archived_response() if recover else None
    if archived is not None and archived["source_request_sha256"] != profile["replayed_request_sha256"]:
        raise ValueError("sealed archived response differs")
    reader, tokenizer = fixture.bound.source(), fixture.tokenize()
    if frozen_inputs(reader) != profile["fixture"]:
        raise ValueError("sealed authored request changed")
    directory = out / "run"
    directory.mkdir()
    idle_before_gpu()
    baseline_used, baseline_free = read_memory()
    raw = RawAttempts(directory, profile.get("replayed_request_sha256"))
    candidates = ShardWriter(directory, "candidate")
    states, metadata = [], {}
    candidate_count = 0
    wrapped = gemma.GemmaSession(False)
    start = monotonic()
    status, rc, error = "MEASURED", 0, None
    transport = None
    try:
        with wall_limit(WALL), wrapped as session:
            print("SODA_LOCAL_TEACHER_READY", session.process.pid, session.startup_sec, flush=True)
            transport = TeacherTransport(session, archived)
            for row, language, task, hold in CASES:
                authority(10)
                previous = len(raw.metadata)
                previous_calls = transport.live_calls
                result = produce_bound_group(
                    reader, dict(reader.start(), next_row=row), session=transport, raw=raw, tokenizer=tokenizer,
                    teacher_model_sha256=profile["model_sha256"], language=language, profile=task, seed=650000 + row)
                calls = len(raw.metadata) - previous
                state = fixture.record(result, candidates, calls)
                state.update(row=row, language=language, task=task, next_row=result.next_cursor["next_row"],
                             live_calls=transport.live_calls - previous_calls)
                if hold != (state["outcome"] == "HOLD") or (hold and calls):
                    raise ValueError("HOLD enforcement changed")
                if result.candidate is not None:
                    candidate_count += 1
                    state["assistant_target_counts"] = result.candidate["meta"]["assistant_turn_target_counts"]
                states.append(state)
                print("SODA_LOCAL_TEACHER_GROUP", row, language, state["outcome"], calls, flush=True)
            if recover and transport.replays != 1:
                raise ValueError("the first live answer must be used exactly once for recovery")
            metadata = dict(session.memory(), startup_seconds=session.startup_sec)
    except (Exception, KeyboardInterrupt) as exc:
        status, rc = disposition(exc)
        error = f"{type(exc).__name__}: {exc}"
        print("SODA_LOCAL_TEACHER_TERMINAL", status, error, flush=True)
    process = wrapped.session.process if wrapped.session is not None else None
    try:
        returned = return_state(process, baseline_free)
    except (OSError, RuntimeError, ValueError) as exc:
        returned = dict(returned=False, free_mib=None, error=f"{type(exc).__name__}: {exc}")
    print("SODA_LOCAL_TEACHER_GPU_RETURN", returned["returned"], returned["free_mib"], flush=True)
    if not returned["returned"] or (process is not None and process.poll() is None):
        status, rc, error = "RETURN_UNVERIFIED", 9, "owned GPU return could not be verified"
    if wrapped.session is not None and not metadata:
        samples = wrapped.session.samples
        if samples:
            metadata = dict(sample_count=len(samples),
                            sampled_gpu_global_peak_mib=max(x["used"] for x in samples),
                            sampled_gpu_min_free_mib=min(x["free"] for x in samples))
    try:
        check_pins(profile)
    except (OSError, ValueError) as exc:
        status, rc, error = "SOURCE_CHANGED", 9, str(exc)
    lineage = {"scope": profile["scope"], "corpus_admitted": False, "model_sha256": profile["model_sha256"]}
    manifests = {}
    for stem, writer, count in (("raw", raw, len(raw.metadata)), ("candidate", candidates, candidate_count)):
        if count:
            manifest = writer.close(lineage=lineage)
            verify(directory, manifest)
            manifests[stem] = manifest
    io.write(out / "report.json", dict(status=status, actual_exit=rc, error=error, attempts=raw.metadata,
             groups=states, candidates=candidate_count, manifests=manifests, resources=metadata,
             live_calls=transport.live_calls if transport else 0, replays=transport.replays if transport else 0,
             gpu_before=dict(used_mib=baseline_used, free_mib=baseline_free), gpu_return=returned,
             elapsed_seconds=monotonic()-start, admitted_rows=0, student_updates=0))
    return rc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("seal", "run", "seal-recovery", "recover"))
    args = parser.parse_args()
    if args.action == "seal":
        seal()
        return 0
    if args.action == "seal-recovery":
        seal_recovery()
        return 0
    return execute(args.action == "recover")


if __name__ == "__main__":
    raise SystemExit(main())
