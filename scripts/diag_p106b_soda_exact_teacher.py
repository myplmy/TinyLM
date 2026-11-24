"""Measure local teacher production on the source-bound SODA TRAIN sample."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import itertools
import os
from pathlib import Path
from time import monotonic, time
from types import SimpleNamespace
from unittest.mock import patch

from scripts import diag_p106b_soda_local_teacher as previous
from scripts import diag_p106b_qwen_coload as runtime
from scripts.p106b_soda_manifest_source import ManifestSodaSource


ROOT, gemma, io = previous.ROOT, previous.gemma, previous.io
SOURCE = ROOT / "test_result/evidence/p106b_soda_248_exact_train_link_resume_cpu_20261120"
BASELINE = SOURCE.with_name("p106b_soda_exact_local_teacher_v2_20261120")
MTP_OUT = SOURCE.with_name("p106b_soda_exact_local_teacher_mtp_v1_20261120")
PARALLEL_OUT = SOURCE.with_name("p106b_soda_exact_local_teacher_mtp_two_v1_20261120")
MANIFEST = SOURCE / "fixtures/raw_shards_manifest.json"
BASE = previous.RECOVERY / "profile.json"
CUTOFF = datetime.fromisoformat("2026-11-21T12:57:00+09:00").timestamp()
CASE_TYPES = tuple(itertools.product(("en", "ko"), ("qa", "json", "multiturn")))
CASES = [(round(index * 247 / 11), *CASE_TYPES[index % len(CASE_TYPES)]) for index in range(12)]
MAX_WALL = 720
MAX_CARD_MIB = 12390


def authority(output, reserve=0):
    if time() + reserve >= CUTOFF or (output / "STOP").exists():
        raise RuntimeError("authorized window or remaining time unavailable")


class TeacherTransport:
    """Bind the existing server to this run's approved window."""

    def __init__(self, session, output):
        self.session = session
        self.output = output

    def check(self):
        authority(self.output, 10)
        self.session.check()

    def request(self, route, payload, *, timeout=10):
        authority(self.output, timeout)
        return self.session.request(route, payload, timeout)


class TwoSlotSession(runtime.QwenSession):
    expected_slots = 2

    def __enter__(self):
        def command(port, key):
            argv = gemma.command(port, key, mtp=True)
            argv[argv.index("--parallel") + 1] = str(self.expected_slots)
            argv[argv.index("--ctx-size") + 1] = str(gemma.CONTEXT * self.expected_slots)
            return argv

        with patch.object(runtime, "profile", SimpleNamespace(command=command)):
            session = super().__enter__()
        if session.props.get("default_generation_settings", {}).get("n_ctx") != gemma.CONTEXT:
            self.__exit__()
            raise ValueError("per-slot context differs from the single-slot reference")
        return session

    def check(self):
        super().check()
        if self.samples and self.samples[-1]["used"] > MAX_CARD_MIB:
            raise RuntimeError("the paired workload exceeded the declared card target")


def open_source():
    original = previous.fixture.load(SOURCE / "profile.json")
    return ManifestSodaSource(MANIFEST, original["manifest_sha256"], previous.fixture.bound.SPEC)


