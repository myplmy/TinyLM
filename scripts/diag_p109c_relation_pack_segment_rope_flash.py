"""Isolate segment-local rotary positions in the verified P109C Flash comparison."""

import argparse
from datetime import datetime
from functools import partial
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

from scripts import diag_p109c_same_update_relation_pack_flash as flash
from tinylm.model import modules


TAG = "p109c_relation_pack_segment_rope_flash_v1_20261123"
CANDIDATE = "packed_segment_relative"
mixed = flash.mixed


def positions(segments):
    indices = np.arange(segments.shape[1])
    new_segment = np.ones(segments.shape,dtype=bool)
    new_segment[:,1:] = segments[:,1:] != segments[:,:-1]
    return indices - np.maximum.accumulate(np.where(new_segment,indices,0),axis=1)


def relative_hidden(model, x, segments, *, flash, hidden):
    index = torch.as_tensor(positions(segments),device=x.device)
    local_cos = model.rope_cos[index].unsqueeze(1)
    local_sin = model.rope_sin[index].unsqueeze(1)

    def apply(values, _cosine, _sine):
        left,right = values.float().chunk(2,dim=-1)
        return torch.cat((left*local_cos-right*local_sin,left*local_sin+right*local_cos),dim=-1).to(values.dtype)

    with patch.object(modules,"apply_rope",apply):
        return hidden(model,x,segments,flash=flash)


def worker(training, previous, old, pins, manifest, digest, resume, record, cutoff):
    layout = flash.layouts
    evaluate = flash.comparison.measure
    hidden = mixed.masked_hidden

    def cases(bundle):
        batches, counts = layout(bundle)
        return {"dedicated":batches["dedicated"], CANDIDATE:batches["packed_trimmed"]}, counts

    def measure(model,batches,counts,limit,**kwargs):
        if len(batches) != 1:
            return evaluate(model,batches,counts,limit,**kwargs)
        with patch.object(mixed,"masked_hidden",partial(relative_hidden,hidden=hidden)):
            return evaluate(model,batches,counts,limit,**kwargs)

    with (patch.object(flash,"TAG",TAG),
          patch.object(flash,"ORDER",("dedicated",CANDIDATE,CANDIDATE)),
          patch.object(flash,"layouts",cases),
          patch.object(flash.comparison,"measure",measure)):
        flash.worker(training,pins,manifest,digest,resume,record,cutoff)
    latest = json.loads((record/"report.json").read_text(encoding="utf-8"))
    if (latest["checkpoint_sha256"] != old["checkpoint_sha256"] or latest["profile_sha256"] != old["profile_sha256"]
            or latest["source_update"] != old["source_update"] or latest["targets"] != old["targets"]):
        raise ValueError("the new position comparison must use the earlier completed relation update")
    source = old["trials"]["packed_trimmed"]
    candidate = latest["trials"][CANDIDATE]
    mixed.native.publish(record/"position_comparison.json",dict(status="SEGMENT_RELATIVE_ROPE_COMPARED",
        source_report=str(previous), source_sha256=pins[previous],
        prior_relative_l2=max(row["gradient_relative_l2"] for row in source),
        new_relative_l2=max(row["gradient_relative_l2"] for row in candidate),
        prior_max_choice_delta=max(row["max_choice_logp_delta"] for row in source),
        new_max_choice_delta=max(row["max_choice_logp_delta"] for row in candidate),
        selected_choices_preserved=all(row["same_selected_choices"] for row in candidate),
        prior_median_seconds=old["median_seconds"]["packed_trimmed"],
        new_median_seconds=latest["median_seconds"][CANDIDATE], optimizer_updates=0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("training","manifest","previous","record"):
        parser.add_argument("--"+option,required=True,type=Path)
    for option in ("manifest-sha256","source-sha256"):
        parser.add_argument("--"+option,required=True)
    parser.add_argument("--stop-by",required=True,type=datetime.fromisoformat)
    args = parser.parse_args()
    previous = args.previous.absolute()
    old = json.loads(mixed.native.manifest_bytes(previous,mixed.prep.sha(previous)))
    record = args.record.absolute()
    sources = tuple(Path(module.__file__).resolve() for module in (flash,flash.comparison,mixed,modules))
    own = Path(__file__).resolve()
    pins = {path:mixed.prep.sha(path) for path in (own,previous,*sources)}
    if (old["status"]!="RELATION_LAYOUTS_FLASH_MEASURED" or old["profile_sha256"]!=args.manifest_sha256
            or pins[own]!=mixed.native.digest(args.source_sha256) or args.stop_by.tzinfo is None
            or record.exists() or record.is_symlink()):
        parser.error("the earlier measured layout, new code signature and authorized cutoff are required")
    target = partial(worker,args.training.absolute(),previous,old,pins)
    return flash.supervisor.supervise(target,args.manifest.absolute(),args.manifest_sha256,record,args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
