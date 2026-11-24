"""Shared physical norm and fixed diagnostic panels, independent of new answers."""
import numpy as np
from scripts import p108d_compare as physical_owner


def match_all(original,after,target):
    if set(original)!=set(after)or set(original)!=set(range(14)):
        raise ValueError("same complete14 physical owners required")
    before=np.concatenate([original[i]for i in range(14)],axis=0)
    candidate=np.concatenate([after[i]for i in range(14)],axis=0)
    result,actual,receipt=physical_owner.match_norm(before,
        candidate.astype(np.float64)-before.astype(np.float64),target)
    height=original[0].shape[0]
    if any(x.shape!=original[0].shape for x in original.values()):
        raise ValueError("same native down shapes required")
    return {i:result[i*height:(i+1)*height].copy()for i in range(14)},receipt


def question_only(row):
    allowed=("id","question","language","expected","protected","family","fact","split",
             "content_answer","scope_expected","full_sentence_requested","turn","conversation")
    return {key:row[key]for key in allowed if key in row}


def panels(fits,dev,guards,boundary,sentences):
    rows=[]
    for family,group in (("FIT",fits),("DEV",dev),("GUARD",guards)):
        rows.extend(dict(question_only(r),evaluation_panel=family,max_new=64)for r in group)
    rows.extend(dict(question_only(r),evaluation_panel="OPEN48",max_new=96)
                for r in boundary["singles"]if r["family"]=="open_sentence")
    rows.extend(dict(id="grammar:"+str(i),question=q,language="ko",expected=None,
                     evaluation_panel="NATURAL_KO8",max_new=96)for i,q in enumerate(sentences))
    rows.extend(dict(question_only(r),evaluation_panel="SENTENCE_EN4",max_new=96)
                for r in boundary["singles"]if r["family"]=="target"
                and r["language"]=="en"and r["expected"]is None)
    dialogs=[[dict(question_only(r),evaluation_panel="OWN_HISTORY12",max_new=96)for r in dialog]
             for dialog in boundary["dialogs"]]
    single_ids=[r["id"]for r in rows]
    all_ids=single_ids+[r["id"]for dialog in dialogs for r in dialog]
    if len(rows)!=187 or len(dialogs)!=4 or any(len(d)!=3 for d in dialogs)or len(set(all_ids))!=199:
        raise ValueError("fixed187 single and12 own-history calls with unique IDs required")
    if any(key in r for r in rows for key in ("actual_history","answer","generation")):
        raise ValueError("model answers must not enter frozen question panels")
    return rows,dialogs


def extend_history(history,row,answer):
    return [*history,dict(role="user",content=row["question"]),
            dict(role="assistant",content=answer)]
