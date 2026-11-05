"""Reuse exact guards and diff reconstruction; transport byte-bounded pair views."""
from pathlib import Path
import hashlib
import importlib.util
import json

BASE = Path(__file__).with_name('lossless_review_packet_v1.py')
BASE_SHA = '9AF5084792D1D2DCE37DF6CD771B0527154DA7FF2919B4023AA261BD1C78C28E'
if BASE.is_symlink() or hashlib.sha256(BASE.read_bytes()).hexdigest().upper() != BASE_SHA:
    raise ValueError('frozen lossless core1 changed')
spec = importlib.util.spec_from_file_location('frozen_lossless_v1_for_v2', BASE)
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
resolve_assignment, load_pair = base.resolve_assignment, base.load_pair
require = base.require
PROTOCOL = 'FULL_ORIGINAL_AND_LOSSLESS_CANDIDATE_V2'
VIEW_BYTES = 4000


def prepare_views(original_raw, candidate_raw):
    views = base.prepare_views(original_raw, candidate_raw)
    source = views['original']; candidate = candidate_raw.decode('utf-8')
    changes = views['changes']
    index = [dict(number=n, op=row['op'], source_range=row['source_range'],
        candidate_range=row['candidate_range']) for n,row in enumerate(changes,1)]
    header = 'ALL_CHANGE_RANGES '+json.dumps(index,ensure_ascii=False,separators=(',',':'))+'\n'
    if not changes:
        mode, representation = 'EXACT_IDENTICAL', header+'CANDIDATE_EQUALS_FULL_ORIGINAL\n'
    else:
        pieces = [header]
        for n,row in enumerate(changes,1):
            lo,hi = row['source_range']
            for kind,text in [('OLD',source[lo:hi]),('NEW',row['after'])]:
                pieces.extend([f'CHANGE_{n}_{kind}_TEXT_BEGIN chars={len(text)}\n', text,
                               f'\nCHANGE_{n}_{kind}_TEXT_END\n'])
        patch = ''.join(pieces)
        full = header+'FULL_CANDIDATE_BEGIN\n'+candidate+'\nFULL_CANDIDATE_END\n'
        if len(patch.encode('utf-8')) < len(full.encode('utf-8')):
            mode, representation = 'EXACT_PATCH_WITH_OLD_AND_NEW', patch
        else:
            mode, representation = 'INDEX_AND_FULL_CANDIDATE', full
    prefix = 'FULL_ORIGINAL_BEGIN\n'
    separator = '\nFULL_ORIGINAL_END\nLOSSLESS_CANDIDATE_BEGIN\n'
    suffix = 'LOSSLESS_CANDIDATE_END\n'
    pair = prefix+source+separator+representation+suffix
    lo = len(prefix); end = lo+len(source); rep_start = end+len(separator)
    views.update(protocol=PROTOCOL,candidate=representation,candidate_representation=mode,
        full_candidate=candidate,pair=pair,
        pair_original_characters=[lo,end],
        pair_representation_characters=[rep_start,rep_start+len(representation)])
    return views


def view_part(views, view, part, width=VIEW_BYTES):
    require(view in {'original','candidate','full_candidate','pair'}, 'unknown logical view')
    require(type(part) is int and part>=1 and type(width) is int and 4<=width<=VIEW_BYTES,
        'invalid byte-bounded part')
    raw = views[view].encode('utf-8')
    boundaries = [0]
    while boundaries[-1] < len(raw):
        end = min(boundaries[-1]+width,len(raw))
        while end < len(raw) and raw[end]&0xC0 == 0x80: end-=1
        require(end>boundaries[-1], 'UTF8 character exceeds part capacity')
        boundaries.append(end)
    if not raw: boundaries.append(0)
    parts=len(boundaries)-1
    require(part<=parts,'part outside logical view')
    lo,hi=boundaries[part-1:part+1]
    return dict(view=view,part=part,parts=parts,range=[lo,hi],range_unit='UTF8_BYTES',
        text=raw[lo:hi].decode('utf-8'),end_of_view=part==parts,
        next_part=None if part==parts else part+1)
