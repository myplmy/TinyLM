"""Require real empty-footer removal as well as the frozen independent value proof."""
from pathlib import Path
import hashlib
import importlib.util
import argparse

HERE=Path(__file__).resolve().parent
path=HERE/'verify_event_metadata_literal_delta_v1.py'
# Filled by the caller's pinned census; this adapter also checks the frozen
# verifier hash before importing it. No production edit helper is introduced.
EXPECTED='DDB9D878E91AC0536DDFA4919A83874DE58396F3FE2B555EF994957777889DE1'


def load_previous():
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest().upper()!=EXPECTED:
        raise ValueError('independent event verifier1 changed')
    spec=importlib.util.spec_from_file_location('frozen_event_literal_v1_for_v2',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


previous=load_previous()
old_evaluate=previous.evaluate


def evaluate(original,candidate):
    value=old_evaluate(original,candidate)
    changed=(original!=candidate and value['source_empty_eof_appendix_headings']
             !=value['candidate_empty_eof_appendix_headings'])
    value['guards']['actual_empty_footer_removal']=bool(changed)
    value['eligible_narrow_literal_delta']=all(value['guards'].values())
    return value


def run(census_path,output_path):
    previous.evaluate=evaluate
    previous.__file__=str(Path(__file__))
    previous.run(census_path,output_path)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--census',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    paths=[Path(x).resolve() for x in [args.census,args.output]]
    assert all(p.parent==HERE and not p.is_symlink() for p in paths)
    assert not paths[1].exists()
    run(*paths)
