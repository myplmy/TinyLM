"""Reproduce text-only review inventory; coordinator approval is separate."""
from pathlib import Path
import difflib
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/"data_cache/p106b_corpus_cleanup_v1_20261026_goalc"
ROLES=["legacy_review","historical_review","context_hangul","context_latin","context_controls"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def table_cells(line):
    """Split table delimiters while preserving pipes inside inline code."""
    cells=[];cell=[];quoted=False;escaped=False
    for char in line.strip():
        if char=="|" and not quoted and not escaped:
            cells.append("".join(cell).strip().strip("`* "));cell=[]
        else:
            cell.append(char)
            if char=="`" and not escaped:quoted=not quoted
        escaped=char=="\\" and not escaped
    cells.append("".join(cell).strip().strip("`* "))
    return cells[1:-1]


def review_rows(path):
    header=None
    for line in path.read_text().splitlines():
        if not line.startswith("|"):continue
        cells=table_cells(line)
        if cells and cells[0]=="ID":
            header=cells
            continue
        if not cells or not re.fullmatch("(expanded_train|historical_train|validation):[0-9]+",cells[0]):continue
        if header is None or len(cells)!=len(header):raise ValueError((path,"table schema differs",cells))
        output_index=next(i for i,h in enumerate(header) if "txt" in h.lower())
        reason_index=next(i for i,h in enumerate(header)
                          if "근거" in h or h=="이유" or h=="Review basis")
        yield cells[0],cells[1],cells[output_index],cells[reason_index]


def main():
    by_sha={};reviews=[];instance_counts={}
    for phase,packet in [("","packets_initial"),("coverage_v2","packets_coverage_v2"),("final_context","packets_final")]:
        catalog={r["id"]:r for r in json.loads((BASE/packet/"manifest.json").read_text())["rows"]}
        for role in ROLES[2:] if not phase else ROLES:
            folder=BASE/"agents"/role
            if phase:folder=folder/phase
            path=folder/"review.md";found=[]
            for ident,decision,filename,reason in review_rows(path):
                if decision not in ["KEEP","EDIT","HOLD"]:raise ValueError((path,ident,decision))
                raw=catalog[ident];source=ROOT/raw["path"]
                if digest(source)!=raw["sha256"]:raise ValueError("sealed packet source SHA differs")
                row=dict(input_text_sha256=raw["sha256"],decision=decision,reason=reason,
                    review=str(path.relative_to(ROOT)),id=ident,original_path=str(source.relative_to(ROOT)),
                    role=role,root_reviewed=False)
                if decision=="EDIT":
                    target=folder/filename
                    row.update(path=str(target.relative_to(ROOT)),sha256=digest(target))
                by_sha.setdefault(raw["sha256"],[]).append(row);found.append(ident)
            instance_counts[str(path.relative_to(ROOT))]=len(found);reviews.append(str(path.relative_to(ROOT)))
            expected=(15 if role=="context_hangul" else 16 if role=="context_latin" else 13) if not phase else 32 if phase=="coverage_v2" else 10 if role in ROLES[:2] else 9
            if len(found)!=expected:raise ValueError((path,len(found),expected))
    legacy=ROOT/"data_cache/p106b_native_source_context_clean_v1_20261026"
    for number,decision,name in [("01","EDIT","source_01_v2.txt"),("02","EDIT","source_02.txt"),
            ("03","HOLD",None),("04","EDIT","source_04_v3.txt"),("05","EDIT","source_05.txt"),
            ("06","HOLD",None),("07","HOLD",None),("08","EDIT","source_08_v3.txt")]:
        source=ROOT/"handoff/audit/oct26_research/source_context_review_v1/long_source_05/original.txt" if number=="05" else legacy/("source_"+number+"_original.txt")
        role="historical_review" if number=="05" else "legacy_review"
        review=BASE/"agents"/role/("review_v2.md" if number=="05" else "review_v3.md")
        row=dict(input_text_sha256=digest(source),decision=decision,
            reason="기존 대표 원문 재검토; 인용·학술어·불확실성 보존과 비본문 분리; 손상표/제목 HOLD",
            review=str(review.relative_to(ROOT)),id="source_"+number,original_path=str(source.relative_to(ROOT)),
            role=role,root_reviewed=False)
        if name:
            target=BASE/"agents"/role/name
            row.update(path=str(target.relative_to(ROOT)),sha256=digest(target))
        by_sha.setdefault(row["input_text_sha256"],[]).append(row);reviews.append(str(review.relative_to(ROOT)))
    output=[];conflicts=[];edits=[]
    for key,opinions in by_sha.items():
        decisions={r["decision"] for r in opinions}
        if "HOLD" in decisions:
            chosen=next(r for r in opinions if r["decision"]=="HOLD").copy()
        elif "EDIT" in decisions:
            alternatives=[r for r in opinions if r["decision"]=="EDIT"]
            chosen=alternatives[-1].copy()
            if len({r["sha256"] for r in alternatives})>1:
                chosen.update(decision="HOLD",reason="독립 정제본 불일치; 총괄 보수적 보류")
                chosen.pop("path",None);chosen.pop("sha256",None)
        else:chosen=opinions[-1].copy()
        if len(decisions)>1:
            conflicts.append(dict(input_text_sha256=key,ids=[r["id"] for r in opinions],
                                 opinions=sorted(decisions),provisional_decision=chosen["decision"]))
        chosen["opinions"]=opinions
        if chosen["decision"]=="EDIT":
            old=(ROOT/chosen["original_path"]).read_text();new=(ROOT/chosen["path"]).read_text()
            old_lines,new_lines=old.splitlines(keepends=True),new.splitlines(keepends=True)
            changes=[]
            for tag,a,b,c,d in difflib.SequenceMatcher(a=old_lines,b=new_lines,autojunk=False).get_opcodes():
                if tag!="equal":changes.append(dict(source_lines=[a+1,b],clean_lines=[c+1,d],
                    removed="".join(old_lines[a:b]),added="".join(new_lines[c:d])))
            edits.append(dict(id=chosen["id"],input_sha=key,original_path=chosen["original_path"],
                clean_path=chosen["path"],role=chosen["role"],changes=changes))
        output.append(chosen)
    value=dict(schema="P106B_ROOT_TEXT_ADOPTION_CANDIDATES_V1",rows=output,reviews=sorted(set(reviews)),
               instance_counts=instance_counts,conflicts=conflicts,all_root_approved=False)
    for name,document in [("root_adoption_candidates.json",value),("edit_span_readback.json",dict(edits=edits))]:
        with (BASE/name).open("x",encoding="utf-8") as stream:json.dump(document,stream,ensure_ascii=False,indent=2)
    print(json.dumps(dict(review_instances=sum(instance_counts.values())+8,unique_input_texts=len(output),
        candidate_decisions={d:sum(r["decision"]==d for r in output) for d in ["KEEP","EDIT","HOLD"]},
        conflicts=conflicts,manual_edit_bodies=len(edits)),ensure_ascii=False))


if __name__=="__main__":main()
