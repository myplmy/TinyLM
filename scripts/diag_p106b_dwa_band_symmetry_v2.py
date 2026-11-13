"""Reuse immutable v1 math; explicitly prepare only the fresh output parent."""
from pathlib import Path
from types import FunctionType, SimpleNamespace

from scripts import diag_p106b_dwa_band_symmetry as original

BASE=original.ROOT/'test_result/evidence/p106b_dwa_band_symmetry_v2_20261113'


def write_new(path,obj):
    path=Path(path)
    if path.parent!=BASE:raise ValueError('only the owned fresh diagnostic output is writable')
    BASE.mkdir(exist_ok=True)
    return original.data.write_new(path,obj)


def main():
    private_data=SimpleNamespace(**vars(original.data))
    private_data.write_new=write_new
    private=dict(vars(original),BASE=BASE,data=private_data,
        SOURCES=original.SOURCES+('scripts/diag_p106b_dwa_band_symmetry_v2.py',))
    return FunctionType(original.main.__code__,private,original.main.__name__)()


if __name__=='__main__':main()
