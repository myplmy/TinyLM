"""Read-only replay of the DEV-frozen afternoon candidate, never a new fit."""
from pathlib import Path
import hashlib
import json
import numpy as np
import torch
from scripts import diag_p108b_norm_sweep as study
from scripts import diag_p108b_policy as raw
from scripts import p108b_replay as replay
from scripts import interactive_research_infer as manual

ROOT, BASE, SOURCE = study.ROOT, study.BASE, study.SOURCE


def selection():
    study.sweep.Budget().check()
    chosen = study.read(BASE/'norm_selection_v1.json')
    if (chosen['final_or_official_answers_used'] or chosen['root_language_read_used_for_selection'] or
            chosen['source_profile_sha256'] != manual.file_sha(study.PROFILE)):
        raise ValueError('pre-evaluation DEV selection required')
    if manual.file_sha(ROOT/chosen['source']) != chosen['source_sha256']:
        raise ValueError('frozen selected arm source changed')
    return chosen


def arm(name):
    chosen = selection()
    if name == 'original':
        return replay.read_arm(name)
    if name != chosen['name']:
        raise ValueError('only original and one preselected global weight state')
    record = study.read(ROOT/chosen['source'])
    receipt, = record['receipt']
    packet = dict(record['packet'], layer=record['layer'],
        before_weight_sha256=receipt['before_sha256'], after_weight_sha256=receipt['after_sha256'])
    return dict(name=name, origin=study.read(study.PROFILE)['origin'], packets=[packet],
        core_sha256=record['edited_core_sha256'],
        answers=raw.read_answers((ROOT/chosen['source']).parent,record['answers_manifest']))


def packet_loader(reference):
    path = ROOT/reference['path']
    if path.is_symlink() or not path.resolve().is_relative_to(BASE.resolve()):
        raise ValueError('owned afternoon regular packet required')
    if not path.is_file() or path.stat().st_size >= 20_000_000 or manual.file_sha(path)!=reference['sha256']:
        raise ValueError('exact small frozen afternoon packet required')
    with np.load(path,allow_pickle=False) as stream:
        if set(stream.files) != {'requested','after'}:
            raise ValueError('complete requested/physical-after packet required')
        return {k:torch.from_numpy(stream[k].copy()) for k in stream.files}


def source_identity(names):
    files = {n:manual.file_sha(ROOT/n) for n in sorted(set(names))}
    digest = hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest().upper()
    return dict(files=files,sha256=digest)
