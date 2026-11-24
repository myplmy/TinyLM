"""Compare section descriptions with title-only selection in the native pipeline."""

import argparse
from contextlib import ExitStack
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
from time import perf_counter
from unittest.mock import patch

from scripts import diag_p077_native_table_retrieval as retrieval


TAG = "p077_native_table_descriptions_cpu_v1_20261121"
OUT = retrieval.OUT.with_name(TAG)
trial, native, mapped, codec, window = (retrieval.trial,retrieval.native,retrieval.mapped,
                                       retrieval.codec,retrieval.window)
full = retrieval.full
SELECTOR = codec.SCRIPTS/"p077_native_table_description.hpp"
SECTIONS = {
    "ko": (
        ("항만지원반","부두 적재 장비와 선박 하역 일정을 담당합니다.",
         "부두 적재 장비를 다루는 팀의 표를 보세요.","화물선을 싣는 인원의 자료에서 찾으세요."),
        ("품질검사반","결함 표본 검사와 출하 품질을 기록합니다.",
         "결함 표본 검사를 하는 조직의 표에서 찾으세요.","불량품을 가려내는 쪽의 자료에서 찾으세요."),
    ),
    "en": (
        ("Dock Services","Handles crane maintenance, dock cargo loading, and vessel schedules.",
         "Use the record for cargo loading and crane maintenance.","Read the team that puts freight on ships."),
        ("Inspection Office","Handles defect sampling, shipment inspection, and quality audit records.",
         "Use the defect sampling and quality audit record.","Read the crew that screens faulty stock."),
    ),
}
STYLES = ("explicit","shared_terms","synonyms")
ARMS = ("description","title")


def grams(text):
    value = "".join(re.findall(r"\w+",text.casefold()))
    return {value[i:i+3] for i in range(len(value)-2)}


def choose(hint, sections, use_summary):
    keys = [item[0].casefold() for item in sections]
    hint_key = "".join(re.findall(r"\w+",hint.casefold()))
    explicit = ["".join(re.findall(r"\w+",key)) in hint_key for key in keys]
    if use_summary and not any(explicit):
        query = grams(hint)
        left,right = [grams(item[1]) for item in sections]
        l,r = len(query & (left-right)),len(query & (right-left))
        return int(not (l>=2 and l>r))
    return int(not (explicit[0] and not explicit[1]))


def assemble(tok, known):
    rows = []
    for sample in known:
        if sample["phrasing"]!="explicit":
            continue
        lead,rest = sample["raw"].split("<SECTION>\n",1)
        first,rest = rest.split("\n<BACKGROUND>\n",1)
        background,rest = rest.split("\n<SECTION>\n",1)
        second,request = rest.split("\n<REQUEST>\n",1)
        _,question = request.split("\n",1)
        _,table0 = first.split("\n",1)
        _,table1 = second.split("\n",1)
        slots = SECTIONS[sample["language"]]
        tails = background[-sample["tail_chars"]:]
        left,_,meta,alias = slots[sample["target"]]
        explicit = f"{left} 자료를 보세요." if sample["language"]=="ko" else f"Use the record for {left}."
        parts = [f"{item[0]}\n<DESCRIPTION>\n{item[1]}\n<VALUES>\n{table}"
                 for item,table in zip(slots,(table0,table1),strict=True)]
        for kind,hint in zip(STYLES,(explicit,meta,alias),strict=True):
            body = background
            for _ in range(12):
                raw = (lead+"<SECTION>\n"+parts[0]+"\n<BACKGROUND>\n"+body
                       +"\n<SECTION>\n"+parts[1]+"\n<REQUEST>\n"+hint+"\n"+question)
                in_len = len(tok.encode(raw,add_special_tokens=False).ids)
                if in_len<=4096:
                    break
                body = body[64:]
            if not 3900<=in_len<=4096 or not body.endswith(tails):
                raise ValueError("could not preserve the exact recent cutoff inside a long source")
            arms = {}
            for arm in ARMS:
                chosen = choose(hint,slots,arm=="description")
                visible = lead+tails+"\n"+(table0,table1)[chosen]+question
                ids = tok.encode(visible,add_special_tokens=False).ids
                if len(ids)>2041:
                    raise ValueError("the native layout must stay inside the short model view")
                arms[arm] = dict(chosen=chosen,ids=ids)
            rows.append(dict(language=sample["language"],gold=sample["gold"],target=sample["target"],kind=kind,
                             raw=raw,tail_chars=sample["tail_chars"],full_tokens=in_len,arms=arms))
    if len(rows)!=12 or len({row["raw"] for row in rows})!=12:
        raise ValueError("expected twelve distinct full sources")
    return rows


