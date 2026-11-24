"""Tokenize and decode the measured 248K G4 request in the native worker PID."""

import fcntl
import json
import os
from pathlib import Path
import struct
import sys
import sysconfig
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from scripts import p109_g270_text_exec as common


ASSIGNED, EOS = 248066, 248044
GEN = common.GEN


def codec(vocab_fd):
    if fcntl.fcntl(vocab_fd, common.F_GET_SEALS) != common.REQUIRED_SEALS:
        raise ValueError("Qwen tokenizer descriptor is not sealed")
    sys.path.append(sysconfig.get_path("purelib"))
    from scripts.p109_compact_qwen_tokenizer import CompactQwenTokenizer

    return CompactQwenTokenizer(f"/proc/self/fd/{vocab_fd}")


def encode(binary, model_fd, vocab_fd, tokens_fd, encoded_fd, native_fd):
    t0 = perf_counter()
    startup = common.snapshot()
    raw = sys.stdin.buffer.read(65537)
    if not 0 < len(raw) <= 65536:
        raise ValueError("Qwen UTF-8 request length exceeds the test contract")
    with codec(vocab_fd) as tokenizer:
        loaded = common.snapshot()
        ids = tokenizer.encode(raw.decode("utf-8")).ids
        if not 0 < len(ids) <= 1024-GEN+1 or any(not 0 <= i < ASSIGNED for i in ids):
            raise ValueError("Qwen request outside the assigned G4 token range")
        completed = common.snapshot()
    common.store(tokens_fd, struct.pack(f"<{len(ids)+2}I",len(ids),GEN,*ids))
    common.store(encoded_fd, json.dumps(dict(pid=os.getpid(),ids=ids,startup=startup,loaded=loaded,
        complete=completed,seconds=perf_counter()-t0)).encode("utf-8"))
    original = os.dup(1)
    os.set_inheritable(original,True)
    os.lseek(tokens_fd,0,os.SEEK_SET)
    os.dup2(tokens_fd,0)
    os.close(tokens_fd)
    os.dup2(native_fd,1)
    args=[binary,str(model_fd),str(original),sys.executable,str(Path(__file__).resolve()),
          *map(str,(vocab_fd,encoded_fd,native_fd))]
    os.execv(binary,args)


def decode(vocab_fd, encoded_fd, native_fd):
    t0=perf_counter()
    startup=common.snapshot()
    source,engine=common.read(encoded_fd),common.read(native_fd)
    assert source["pid"]==engine["pid"]==os.getpid()
    ids=engine["native"]["ids"]
    assert 1<=len(ids)<=GEN and all(0<=i<ASSIGNED for i in ids)
    with codec(vocab_fd) as tokenizer:
        loaded=common.snapshot()
        result=tokenizer.decode(ids,skip_special_tokens=True)
        completed=common.snapshot()
    print(json.dumps(dict(encoding=source,native=engine["native"],native_pid=engine["pid"],decoding=dict(
        pid=os.getpid(),startup=startup,loaded=loaded,complete=completed,seconds=perf_counter()-t0,text=result,
        finish="eos" if ids[-1]==EOS else "length")),ensure_ascii=False),flush=True)


if __name__=="__main__":
    if sys.argv[1]=="encode":
        encode(sys.argv[2],*map(int,sys.argv[3:]))
    elif sys.argv[1]=="decode":
        decode(*map(int,sys.argv[2:]))
    else:
        raise ValueError("unknown request phase")
