"""Read-only disjoint native train windows; no cache copies or model imports."""
from pathlib import Path
WIDTH=1024
NATIVE_TRAIN='data_cache/ko-en_601000000_chat32/train.bin'


class IndexedNativeWindows:
    def __init__(self,tokens,offsets):
        self.tokens=tokens;self.offsets=list(offsets)
        ordered=sorted(self.offsets)
        if (not ordered or any(type(i) is not int or i<0 or i+WIDTH+1>len(tokens) for i in ordered)
                or any(b-a<WIDTH+1 for a,b in zip(ordered,ordered[1:]))):
            raise ValueError('native windows must be in-bounds and disjoint including next targets')
    def __len__(self):return len(self.offsets)
    def __getitem__(self,key):
        if isinstance(key,slice):return [self[i] for i in range(*key.indices(len(self)))]
        offset=self.offsets[key]
        return self.tokens[offset:offset+WIDTH+1]


def reader(root,contract):
    import numpy as np
    if contract.get('native_access')=='INDEXED_TRAIN_ONLY':
        if contract['native_train_file']!=NATIVE_TRAIN:raise ValueError('only declared nonprotected native train cache allowed')
        tokens=np.memmap(root/NATIVE_TRAIN,dtype=np.uint16,mode='r')
        return IndexedNativeWindows(tokens,contract['native_train_offsets'])
    return np.memmap(root/contract['native_copy'],dtype=np.uint16,mode='r').reshape(-1,WIDTH+1)
