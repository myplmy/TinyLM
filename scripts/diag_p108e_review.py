"""Complete readable Q/A for all frozen edited states, without automatic ratings."""
import json
from scripts import diag_p108e_evaluate as experiment
from scripts import diag_p108c_scope as io


def render():
    base=experiment.BASE/"actual";report=io.read(base/"report.json")
    if(report["status"]!="EXACT_STATE_REPLY_COMPARISON_COMPLETE"or not report["original_core_restored"]
       or report["cuda_allocated_after_bytes"]or report["cuda_reserved_after_bytes"]):
        raise ValueError("closed restored seven-state comparison required")
    states={r["name"]:io.closed_answers(base/r["name"],r["answers_manifest"])for r in report["states"]}
    first=next(iter(states.values()))
    if len(first)!=199 or any(set(rows)!=set(first)for rows in states.values()):
        raise ValueError("same199 complete question scenarios required")
    directory=io.ROOT/"review_request/20261116_NIGHT_P108E_actual_v1"
    if directory.exists():raise FileExistsError("preserve previous reading packet")
    directory.mkdir();parts=[];sources=[];ordered=list(first)
    for identifier in ordered:
        row=first[identifier]
        sources.append(dict(id=identifier,question=row["question"],expected=row.get("expected"),
            language=row.get("language"),panel=row["evaluation_panel"],original_answer=row["baseline_answer"],
            edits={name:dict(answer=values[identifier]["answer"],exact=values[identifier]["exact"],
                diagnostics=values[identifier]["diagnostics"],history=values[identifier]["actual_history"],
                finish=values[identifier]["generation"]["finish_reason"])for name,values in states.items()}))
    for start in range(0,len(sources),16):
        group=sources[start:start+16]
        lines=["P108E 실제 질문·답: 원본과 단일/적응/공동·같은NET·affine 증인",
               "편집/기존진단 자료입니다. 문장성과 정답성은 따로 읽으며 자동 언어 평점은 없습니다.",
               "대화2/3턴은 각 상태의 실제 이전 답이 달라지는 시나리오입니다.",""]
        for row in group:
            lines.extend([row["id"]+" / "+row["panel"]+" / "+str(row["language"]),
                "질문> "+row["question"],"비교 정답> "+str(row["expected"]),"원본 답> "+row["original_answer"]])
            for name,value in row["edits"].items():
                if value["history"]:
                    lines.append(name+"의 실제 앞 대화>")
                    lines.extend(m["role"]+"> "+m["content"]for m in value["history"])
                lines.extend([name+" 답> "+value["answer"],"종료> "+value["finish"]+
                    " / 엄격 정답> "+str(value["exact"])])
            lines.append("")
        path=directory/("paired_answers_"+str(start//16+1).zfill(3)+".txt")
        body=chr(10).join(lines)+chr(10)
        if len(body.encode())>=2_000_000:raise ValueError("split readable answers before2MB")
        with path.open("x",encoding="utf-8")as stream:stream.write(body)
        parts.append(dict(path=str(path.relative_to(io.ROOT)),sha256=io.sha(path),ids=[r["id"]for r in group]))
    io.write_new(directory/"source_rows.json",dict(rows=sources))
    io.write_new(directory/"READING_MANIFEST.json",dict(schema="P108E_COMPLETE_HUMAN_READING_PACKET_V1",
        paired_scenarios=199,new_native_replies=1393,cached_original_replies=199,
        source_report_sha256=io.sha(base/"report.json"),parts=parts,
        automatic_language_rating=False,root_read_status="PENDING",training_allowed=False))
    print("[E_READABLE_REPLIES]199 scenarios;1393 edited answers;13 plain text files",flush=True)


if __name__=="__main__":render()