def prepared(mtp, slots):
    from scripts.summarize_p106b_core6_pairs import Inputs

    provenance = previous.fixture.load(SOURCE / "report.json")
    if provenance["mapped_rows"] != 248 or len(provenance["original_group_binding"]) != 248:
        raise ValueError("official TRAIN source binding is incomplete")
    source = open_source()
    prior = previous.fixture.load(BASE)
    model_identity = previous.identity(gemma.MODEL)
    if model_identity != prior["model_identity"] or io.digest(gemma.MODEL) != prior["model_sha256"]:
        raise ValueError("the locally verified teacher file changed")
    for name, signature in prior["runtime_identity"].items():
        if previous.identity(gemma.SERVER.parent / name) != signature:
            raise ValueError("the locally verified teacher runtime changed")
    pins = Inputs()
    for path in (Path(__file__), MANIFEST, SOURCE / "report.json", SOURCE / "profile.json",
                 BASE, previous.fixture.TOKENIZER, Path(previous.__file__),
                 ROOT / "scripts/p106b_soda_manifest_source.py", ROOT / "scripts/p106b_soda_production_group.py",
                 ROOT / "scripts/p106b_soda_candidate_wire.py", ROOT / "scripts/p106b_gemma_teacher.py",
                 ROOT / "scripts/p106b_gemma_task_contract.py"):
        pins.add(path)
    cases = []
    for row, language, task in CASES:
        seed = 701000 + row
        cursor = dict(source.start(), next_row=row)
        first = source.read_request(cursor, language, task, seed + 1)
        if first is None or first.payload is None:
            raise ValueError(f"unusable source-bound row {row}")
        cases.append(dict(row=row, language=language, task=task, seed=seed, cursor=cursor,
                          binding=provenance["original_group_binding"][row],
                          first_sha256=first.request_sha256, raw_sha256=first.row.raw_sha256))
    profile = dict(approval="WIP191", item=69, pins=pins.files, cases=cases, scope="BOUND_TRAIN_RESEARCH",
                   model_sha256=prior["model_sha256"], model_identity=model_identity,
                   runtime_identity=prior["runtime_identity"], mtp=mtp, context=gemma.CONTEXT,
                   max_output=gemma.MAX_OUTPUT, thinking_budget=gemma.THINKING)
    if mtp:
        receipt = pins.add(BASELINE / "profile.json")
        pins.add(BASELINE / "report.json")
        baseline = previous.fixture.load(BASELINE / "profile.json")
        result = previous.fixture.load(BASELINE / "report.json")
        if (baseline["mtp"] or not result["complete"]
                or result["profile_sha256"].upper() != receipt["sha256"]
                or any(profile[field] != baseline[field] for field in (
                    "cases", "model_sha256", "model_identity", "runtime_identity",
                    "context", "max_output", "thinking_budget"))):
            raise ValueError("the completed MTP-off reference conditions differ")
        pins.add(previous.RECEIPT)
        assets = previous.fixture.load(previous.RECEIPT)["assets"]
        if assets["model_sha256"] != prior["model_sha256"]:
            raise ValueError("the known MTP receipt is for a different target")
        draft = pins.add(gemma.DRAFT, expected=assets["draft_sha256"])
        if draft["bytes"] != assets["draft_bytes"]:
            raise ValueError("the verified MTP drafter size differs")
        profile.update(baseline_profile_sha256=receipt["sha256"], draft_sha256=draft["sha256"])
    if slots == 2:
        serial_receipt = pins.add(MTP_OUT / "profile.json")
        pins.add(MTP_OUT / "report.json")
        pins.add(Path(runtime.__file__))
        serial = previous.fixture.load(MTP_OUT / "profile.json")
        result = previous.fixture.load(MTP_OUT / "report.json")
        if (not mtp or not result["complete"]
                or result["profile_sha256"].upper() != serial_receipt["sha256"]
                or any(profile[field] != serial[field] for field in (
                    "cases", "model_sha256", "draft_sha256", "runtime_identity",
                    "context", "max_output", "thinking_budget", "mtp"))):
            raise ValueError("the completed single-slot MTP conditions differ")
        profile.update(parallel_slots=slots, per_slot_context=gemma.CONTEXT, target_card_mib=MAX_CARD_MIB,
                       serial_profile_sha256=serial_receipt["sha256"])
    return pins, source, profile


class GroupAttempts:
    def __init__(self):
        self.rows = []

    @property
    def _total_rows(self):
        return len(self.rows)

    def append(self, row):
        self.rows.append(row)


def produce(case, source, transport, raw, tokenizer, model_sha):
    result = previous.produce_bound_group(
        source, case["cursor"], session=transport, raw=raw, tokenizer=tokenizer,
        teacher_model_sha256=model_sha, language=case["language"], profile=case["task"], seed=case["seed"],
    )
    if result.raw_sha256 != case["raw_sha256"] or result.request_shas[0] != case["first_sha256"]:
        raise ValueError("the measured source request differs from the sealed case")
    return result


def append_group(case, result, attempts, candidates):
    state = previous.fixture.record(result, candidates, attempts)
    state.update(row=case["row"], language=case["language"], task=case["task"], binding=case["binding"])
    if result.candidate is not None:
        state["assistant_target_counts"] = result.candidate["meta"]["assistant_turn_target_counts"]
    print("SODA_EXACT_GROUP", case["row"], case["language"], case["task"],
          result.outcome, attempts, flush=True)
    return state


