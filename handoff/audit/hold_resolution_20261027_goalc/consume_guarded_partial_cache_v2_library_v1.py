"""Enter the frozen independent consumer through its library API, without CLI rebinding."""
from pathlib import Path
import argparse
import json
import os
import sys

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
import guarded_reviewed_cache_v2 as guarded


def consume(base,roster,output,selection):
    # The historic CLI temporarily assigns previous.verify to guarded.verify;
    # its own verifier then calls that alias recursively. Never enter that CLI.
    if guarded.previous.verify is guarded.verify:
        raise ValueError('legacy CLI verify alias is active; independent library context required')
    return guarded.verify(base,roster,output,selection)


def main():
    os.environ.update(CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
                      MKL_NUM_THREADS='1',RAYON_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['verify'])
    parser.add_argument('--roster',type=Path,required=True)
    parser.add_argument('--selection',type=Path,required=True)
    parser.add_argument('--output-name',required=True)
    args=parser.parse_args()
    result=consume(guarded.inv.BASE,args.roster.resolve(),args.output_name,args.selection.resolve())
    print(json.dumps({key:value for key,value in result.items() if key in
                      {'status','summary','partial_resolution','restricted_metadata'}}),flush=True)


if __name__=='__main__':
    main()
