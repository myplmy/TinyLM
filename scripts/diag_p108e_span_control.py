"""CPU feasibility control for the actual fixed last-layer B44/R78 span."""
import argparse
import json
import time
import unittest
import numpy as np
import torch
from scripts import p108e_io as native
from scripts import diag_p108e_geometry as geometry
from scripts import p108e_span_control as mathematics
from scripts import diag_p108c_scope as archive
from scripts import diag_p108d_winner as D
from scripts import p108d_winner as margin_calculation
from scripts import p108_weight_space as identity

OUT=native.BASE/"span_control_v1"


def check():
    geometry.verify();native.Budget(600).check(admission=True)
    if archive.read(native.BASE/"policies/SINGLE13/report.json")["status"]!="BOUNDED_MARGIN_POLICY_COMPLETE":
        raise ValueError("closed single-layer approximation control required")


def actual():
    check();budget=native.Budget(600)
    if OUT.exists():raise FileExistsError("preserve previous subspace control")
    suite=unittest.defaultTestLoader.loadTestsFromName("scripts.test_p108e_span_control")
    tests=unittest.TextTestRunner(verbosity=2).run(suite)
    if not tests.wasSuccessful()or tests.testsRun!=3:raise RuntimeError("three independent offset/history contracts required")
    capture,arrays,head=D.captured();completed=archive.read(native.GEOMETRY/"report.json")
    layer=next(row for row in completed["layers"]if row["layer"]==13)
    basis=archive.load_arrays(native.ROOT/layer["basis"]["path"])
    OUT.mkdir();started=time.monotonic()
    sources=("scripts/p108e_span_control.py","scripts/test_p108e_span_control.py","scripts/diag_p108e_span_control.py")
    with (OUT/"initial_plan.md").open("xb")as stream:stream.write(archive.PLAN.read_bytes())
    archive.write_new(OUT/"admission.json",dict(authority_directive=142,
        authority_end=native.time_owner.AUTHORITY_END.isoformat(),source_code={p:archive.sha(native.ROOT/p)for p in sources},
        E_geometry_sha256=archive.sha(native.GEOMETRY/"report.json"),D_capture_sha256=archive.sha(D.CAPTURE/"report.json"),
        basis=layer["basis"],initial_plan_sha256=archive.sha(OUT/"initial_plan.md"),CPU_contracts=3,
        no_new_model=True,no_new_forward=True,no_new_generation=True))
    original_scores=arrays["residuals"].astype(np.float64)@head.astype(np.float64).T
    variable_head=head.astype(np.float64)@basis["left"]
    keys=arrays["keys"].astype(np.float64)@basis["right"].T
    theta,result=mathematics.solve(variable_head,original_scores,keys,arrays["gold"],capture["gate"],
        arrays["original_rms"]*.10,native.COMMON_BUDGET,check=budget.check)
    delta=basis["left"]@theta@basis["right"]
    requested=delta.astype(np.float32);after=arrays["original_before"]+requested
    physical=after.astype(np.float64)-arrays["original_before"].astype(np.float64)
    actual_scores=(arrays["residuals"]+capture["gate"]*(arrays["keys"]@physical.T))@head.T
    required=arrays["original_rms"]*.10
    measured,rivals=margin_calculation.winner_margins(actual_scores,arrays["gold"])
    packet=archive.save_arrays(OUT/"physical_packet.npz",requested=requested,after=after)
    report=dict(status="CPU_SUBSPACE_FEASIBILITY_CONTROL_COMPLETE",solver=result,left_rank=basis["left"].shape[1],
        right_rank=basis["right"].shape[0],coefficient_packet=archive.save_arrays(OUT/"coordinates.npz",theta=theta),
        physical_packet=packet,physical_norm=float(np.linalg.norm(physical)),
        physical_predicted_gold=int(np.sum(actual_scores.argmax(axis=1)==arrays["gold"])),
        physical_maximum_raw_violation=float((required-measured).max()),
        before_sha256=identity.tensor_sha(torch.from_numpy(arrays["original_before"])),
        after_sha256=identity.tensor_sha(torch.from_numpy(after)),norm_budget=native.COMMON_BUDGET,
        already_seen_FIT_not_general_quality=True,new_model_loads=0,new_forwards=0,new_generations=0,
        optimizer_updates=0,checkpoint_writes=0,wall_seconds=time.monotonic()-started)
    if torch.cuda.is_initialized():raise RuntimeError("CPU affine control initialized CUDA")
    archive.write_new(OUT/"report.json",report)
    print("[E_SPAN_END]"+json.dumps(dict(status=report["status"],solver_status=result["status"],
        predicted=report["physical_predicted_gold"],norm=report["physical_norm"],wall=report["wall_seconds"])),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("phase",choices=("check","actual"))
    if parser.parse_args().phase=="check":check();print("[E_SPAN_CHECK]closed actual same-basis source;model0",flush=True)
    else:actual()


if __name__=="__main__":main()
