"""Keep tokenization, native G270 inference, and decoding in one PID."""

import fcntl
import json
import os
from pathlib import Path
import struct
import sys
import sysconfig
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
GEN = 8
VOCAB = 262144
# Linux ABI used by the existing packed-request runner, including Python 3.10.
F_ADD_SEALS, F_GET_SEALS, REQUIRED_SEALS = 1033, 1034, 15


def snapshot():
    with open("/proc/self/status", encoding="ascii") as stream:
        high_water = next(int(line.split()[1])*1024 for line in stream if line.startswith("VmHWM:"))
    with open("/proc/self/smaps_rollup", encoding="ascii") as stream:
        rss = next(int(line.split()[1])*1024 for line in stream if line.startswith("Rss:"))
    return dict(vm_hwm_bytes=high_water, rss_bytes=rss)


def codec(asset, spelling, table):
    sys.path.append(str(ROOT))
    sys.path.append(sysconfig.get_path("purelib"))
    from scripts.diag_p109_csr_gemma_tokenizer import CsrGemma

    fds = (asset, spelling, table)
    if not all(fcntl.fcntl(fd, F_GET_SEALS) == REQUIRED_SEALS for fd in fds):
        raise ValueError("tokenizer descriptors are not sealed")
    return CsrGemma(*(f"/proc/self/fd/{fd}" for fd in fds))


def store(fd, data):
    with os.fdopen(os.dup(fd), "wb") as stream:
        stream.write(data)


def read(fd):
    with os.fdopen(os.dup(fd), "rb") as stream:
        stream.seek(0)
        return json.load(stream)


def encode(binary, model, asset, spelling, table, token_fd, encoding_fd, native_fd):
    started = perf_counter()
    initial = snapshot()
    raw = sys.stdin.buffer.read(65537)
    if not 0 < len(raw) <= 65536:
        raise ValueError("G270 UTF-8 request length exceeds the experiment contract")
    with codec(asset, spelling, table) as tok:
        loaded = snapshot()
        ids = tok.encode(raw.decode("utf-8")).ids
        if not ids or len(ids) > 1024 - GEN + 1:
            raise ValueError("G270 request has an unsupported token count")
        if any(token < 0 or token >= VOCAB for token in ids):
            raise ValueError("token outside the G270 model vocabulary")
        complete = snapshot()
    store(token_fd, struct.pack(f"<{len(ids)+2}I", len(ids), GEN, *ids))
    encoding = dict(pid=os.getpid(), input_bytes=len(raw), ids=ids, startup=initial, loaded=loaded,
                    complete=complete, seconds=perf_counter()-started)
    store(encoding_fd, json.dumps(encoding).encode("utf-8"))
    original_stdout = os.dup(1)
    os.set_inheritable(original_stdout, True)
    os.lseek(token_fd, 0, os.SEEK_SET)
    os.dup2(token_fd, 0)
    os.close(token_fd)
    os.dup2(native_fd, 1)
    args = [binary, str(model), str(original_stdout), sys.executable, str(Path(__file__).resolve()),
            *map(str, (asset, spelling, table, encoding_fd, native_fd))]
    os.execv(binary, args)


def decode(asset, spelling, table, encoding_fd, native_fd):
    started = perf_counter()
    initial = snapshot()
    enc, native = read(encoding_fd), read(native_fd)
    if enc["pid"] != os.getpid() or native["pid"] != os.getpid():
        raise ValueError("G270 text stages must share a PID")
    ids = native["native"]["ids"]
    if not 1 <= len(ids) <= GEN or any(token < 0 or token >= VOCAB for token in ids):
        raise ValueError("G270 engine returned invalid tokens")
    with codec(asset, spelling, table) as tok:
        loaded = snapshot()
        value = tok.decode(ids, skip_special_tokens=True)
        complete = snapshot()
    result = dict(encoding=enc, native=native["native"], native_pid=native["pid"], decoding=dict(
        pid=os.getpid(), startup=initial, loaded=loaded, complete=complete, text=value,
        seconds=perf_counter()-started, finish="eos" if ids[-1] == 1 else "length"))
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "encode":
        encode(sys.argv[2], *map(int, sys.argv[3:]))
    elif sys.argv[1] == "decode":
        decode(*map(int, sys.argv[2:]))
    else:
        raise ValueError("unsupported request phase")
