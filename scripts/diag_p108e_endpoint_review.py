"""Readable original/selected-layer replies; original schema and history retained."""
from scripts import diag_p108c_scope as io


def main():
    base=io.ROOT/"test_result/evidence/p108e_margin_sqp_v1_s1337/endpoint_predict_v1/actual"
    parent=io.read(base/"report.json");selected=io.read(base/"chosen_layer12/report.json")
    if(parent["status"]!="ALL14_ENDPOINT_PREDICTION_COMPLETE" or not parent["original_core_restored"]
       or parent["cuda_allocated_after_bytes"] or parent["cuda_reserved_after_bytes"] or selected["layer"]!=12):
        raise ValueError("complete native selection, restored original and empty CUDA required")
    rows=list(io.closed_answers(base/"chosen_layer12",selected["answers_manifest"]).values())
    if len(rows)!=199:raise ValueError("all199 original/edited scenarios required")
    directory=io.ROOT/"review_request/20261116_NIGHT_P108E_endpoint12_v1"
    if directory.exists():raise FileExistsError("preserve original reading packet")
    directory.mkdir();parts=[]
    for start in range(0,len(rows),16):
        lines=["P108E 사전 예측 선택12층의 실제 질문·답","정답성/문법/관련성/반복은 서로 다른 판독 항목입니다.",
               "대화2/3턴은 각 모델의 앞 답이 달라진 실제 이력입니다. 자동 언어 평점은 없습니다.",""]
        for row in rows[start:start+16]:
            lines.extend([row["id"]+" / "+row["evaluation_panel"],"질문> "+row["question"],
                          "비교 정답> "+str(row.get("expected")),"원본 답> "+row["baseline_answer"]])
            if row["actual_history"]:
                lines.append("선택 모델의 실제 앞 대화>")
                lines.extend(m["role"]+"> "+m["content"] for m in row["actual_history"])
            lines.extend(["12층 수정 답> "+row["answer"],"종료> "+row["generation"]["finish_reason"],""])
        body=chr(10).join(lines)+chr(10)
        if len(body.encode())>=2_000_000:raise ValueError("split reading files before2MB")
        path=directory/("paired_answers_"+str(start//16+1).zfill(3)+".txt")
        with path.open("x",encoding="utf-8") as stream:stream.write(body)
        parts.append(dict(path=str(path.relative_to(io.ROOT)),sha256=io.sha(path),rows=len(rows[start:start+16])))
    io.write_new(directory/"source_rows.json",dict(rows=rows))
    io.write_new(directory/"READING_MANIFEST.json",dict(schema="P108E_ENDPOINT12_COMPLETE_READING_PACKET_V1",
        paired_scenarios=199,selected_layer=12,source_report_sha256=io.sha(base/"chosen_layer12/report.json"),
        parts=parts,root_read_status="PENDING",training_allowed=False,new_model_calls=0))
    print("[ENDPOINT_READABLE]all199 pairs;13 plain files;no new model calls",flush=True)


if __name__=="__main__":main()
