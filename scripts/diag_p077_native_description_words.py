"""Compare whole-word and character overlap on a fresh authored retrieval panel."""

import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
from unittest.mock import patch

from scripts import diag_p077_native_table_descriptions as base


TAG = "p077_native_description_words_cpu_v1_20261121"
OUT = base.OUT.with_name(TAG)
trial,native = base.trial,base.native
BASE_PREPARE,BASE_OUTPUT = base.prepare,base.OUT
ARMS = ("words","description","title")
STOPWORDS = (
    "the","and","for","use","record","team","that","with","from","crew","records","work","which",
    "자료","기록","조직","부서","팀","표","에서",
)
PANELS = (
    {
        "ko": (
            ("전기관리팀","복도 조명 전선 교체와 비상등 검사를 맡습니다.",
             "복도 조명 전선 업무를 맡은 자료를 확인하세요.","길을 밝히는 기구를 수리하는 쪽의 기록을 보세요."),
            ("창호보수팀","창틀 유리 판재 치수와 문지방 수리를 맡습니다.",
             "창틀 유리 판재 업무 쪽의 자료를 보세요.","건물 밖이 보이는 틈을 막는 담당의 기록을 보세요."),
        ),
        "en": (
            ("Electrical Desk","Corridor lighting, emergency wiring, and voltage tests.",
             "Use the corridor lighting and emergency wiring record.","Read the staff who repair bulbs."),
            ("Glazing Office","Window frames, glass sheets, and seal replacement.",
             "Use the window frames and glass sheets record.","Read the staff who stop drafts around openings."),
        ),
    },
    {
        "ko": (
            ("수질운영실","하천 수질 표본 채취와 탁도 측정 장비를 관리합니다.",
             "하천 수질 표본 관련 기록을 참조하세요.","물이 얼마나 흐린지 살피는 인원의 자료에서 답하세요."),
            ("기록보존실","고문서 복원 상자와 온도 습도 조절 장치를 기록합니다.",
             "고문서 복원 상자 업무의 표를 보세요.","오래된 종이가 상하지 않게 하는 부서 자료를 보세요."),
        ),
        "en": (
            ("Water Sampling","River turbidity, sediment collection, and stream sampling.",
             "Use the river turbidity and sediment collection record.","Read the team that checks if creeks are cloudy."),
            ("Archive Records","Manuscript restoration, storage boxes, and humidity control.",
             "Use the manuscript restoration and storage boxes record.","Read the team that protects old paper."),
        ),
    },
)


def terms(text):
    return {s for s in re.findall(r"\w+",text.casefold()) if len(s)>=2 and s not in STOPWORDS}


def word_view(tokenizer,row):
    lead,rest=row["raw"].split("<SECTION>\n",1)
    before,rest=rest.split("\n<BACKGROUND>\n",1)
    background,rest=rest.split("\n<SECTION>\n",1)
    after,request=rest.split("\n<REQUEST>\n",1)
    hint,question=request.split("\n",1)
    entries=[]
    for section in (before,after):
        name,content=section.split("\n<DESCRIPTION>\n",1)
        description,table=content.split("\n<VALUES>\n",1)
        entries.append((name,description,table))
    normal="".join(re.findall(r"\w+",hint.casefold()))
    named=["".join(re.findall(r"\w+",e[0].casefold())) in normal for e in entries]
    left,right=[terms(e[1]) for e in entries]
    wanted=terms(hint)
    a,b=len(wanted & (left-right)),len(wanted & (right-left))
    chosen=int(not (named[0] and not named[1])) if any(named) else int(not (a>=2 and a>b))
    visible=lead+background[-row["tail_chars"]:]+"\n"+entries[chosen][2]+question
    return dict(chosen=chosen,ids=tokenizer.encode(visible,add_special_tokens=False).ids)


