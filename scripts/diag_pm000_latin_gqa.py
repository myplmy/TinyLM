#!/usr/bin/env python3
"""PM000 Latin GQA 동적 계약 진단.

이 파일은 torch 모델을 만들고 forward/backward를 수행한다. AI 정적 검증 대상이 아니며,
사용자가 `moonshot_batch/run_PM000__MOONSHOT__Stage0_contract.bat` 또는
`run_smoke_check.bat`를 통해 실행한다. 데이터 준비와 학습은 하지 않는다.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _cfg(schedule: str, seed: int = 0):
    from tinylm.config import TMTConfig

    return TMTConfig(
        vocab_size=64,
        dim=32,
        ffn_dim=64,
        n_q_heads=4,
        n_kv_heads=2,
        emb_rank=8,
        n_prelude=1,
        n_middle=2,
        n_coda=1,
        mlp_group=1,
        cla_group=2,
        micro_group=16,
        max_seq_len=16,
        grad_checkpoint=False,
        train_repeat=3.0,
        repeat_mode="uniform",
        gqa_pass_schedule=schedule,
        gqa_pass_seed=seed,
    )


def _pass(label: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"[PASS] {label}{suffix}")


def run(device_name: str) -> None:
    import torch

    from tinylm.moonshot.pm000_latin_gqa import gqa_pass_order
    from tinylm.model import TiedMLPTransformer

    if device_name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("--device cuda 를 요청했지만 CUDA를 사용할 수 없다")
    device = torch.device(device_name)
    if device.type == "cpu":
        torch.set_num_threads(1)

    # 1. 수학적 schedule 계약 — torch RNG와 무관한 순수 정수 함수다.
    assert gqa_pass_order("fixed", 3, 999) == (0,)
    assert gqa_pass_order("latin", 3, 999) == (0, 1, 2)
    random_orders = [gqa_pass_order("random", 5, seed) for seed in range(16)]
    assert all(order[0] == 0 and sorted(order) == list(range(5)) for order in random_orders)
    assert len(set(random_orders)) > 1
    assert gqa_pass_order("random", 5, 17) == gqa_pass_order("random", 5, 17)
    _pass("schedule contract", f"random seed17={list(gqa_pass_order('random', 5, 17))}")

    # 동일 가중치를 가진 fixed/latin 모델을 만든다. plain tuple만 달라야 한다.
    torch.manual_seed(20260906)
    fixed = TiedMLPTransformer(_cfg("fixed")).to(device)
    latin = TiedMLPTransformer(_cfg("latin")).to(device)
    fixed_keys = tuple(fixed.state_dict().keys())
    latin_keys = tuple(latin.state_dict().keys())
    assert fixed_keys == latin_keys
    latin.load_state_dict(fixed.state_dict(), strict=True)
    n_fixed = sum(p.numel() for p in fixed.parameters())
    n_latin = sum(p.numel() for p in latin.parameters())
    assert n_fixed == n_latin
    _pass("parameter/state contract", f"params={n_fixed:,}, keys={len(fixed_keys)}")

    tokens = torch.tensor([[1, 7, 3, 9, 2, 11]], dtype=torch.long, device=device)
    fixed.eval()
    latin.eval()
    fixed.freeze_quant()
    latin.freeze_quant()

    # 2. R1은 pass 0만 방문하므로 exact equality여야 한다.
    fixed.cfg.train_repeat = 1.0
    latin.cfg.train_repeat = 1.0
    with torch.no_grad():
        r1_fixed = fixed(tokens)
        r1_latin = latin(tokens)
    assert torch.equal(r1_fixed, r1_latin), \
        f"R1 exact identity 실패: max_abs={(r1_fixed-r1_latin).abs().max().item():.3e}"
    _pass("R1 exact identity")

    # 3. R3에서는 pass 1이 실제로 KV head를 바꿔 출력이 달라야 한다.
    fixed.cfg.train_repeat = 3.0
    latin.cfg.train_repeat = 3.0
    with torch.no_grad():
        r3_fixed = fixed(tokens)
        r3_latin = latin(tokens)
    live_delta = (r3_fixed - r3_latin).abs().max().item()
    assert live_delta > 0.0, "R3 latin 처치가 출력을 전혀 바꾸지 않았다"
    _pass("R3 treatment is live", f"max_abs_delta={live_delta:.3e}")

    # 4. 같은 Latin schedule의 full prefill과 token-by-token cache가 일치해야 한다.
    cached_parts = []
    past = None
    with torch.no_grad():
        for pos in range(tokens.shape[1]):
            logits, past = latin(tokens[:, pos:pos + 1], past_kv=past, use_cache=True)
            cached_parts.append(logits)
    cached = torch.cat(cached_parts, dim=1)
    cache_max = (cached - r3_latin).abs().max().item()
    torch.testing.assert_close(cached, r3_latin, rtol=1e-4, atol=1e-5)
    latin_entries = len(past)
    past_fixed = None
    with torch.no_grad():
        for pos in range(tokens.shape[1]):
            _, past_fixed = fixed(tokens[:, pos:pos + 1], past_kv=past_fixed, use_cache=True)
    assert len(past_fixed) == latin_entries
    _pass("cached/full agreement", f"max_abs={cache_max:.3e}, kv_entries={latin_entries}")

    # 5. 실제 backward에서 Latin roll을 통과한 gradient가 유한해야 한다.
    grad_model = TiedMLPTransformer(replace(_cfg("latin"), max_seq_len=8)).to(device)
    grad_model.train()
    grad_tokens = tokens[:, :4]
    loss = grad_model(grad_tokens).float().square().mean()
    loss.backward()
    grads = [p.grad for p in grad_model.parameters() if p.grad is not None]
    assert grads and all(torch.isfinite(g).all().item() for g in grads)
    _pass("finite backward", f"loss={loss.item():.6f}, grad_tensors={len(grads)}")

    print("\nPM000 CONTRACT PASS — this proves wiring only, not model quality.")


def main() -> int:
    ap = argparse.ArgumentParser(description="PM000 Latin GQA dynamic contract diagnostic")
    ap.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    a = ap.parse_args()
    try:
        run(a.device)
    except Exception as exc:  # noqa: BLE001 — 계약 실패를 한 줄로 남기고 nonzero 종료
        print(f"\n[FAIL] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