def generated():
    src = retrieval.generated()
    replace = native.port.replace_once
    pairs = (
        (b'#include "p077_native_table_select.hpp"',b'#include "p077_native_table_description.hpp"'),
        (b"char* archive_fd, size_t tail_chars)",b"char* archive_fd, size_t tail_chars, bool descriptions)"),
        (b"p077_table::choose(std::string_view(text.data(), bytes),tail_chars)",
         b"p077_description::choose(std::string_view(text.data(), bytes),tail_chars,descriptions)"),
        (b'if (argc == 6 && std::strcmp(argv[1], "encode") == 0)',b'if (argc == 7 && std::strcmp(argv[1], "encode") == 0)'),
        (b"            encode(argv[0],argv[2],argv[3],argv[4],chars);",
         b'''            const std::string_view mode(argv[6]);
            check(mode=="title" || mode=="description","unknown retrieval mode");
            encode(argv[0],argv[2],argv[3],argv[4],chars,mode=="description");'''),
    )
    for before,after in pairs:
        src=replace(src,before,after)
    return src


def prepare():
    ref, (known,model,_,_) = retrieval.prepare()
    result = retrieval.OUT/"report.json"
    prior = trial.read_json(result)
    if prior["plan"]!=ref or len(prior["results"])!=8:
        raise ValueError("requires the exact native selector integration proof")
    _,(tok,_,_,_,_) = full.prepare()
    panels = assemble(tok,known)
    cpp = generated()
    device_digest = native.training.data.authored.digest(panels)
    plan = dict(tag=TAG,source=trial.file_sha(Path(__file__)),selector=trial.file_sha(SELECTOR),
                native=trial.file_sha(result),proof=ref["proof"],panel=device_digest,
                generated=sha256(cpp).hexdigest(),rows=len(panels))
    return plan,(panels,model,cpp)


def run(plan,deadline):
    if (OUT.exists() or os.environ.get("CUDA_VISIBLE_DEVICES")!="" or not deadline.tzinfo
            or deadline>mapped.compact.AUTHORIZATION_END
            or (deadline-datetime.now(deadline.tzinfo)).total_seconds()<360):
        raise ValueError("requires a fresh and bounded native CPU comparison")
    checked,(panels,model,cpp)=prepare()
    if checked!=plan:
        raise ValueError("the sealed description comparison changed")
    cpu=min(set(model["cpus"]) & os.sched_getaffinity(0))
    os.sched_setaffinity(0,{cpu})
    OUT.mkdir()
    source=OUT/"codec_description.cpp"
    source.write_bytes(cpp)
    binary=OUT/"codec_description"
    build=["/usr/bin/g++","-std=c++17","-O3","-Wall","-Wextra","-Werror","-I",str(codec.OUT),
           "-I",str(codec.SCRIPTS),str(source),"-ldl","-o",str(binary)]
    subprocess.run(build,check=True,timeout=65)
    with patch.object(window,"OUT",OUT):
        engine=window.get_binary(plan)
    results=[]
    with ExitStack() as stack:
        with patch.object(mapped.request,"OUT",OUT):
            state=plan["proof"]["native"]["native"]["native"]["state_sha256"]
            image=mapped.request.pack_model(stack,state,model)
        archive=os.open(codec.ASSET,os.O_RDONLY)
        stack.callback(os.close,archive)
        for index,row in enumerate(panels):
            reusable={}
            for arm in ARMS:
                if (OUT/"STOP").exists() or (deadline-datetime.now(deadline.tzinfo)).total_seconds()<90:
                    raise TimeoutError("the description route reached its boundary")
                expected=row["arms"][arm]
                ids=tuple(expected["ids"])
                reuse=ids in reusable
                if not reuse:
                    begin=perf_counter()
                    proc=subprocess.run([binary,"encode",engine,str(image),str(archive),str(row["tail_chars"]),arm],
                                        pass_fds=(image,archive),input=row["raw"].encode("utf-8"),
                                        capture_output=True,timeout=100)
                    seconds=perf_counter()-begin
                    if proc.returncode:
                        print(proc.stderr.decode("utf-8","replace"),flush=True)
                        proc.check_returncode()
                    report=json.loads(proc.stdout)
                    if (report["encoding"]["chosen"]!=expected["chosen"] or report["encoding"]["ids"]!=expected["ids"]
                            or not report["native_pid"]==report["encoding"]["pid"]==report["decoding"]["pid"]):
                        raise ValueError("the native selection or context differed")
                    trial.publish(OUT/f"case_{index:02d}_{arm}.json",report)
                    reusable[ids]=(arm,report,seconds)
                origin,got,seconds=reusable[ids]
                ended=got["native"]["ids"][-1]==plan["proof"]["stop"][0]
                answer=got["decoding"]["text"].strip()
                result=dict(case=index,arm=arm,kind=row["kind"],language=row["language"],target=row["target"],
                            selected=expected["chosen"],correct_source=expected["chosen"]==row["target"],
                            full_tokens=row["full_tokens"],exact=ended and answer==row["gold"],eot=ended,answer=answer)
                if reuse:
                    result["reused"]=origin
                else:
                    result.update(seconds=seconds,peak_rss=native.bounded.prior.peak(got))
                results.append(result)
                print(json.dumps(result,ensure_ascii=False),flush=True)
    trial.publish(OUT/"report.json",dict(plan=plan,cpu=cpu,results=results,executable=trial.file_sha(binary)))


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
        parser.error("requires sealed exact receipts and a cutoff")
    run(plan,args.stop_by)
    return 0


if __name__=="__main__":
    main()
