"""Audit full versus conditioned 248K KL on two stored native logit vectors."""

import os
from pathlib import Path

import torch

from scripts import diag_p102a_tiled_bonsai_exact_kd as data
from scripts import diag_p106b_teacher_tokenizer_map as ref

TAG = "p106b_248k_kl_support_readback_v1_20261119"
OUT = ref.OUT.with_name(TAG)


def divergence(lp, lq):
    return (lp.exp() * (lp - lq)).sum()


def comparison(teacher, student, keep, temperature):
    teacher = teacher / temperature
    student = student / temperature
    lp, lq = teacher.log_softmax(0), student.log_softmax(0)
    full = divergence(lp, lq)
    parts = [keep, ~keep]
    group_p = torch.stack([lp[part].logsumexp(0) for part in parts])
    group_q = torch.stack([lq[part].logsumexp(0) for part in parts])
    slice_p = [teacher[part].log_softmax(0) for part in parts]
    slice_q = [student[part].log_softmax(0) for part in parts]
    conditioned, excluded = (divergence(p, q) for p, q in zip(slice_p, slice_q, strict=True))
    mass_kl = divergence(group_p, group_q)
    component = group_p[0].exp()*conditioned + group_p[1].exp()*excluded + mass_kl
    assert torch.isclose(full, component, rtol=1e-12, atol=1e-12)
    # Derivatives with respect to student logits before temperature scaling.
    full_gradient = temperature * (lq.exp() - lp.exp())
    masked_gradient = torch.zeros_like(full_gradient)
    masked_gradient[keep] = temperature * (slice_q[0].exp() - slice_p[0].exp())
    delta = masked_gradient - full_gradient
    with torch.enable_grad():
        w = (student * temperature).detach().requires_grad_()
        actual = torch.autograd.grad(temperature**2 * divergence(lp, (w / temperature).log_softmax(0)), w)[0]
        torch.testing.assert_close(actual, full_gradient, atol=1e-13, rtol=1e-10)
    return dict(temperature=temperature, full_kl=float(full), conditioned_kl=float(conditioned),
                excluded_conditional_kl=float(excluded), group_mass_kl=float(mass_kl),
                excluded_mass_teacher=float(group_p[1].exp()), excluded_mass_comparison=float(group_q[1].exp()),
                chain_residual=float(full-component), gradient_l1_delta=float(delta.abs().sum()),
                gradient_l1_full=float(full_gradient.abs().sum()), gradient_l2_delta=float(delta.norm()),
                gradient_max_abs_delta=float(delta.abs().max()))


def main():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    torch.set_num_threads(1)
    earlier_path = ref.OUT / "report.json"
    earlier = ref.read(earlier_path)
    tok_path = ref.QWEN_HF / "tokenizer.json"
    assert ref.sha(tok_path) == earlier["assets"]["qwen35_hf"]["file_sha256"]
    tokenizer = ref.read(tok_path)
    ids = set(tokenizer["model"]["vocab"].values())
    ids.update(row["id"] for row in tokenizer["added_tokens"])
    assert ids == set(range(248066))
    keep = torch.zeros((248320,), dtype=torch.bool)
    keep[sorted(ids)] = True
    bank, receipts = data.frozen_logits(torch)
    assert bank.dtype == torch.float64 and bank.shape == (2, len(keep))
    observations = {}
    for t in (1., 2.):
        for name, (a, b) in (("A_to_B", bank), ("B_to_A", bank.flip(0))):
            observations[f"{name}_T{int(t)}"] = comparison(a, b, keep, t)
    assert not torch.cuda.is_initialized()
    OUT.mkdir(exist_ok=False)
    ref.write(OUT / "report.json", dict(tag=TAG, prior_sha256=ref.sha(earlier_path),
        tokenizer_sha256=ref.sha(tok_path), source_sha256=ref.sha(Path(__file__)), vector_receipts=receipts,
        rows=len(keep), shared_rows=len(ids), excluded_rows=int((~keep).sum()),
        observations=observations, gpu_evaluation=0, student_inference=0))
    print("P106B_248K_KL_SUPPORT", {key:[row["full_kl"],row["conditioned_kl"],row["gradient_l1_delta"]]
                                             for key,row in observations.items()}, flush=True)


if __name__ == "__main__":
    main()
