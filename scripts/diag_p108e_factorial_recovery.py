"""Recover a fully written calculation after its final stdout serializer failed."""
import argparse
import json
import math
from pathlib import Path
from scripts import diag_p108e_endpoint_factorial as original
from scripts import diag_p108c_scope as io

BASE=original.BASE/"recovery_v1"
LOG=io.ROOT/"test_result/108_log_20261117_P108E_Stage4bW_endpoint_error_factorial_cpu.txt"


def validate():
    original.check();profile=io.read(original.BASE/"profile.json");report=io.read(original.BASE/"report.json")
    for name,digest in profile["sources"].items():
        if io.sha(io.ROOT/name)!=digest:raise ValueError("failed calculation source changed")
    if io.sha(original.BASE/"initial_plan.md")!=profile["initial_plan_sha256"]:
        raise ValueError("initial calculation plan changed")
    raw=LOG.read_text()
    if(raw.count("[runlog] 종료코드 1")!=1 or "NameError: name 'json' is not defined"not in raw
       or "Ran 5 tests"not in raw or "[ENDPOINT_FACTORIAL]layer=13"not in raw):
        raise ValueError("exact terminal serializer failure evidence required")
    if(report["status"]!="ENDPOINT_FACTORIAL_COMPLETE"or len(report["rows"])!=14
       or {r["layer"]for r in report["rows"]}!=set(range(14))
       or any(report[k]for k in("new_model_loads","new_model_forwards","new_generated_answers"))):
        raise ValueError("complete saved calculation without model calls required")
    for row in report["rows"]:
        if(row["argmax_mismatches"]or max(row["native_top8_reconstruction_max_error"],
            row["native_gold_reconstruction_max_error"])>.002):raise ValueError("native reconstruction parity failed")
    for name,summary in report["summary"].items():
        recomputed=dict(mean_full_question_absolute_error=sum(abs(r["signals"][name]["score"]["questions_all_gold"]-
            r["actual"]["questions_all_gold"])for r in report["rows"])/14,
            pooled_actual_fixed_rival_RMSE=math.sqrt(sum(r["signals"][name]["actual_fixed_rival_RMSE"]**2 for r in report["rows"])/14),
            pooled_actual_full_vocab_RMSE=math.sqrt(sum(r["signals"][name]["actual_full_vocab_RMSE"]**2 for r in report["rows"])/14))
        if any(abs(recomputed[k]-summary[k])>1e-12 for k in summary):raise ValueError("independent summary differs")
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=("check","actual"));args=parser.parse_args()
    report=validate()
    if args.action=="check":print("[FACTORIAL_RECOVERY_CHECK]complete raw report and terminal failure verified");return
    if BASE.exists():raise FileExistsError("preserve existing recovery receipt")
    BASE.mkdir()
    result=dict(schema="P108E_FACTORIAL_TERMINAL_RECOVERY_V1",status="COMPLETE_CALCULATION_RECOVERED_NOT_REEXECUTED",
        original_execution_exit_code=1,original_failure="MISSING_JSON_IMPORT_AT_FINAL_STDOUT_ONLY",
        original_report_sha256=io.sha(original.BASE/"report.json"),original_profile_sha256=io.sha(original.BASE/"profile.json"),
        original_log_sha256=io.sha(LOG),recovery_source_sha256=io.sha(Path(__file__)),
        new_matrix_calculations=0,new_model_calls=0,original_failed_source_and_log_unchanged=True,
        summary=report["summary"],native_argmax_mismatches=0)
    io.write_new(BASE/"report.json",result)
    print("[FACTORIAL_RECOVERY_END]"+json.dumps(result,ensure_ascii=False),flush=True)


if __name__=="__main__":main()
