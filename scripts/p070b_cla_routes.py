"""Experimental, fixed CLA-atomic visit routes; product model stays unchanged."""
from collections import Counter,defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import random
from tinylm.model import TiedMLPTransformer
VERSION='P070B_CLA_ATOMIC_FIXED_ROUTE_V1'
MODES=('uniform','reverse','shuffle')


def middle_units(cfg,owners):
    if len(owners)!=cfg.n_layers:raise ValueError('one declared owner per logical layer')
    middle=set(range(cfg.n_prelude,cfg.n_prelude+cfg.n_middle));members=defaultdict(set)
    for layer,own in enumerate(owners):
        if not 0<=own<=layer:raise ValueError('causal owner must be an existing earlier layer')
        members[own].add(layer)
    units=[]
    for layer in sorted(middle):
        if units and owners[units[-1][0]]==owners[layer]:units[-1].append(layer)
        else:units.append([layer])
    movable=[i for i,u in enumerate(units) if set(u)==members[owners[u[0]]] and owners[u[0]] in u]
    if not movable:raise ValueError('no complete middle CLA group to permute')
    lo,hi=min(movable),max(movable)
    if movable!=list(range(lo,hi+1)):raise ValueError('only boundary-pinned partial CLA groups supported')
    return units[:lo],units[lo:hi+1],units[hi+1:]


def schedule(cfg,owners,mode='uniform',repeats=2,seed=1337):
    if mode not in MODES or type(repeats) is not int or not 1<=repeats<=4:raise ValueError('registered fixed route and integer1..4 required')
    before,units,after=middle_units(cfg,owners);units=[list(x) for x in units]
    if mode=='reverse':units.reverse()
    if mode=='shuffle':random.Random(seed).shuffle(units)
    body=[x for u in before+units+after for x in u]
    result=list(range(cfg.n_prelude))+body*repeats+list(range(cfg.n_prelude+cfg.n_middle,cfg.n_layers))
    trace(cfg,owners,result)
    return result


def repeat_draw(maximum,seed,update):
    if type(maximum) is not int or not 1<=maximum<=4 or type(update) is not int or update<0:raise ValueError('bounded deterministic draw only')
    material=json.dumps([VERSION,seed,update]).encode()
    return random.Random(int.from_bytes(hashlib.sha256(material).digest()[:8],'big')).randint(1,maximum)


def trace(cfg,owners,route):
    if cfg.n_prelude<1 or cfg.n_coda<1:raise ValueError('nonempty fixed edges required in this prototype')
    if not route or any(type(i) is not int or not 0<=i<cfg.n_layers for i in route):raise ValueError('all visits must be valid logical layers')
    p=cfg.n_prelude;end=p+cfg.n_middle;middle=set(range(p,end));counts=Counter(route)
    repeats=counts[p]
    if not 1<=repeats<=4 or any(counts[i]!=(repeats if i in middle else 1) for i in range(cfg.n_layers)):
        raise ValueError('same complete middle multiset; no layer omission or arbitrary overvisit')
    if route[:p]!=list(range(p)) or route[-cfg.n_coda:]!=list(range(end,cfg.n_layers)):raise ValueError('prelude/coda fixed')
    before,units,after=middle_units(cfg,owners)
    left=[i for u in before for i in u];right=[i for u in after for i in u]
    for cycle in range(repeats):
        part=route[p+cycle*cfg.n_middle:p+(cycle+1)*cfg.n_middle]
        if Counter(part)!=Counter(middle):raise ValueError('each cycle needs the same complete middle multiset')
        if (left and part[:len(left)]!=left) or (right and part[-len(right):]!=right):raise ValueError('boundary CLA fragments must remain pinned')
        for unit in units:
            pos=part.index(unit[0])
            if part[pos:pos+len(unit)]!=unit:raise ValueError('complete CLA group must remain atomic owner first')
    seen=Counter();layer_seen=Counter();written=set();events=[];repeating=len(route)!=cfg.n_layers
    for layer in route:
        own=owners[layer];occ=layer_seen[layer];layer_seen[layer]+=1
        if own==layer:
            pas=seen[own];seen[own]+=1
            key=(own,pas) if repeating else own
            if key in written:raise ValueError('KV owner visit key collision')
            written.add(key)
        else:
            if seen[own]==0:raise ValueError('consumer before KV owner; no fallback accepted')
            pas=seen[own]-1;key=(own,pas) if repeating else own
            # Full middle owner groups must consume the SAME numbered visit.
            members=[i for i,o in enumerate(owners) if o==own]
            if all(i in middle for i in members) and pas!=occ:raise ValueError('consumer used a previous-cycle owner visit')
        events.append(dict(layer=layer,owner=own,owner_pass=pas,key=key,layer_pass=occ))
    return dict(visits=len(route),middle_repeats=repeats,kv_entries=len(written),events=events)


def route_sha(cfg,owners,route):
    return hashlib.sha256(json.dumps(dict(schema=VERSION,owners=list(owners),route=list(route),
        prelude=cfg.n_prelude,middle=cfg.n_middle,coda=cfg.n_coda),sort_keys=True).encode()).hexdigest().upper()


@dataclass(frozen=True)
class RouteCache(Mapping):
    route_sha256:str
    bank:dict
    def __getitem__(self,key):return self.bank[key]
    def __iter__(self):return iter(self.bank)
    def __len__(self):return len(self.bank)


class FixedRouteTransformer(TiedMLPTransformer):
    """Research-only wrapper. No weights/parameters added and no learned router."""
    def __init__(self,cfg,mode='uniform',repeats=2,route_seed=1337):
        super().__init__(cfg)
        if cfg.repeat_mode!='uniform' or cfg.infer_repeat!=1. or cfg.train_repeat!=float(repeats):
            raise ValueError('explicit matching train_repeat and uniform base required; no inference override')
        if cfg.repeat_kv_reuse or cfg.reuse_attn_on_dup or cfg.repeat_embed_reinject or cfg.mtp_aux:
            raise ValueError('KV reuse, reinjection and MTP excluded from this contract')
        self.set_route(schedule(cfg,self.owner,mode,repeats,route_seed))

    def set_route(self,route):
        checked=trace(self.cfg,self.owner,route)
        if checked['middle_repeats']!=int(self.cfg.train_repeat):raise ValueError('actual repeat count differs from cfg')
        identity=route_sha(self.cfg,self.owner,route)
        self._fixed_route=tuple(route);self.route_sha256=identity;self.route_trace=checked

    def visit_schedule(self):
        return list(self._fixed_route) if hasattr(self,'_fixed_route') else super().visit_schedule()

    def forward(self,*args,past_kv=None,use_cache=False,**kwargs):
        if use_cache and (kwargs.get('return_aux') or kwargs.get('return_hidden')):
            raise ValueError('only ordinary logits cache API supported')
        if past_kv is not None:
            if not isinstance(past_kv,RouteCache) or past_kv.route_sha256!=self.route_sha256:
                raise ValueError('route changed during cached decoding or unbound cache supplied')
            past_kv=past_kv.bank
        result=super().forward(*args,past_kv=past_kv,use_cache=use_cache,**kwargs)
        if use_cache:
            logits,bank=result
            return logits,RouteCache(self.route_sha256,bank)
        return result
