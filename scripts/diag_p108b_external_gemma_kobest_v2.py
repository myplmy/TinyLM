"""Entry-order recovery; preserve v1 and reuse its evaluation implementation."""
import argparse
from scripts import diag_p108b_external_gemma_kobest as parent
from scripts import p108b_decode as reuse
from scripts.prepare_p106b_official_eval import configure_hf_cache

PROFILE=parent.BASE/'external_gemma_kobest_profile_v2.json'
INITIAL=parent.BASE/'external_gemma_kobest_initial_plan_v2.md'
OUT=parent.BASE/'external_gemma_kobest_v2'
CODE=parent.CODE+('scripts/diag_p108b_external_gemma_kobest_v2.py',
                  'scripts/p108b_decode.py','scripts/prepare_p106b_official_eval.py')

prepare=reuse.private_function(parent.prepare,PROFILE=PROFILE,INITIAL=INITIAL,CODE=CODE)
verify=reuse.private_function(parent.verify,PROFILE=PROFILE,INITIAL=INITIAL)
_actual=reuse.private_function(parent.actual,PROFILE=PROFILE,OUT=OUT,verify=verify)


def entry_check():
    receipt=configure_hf_cache()
    from lm_eval.evaluator import simple_evaluate
    assert callable(simple_evaluate)
    verify()
    print('[GEMMA_KOBEST_ENTRY_CPU] cache configured before HF;official imports then same-process verify;model0')
    return receipt


def actual():
    configure_hf_cache()
    return _actual()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('prepare','check','entry-check','actual'))
    args=parser.parse_args()
    if args.phase=='prepare':prepare()
    elif args.phase=='check':verify();print('GEMMA_KOBEST_V2_PREFLIGHT_MODEL0')
    elif args.phase=='entry-check':entry_check()
    else:actual()


if __name__=='__main__':main()
