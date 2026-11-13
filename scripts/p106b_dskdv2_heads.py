"""Bounded native row gathering; never truncate a distribution to this overlap."""
import torch


def gather_rows(view,indices,*,rows,width,chunk=4096):
    if (not isinstance(indices,list) or not indices or any(type(i)is not int or not 0<=i<rows for i in indices)
            or len(set(indices))!=len(indices) or type(chunk)is not int or chunk<1
            or list(view.get_shape())!=[rows,width]):
        raise ValueError('unique ordered native row IDs and exact original head shape required')
    result=torch.empty((len(indices),width),dtype=torch.float32)
    ids=torch.tensor(indices,dtype=torch.long)
    for a in range(0,rows,chunk):
        positions=torch.nonzero((ids>=a)&(ids<min(rows,a+chunk)),as_tuple=False).flatten()
        if not len(positions):continue
        block=view[a:min(rows,a+chunk),:]
        if list(block.shape)!=[min(rows,a+chunk)-a,width] or not bool(torch.isfinite(block).all()):
            raise ValueError('complete finite original native rows required')
        result[positions]=block.index_select(0,ids[positions]-a).float()
    return result
