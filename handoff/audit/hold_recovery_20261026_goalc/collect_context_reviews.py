"""Collect exact text artifacts and prepare author-independent context checks."""
import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts.p106b_native_text_audit import file_sha,write_json
from scripts import p106b_hold_recovery as recovery

parser_path=ROOT/"handoff/audit/source_cleanup_20261026_goalc/build_review_manifest.py"
spec=importlib.util.spec_from_file_location("review_table",parser_path)
table=importlib.util.module_from_spec(spec);spec.loader.exec_module(table)


def rows(path,default_source=None):
    header=None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):continue
        cells=table.table_cells(line)
        if cells and cells[0]=="ID":header=cells;continue
        if cells and default_source and cells[0].isdigit():
            assert default_source in ("expanded_train","historical_train","validation")
            cells[0]=default_source+":"+cells[0]
        if not cells or not re.fullmatch(r"(?:expanded_train|historical_train|validation):[0-9]+",cells[0]):continue
        assert header is not None
        if len(cells)>len(header):
            reason=next(i for i,x in enumerate(header) if "근거" in x or "사유" in x or x=="이유")
            extra=len(cells)-len(header)
            cells=cells[:reason]+[" | ".join(cells[reason:reason+extra+1])]+cells[reason+extra+1:]
        assert len(cells)==len(header),(path,cells)
        result=dict(zip(header,cells))
        if "결정" in result and "판정" not in result:result["판정"]=result["결정"]
        if "새 본문" in result and "파일" not in result:result["파일"]=result["새 본문"]
        yield result


def collect(roles,wave):
    base=recovery.BASE;catalog={}
    for name in ["packets_initial_v2/manifest.json","proposals_v1/review_packets/manifest.json"]:
        for raw in json.loads((base/name).read_text())["rows"]:
            raw=dict(raw);raw["original_path"]=raw.get("original_path",raw.get("path"));catalog[raw["id"]]=raw
    targets={"context_controls":"historical_review","historical_review":"context_controls",
        "context_latin":"legacy_review","legacy_review":"context_hangul","context_hangul":"context_latin"}
    result=[];by_reviewer={};counts={}
    for role in roles:
        review=base/"agents"/role/"recovery_context_v2/review.md"
        assignment=base/"assignments"/(role+"_recovery_context_v2.md")
        expected=set(re.findall(r"^\| ((?:expanded_train|historical_train|validation):[0-9]+) \|",assignment.read_text(),re.M))
        found=set();role_counts=Counter()
        for item in rows(review):
            ident=item["ID"];decision=item["판정"];assert ident in expected and ident not in found
            artifact_review=review;superseded=None
            if role=="context_hangul" and ident=="expanded_train:705988":
                revised=review.parent.parent/"recovery_context_v3/review.md"
                replacement=[r for r in rows(revised) if r["ID"]==ident]
                assert len(replacement)==1
                superseded=str(review.parent/(ident.replace(":","_")+".txt"))
                item=replacement[0];decision=item["판정"];artifact_review=revised
            assert decision in ["KEEP","EDIT","HOLD"],(ident,decision)
            found.add(ident);role_counts.update([decision]);raw=catalog[ident];source=ROOT/raw["original_path"]
            assert file_sha(source)==raw["original_text_sha256"],ident
            reason=next(v for k,v in item.items() if "근거" in k or "사유" in k or k=="이유")
            row=dict(id=ident,role=role,decision=decision,reason=reason,review=str(artifact_review.relative_to(ROOT)),
                input_text_sha256=raw["original_text_sha256"],original_path=raw["original_path"],
                source=raw["source"],source_ids=raw["source_ids"],source_ids_sha256=raw["source_ids_sha256"],
                root_reviewed=False,recovery_review=True,source_proof="handoff/audit/hold_recovery_20261026_goalc/review_source_proof_v1.json")
            stem=ident.replace(":","_");target=artifact_review.parent/(stem+".txt");sidecar=artifact_review.parent/(stem+"_hold.md")
            if superseded:row["preserved_earlier_draft"]=str(Path(superseded).relative_to(ROOT))
            if decision=="EDIT":
                output=next(v for k,v in item.items() if "파일" in k or "txt" in k.lower())
                assert target.name in output and target.is_file(),(ident,output)
                assert 0<target.stat().st_size<20_000_000
                assert not recovery.corpus.MEMOS.search(target.read_text(encoding="utf-8")),ident
                row.update(path=str(target.relative_to(ROOT)),sha256=file_sha(target))
            if sidecar.exists():
                assert sidecar.stat().st_size<20_000_000
                row.update(sidecar_path=str(sidecar.relative_to(ROOT)),sidecar_sha256=file_sha(sidecar))
            result.append(row);by_reviewer.setdefault(targets[role],[]).append(row)
        assert found==expected,(role,expected-found,found-expected)
        counts[role]=dict(role_counts)
    write_json(base/("context_candidates_"+wave+".json"),dict(schema="P106B_CONTEXT_RECOVERY_CANDIDATES_V2",rows=result,counts=counts,admission="NOT_APPROVED"))
    for reviewer,items in by_reviewer.items():
        lines=["# "+reviewer+" "+wave+" 실제 저장물 독립 대조","",
            "아래 원문·실제본문·존재하는sidecar와작성자review의해당ID행만읽는다. 새출력은자기 agents/"+reviewer+"/counter_context_"+wave+".md 하나다. 본문수정/코드/시험/스크립트/계수/해시/모델/GPU/Git/웹/JSON/memory/목록외0. 기존부정기록·초안은보존한다.","",
            "| ID | 작성판정 | 정확원문 | 실제본문 | sidecar | 작성자review |","|---|---|---|---|---|---|"]
        for row in items:
            body=row.get("path",row["original_path"])
            lines.append("| "+" | ".join([row["id"],row["decision"],"`"+row["original_path"]+"`","`"+body+"`",
                "`"+row["sidecar_path"]+"`" if row.get("sidecar_path") else "없음","`"+row["review"]+"`"])+" |")
        lines.extend(["","원문/실제본문을전문대조하고 | ID | 판정 | 근거 | 전체 판독 | 표로PASS/REVISE/HOLD를기록한다. 작성판정HOLD가과도하고독립복구가가능하면RECOVERABLE과근거를적는다. 실제유효정보/서지/코드/Unicode문자/고유명사/숫자/부정/조건/인용주체가보존됐는지,빈절/UI/고아참조가남았는지확인한다. sidecar기록은오삭제를자동정당화하지않는다. 누락수식/제목/이름은생성하지않는다. 1422568은비코드단위표의정확한추출fence4문자만제거하는총괄판정이있으며표값/순서는모두보존돼야한다. 불명확한문제는총괄에게보낸다. 잘린출력은지정파일에서구간별로끝까지재독한다."])
        path=base/"assignments"/(reviewer+"_counter_context_"+wave+".md")
        with path.open("x",encoding="utf-8") as stream:stream.write(chr(10).join(lines)+chr(10))
    print(dict(wave=wave,counts=counts,counter_assignments={k:len(v) for k,v in by_reviewer.items()}))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--roles",nargs="+",required=True);p.add_argument("--wave",required=True)
    a=p.parse_args();assert set(a.roles)<=set(recovery.ROLE_NAMES);assert a.wave.isascii() and a.wave.replace("_","").isalnum()
    collect(a.roles,a.wave)
