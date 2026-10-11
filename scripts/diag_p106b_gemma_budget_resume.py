#!/usr/bin/env python3
"""User-only literal continuation: classify only the owned wall alarm as pause8.

The generation14 source files, inputs, quotas, source cursor and batch schema are
unchanged. Original failing reports are not rewritten; new batches are immutable.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime,timezone
import json
from pathlib import Path
import signal
import subprocess
import sys
import uuid
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_gemma_telemetry_resume as prior
from scripts import diag_p106b_gemma_deficit_production as producer
from scripts.p106b_gate_runtime import PrerequisiteHold
from scripts.p106b_stage_receipt import pipeline
from scripts.p106b_mixed_scale import digest,safe_repo_path

class ProductionBudgetPause(PrerequisiteHold):
    """Owned production deadline, never a server/VRAM timeout exemption."""


@contextmanager
def production_budget_scope(evidence):
    original=producer.wall_limit
    @contextmanager
    def owned(seconds):
        with original(seconds):
            def expired(*_args):
                evidence.update(expired=True,remaining_window_sec=seconds,
                    pause_scope="owned production wall alarm only; not dataset completion")
                raise ProductionBudgetPause("controlled production budget expired; partial evidence retained")
            signal.signal(signal.SIGALRM,expired)
            yield
    with patch.object(producer,"wall_limit",owned):
        yield


def execute_resume(args):
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence_path=safe_repo_path(ROOT/"test_result/evidence"/
        ("101_P106B_Stage4jWh_budget_resume_"+stamp+"_"+uuid.uuid4().hex[:12]+".json"))
    if evidence_path.exists() or evidence_path.is_symlink():raise FileExistsError("preserve receipt")
    reader=prior.RetryingMemoryReader(prior.memory_source.read_memory,
        emit=lambda line:print(line,flush=True))
    budget={"expired":False,"policy":"OWNED_ALARM_PAUSE8_V1"}
    paths=(*prior.CODE_PATHS,"scripts/diag_p106b_gemma_budget_resume.py",
           "scripts/test_p106b_gemma_budget_resume.py")
    proof={"schema":"P106B_GEMMA_BUDGET_RESUME_V1","policy":prior.POLICY,
        "generation_inputs_sha256":digest(safe_repo_path(prior.literal.PATHS["OUTPUT"]/"inputs.json")),
        "runtime_code_sha256":{name:digest(ROOT/name) for name in paths},
        "max_wall_sec":args.max_wall_sec,"student_training":"NOT_RUN",
        "generation_contract_changed":False,"original_reports_mutated":False}
    rc=9
    try:
        with prior.telemetry_scope(reader),production_budget_scope(budget):
            rc=prior.run_resume(args,execute=True)
        return rc
    finally:
        proof.update(returncode=rc,telemetry=reader.snapshot(),budget=budget,
            readiness="NOT_ESTABLISHED; quota/replay gate still owns completion")
        body=json.dumps(proof,ensure_ascii=False,indent=2)+"\n"
        if len(body.encode())>20_000_000:raise ValueError("receipt exceeds20MB")
        evidence_path.parent.mkdir(parents=True,exist_ok=True)
        with evidence_path.open("x",encoding="utf-8") as f:f.write(body)
        print("[BUDGET_RECEIPT] "+str(evidence_path.relative_to(ROOT)),flush=True)
        print("[BUDGET_FINAL] "+json.dumps({"returncode":rc,"budget":budget,
            "telemetry":reader.snapshot(),"student_training":"NOT_RUN"},ensure_ascii=False),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",choices=("resume",),required=True)
    p.add_argument("--max-wall-sec",type=int,default=21600)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--execute",action="store_true");g.add_argument("--check-only",action="store_true")
    a=p.parse_args()
    if not 60<=a.max_wall_sec<=21600:p.error("wall limit must be60..21600 seconds")
    if a.check_only:return prior.run_resume(a,execute=False)
    def launch(command):
        if command[0]=="CHECK_ONLY":return prior.run_resume(a,execute=False)
        if command[0]=="EXECUTE":return execute_resume(a)
        return subprocess.run(command,cwd=ROOT,stdin=subprocess.DEVNULL).returncode
    phases=[("REGRESSION",[sys.executable,"-B","-X","utf8","-m","unittest",
        *prior.literal.REGRESSION,"scripts.test_p106b_gemma_telemetry_resume",
        "scripts.test_p106b_gemma_budget_resume"]),
        ("PREFLIGHT",["CHECK_ONLY"]),("EXECUTE",["EXECUTE"])]
    return pipeline(phases,launch,lambda line:print(line,flush=True),
        experiment=f"P106B_GEMMA_BUDGET_V1_{a.mode}")["returncode"]

if __name__=="__main__":raise SystemExit(main())
