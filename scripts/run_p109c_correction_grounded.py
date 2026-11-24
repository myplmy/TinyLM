"""Compare teaching views after the locally trained model can retrieve table values."""

import argparse
from datetime import datetime
import json
from collections import Counter
from pathlib import Path
import sys
import time

import torch
import torch.nn.functional as F

from scripts import p109_cuda_owner as owner
from scripts import run_p109c_correction_scratch as trial
from scripts import run_p109c_table_grounding as data
from scripts import run_p109c_table_value_link as foundation
from tinylm.config import TMTConfig
from tinylm.model import TiedMLPTransformer
from tinylm.train.mtp_sft import IGNORE, pad_records


TAG = "p109c_correction_grounded_scratch_gpu_v1_20261121"
OUT = trial.DATA.parent / TAG
LR = 0.0002


def prepare():
    report = trial.read_json(foundation.OUT/"report.json")
    terminal = trial.read_json(foundation.OUT/"supervisor.json")
    if report["tag"]!=foundation.TAG or report["parent"] is not None or terminal["returncode"]!=0 or terminal["stop_reason"]:
        raise ValueError("requires the previously completed unparented table foundation")
    val = trial.read_json(foundation.OUT/"original_eval.json")
    total = Counter(row["language"] for row in val["rows"])
    qualified = Counter(row["language"] for row in val["rows"] if row["output"]["answer"]==row["gold"] and row["output"]["eot"])
    if (total != {"ko":32,"en":32} or sum(qualified.values()) != report["original"]
            or sum(qualified.values())<data.GATE["original_single"]
            or min(qualified[language] for language in total)<data.GATE["language_pairs"]):
        raise ValueError("requires a usable holdout single-question baseline in both languages")
    checkpoint = foundation.OUT/"foundation.pt"
    if trial.file_sha(checkpoint)!=report["checkpoint_sha256"]:
        raise ValueError("the selected foundation bytes differ")
    _, _, _, _, profiles = trial.load_cases()
    files = (Path(__file__),Path(foundation.__file__),Path(owner.__file__),foundation.OUT/"report.json",
             foundation.OUT/"wide_eval.json",foundation.OUT/"original_eval.json",foundation.OUT/"supervisor.json")
    pins = trial.source_pins()
    pins.update({str(p.relative_to(trial.ROOT)):trial.file_sha(p) for p in files})
    return dict(tag=TAG,profile=profiles,checkpoint_sha256=report["checkpoint_sha256"],
                state_sha256=report["state_sha256"],lr=LR,sources=pins,
                original_validation=dict(qualified),general_retrieval_gate=report["gate"])


def worker(profile, fraction):
    if prepare()!=profile:
        raise ValueError("the correction receipt changed before training")
    tok,special,cases,orders,profiles = trial.load_cases()
    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction(fraction)
    state = torch.load(foundation.OUT/"foundation.pt",weights_only=True,map_location="cpu")
    if state["tag"]!=foundation.TAG or state["parent"] is not None or trial.state_sha(state["model"])!=profile["state_sha256"]:
        raise ValueError("the common foundation state differs")
    config = TMTConfig(**state["config"])
    if config.quant_anneal!=1.0 or config.train_repeat!=2.0:
        raise ValueError("the pretrained quant and visitation state must be fixed")
    model = TiedMLPTransformer(config).to("cuda")
    model.load_state_dict(state["model"])
    model.eval()
    original = trial.evaluate(model,tok,special,cases["test"])
    trial.publish(OUT/"common_test.json",original)
    pad = special["<pad>"]
    rows = cases["train"]
    print(f"START {TAG}: coherent independent test baseline saved",flush=True)
    for arm in trial.course.ARMS:
        torch.manual_seed(data.SEED)
        model.load_state_dict(state["model"])
        model.train()
        model.clear_quant()
        optimizer = torch.optim.AdamW(model.parameters(),lr=LR,weight_decay=.01,fused=True)
        step, targets, actual = 0,0,0
        stats = []
        start_time = time.perf_counter()
        torch.cuda.reset_peak_memory_stats()
        for epoch,block in enumerate(orders[arm]*trial.CYCLES,1):
            ordered = [rows[z["case_id"]]["records"][z["view"]] for z in block]
            loss_sum,count = torch.zeros((),device="cuda"),0
            for index in range(0,len(ordered),trial.BATCH):
                items = ordered[index:index+trial.BATCH]
                x,y,_ = pad_records(items,pad,"cuda",fixed_width=trial.WIDTH,batch_size=trial.BATCH)
                active = y.ne(IGNORE)
                expected = y[active]
                step += 1
                optimizer.param_groups[0]["lr"] = LR*min(1.,step/29)*(1-.7*(step/profiles[arm]["updates"])**2)
                optimizer.zero_grad(set_to_none=True)
                with torch.autocast("cuda",dtype=torch.bfloat16):
                    h = model(x,return_hidden=True)
                    logits = model._head_logits(h[active])
                    loss = F.cross_entropy(logits.float(),expected,reduction="sum")
                (loss/expected.numel()).backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(),1.0,error_if_nonfinite=True)
                optimizer.step()
                count += expected.numel()
                actual += sum(len(z.x) for z in items)
                loss_sum += loss.detach()
            targets += count
            stats.append(dict(epoch=epoch,steps=step,targets=targets,ce=loss_sum.item()/count))
            print(json.dumps(dict(arm=arm,**stats[-1])),flush=True)
        planned = profiles[arm]
        if (step,targets,actual)!=(planned["updates"],planned["targets"],planned["actual_input_tokens"]):
            raise RuntimeError("training exposures differ from the matched order")
        model.eval()
        model.clear_quant()
        val = trial.evaluate(model,tok,special,cases["validation"])
        test = trial.evaluate(model,tok,special,cases["test"])
        weights = {name: value.detach().cpu() for name,value in model.state_dict().items()}
        stem = arm.lower()
        ckpt = OUT/f"{stem}.pt"
        with ckpt.open("xb") as stream:
            torch.save(dict(model=weights,config=state["config"],course=arm,
                            foundation_sha256=profile["checkpoint_sha256"],tag=TAG),stream)
        trial.publish(OUT/f"{stem}.json",dict(validation=val,test=test,epochs=stats,arm=arm,
                     state_sha256=trial.state_sha(weights),checkpoint_sha256=trial.file_sha(ckpt),
                     wall=time.perf_counter()-start_time,peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20))
    if prepare()!=profile:
        raise ValueError("the verified inputs changed during the comparison")
    trial.publish(OUT/"report.json",profile)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("check","run"))
    parser.add_argument("--receipt",type=Path)
    parser.add_argument("--stop-by",type=datetime.fromisoformat)
    args = parser.parse_args()
    receipt = prepare()
    if args.mode=="check":
        print(json.dumps(receipt,indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt)!=receipt:
        parser.error("run requires the matching CPU receipt and a stop time")
    return owner.supervise(worker,(receipt,),OUT,args.stop_by,authorization_end=trial.CUTOFF,min_seconds=300)


if __name__=="__main__":
    sys.exit(main())
