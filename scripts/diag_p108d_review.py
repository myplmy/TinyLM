"""Render complete original/two-edit Q/A pairs; never auto-rate fluency."""
import json
from pathlib import Path
from scripts import diag_p108c_scope as io
from scripts import diag_p108d_winner as study


def run():
    report=io.read(study.VALIDATE/"report.json")
    if (report["status"]!="WINNER_NATIVE_VALIDATION_COMPLETE" or not report["original_core_restored"]
            or report["cuda_allocated_after_bytes"] or report["cuda_reserved_after_bytes"]):
        raise ValueError("closed physical native validation required")
    arms={a["name"]:io.closed_answers(study.VALIDATE/a["name"],a["answers_manifest"]) for a in report["arms"]}
    first=next(iter(arms.values()))
    if len(first)!=127 or any(set(rows)!=set(first) for rows in arms.values()):
        raise ValueError("same127 paired contexts required")
    directory=io.ROOT/"review_request/20261116_NIGHT_P108D_winner_v2"
    if directory.exists():raise FileExistsError("preserve prior reading packet")
    directory.mkdir()
    rows=[];parts=[]
    for identifier,original in first.items():
        row=dict(id=identifier,question=original["question"],expected=original["expected"],
                 language=original["language"],split=original["split"],family=original["family"],
                 original_answer=original["baseline_answer"],original_exact=original["baseline_exact"],
                 edits={name:dict(answer=items[identifier]["answer"],exact=items[identifier]["exact"],
                     diagnostics=items[identifier]["diagnostics"],finish=items[identifier]["generation"]["finish_reason"])
                     for name,items in arms.items()})
        rows.append(row)
    for start in range(0,len(rows),20):
        lines=["P108D 실제 원답: 원본과 두 전역 편집의 같은 질문 대조",
               "FIT은 편집 목표이며 DEV도 기존 탐색 자료입니다. 새 맹검·자동 문장성 판정이 아닙니다.",
               "MINIMUM 파일명은 수렴 증명이 아닙니다. 두 solver는 엄격 버퍼 수렴 미확인입니다.",""]
        group=rows[start:start+20]
        for row in group:
            lines.extend([row["id"]+" / "+row["language"]+" / "+row["split"]+" / "+row["family"],
                "질문> "+row["question"],"비교 정답> "+str(row["expected"]),
                "원본 답> "+row["original_answer"],"원본 엄격 정답> "+str(row["original_exact"])])
            for name,item in row["edits"].items():
                lines.extend([name+" 답> "+item["answer"],"종료> "+item["finish"]+
                              " / 엄격 정답> "+str(item["exact"])])
            lines.append("")
        path=directory/("paired_answers_"+str(start//20+1).zfill(3)+".txt")
        body=chr(10).join(lines)+chr(10)
        if len(body.encode())>=2_000_000:raise ValueError("split readable text")
        with path.open("x",encoding="utf-8")as stream:stream.write(body)
        parts.append(dict(path=str(path.relative_to(io.ROOT)),sha256=io.sha(path),case_ids=[r["id"] for r in group]))
    io.write_new(directory/"source_rows.json",dict(rows=rows))
    io.write_new(directory/"READING_MANIFEST.json",dict(paired_cases=127,new_native_answers=254,
        original_cached_answers=127,parts=parts,source_report_sha256=io.sha(study.VALIDATE/"report.json"),
        automatic_language_rating=False,root_read_status="PENDING"))
    print("[WINNER_REVIEW_RENDERED]127 complete questions;254 actual edits;7 plain text files",flush=True)


if __name__=="__main__":run()
