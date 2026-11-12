"""Select a literal span by unique retained anchors in the same unfinished file."""
from pathlib import Path
import hashlib
import importlib.util
import json

AUDIT=Path(__file__).resolve().parent
path=AUDIT/'literal_author_editor_v1.py'
assert hashlib.sha256(path.read_bytes()).hexdigest().upper()=='97667C54BD2E16C41DA274C8A424C93846C5ABE4D1D54A746E540B87248C9A41'
spec=importlib.util.spec_from_file_location('frozen_literal_author_editor1_for_v2',path)
previous=importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
literal_edit=previous.edit


def edit(raw,request):
    if 'spans' not in request:
        return literal_edit(raw,request)
    if set(request)!={'expected_sha256','spans'} or request['expected_sha256']!=previous.digest(raw):
        raise ValueError('current final SHA differs or extra request fields; no write')
    spans=request['spans']
    if not isinstance(spans,list) or not 1<=len(spans)<=32:
        raise ValueError('one to32 literal spans required')
    current=raw
    hunks=[]
    for span in spans:
        if set(span)!={'keep_before','keep_after','replacement'}:
            raise ValueError('only two retained literal anchors and replacement accepted')
        if not all(isinstance(value,str) for value in span.values()):
            raise ValueError('literal strings required')
        left,right,new=span['keep_before'],span['keep_after'],span['replacement']
        if not 8<=len(left)<=400 or not 8<=len(right)<=400:
            raise ValueError('retained literal anchors must contain8to400characters')
        text=current.decode('utf-8')
        if text.count(left)!=1 or text.count(right)!=1:
            raise ValueError('each retained anchor must match exactly once; no write')
        start=text.index(left);stop=text.index(right)
        if start+len(left)>=stop:
            raise ValueError('anchors must enclose a nonempty span in source order; no write')
        old=text[start:stop+len(right)]
        current,changes=literal_edit(current,dict(expected_sha256=previous.digest(current),
            edits=[dict(old=old,new=left+new+right)]))
        hunks.extend(dict(change,retained_anchor_selection=True) for change in changes)
    if len(json.dumps(hunks,ensure_ascii=False).encode())>24000:
        raise ValueError('combined exact hunk report too large; no write')
    return current,hunks


def cli(root,role,scope_pin):
    previous.edit=edit
    return previous.cli(root,role,scope_pin)
