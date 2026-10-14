"""New read-only-ancestor stream fork; old generation semantics stay unchanged."""
from __future__ import annotations
import argparse
from contextlib import contextmanager,ExitStack
import json
from pathlib import Path
import sys
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_gemma_mtp_resume as old
from scripts import diag_p106b_gemma_deficit_production as producer
from scripts import diag_p106b_gemma_telemetry_resume as telemetry
from scripts import diag_p106b_gemma_budget_resume as budget
from scripts.p106b_memory_stream import PersistentMemory,stream_session_scope
from scripts.p106b_mixed_scale import digest,safe_repo_path
from scripts.p106b_shards import verify
PARENT=ROOT/'HF/sft_ready/p106b_gemma_deficit_mtp_v4'
PARENT_SHA='585A54C7B3BBDD3D30FF9D9EC48E6BF7677C4C8B076BD8EAC45245166A81E2AE'
REPORTS=('F00A6BAE61F6D345EBE91904E184F31F27711E5FDDB7A0B40F01C792DDE5CF64',
         'E870A7D45AF180EEA8B2EF71F0A069DCF50927BC3BA3B167EF6E939B57EC214B')
VERSION='GEMMA_LITERAL_MTP_FRESH_STREAM_FORK_V2'
TAG='p106b_s4_gemma_capability300m_chat32_mtpstreamv5_s1337'
PATHS=dict(OUTPUT=ROOT/'HF/sft_ready/p106b_gemma_deficit_mtpstream_v5',
    CORPUS=ROOT/'HF/sft_ready/p106b_capability_gemma_mtpstream_v6',
    WIRE=ROOT/'HF/sft_ready/p106b_capability_gemma_mtpstream_wire_v6',
    STUDENT=ROOT/'HF/sft_ready/p106b_capability_gemma_mtpstream_student_v6',
    EVALUATION=ROOT/'HF/sft_ready/p106b_gemma_mtpstream_capability_multiaxis_v6')
CODE=('scripts/diag_p106b_gemma_stream_fork.py','scripts/test_p106b_gemma_stream_fork.py',
    'scripts/p106b_memory_stream.py','scripts/test_p106b_memory_stream.py')


def pinned_on_reports():
    if digest(safe_repo_path(PARENT/'inputs.json'))!=PARENT_SHA:raise ValueError('old ON inputs changed')
    directories=sorted(PARENT.glob('batch_*'))
    if [p.name for p in directories]!=['batch_000004','batch_000005']:
        raise ValueError('old ON ancestry changed; do not race concurrent production')
    reports=[]
    for directory,sha in zip(directories,REPORTS):
        p=safe_repo_path(directory/'report.json')
        if digest(p)!=sha:raise ValueError('old ON report changed')
        d=json.loads(p.read_text())
        for key in ('raw_manifest','candidate_manifest'):
            if key in d:verify(directory,d[key])
        reports.append((directory,d))
    return reports


def combined(ancestors,destination):
    yield from ancestors
    for index,p in enumerate(sorted(destination.glob('batch_*')),len(ancestors)):
        if p.name!=f'batch_{index:06d}':raise ValueError('fresh stream batch gap')
        rp=safe_repo_path(p/'report.json')
        if not rp.exists():raise FileExistsError('partial fresh batch; inspect explicitly')
        d=json.loads(rp.read_text())
        if d.get('input',{}).get('production_fork')!=VERSION:
            raise ValueError('other version in fresh namespace')
        yield p,d


@contextmanager
def fork_scope():
    # Validate original scopes without changing any source files or inputs.
    with old.on_scope():
        previous=producer.require_pilots()
        if json.loads((PARENT/'inputs.json').read_text())!=previous:raise ValueError('old source/code controls changed')
        ancestors=old.pinned_ancestors()+pinned_on_reports()
        info=dict(previous,production_fork=VERSION,stream_parent_input_sha256=PARENT_SHA,
            stream_parent_reports=list(REPORTS),stream_policy='PERSISTENT_FRESH_SEQUENCE_2S',
            generation_semantics='UNCHANGED_LITERAL_V3_BASELINE; visible support prototype NOT_ADOPTED',
            stream_code_sha256={p:digest(ROOT/p) for p in CODE})
        original_group=producer.produce_group;quota_type=producer.control.Quotas
        def group(*args,**kwargs):
            row=original_group(*args,**kwargs)
            if row is not None:row['meta'].update(production_fork=VERSION,memory_policy=info['stream_policy'])
            return row
        class Quotas(quota_type):
            def report(self):return dict(super().report(),teacher_production_fork=VERSION,
                teacher_profiles=['OFF_PINNED4','ON_PINNED2','ON_FRESH_STREAM_NEW'],
                stream_parent_input_sha256=PARENT_SHA,stream_parent_reports=list(REPORTS))
        with ExitStack() as stack:
            for module,name,value in ((producer,'require_pilots',lambda:info),
                (producer,'produce_group',group),(producer.control,'Quotas',Quotas),
                (producer.control,'batch_reports',lambda:combined(ancestors,PATHS['OUTPUT'])),
                (producer.control,'TAG',TAG)):
                stack.enter_context(patch.object(module,name,value))
            for name,path in PATHS.items():stack.enter_context(patch.object(producer.control,name,path))
            yield info


def dispatch(args,execute):
    with fork_scope() as info:
        producer.control.base_report()
        destination=PATHS['OUTPUT'];safe_repo_path(destination)
        if args.mode=='start' and destination.exists():raise FileExistsError('new fork exists; explicit resume only')
        if args.mode=='resume' and not destination.is_dir():raise FileNotFoundError('new fork absent; start first')
        if not execute:print('[CHECK_ONLY] '+json.dumps(info,ensure_ascii=False));return 0
        evidence=dict(expired=False)
        with PersistentMemory() as source:
            reader=telemetry.RetryingMemoryReader(source,emit=lambda line:print(line,flush=True))
            try:
                with stream_session_scope(reader),budget.production_budget_scope(evidence):
                    return producer.production(resume=args.mode=='resume',max_wall_sec=args.max_wall_sec)
            finally:print('[FRESH_STREAM_FORK] '+json.dumps(dict(telemetry=reader.snapshot(),
                fresh=source.snapshot(),budget=evidence,source_visibility='BASELINE_UNVERIFIED'),ensure_ascii=False),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('start','resume'),required=True)
    p.add_argument('--max-wall-sec',type=int,default=3600)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true')
    a=p.parse_args()
    if not 60<=a.max_wall_sec<=21600:p.error('bounded fresh production window required')
    try:return dispatch(a,a.execute)
    except (FileNotFoundError,FileExistsError) as exc:print('[HOLD] '+str(exc));return 8
    except KeyboardInterrupt:return 130
    except Exception as exc:print('[ERROR] '+type(exc).__name__+': '+str(exc));return 9

if __name__=='__main__':raise SystemExit(main())
