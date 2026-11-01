"""New-directory-only, bounded-shard checkpoint storage with a final manifest."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import re
import time
import torch

SCHEMA='P107_COMPLETED_BOUNDARY_STORE_V1'
MAX_PART=16_000_000


def _regular_directory(path):
    path=Path(path)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('링크 경로의 checkpoint는 허용하지 않습니다')
    return path


def save_new(state,path,*,part_bytes=MAX_PART):
    if type(part_bytes) is not int or not 1024<=part_bytes<=MAX_PART:
        raise ValueError('각 shard 크기는1024..16000000B 범위여야 합니다')
    path=_regular_directory(path)
    path.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter()
    buffer=io.BytesIO();torch.save(state,buffer)
    view=buffer.getbuffer()
    whole=hashlib.sha256();parts=[]
    for i,start in enumerate(range(0,len(view),part_bytes)):
        data=view[start:start+part_bytes]
        name=f'part_{i:06d}.bin'
        with (path/name).open('xb') as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        whole.update(data)
        parts.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest().upper()))
    record=dict(schema=SCHEMA,serialization='torch.save/weights_only_load',parts=parts,
        bytes=len(view),sha256=whole.hexdigest().upper(),save_seconds=time.perf_counter()-started)
    with (path/'manifest.json').open('x',encoding='utf-8') as stream:
        stream.write(json.dumps(record,sort_keys=True,indent=2)+chr(10));stream.flush();os.fsync(stream.fileno())
    if os.name=='posix':
        descriptor=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(descriptor)
        finally:os.close(descriptor)
    return record


def load_complete(path):
    path=_regular_directory(path)
    manifest=path/'manifest.json'
    if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size>1_000_000:
        raise ValueError('완료 manifest가 없거나 비정상입니다')
    record=json.loads(manifest.read_text())
    parts=record.get('parts')
    if record.get('schema')!=SCHEMA or not isinstance(parts,list) or not parts:
        raise ValueError('checkpoint schema·shard 목록이 다릅니다')
    names=[f'part_{i:06d}.bin' for i in range(len(parts))]
    if any(not isinstance(x,dict) or x.get('path')!=name for x,name in zip(parts,names)):
        raise ValueError('checkpoint 조각의 순서·경로가 다릅니다')
    if {p.name for p in path.iterdir()}!=set(names)|{'manifest.json'}:
        raise ValueError('완료 목록 밖의 파일이 있습니다')
    buffer=io.BytesIO();whole=hashlib.sha256()
    for item in parts:
        file=path/item['path']
        if (file.is_symlink() or not file.is_file() or type(item.get('bytes')) is not int
                or not 0<item['bytes']<=MAX_PART or file.stat().st_size!=item['bytes']):
            raise ValueError('checkpoint 조각의 크기·형식이 다릅니다')
        data=file.read_bytes()
        if hashlib.sha256(data).hexdigest().upper()!=item.get('sha256'):
            raise ValueError('checkpoint 조각 SHA가 다릅니다')
        buffer.write(data);whole.update(data)
    if buffer.tell()!=record.get('bytes') or whole.hexdigest().upper()!=record.get('sha256'):
        raise ValueError('checkpoint 전체 크기·SHA가 다릅니다')
    buffer.seek(0)
    return torch.load(buffer,map_location='cpu',weights_only=True)
