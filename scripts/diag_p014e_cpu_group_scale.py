"""Compare per-trit scaling and per-group scaling of new packed CPU inputs."""

import ctypes
import math
import os
import resource
import shutil
import subprocess
import time

import numpy as np

from scripts import diag_p013_native_matched_training as io


TAG = "p014e_cpu_group_scale_factored_v1_20261118"
OUT = io.ROOT / "test_result/evidence" / TAG
FILES = ("scripts/p014e_direct_cpu.c", "scripts/p014e_cpu_group_scale.c", "scripts/diag_p014e_cpu_group_scale.py")
CASES = (("row_body",1,2048,768), ("batch_body",8,768,2048),
    ("head_32k",1,32768,256), ("head_248k",1,248320,256))
ATOL, RTOL = 2e-6, 2e-5


def bind(library, name):
    fn = getattr(library,name)
    fn.argtypes = [ctypes.c_void_p]*4 + [ctypes.c_int64]*6
    fn.restype = ctypes.c_int
    return fn


def call(fn, x, codes, scales, y, group):
    m,k = x.shape
    n = y.shape[1]
    return fn(x.ctypes.data,codes.ctypes.data,scales.ctypes.data,y.ctypes.data,m,n,k,group,0,m*n)


def exact_dot(x, codes, scales, group, row):
    terms = []
    for index,packed in enumerate(codes[row]):
        for offset in range(group):
            trit = int(packed[offset//5]) // 3**(offset%5) % 3 - 1
            terms.append(float(x[index*group+offset]) * float(scales[row,index]) * trit)
    return np.float32(math.fsum(terms))


def compare_case(name, m, n, k, rng, paths):
    group = 128
    x = rng.standard_normal((m,k),dtype=np.float32)
    codes = rng.integers(0,243,(n,k//group,(group+4)//5),dtype=np.uint8)
    scales = rng.uniform(.001,.3,(n,k//group)).astype(np.float32)
    y = {label: np.empty((m,n),dtype=np.float32) for label in paths}
    for label,fn in paths.items():
        assert call(fn,x,codes,scales,y[label],group) == 0
    np.testing.assert_allclose(y["group"],y["reference"],atol=ATOL,rtol=RTOL)
    for sample,row in ((0,0),(m-1,n//3),(m-1,n-1)):
        exact = exact_dot(x[sample],codes,scales,group,row)
        assert all(a[sample,row] == exact for a in y.values())
    a,b = y["reference"],y["group"]
    maximum = float(np.abs(a.astype(np.float64)-b).max())
    byte_differences = int(np.count_nonzero(a.view("<u4") != b.view("<u4")))
    costs = {label: [] for label in paths}
    for label in ("reference","group","group","reference"):
        tick = time.perf_counter()
        for _ in range(3):
            assert call(paths[label],x,codes,scales,y[label],group) == 0
        costs[label].append((time.perf_counter()-tick)/3)
    result = dict(name=name,m=m,n=n,k=k,group=group,outputs=m*n,max_abs_difference=maximum,
        baseline_bit_differences=byte_differences,exact_fsum_checks=3,packed_bytes=codes.nbytes,
        scale_bytes=scales.nbytes,seconds_per_call_ABBA=costs,ratio=math.fsum(costs["reference"])/math.fsum(costs["group"]))
    print("P014E_GROUP_SCALE_CPU",name,result["ratio"],maximum,byte_differences,flush=True)
    return result


def edge_checks(paths):
    x = np.array([[1.,2.,3.,4.,5.,6.,7.]],dtype=np.float32)
    codes = np.array([[[242,242]]],dtype=np.uint8)
    scales = np.array([[.5]],dtype=np.float32)
    y = np.empty((1,1),dtype=np.float32)
    for fn in paths.values():
        assert call(fn,x,codes,scales,y,7)==0 and y[0,0]==14.
    codes[0,0,1] = 255
    assert all(call(fn,x,codes,scales,y,7)==4 for fn in paths.values())
    assert all(call(fn,x,codes,scales,y,6)==1 for fn in paths.values())


def main():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    affinity = max(os.sched_getaffinity(0))
    os.sched_setaffinity(0,{affinity})
    compiler = shutil.which("cc")
    assert compiler
    versions = subprocess.check_output([compiler,"--version"],text=True,timeout=10).splitlines()
    OUT.mkdir(exist_ok=False)
    so = OUT / "compare.so"
    pins = {name: io.digest(io.ROOT / name) for name in FILES}
    argv = [compiler,"-O3","-std=c11","-fPIC","-shared","-ffp-contract=off","-march=native",
        str(io.ROOT / FILES[1]),"-o",str(so)]
    subprocess.run(argv,check=True,timeout=30)
    library = ctypes.CDLL(str(so),mode=ctypes.RTLD_LOCAL)
    paths = {"reference":bind(library,"p014e_reference_linear"),"group":bind(library,"p014e_group_scale_linear")}
    edge_checks(paths)
    rng = np.random.default_rng(601731)
    results = [compare_case(*case,rng,paths) for case in CASES]
    assert pins == {name: io.digest(io.ROOT / name) for name in FILES}
    io.write(OUT / "report.json",dict(tag=TAG,sources=pins,compiler=versions[0],compile_args=argv,
        binary_sha256=io.digest(so),seed=601731,cpus=sorted(os.sched_getaffinity(0)),cases=results,
        edge_checks=["partial_packed_byte","invalid_code","invalid_dimensions"],
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,old_payload_reads=0,model_calls=0,gpu_calls=0))


if __name__ == "__main__":
    main()
