"""One original attrs check on explicit owned Python inputs, with read denial.

This does not replace the shared suite, its registry, or the smoke contract.
Only the in-memory TARGETS argument changes. No global PASS is reported.
"""
from pathlib import Path
from contextlib import redirect_stdout
import hashlib
import json
import os
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
import check_attrs as original


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main():
    scope=ROOT/'handoff/audit/nov01_afternoon/SCOPE_v2.json'
    names=json.loads(scope.read_text())['paths']
    names+=['tinylm/train/causal_teacher.py','scripts/test_p107_causal_teacher.py',
        'scripts/test_p107_causal_integration.py','scripts/diag_p107_causal_kd_cost.py',
        'scripts/test_p107_causal_kd_driver.py']
    selected=sorted({ROOT/p for p in names if p.endswith('.py')
        and p.startswith(('scripts/','tinylm/'))})
    assert selected and all(p.is_file() and not p.is_symlink() for p in selected)
    allowed=set(selected)|{ROOT/'tinylm/config.py'}
    source_sha=sha(Path(original.__file__))
    opened=[];denied=[]

    def guard(event,args):
        if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
        path=Path(os.fsdecode(args[0])).resolve()
        mode,flags=args[1:3]
        reading=(not isinstance(mode,str) or 'r' in mode or '+' in mode)
        if flags is not None and flags&os.O_WRONLY and not flags&os.O_RDWR:reading=False
        # Directory handles used by tempfile cleanup are metadata, not file text.
        if not reading or not path.is_relative_to(ROOT) or path.is_dir():return
        if path not in allowed:
            denied.append(str(path.relative_to(ROOT)))
            raise PermissionError('workspace read outside explicit attrs inventory')
        opened.append(str(path.relative_to(ROOT)))

    with tempfile.TemporaryDirectory(prefix='attrs_owned_',dir=ROOT/'tmp') as temp:
        temp=Path(temp)
        foreign=temp/'foreign_canary.py';foreign.write_text('raise RuntimeError("must not be read")')
        defect=temp/'owned_defect.py';defect.write_text('def bad(cfg): return cfg.p107_no_such_field')
        log=ROOT/'handoff/audit/nov01_afternoon/SCOPED_ATTRS_v2.log'
        # Open the output before the audit hook. The hook only limits reads.
        with log.open('x',encoding='utf-8') as stream,redirect_stdout(stream):
            sys.addaudithook(guard)
            refused=False
            try:foreign.read_text()
            except PermissionError:refused=True
            assert refused
            allowed.add(defect);original.TARGETS=[defect]
            defect_result=original.main()
            assert defect_result==1
            allowed.remove(defect)
            original.TARGETS=selected
            result=original.main()
            # sha() also uses the active read-set; include only this original source.
            allowed.add(Path(original.__file__))
            assert sha(Path(original.__file__))==source_sha
        allowed.add(scope)
        receipt=dict(schema='P107_OWNED_ATTRS_READBACK_V1',original_criteria_unchanged=True,
            original_source_sha256=source_sha,original_target_inventory_replaced_in_memory=True,
            actual_exit=result,selected_inputs=[str(p.relative_to(ROOT)) for p in selected],
            actual_workspace_reads=sorted(set(opened)),foreign_canary_read_refused=refused,
            deliberate_invalid_cfg_errors=defect_result,expected_denied_reads=denied,
            whole_static_suite_run=False,whole_repository_coverage=False,gpu_model_runs=0)
        output=ROOT/'handoff/audit/nov01_afternoon/SCOPED_ATTRS_v2.json'
        with output.open('x',encoding='utf-8') as stream:json.dump(receipt,stream,indent=2)
        print(json.dumps(dict(actual_exit=result,inputs=len(selected),invalid_cfg_errors=defect_result,
            foreign_canary_read_refused=refused,whole_static_suite_run=False)))
        return result


if __name__=='__main__':raise SystemExit(main())
