"""Check the native KV cache at the two-head geometry of the small G4."""

from hashlib import sha256
import json
from pathlib import Path
import struct
import subprocess
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np

from scripts import diag_p077_lowbit_native as native
from scripts import p077_g4_blocked_runtime as port


def main():
    engine = native.SCRIPTS / "p109_g4_compact_cpu.cpp"
    driver = native.SCRIPTS / native.TEST
    rendered = port.replace_once(engine.read_bytes(),
        b"constexpr int D = 768, E = 256, F = 2048, V = 32768;",
        b"constexpr int D = 256, E = 128, F = 768, V = 32768;")
    rendered = port.replace_once(rendered,
        b"constexpr int Heads = 12, Head = 64, Kv = 3 * Head;",
        b"constexpr int Heads = 4, Head = 64, Kv = 2 * Head;")
    rng = np.random.default_rng(280419)
    key, value = (rng.normal(size=(2048,2,64)).astype(np.float16) for _ in range(2))
    key[:32,0,0] = np.float16(0.125)
    value[1919,-1].fill(np.float16(-.5))
    results = []
    synthetic = native.synthetic
    with TemporaryDirectory(prefix="p077_small_kv_",dir="/tmp") as name, patch.object(synthetic.previous,"KV_HEADS",2):
        directory = Path(name)
        (directory/engine.name).write_bytes(rendered)
        for length,arms in ((1024,[(0,8,8)]),(2048,[(0,8,8),(1920,4,2)])):
            source = driver.read_bytes()
            if length==1024:
                source = port.replace_once(source,b"constexpr int Capacity = 2048;",b"constexpr int Capacity = 1024;")
                source = port.replace_once(source,b"{31, 32, 1009, 1024, 1887, 1901, 1919, 1920, 1921, 2017, Capacity}",
                                           b"{31, 32, 1009, Capacity}")
            build_source = directory/f"verify_{length}.cpp"
            build_source.write_bytes(source)
            binary = directory/f"verify_{length}"
            native.compile_probe(build_source,binary)
            payload = key[:length].astype("<f4").tobytes()+value[:length].astype("<f4").tobytes()
            for old,kbits,vbits in arms:
                output = subprocess.check_output([binary,str(kbits),str(vbits),str(old)],input=payload,timeout=40)
                size = struct.unpack_from("<Q",output)[0]
                restored = np.frombuffer(output[8:],dtype="<f4").reshape(2,2,length,2,64)
                refs = [synthetic.mixed(sign*key[:length],sign*value[:length],old,kbits,vbits,False,vbits==2)
                        for sign in (1,-1)]
                if any(size != ref[2] for ref in refs) or not np.array_equal(restored,np.array([x[:2] for x in refs])):
                    raise ValueError("two-head native cache differs from reference bytes or values")
                results.append(dict(context=length,older_rows=old,key=kbits,value=vbits,cache_bytes=size,
                                    restored_values=restored.size,output_sha256=sha256(output).hexdigest()))
    pins = native.seal((Path(__file__),engine,driver,native.SCRIPTS/native.HEADER))
    print(json.dumps(dict(results=results,source_sha256=pins),indent=2))


if __name__=="__main__":
    main()
