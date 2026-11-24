"""Test value transfer under a new paired-row order from the same warm state."""

import argparse
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import time

import numpy as np
import torch

from scripts import run_p109c_bilingual_value_transfer as previous


TAG = "p109c_bilingual_shuffled_pairs_gpu_v1_20261121"
OUT = previous.OUT.with_name(TAG)
SEED = 2026112107
SNAPSHOT = previous.OUT/"shared_wide_start.pt"
trial,data,baseline,bridge = previous.trial,previous.data,previous.baseline,previous.bridge


def prepare():
    path=previous.OUT/"report.json"
    done=previous.OUT/"supervisor.json"
    prior,terminal=trial.read_json(path),trial.read_json(done)
    original=previous.prepare()
    if (prior["plan"]!=original or terminal["returncode"] or terminal["stop_reason"]
            or trial.file_sha(SNAPSHOT)!=prior["warm_checkpoint"]):
        raise ValueError("requires completed paired comparison and identical warm snapshot")
    size=original["supervised"][-1]
    order=np.random.default_rng(SEED).permutation(size//2)
    if not np.array_equal(np.sort(order),np.arange(size//2)):
        raise ValueError("the new order must contain each bilingual pair exactly once")
    plan=dict(tag=TAG,source=trial.file_sha(Path(__file__)),paired_source=trial.file_sha(path),
              paired_terminal=trial.file_sha(done),warm=prior["warm_checkpoint"],warm_proof=prior["warm_state"],
              original=original,seed=SEED,pair_order_sha256=data.authored.digest(order.tolist()),pairs=len(order))
    return plan,order


def worker(plan,fraction):
    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction(fraction)
    checked,order=prepare()
    if checked!=plan:
        raise ValueError("the sealed shuffle order or warm state changed")
    rows=np.stack((2*order,2*order+1),axis=1).reshape(-1)
    with np.load(previous.PAYLOAD,allow_pickle=False) as datafile:
        tensors=previous.gpu_arrays([datafile[k][rows] for k in ("tokens","labels","context","sites")])
        options=torch.as_tensor(datafile["options"][order],device="cuda",dtype=torch.long)
        unique=torch.as_tensor(datafile["unique"][order],device="cuda")
    panel,(tok,special,_,translated)=previous.crossed.prepare()
    if panel!=plan["original"]["cross"]:
        raise ValueError("the cross-language holdout changed")
    validation=trial.read_json(baseline.INPUT/"validation.json")
    ordinary=trial.read_json(data.DATA/"evaluation.json")
    model=baseline.TiedMLPTransformer(trial.make_config()).to("cuda")
    selector=baseline.ValueLink(model.cfg.dim).to("cuda")
    optimizer=torch.optim.AdamW([*model.parameters(),*selector.parameters()],lr=.0015,weight_decay=.01,fused=True)
    shared=torch.load(SNAPSHOT,weights_only=True,map_location="cpu")
    warm_steps=plan["original"]["warm_updates"]
    started=time.perf_counter()
    results={}
    for arm in previous.ARMS:
        model.load_state_dict(shared["model"])
        selector.load_state_dict(shared["selector"])
        optimizer.load_state_dict(torch.load(SNAPSHOT,weights_only=True,map_location="cpu")["optimizer"])
        torch.set_rng_state(shared["cpu_rng"])
        torch.cuda.set_rng_state(shared["cuda_rng"])
        model.train()
        selector.train()
        model.clear_quant()
        warm=json.dumps(previous.fingerprint(model,selector,optimizer),sort_keys=True)
        if warm!=json.dumps(plan["warm_proof"],sort_keys=True):
            raise ValueError("the shuffled arm restored a different warm state")
        meta=(options,unique) if arm=="transfer" else None
        wide=previous.train_phase(model,selector,optimizer,tensors,plan["original"]["supervised"],
                                  arm,warm_steps,started,meta)
        if wide["step"]!=data.UPDATES or (meta is not None and not wide["transfer_pairs"]):
            raise ValueError("the shuffled arm did not complete the intended condition")
        folder=OUT/arm
        folder.mkdir()
        assessment=previous.evaluate(model,selector,tok,special,validation,ordinary,translated,folder)
        final=folder/"foundation.pt"
        with final.open("xb") as file:
            torch.save(dict(tag=TAG,arm=arm,step=wide["step"],parent=None,config=asdict(model.cfg),
                            model={k:v.detach().cpu() for k,v in model.state_dict().items()},
                            train_head={k:v.detach().cpu() for k,v in selector.state_dict().items()}),file)
        results[arm]=dict(wide=wide,assessment=assessment,checkpoint=trial.file_sha(final),
                          state=trial.state_sha(model.state_dict()))
        trial.publish(folder/"report.json",results[arm])
        print(json.dumps(dict(arm=arm,assessment=assessment),ensure_ascii=False),flush=True)
    trial.publish(OUT/"report.json",dict(plan=plan,results=results,updates=len(previous.ARMS)*(data.UPDATES-warm_steps),
                                        elapsed=time.perf_counter()-started,
                                        peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("check","run"))
    parser.add_argument("--receipt",type=Path)
    parser.add_argument("--stop-by",type=datetime.fromisoformat)
    args=parser.parse_args()
    plan,_=prepare()
    if args.mode=="check":
        print(json.dumps(plan,indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt)!=plan:
        parser.error("requires a sealed shuffle order and an approved cutoff")
    return baseline.owner.supervise(worker,(plan,),OUT,args.stop_by,
                                    authorization_end=bridge.AUTHORIZATION_END,min_seconds=1020)


if __name__=="__main__":
    raise SystemExit(main())