def run(output, mtp, slots):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise RuntimeError("an explicit single-device launch is required")
    authority(output, MAX_WALL + 30)
    pins, source, profile = prepared(mtp, slots)
    if profile != previous.fixture.load(output / "profile.json"):
        raise ValueError("sealed inputs or runtime changed")
    tokenizer = previous.fixture.tokenize()
    previous.idle_before_gpu()
    _, free_before = previous.read_memory()
    raw = previous.RawAttempts(output)
    candidates = previous.ShardWriter(output, "candidate")
    wrapped = TwoSlotSession("gemma_mtp_two_slots") if slots == 2 else gemma.GemmaSession(mtp)
    groups = []
    resources = {}
    started = monotonic()
    error = None
    rc = 0
    try:
        with previous.wall_limit(MAX_WALL), wrapped as session:
            transport = TeacherTransport(session, output)
            print("SODA_EXACT_TEACHER_READY", session.process.pid, flush=True)
            if slots == 2:
                def parallel_case(case):
                    authority(output, 60)
                    buffer = GroupAttempts()
                    result = produce(case, open_source(), transport, buffer, tokenizer, profile["model_sha256"])
                    return case, result, buffer.rows

                with ThreadPoolExecutor(max_workers=slots) as pool:
                    for case, result, rows in pool.map(parallel_case, profile["cases"]):
                        offset = raw._total_rows
                        for row in rows:
                            raw.append(row)
                        if result.candidate is not None:
                            for ref in result.candidate["meta"]["teacher_reasoning_refs"]:
                                ref["raw_row_1based"] += offset
                        groups.append(append_group(case, result, len(rows), candidates))
            else:
                for case in profile["cases"]:
                    authority(output, 60)
                    before = len(raw.metadata)
                    result = produce(case, source, transport, raw, tokenizer, profile["model_sha256"])
                    groups.append(append_group(case, result, len(raw.metadata) - before, candidates))
            resources = dict(session.memory(), startup_seconds=session.startup_sec)
            resources.update(server_slots=session.props["total_slots"],
                             server_slot_context=session.props["default_generation_settings"]["n_ctx"])
    except (Exception, KeyboardInterrupt) as exc:
        _, rc = previous.disposition(exc)
        error = f"{type(exc).__name__}: {exc}"
        print("SODA_EXACT_ERROR", error, flush=True)
    returned = None
    observed_session = wrapped if slots == 2 else wrapped.session
    if observed_session is not None and observed_session.process is not None:
        returned = previous.return_state(observed_session.process, free_before)
        if not returned["returned"]:
            rc, error = 9, "GPU return not verified"
    pins.unchanged()
    lineage = dict(scope=profile["scope"], corpus_admitted=False, model_sha256=profile["model_sha256"],
                   source="Ai2 SODA · fdc848ab0183208ea7808206c91c724414d0a071 · CC BY 4.0")
    for writer in (raw, candidates):
        if writer._total_rows:
            previous.verify(output, writer.close(lineage=lineage))
    io.write(output / "report.json", dict(complete=rc == 0 and len(groups) == len(CASES), error=error,
             actual_exit=rc, groups=groups, attempts=raw.metadata, candidate_count=candidates._total_rows,
             gpu_return=returned, resources=resources, elapsed_seconds=monotonic() - started,
             admitted_rows=0, student_updates=0, profile_sha256=io.digest(output / "profile.json")))
    return rc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "gpu"))
    parser.add_argument("--mtp", action="store_true", help="pair against the completed MTP-off arm")
    parser.add_argument("--slots", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    if args.slots == 2 and not args.mtp:
        parser.error("the parallel arm requires --mtp")
    output = PARALLEL_OUT if args.slots == 2 else MTP_OUT if args.mtp else BASELINE
    if args.phase == "prepare":
        authority(output, MAX_WALL + 30)
        pins, _, profile = prepared(args.mtp, args.slots)
        pins.unchanged()
        output.mkdir(exist_ok=False)
        io.write(output / "profile.json", profile)
        print("SODA_EXACT_SEALED", len(profile["cases"]), flush=True)
        return 0
    return run(output, args.mtp, args.slots)


if __name__ == "__main__":
    raise SystemExit(main())
