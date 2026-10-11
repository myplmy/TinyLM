"""Opt-in balanced4096 procedural corpus; pure callbacks, no model/data IO.

Both arms have the same changed/unchanged curriculum. The fixed arm repeats
one accepted view; the view arm cycles matched alternatives of that root.
"""
from __future__ import annotations
import copy
import random
import time
from scripts import p106d_views as small
from scripts import p106b_rule_views as rules

VERSION="P106D_BALANCED_MATCHED4096_V2"
KEYS=("answer","value","result","reply")


def node(op,*args):
    return {"op":op,"args":list(args)}


def expanded_recipe(family,index):
    if family=="arithmetic":
        return {"family":family,"index":index,"a":2+index%64,"b":2+index//64%64,
                "op":("+","-","*")[index//4096%3]}
    if family=="boolean":
        forms=[
            ("A",node("not","B")),("C",node("not","D")),
            (node("not","A"),"B"),(node("not","C"),"D"),
            ("A","C"),("B","D"),("A",node("not","D")),("B",node("not","C")),
            (node("and","A","B"),node("or","C","D")),
            (node("or","A","B"),node("and","C","D")),
            (node("xor","A","B"),node("xor","C","D")),
            (node("eq","A","C"),node("eq","B","D")),
            (node("implies","A","B"),node("implies","C","D")),
            (node("not",node("and","A","B")),node("or","C","D")),
            (node("not",node("or","A","B")),node("xor","C","D")),
            (node("not",node("xor","A","C")),node("eq","B","D")),
            (node("and","A","C"),node("or","B","D")),
            (node("or","A","D"),node("xor","B","C")),
            (node("eq","A","D"),node("implies","B","C")),
            (node("not",node("eq","A","B")),node("and","C","D"))]
        outer=("and","or","xor","implies","eq")[index//320%5]
        return {"family":family,"index":index,"values":{v:bool(index>>i&1) for i,v in enumerate("ABCD")},
                "expression":node(outer,*copy.deepcopy(forms[index//16%20]))}
    return small.recipe(family,index)


def make_spec(data,language,split):
    spec=small.spec_for(data,language,split)
    spec.update(minimum=2,maximum=65)
    spec["source"]["sha256"]=small.hash_object([VERSION,small.root_definition(data),language])
    return spec


def draw_payload(spec,*,changed,rng):
    original=spec["payload"]; p=copy.deepcopy(original); kind=spec["kind"]
    if kind=="integer_arithmetic":
        a,b,op=p["a"],p["b"],p["op"]
        if changed:
            p["a"],p["b"]=rng.randint(2,65),rng.randint(2,65)
        elif op=="+":
            choices=[(v,a+b-v) for v in range(2,66) if 2<=a+b-v<=65]
            p["a"],p["b"]=rng.choice(choices)
        elif op=="-":
            choices=[(v,v-(a-b)) for v in range(2,66) if 2<=v-(a-b)<=65]
            p["a"],p["b"]=rng.choice(choices)
        else:
            choices=[(v,a*b//v) for v in range(2,66) if a*b%v==0 and 2<=a*b//v<=65]
            p["a"],p["b"]=rng.choice(choices)
    elif kind=="boolean_expression":
        p["values"]={name:bool(rng.randrange(2)) for name in sorted(p["values"])}
    elif kind=="table_lookup":
        rng.shuffle(p["entries"])
        p["target"]=next(name for name,value in p["entries"] if name!=original["target"]) if changed else original["target"]
    else: raise ValueError("closed changed/unchanged family required")
    return p


def candidates(spec,*,changed,key,seed,count=64):
    rng=random.Random(int(small.hash_object([VERSION,spec["root_id"],seed,changed]),16))
    base_answer=rules._render(spec,spec["payload"])[1]
    for i in range(count):
        if spec["kind"]=="verbatim_qa":
            row=rules.make_format_followup(spec,view_index=i,field_name=key)
            row["messages"][-2]["content"][0]["text"]=format_instruction(spec["language"],key,i)
            row["meta"]["format_prompt_variant"]=i%16
            yield row
        else:
            p=draw_payload(spec,changed=changed,rng=rng)
            answer=rules._render(spec,p)[1]
            if (answer!=base_answer)!=changed: continue
            yield small.closed_row(spec,p)


def format_instruction(language,key,index):
    """Real instruction paraphrases, with the same exact one-key/string target."""
    if key not in KEYS or language not in ("ko","en"):
        raise ValueError("known language/key required")
    if language=="en":
        verbs=("Return","Output","Write","Give")
        ends=("Preserve the answer exactly.","Keep the answer unchanged.",
              "Do not alter the answer.","Do not change the answer.")
        return (f"{verbs[index%4]} only a JSON object with exactly one key {key} and "
                f"the complete previous answer as its string value. {ends[index//4%4]}")
    verbs=("출력하세요","반환하세요","작성하세요","제시하세요")
    ends=("답변의 내용은 그대로 보존하세요.","답변을 변경하지 마세요.",
          "답변 내용을 바꾸지 마세요.","답변을 고치거나 요약하지 마세요.")
    return (f"이전 답변의 전체 문자열을 {key} 키 하나만 가진 JSON 객체의 값으로 "
            f"{verbs[index%4]}. {ends[index//4%4]}")


def matched_class(rows,signature):
    """Choose a deterministic viable length bucket; never pad or inspect quality."""
    buckets={}
    for row in rows:
        sig=signature(row)
        identity=(small.text_at(row,-2),small.text_at(row,-1))
        buckets.setdefault(sig,{}).setdefault(identity,row)
    viable=[(sig,list(values.values())) for sig,values in buckets.items() if len(values)>=2]
    if not viable:raise ValueError("not_enough_matched_distinct_views")
    sig,options=min(viable,key=lambda item:(-len(item[1]),item[0]))
    return options[0],options,sig


def build(signature,*,train_rows=4096,val_rows=64,seed=1337,attempts=64,
          excluded_roots=(),excluded_questions=(),deadline=None):
    if train_rows%16 or val_rows%16 or attempts<2:
        raise ValueError("even balanced family/language/condition counts required")
    excluded_roots=set(excluded_roots); excluded_questions=set(excluded_questions)
    fixed=[]; epochs=[[] for _ in range(4)]; probes=[]; seen=set(); rejected={}
    roots={"train":[],"val":[]}; counts={f:{"train":0,"val":0} for f in small.FAMILIES}
    policies={}; limits={"arithmetic":12288,"boolean":1600,"lookup":65536,"format":65536}
    def reject(reason): rejected[reason]=rejected.get(reason,0)+1
    for family in small.FAMILIES:
        needs={"train":train_rows//8,"val":val_rows//8}
        for index in range(limits[family]):
            if deadline is not None and time.monotonic()>=deadline:
                raise TimeoutError("balanced4096 corpus wall budget")
            data=expanded_recipe(family,index); root=small.hash_object(small.root_definition(data))
            split="val" if int(root[:8],16)%5==0 else "train"
            if root in excluded_roots or root in set(roots["train"]+roots["val"]):
                reject("excluded_or_duplicate_root"); continue
            current=counts[family][split]
            if current>=needs[split]: continue
            changed=bool(current%2) if family!="format" else None
            key=KEYS[current%len(KEYS)]
            children=[]
            try:
                for language in ("ko","en"):
                    spec=make_spec(data,language,split); first=small.base_pair(spec)[0]["content"]
                    if first in excluded_questions or first in seen: raise ValueError("excluded_or_repeated_first_question")
                    if split=="val":
                        # New closed probes are constructed directly; no val augmenter.
                        row=small.format_probe(spec,key) if family=="format" else None
                        if row is None:
                            rng=random.Random(seed+index*107+current)
                            for _ in range(attempts):
                                p=draw_payload(spec,changed=changed,rng=rng)
                                if (rules._render(spec,p)[1]!=rules._render(spec,spec["payload"])[1])==changed:
                                    row=small.closed_row(spec,p,probe=True); break
                        if row is None: raise ValueError("no_closed_probe")
                        signature(row); children.append((first,row)); continue
                    candidate_rows=[]
                    for row in candidates(spec,changed=changed,key=key,seed=seed,count=attempts):
                        if deadline is not None and time.monotonic()>=deadline:
                            raise TimeoutError("balanced4096 candidate wall budget")
                        if small.text_at(row,0)!=first: raise ValueError("first_question_drift")
                        candidate_rows.append(row)
                    baseline,options,sig=matched_class(candidate_rows,signature)
                    selected=[copy.deepcopy(options[e%len(options)]) for e in range(4)]
                    policy="FORMAT_VERBATIM" if family=="format" else ("ANSWER_CHANGED" if changed else "ANSWER_UNCHANGED")
                    for row in [baseline,*selected]:
                        row["meta"].update(root_family=family,root_concept_id=root,curriculum_policy=policy,
                            dataset_version=VERSION,source_split_before_augmentation=True)
                    children.append((first,baseline,selected,sig))
            except ValueError as error:
                reject(str(error)); continue
            for first,*_rest in children: seen.add(first)
            counts[family][split]+=1; roots[split].append(root)
            if split=="val":
                probes.extend(row for first,row in children)
            else:
                for first,baseline,selected,sig in children:
                    fixed.append(baseline)
                    policy=baseline["meta"]["curriculum_policy"]; policies[policy]=policies.get(policy,0)+1
                    for e,row in enumerate(selected): epochs[e].append(row)
            if all(counts[family][s]>=needs[s] for s in ("train","val")): break
    expected=[signature(r) for r in fixed]
    if any([signature(r) for r in rows]!=expected for rows in epochs): raise ValueError("slot x/target mismatch")
    if set(roots["train"])&set(roots["val"]) or (set(roots["train"]+roots["val"])&excluded_roots):
        raise ValueError("root split/exclusion leakage")
    ready=len(fixed)==train_rows and len(probes)==val_rows and all(len(e)==train_rows for e in epochs)
    return {"fixed":fixed,"epochs":epochs,"probes":probes,"report":{
        "schema":VERSION,"ready":ready,"train_rows":len(fixed),"val_rows":len(probes),
        "desired_train_rows":train_rows,"root_instances":{k:len(v) for k,v in roots.items()},
        "roots":roots,"seed":seed,"task_families":list(small.FAMILIES),"family_root_counts":counts,
        "curriculum_policy_rows":policies,"selection_rejected":rejected,"token_signature":expected,
        "epoch_x_tokens":sum(x for x,t in expected),"epoch_assistant_targets":sum(t for x,t in expected),
        "four_epoch_processed_tokens":4*sum(x for x,t in expected),"slot_token_target_match":True,
        "source_definition_sha256":small.hash_object(roots),"excluded_prior_val_roots":len(excluded_roots),
        "knowledge_claim":"four procedural families; instances are not new independent knowledge",
        "view_policy":"at least2 distinct matched views/root; fixed output key in C3; deterministic largest viable length bucket; no padding",
        "model_loading":"NOT_RUN","meaningful_training":"NOT_RUN"}}
