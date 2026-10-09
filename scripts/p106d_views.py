"""Closed code-owned fixed/view corpus. No files, teacher or model loading.

Root assignment precedes language children/views. Four task families are not
claimed to create hundreds of independent knowledge concepts.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tinylm.chat.canonical import normalize, validate
from scripts import p106b_rule_views as rules

VERSION = "P106D_MATCHED_RULE_VIEWS_V1"
FAMILIES = ("arithmetic", "boolean", "lookup", "format")


def hash_object(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode()).hexdigest().upper()


def root_definition(data):
    return {key:value for key,value in data.items() if key!="index"}


def recipe(family, index):
    if family == "arithmetic":
        return {"family":family,"index":index,"a":2+index%18,"b":2+(index//18)%18,"op":("+","-","*")[index//324%3]}
    if family == "boolean":
        values={name:bool(index>>slot&1) for slot,name in enumerate("ABCD")}
        op=("and","or","xor","implies","eq")[index//16%5]
        return {"family":family,"index":index,"values":values,
            "expression":{"op":op,"args":["A",{"op":"not","args":["B"]}]}}
    if family == "lookup":
        return {"family":family,"index":index,"color1":index%4,"color2":(index//4)%4,
                "name_index":index//16,"target":index%2}
    return {"family":family,"index":index,"value":index}


def spec_for(data, language, split):
    family=data["family"]
    if language not in ("ko","en") or split not in ("train","val"):
        raise ValueError("known language/root split required")
    if family=="arithmetic":
        kind="integer_arithmetic"; payload={k:data[k] for k in ("a","b","op")}
    elif family=="boolean":
        kind="boolean_expression"; payload={k:copy.deepcopy(data[k]) for k in ("values","expression")}
    elif family=="lookup":
        colors=("빨강","파랑","초록","노랑") if language=="ko" else ("red","blue","green","yellow")
        names=[("가" if language=="ko" else "A")+str(data["name_index"]),
               ("나" if language=="ko" else "B")+str(data["name_index"])]
        kind="table_lookup"; payload={"entries":[[names[0],colors[data["color1"]]],[names[1],colors[data["color2"]]]],"target":names[data["target"]]}
    else:
        kind="verbatim_qa"; n=data["value"]
        payload={"question":f"기록 값은 {n}입니다. 이 값만 읽어 쓰세요." if language=="ko" else f"The recorded value is {n}. Return only that value.","answer":str(n)}
    root=hash_object(root_definition(data))
    return {"owner":"code","kind":kind,"language":language,"split":split,
        "root_id":root,"minimum":2,"maximum":19,"payload":payload,
        "source":{"scope":"public_or_code","family":"p106d_code_"+family,
                  "license":"repository-code-generated","sha256":hash_object([VERSION,data,language])}}


def base_pair(spec):
    q,a=rules._render(spec,spec["payload"])
    return [{"role":"user","content":q},{"role":"assistant","content":a}]


def closed_row(spec, payload, *, probe=False):
    """Construct a new closed probe or sham-update, not transform a val file."""
    q=rules.condition_question(spec,payload); _,a=rules._render(spec,payload)
    return validate(normalize({"messages":base_pair(spec)+[{"role":"user","content":q},{"role":"assistant","content":a}],
        "meta":{"source":"p106d_code_probe" if probe else "p106d_code_fixed",
        "source_license":spec["source"]["license"],"source_sha256":spec["source"]["sha256"],
        "source_family":spec["source"]["family"],"language":spec["language"],"split":spec["split"],
        "root_concept_id":spec["root_id"],"root_definition_sha256":hash_object(spec["payload"]),
        "source_original":copy.deepcopy(spec["payload"]),"derived_payload":copy.deepcopy(payload),
        "truth_scope":"code-owned operation only","unique_knowledge_claim":False}}))


def format_probe(spec, key):
    q,a=rules._render(spec,spec["payload"])
    follow=(f"앞서 한 답변의 문자열 전체를 {key} 항목 하나에 넣은 JSON 객체만 출력하세요. 내용을 고치거나 요약하지 마세요." if spec["language"]=="ko"
            else f"Return only one JSON object with exactly one {key} key containing your entire previous answer string. Do not correct or summarize its content.")
    return validate(normalize({"messages":[{"role":"user","content":q},{"role":"assistant","content":a},
        {"role":"user","content":follow},{"role":"assistant","content":json.dumps({key:a},ensure_ascii=False,separators=(",",":"))}],
        "meta":{"source":"p106d_code_probe","source_family":spec["source"]["family"],
            "source_license":spec["source"]["license"],"source_sha256":spec["source"]["sha256"],
            "root_concept_id":spec["root_id"],"split":"val","language":spec["language"],
            "truth_scope":"known verbatim JSON transformation only","unique_knowledge_claim":False}}))


def real_signature(row, tokenizer):
    from tinylm.data.sft import encode_conversation,sft_targets
    ids,labels,_=encode_conversation(row,tokenizer,"chatml"); x,y=sft_targets(ids,labels)
    targets=sum(v>=0 for v in y)
    if not 0<len(x)<=1024 or not targets: raise ValueError("invalid context/assistant mask")
    return len(x),targets


def text_at(row, position):
    return row["messages"][position]["content"][0]["text"]


def build(signature, *, train_rows=256, val_rows=64, seed=1337, attempts=64):
    if train_rows%8 or val_rows%8 or attempts<1:
        raise ValueError("balanced family/language row counts and attempts required")
    fixed=[]; epochs=[[] for _ in range(4)]; probes=[]; rejected={}; roots={"train":[],"val":[]}
    seen_questions=set()
    def reject(reason): rejected[reason]=rejected.get(reason,0)+1
    for family in FAMILIES:
        train_need=train_rows//8; val_need=val_rows//8; train_count=val_count=0
        for index in range(972 if family=="arithmetic" else 2048):
            data=recipe(family,index); root=hash_object(root_definition(data))
            split="val" if int(root[:8],16)%5==0 else "train"
            if (split=="train" and train_count>=train_need) or (split=="val" and val_count>=val_need): continue
            children=[]
            try:
                for language in ("ko","en"):
                    spec=spec_for(data,language,split)
                    first=base_pair(spec)[0]["content"]
                    if first in seen_questions: raise ValueError("repeated_first_question")
                    if split=="val":
                        payload=copy.deepcopy(spec["payload"])
                        if family=="arithmetic": payload["a"]+=21; payload["b"]+=21
                        elif family=="boolean": payload["values"]["A"]=not payload["values"]["A"]
                        elif family=="lookup": payload["target"]=payload["entries"][1-data["target"]][0]
                        row=format_probe(spec,"reply") if family=="format" else closed_row(spec,payload,probe=True)
                        signature(row); children.append((first,row)); continue
                    baseline=rules.make_format_followup(spec) if family=="format" else closed_row(spec,spec["payload"])
                    sig=signature(baseline); views=[]
                    for epoch in range(4):
                        candidate=None
                        for attempt in range(attempts):
                            if family=="format":
                                field=("result","value","reply")[(epoch+attempt)%3]
                                row=rules.make_format_followup(spec,view_index=epoch,field_name=field)
                            else:
                                row=rules.make_condition_followup(spec,seed=seed+attempt+index*101,view_index=epoch)
                            if (signature(row)==sig and text_at(row,-2)!=text_at(baseline,-2)
                                    and text_at(row,0)==first): candidate=row; break
                        if candidate is None: raise ValueError("no_matching_view")
                        candidate["meta"].update(epoch_view=epoch+1,root_family=family,selection_attempt=attempt+1)
                        views.append(candidate)
                    if len({(text_at(row,-2),text_at(row,-1)) for row in views})<2:
                        raise ValueError("not_enough_distinct_epoch_views")
                    baseline["meta"].update(root_family=family,root_concept_id=root)
                    children.append((first,baseline,views,sig))
            except ValueError as e:
                reject(str(e)); continue
            for first,*_rest in children: seen_questions.add(first)
            if split=="val":
                val_count+=1; roots["val"].append(root); probes.extend(row for first,row in children)
            else:
                train_count+=1; roots["train"].append(root)
                for first,baseline,views,sig in children:
                    fixed.append(baseline)
                    for epoch,row in enumerate(views): epochs[epoch].append(row)
            if train_count>=train_need and val_count>=val_need: break
    ready=len(fixed)==train_rows and len(probes)==val_rows and all(len(e)==train_rows for e in epochs)
    if set(roots["train"])&set(roots["val"]): raise ValueError("root split leakage")
    expected=[signature(r) for r in fixed]
    for rows in epochs:
        if [signature(r) for r in rows]!=expected: raise ValueError("slot x/target mismatch")
    return {"fixed":fixed,"epochs":epochs,"probes":probes,"report":{
        "schema":VERSION,"ready":ready,"train_rows":len(fixed),"val_rows":len(probes),
        "root_instances":{k:len(v) for k,v in roots.items()},"roots":roots,"seed":seed,
        "task_families":list(FAMILIES),"knowledge_claim":"four procedural families, not a large unique-knowledge corpus",
        "selection_rejected":rejected,"token_signature":expected,
        "epoch_x_tokens":sum(n for n,t in expected),"epoch_assistant_targets":sum(t for n,t in expected),
        "four_epoch_processed_tokens":4*sum(n for n,t in expected),"slot_token_target_match":True,
        "source_definition_sha256":hash_object(roots),"model_loading":"NOT_RUN","meaningful_training":"NOT_RUN"}}
