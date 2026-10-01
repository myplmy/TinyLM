#!/usr/bin/env python3
"""User-run bounded trusted-output teacher gate; CPU mocks are separate.

Four fixed code-template questions, shared maximum3 per question; no student
loading/training, no original data writes, no stdin or automatic effort choice.
"""
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.p106b_output_contract import OutputContract, request_group, text_sha
from scripts.p106b_gate_runtime import (ROOT, TeacherSession, THINKING_SAMPLER, teacher_inputs,
    new_directory, idle_before_gpu, write_report, disposition, GateNegative, wall_limit)
from scripts.p106b_pipeline import CandidateWriter, validate_job_contract
from scripts.p106b_lexical_observation import TextObserver
from scripts.p106b_report_domains import separated_report
from scripts.p106b_education_followup import runtime_contract
from scripts.diag_p106_bonsai_assets import sha256_file

QUESTIONS = (
    ("ko", "EXACT_LITERAL", "숫자 1만 출력하세요.", "1"),
    ("en", "EXACT_LITERAL", "Output only the digit 1.", "1"),
    ("ko", "VARIANT_ALLOWED", "2+2의 결과를 간단한 답과 같은 결론의 짧은 설명으로 각각 답하세요.", None),
    ("en", "VARIANT_ALLOWED", "State 2+2 concisely, and explain the same result briefly.", None),
)


def jobs():
    for i, (language, kind, question, literal) in enumerate(QUESTIONS):
        contract = OutputContract(kind, question, "CODE_TEMPLATE", "P106B-code-template-v1", literal)
        job = {"teacher_task": "answer_given", "target_language": language,
            "source_payload": {"question": question, "question_policy": "Copy QUESTION exactly; fixed code template."},
            "source_id": f"p106b-output-template:{i}", "source_sha256": text_sha(question),
            "source_license": "project-authored diagnostic template", "source_repo": "TinyLM/code-template",
            "source_revision": "output-contract-v1", "source_transform": "teacher_answer",
            "parent_concept_id": text_sha(f"output-contract:{i}"), "rights_status": "CARD_ONLY", "split": "diagnostic"}
        validate_job_contract(job)
        yield job, contract


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--check-only", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    target = ROOT / "HF/sft_ready/p106b_teacher_sft/v33_output_contract_pilot"
    try:
        prepared = list(jobs())
        if args.self_test or args.check_only:
            if args.check_only:
                new_directory(target)
            print("[PASS] fixed code template/provenance contract; GPU/teacher NOT_RUN")
            return 0
        new_directory(target)
        info = {"teacher": teacher_inputs(), "sampler": dict(THINKING_SAMPLER), "effort": "xhigh",
                "context": 32768, "max_output": 16384, "thinking_budget": 8192,
                "groups": 4, "maximum_attempts_per_group": 3, "formal_train_ready": False,
                "code_sha256": sha256_file(Path(__file__)), "runtime_contract": runtime_contract()}
        idle_before_gpu()
        target.mkdir(parents=True, exist_ok=False)
        writer, records = CandidateWriter(target, info, observer=TextObserver()), []
        began, session, fatal = time.monotonic(), None, None
        try:
            with wall_limit(1800), TeacherSession(32768, 1, effort="xhigh", thinking_budget=8192) as session:
                for index, (job, contract) in enumerate(prepared):
                    rows, recovery = request_group(writer, session, job, f"known_{index}", 20261002+index*10,
                        count=2, per_slot=32768, maximum=16384, contract=contract)
                    effective = {r["meta"]["output_contract_effective"] for r in rows}
                    passed = bool(rows and effective == {contract.kind}
                                  and (contract.kind == "EXACT_LITERAL" or len(rows) == 2))
                    records.append({"contract": contract.as_dict(), "passed": passed, "recovery": recovery,
                        "rows": rows})
                    print("[CONTRACT_ANSWER] " + json.dumps(records[-1], ensure_ascii=False), flush=True)
                    session.check_monitor()
                session.require_valid_resources()
        except (Exception, KeyboardInterrupt) as exc:
            fatal = exc
            raise
        finally:
            metrics = writer.close()
            complete = len(records) == 4 and all(r["passed"] for r in records)
            status, rc = disposition(fatal) if fatal else ("CONTRACT_PILOT_COMPLETE", 0) if complete else ("GATE_NEGATIVE", 8)
            report = {"schema": "P106B_KNOWN_OUTPUT_GATE_V1", "input": info, **metrics,
                "status": status, "exit_code": rc,
                "records": records, "whole_wall_sec": time.monotonic()-began,
                "teacher_truth": "PSEUDO_UNVERIFIED", "student_training": "NOT_RUN",
                "server": session.evidence() if session else None}
            report["report_domains"] = separated_report(report)
            write_report(target / "report.json", report)
        if report["status"] != "CONTRACT_PILOT_COMPLETE":
            raise GateNegative("typed outputs not observed complete; raw/partial slots retained")
        print("[PASS] bounded known-output wiring only; truth/student effect NOT_RUN")
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        status, rc = disposition(exc)
        print(f"[{status}] {type(exc).__name__}: {str(exc)[:250]}", file=sys.stderr)
        return rc


if __name__ == "__main__":
    raise SystemExit(main())