def generated():
    src=base.generated()
    replace=native.port.replace_once
    normal=(base.SELECTOR.parent/"p077_native_table_select.hpp").read_bytes().replace(b"#pragma once\n",b"",1)
    normal=replace(normal,b"normalized(std::string_view value) const",
                   b"normalized(std::string_view value,bool boundaries=false) const")
    normal=replace(normal,b"                result.append(folded.data() + begin, static_cast<size_t>(i - begin));\n            }",
                   b"                result.append(folded.data() + begin, static_cast<size_t>(i - begin));\n"
                   b"            } else if (boundaries && !result.empty() && result.back()!=u' ') result.push_back(u' ');")
    selector=base.SELECTOR.read_bytes().replace(b"#pragma once\n",b"",1)
    selector=replace(selector,b'#include "p077_native_table_select.hpp"',normal)
    word_constants=",".join("u"+json.dumps(w,ensure_ascii=True) for w in STOPWORDS)
    source=f'''
inline std::set<std::u16string> whole_words(const std::u16string& text) {{
    static const std::set<std::u16string> stop{{{word_constants}}};
    std::set<std::u16string> result;
    for (size_t i=0; i<text.size();) {{
        const auto end=text.find(u' ',i);
        const auto word=text.substr(i,end==std::u16string::npos ? end : end-i);
        if (word.size()>=2 && !stop.count(word)) result.insert(word);
        if (end==std::u16string::npos) break;
        i=end+1;
    }}
    return result;
}}
'''.encode("ascii")
    selector=replace(selector,b"inline p077_table::Selection choose(",source+b"\ninline p077_table::Selection choose(")
    selector=replace(selector,b"size_t tail, bool use_summary)",b"size_t tail, bool use_summary,bool words)")
    for key,item in ((b"query",b"hint"),(b"left",b"entries[0].summary"),(b"right",b"entries[1].summary")):
        variable=key+b"_grams"
        argument=b"query" if item==b"hint" else b"key.normalized("+item+b")"
        selector=replace(selector,b"const auto "+variable+b" = grams("+argument+b");",
                         b"const auto "+variable+b" = words ? whole_words(key.normalized("+item+b",true)) : grams("+argument+b");")
    src=replace(src,b'#include "p077_native_table_description.hpp"',selector)
    src=replace(src,b"size_t tail_chars, bool descriptions)",b"size_t tail_chars,bool descriptions,bool words)")
    src=replace(src,b"tail_chars,descriptions);",b"tail_chars,descriptions,words);")
    src=replace(src,b'mode=="title" || mode=="description"',b'mode=="title" || mode=="description" || mode=="words"')
    return replace(src,b'chars,mode=="description");',b'chars,mode!="title",mode=="words");')


def prepare():
    with patch.object(base,"ARMS",("description","title")):
        earlier,_=BASE_PREPARE()
    known_path=BASE_OUTPUT/"report.json"
    prior=trial.read_json(known_path)
    if prior["plan"]!=earlier or len(prior["results"])!=24:
        raise ValueError("requires the completed description-versus-title proof")
    ref, (raw,identity,_,_) = base.retrieval.prepare()
    _,(tok,_,_,_,_)=base.full.prepare()
    panels=[]
    for descriptions in PANELS:
        with patch.object(base,"SECTIONS",descriptions),patch.object(base,"ARMS",("description","title")):
            panels.extend(base.assemble(tok,raw))
    for row in panels:
        row["arms"]["words"]=word_view(tok,row)
    if len(panels)!=24 or len({r["raw"] for r in panels})!=24:
        raise ValueError("the new domains must produce distinct held-out documents")
    source=generated()
    plan=dict(tag=TAG,source=trial.file_sha(Path(__file__)),prior=trial.file_sha(known_path),
              proof=ref["proof"],generated=sha256(source).hexdigest(),
              panel=native.training.data.authored.digest(panels),rows=len(panels))
    return plan,(panels,identity,source)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("check","run"))
    parser.add_argument("--receipt",type=Path)
    parser.add_argument("--stop-by",type=datetime.fromisoformat)
    args=parser.parse_args()
    plan,_=prepare()
    if args.mode=="check":
        print(json.dumps(plan,indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt)!=plan:
        parser.error("requires the sealed held-out panel and an approved deadline")
    with patch.object(base,"OUT",OUT),patch.object(base,"prepare",prepare),patch.object(base,"ARMS",ARMS):
        base.run(plan,args.stop_by)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
