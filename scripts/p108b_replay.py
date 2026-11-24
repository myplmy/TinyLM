"""Exact ordered FP32 replay of the completed P108B physical edit packets."""
from contextlib import contextmanager,ExitStack
import json
from pathlib import Path
import re
import numpy as np
import torch
from scripts import diag_p108b_geometry as atlas
from scripts import diag_p108b_policy as policy_io
from scripts import interactive_research_infer as manual
from scripts import p108_weight_space as metrics


def read_arm(name):
    report=json.loads((atlas.BASE/'geometry/report.json').read_text(encoding='utf-8'))
    origin=report['origin']
    if name=='original':
        return dict(name=name,origin=origin,packets=[],core_sha256=origin['core_sha256'],
                    answers=policy_io.read_answers(atlas.BASE/'geometry',report['baseline']['answers_manifest']))
    if re.fullmatch(r'atlas_layer(?:0[0-9]|1[0-3])',name):
        layer=int(name[-2:]);source=report['layers'][layer]
        packet=dict(source['packet'],layer=layer,before_weight_sha256=source['geometry']['base_weight_sha256'],
                    after_weight_sha256=source['geometry']['after_weight_sha256'])
        return dict(name=name,origin=origin,packets=[packet],core_sha256=source['after_core_sha256'],
                    answers=policy_io.read_answers(atlas.BASE/f'geometry/layer{layer:02d}',source['answers_manifest']))
    if not re.fullmatch(r'[A-Z0-9_]+',name):raise ValueError('registered literal policy name required')
    directory=(atlas.BASE/'support_v2'/name) if name.startswith('SELECT_') else (
        atlas.BASE/'regularizer_v1'/name if name.startswith(('REGINC_','REGTOTAL_')) else policy_io.OUT/name)
    source=json.loads((directory/'report.json').read_text(encoding='utf-8'))
    if source['name']!=name:raise ValueError('policy report name mismatch')
    if name.startswith(('REGINC_','REGTOTAL_')):
        link=json.loads((directory/'method_profile_link.json').read_text(encoding='utf-8'))
        if (manual.file_sha(directory/'report.json')!=link['report_sha256'] or
                manual.file_sha(atlas.BASE/'regularizer_profile_v1.json')!=link['method_profile_sha256']):
            raise ValueError('additional regularizer method-profile binding changed')
    if source['status']=='REUSED_EXACT_ATLAS_ARM':
        parent=json.loads((atlas.ROOT/source['source_report']).read_text(encoding='utf-8'))
        if manual.file_sha(atlas.ROOT/source['source_report'])!=source['source_sha256']:raise ValueError('reused atlas report changed')
        reused=read_arm(f"atlas_layer{parent['layer']:02d}");reused['name']=name;return reused
    if source.get('original_restored')is not True:raise ValueError('closed original-restored policy report required')
    return dict(name=name,origin=origin,packets=source['packets'],core_sha256=source['actual_core_sha256'],
        answers=policy_io.read_answers(directory,source['answers_manifest']))


def load_packet(reference):
    path=atlas.ROOT/reference['path']
    if path.is_symlink()or not path.is_file()or not path.resolve().is_relative_to(atlas.BASE.resolve()):
        raise ValueError('regular owned P108B packet required')
    if path.stat().st_size>=20_000_000 or manual.file_sha(path)!=reference['sha256']:
        raise ValueError('small exact packet SHA required')
    with np.load(path,allow_pickle=False)as stream:
        values={k:torch.from_numpy(stream[k].copy())for k in stream.files if k in ('requested','after','mask')}
    return values


def validate_physical(reference,values,before):
    if set(values)not in ({'requested','after'},{'requested','after','mask'}):raise ValueError('complete physical packet required')
    delta,after=values['requested'],values['after'];before=before.detach().cpu()
    if (before.dtype!=torch.float32 or delta.dtype!=torch.float32 or after.dtype!=torch.float32 or
            before.shape!=delta.shape or after.shape!=before.shape or
            any(not bool(torch.isfinite(x).all())for x in (before,delta,after))):
        raise ValueError('same finite physical FP32 layout required')
    if metrics.tensor_sha(before)!=reference['before_weight_sha256']:raise ValueError('ordered predecessor weight SHA differs')
    if not torch.equal(before+delta,after)or metrics.tensor_sha(after)!=reference['after_weight_sha256']:
        raise ValueError('one FP32 addition does not reproduce the saved after matrix')
    if 'mask'in values:
        mask=values['mask']
        if mask.dtype!=torch.bool or mask.shape!=before.shape or bool(((after!=before)&~mask).any()):
            raise ValueError('physical sparse write escapes frozen support')
    return delta


@contextmanager
def install(adapter,arm,*,packets_loader=load_packet):
    original_core=manual.state_fingerprint(adapter.model)
    if original_core!=arm['origin']['core_sha256']:raise ValueError('exact original core required before replay')
    proof=dict(name=arm['name'],refit=False,optimizer_updates=0,packet_receipts=[])
    try:
        with ExitStack()as stack:
            for reference in arm['packets']:
                layer=reference['layer'];module=adapter.modules[layer]
                values=packets_loader(reference)
                delta=validate_physical(reference,values,module.weight)
                stack.enter_context(adapter.edit(layer,delta))
                if not torch.equal(module.weight.detach().cpu(),values['after']):raise RuntimeError('GPU replay differs from saved CPU matrix')
                proof['packet_receipts'].append(dict(layer=layer,before_sha256=reference['before_weight_sha256'],
                    after_sha256=reference['after_weight_sha256'],path=reference.get('path'),exact=True))
            proof['edited_core_sha256']=manual.state_fingerprint(adapter.model)
            if proof['edited_core_sha256']!=arm['core_sha256']:raise RuntimeError('ordered global edited core mismatch')
            yield proof
            if manual.state_fingerprint(adapter.model)!=arm['core_sha256']:raise RuntimeError('evaluation changed edited core')
    finally:
        proof['original_core_restored']=manual.state_fingerprint(adapter.model)==original_core
        if not proof['original_core_restored']:raise RuntimeError('ordered replay did not restore original core')
