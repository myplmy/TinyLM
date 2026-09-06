"""커스텀 삼진 학습 커널 (기존 경로와 분리, 기본 off).

╔══════════════════════════════════════════════════════════════════════════════╗
║ ★★★ 이 파일은 **표준 학습 경로가 아니다. 한 번도 돌지 않는다.** ★★★          ║
║                                                                              ║
║   표준 경로 = `tinylm/model/ternary.py` 의 `_TernarySTE` + `F.linear`.        ║
║   이 모듈은 `cfg.use_ternary_kernel=True`(CLI `--ternary-kernel`) 일 때만     ║
║   호출되고, **그 플래그는 어떤 실험 배치에도 들어 있지 않다.**                ║
║                                                                              ║
║ ⚠️ **왜 이 배너가 필요한가**(2026-08-13):                                    ║
║   외부 AI 검토문서 2종이 이 파일의 `save_for_backward(x, aw, alpha, eff)` 를  ║
║   **"학습 VRAM 최우선 코드 검토 대상"** 으로 지목했다. 파일 이름과 위치가     ║
║   표준 경로처럼 보였기 때문이다. **죽은 코드를 최적화하는 데 시간을 쓸 뻔했다.**║
║   표준 경로가 저장하는 것은 `(aw, alpha)` **둘뿐**이다.                       ║
║                                                                              ║
║ ⚠️ **이 경로는 정확성 prototype이지 완성된 packed 커널이 아니다**:          ║
║   int8 {-1,0,+1} code를 쓰며 forward만 Triton, backward는 PyTorch다.         ║
║   PM001은 성공·폴백 telemetry와 strict 계약으로 환경 실패를 구현 실패와 분리한다.║
╚══════════════════════════════════════════════════════════════════════════════╝

설계 원칙
  - **기존 학습 무영향**: cfg.use_ternary_kernel=False(기본)면 이 모듈은 호출되지 않는다.
  - **정확성 우선**: use_ternary_kernel=True 라도 기본은 '레퍼런스'(int8 패킹 + dequant 행렬곱)로,
    기존 `_TernarySTE`+`F.linear` 경로와 **수학적으로 동일**하다. STE backward도 동일 window.
  - **Triton은 검증 후**: cfg.ternary_kernel_triton=True 를 추가로 줘야 Triton forward를 쓴다.
    Triton 커널은 GPU 검증이 끝나기 전엔 켜지 말 것(잘못된 결과가 조용히 학습을 오염시킬 수 있음).
    기본은 과거 호환상 폴백하지만 `cfg.ternary_kernel_strict=True`면 즉시 실패한다.

패킹 표현
  - codes: int8 {-1,0,+1}  [O, I]
  - alpha: 그룹(g128)별 스케일  [O, I//group]
  - 복원 wq[o,i] = codes[o,i] * alpha[o, i//group]
"""
from __future__ import annotations

import importlib.metadata

import torch
import torch.nn.functional as F

_KERNEL_WARNED = False
_TRITON_IMPORT_ERROR = None
_KERNEL_STATS = {
    "attempts": 0,
    "triton_successes": 0,
    "fallbacks": 0,
    "reference_calls": 0,
    "anneal_dense_calls": 0,
    "last_backend": "never",
    "last_failure_stage": None,
    "last_failure_category": None,
    "last_error": None,
}
try:
    import triton
    import triton.language as tl
    _HAS_TRITON = True
except Exception as exc:  # noqa: BLE001 - 진단 API가 실제 import 원인을 보고한다
    _HAS_TRITON = False
    _TRITON_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"


def _classify_triton_failure(exc, stage):
    """오류 문자열을 결론이 아니라 **진단 범주**로만 분류한다."""
    msg = f"{type(exc).__name__}: {exc}".lower()
    if stage == "import" or isinstance(exc, (ImportError, ModuleNotFoundError)):
        return "environment_import"
    if stage == "device":
        return "device_contract"
    if "constexpr" in msg or "tl.arange" in msg or "arange's arguments" in msg:
        return "implementation_compile_contract"
    if "dynamo" in msg or "identify_mutated_tensors" in msg or "function argument index" in msg:
        return "compile_integration"
    if "out of memory" in msg:
        return "resource_oom"
    if any(token in msg for token in ("driver", "ptx", "device kernel image", "cuda unavailable")):
        return "environment_runtime"
    return "runtime_unknown"


def reset_ternary_kernel_status():
    """PM001 동적 계약 한 구간의 backend 계측을 0으로 돌린다."""
    global _KERNEL_WARNED
    _KERNEL_WARNED = False
    _KERNEL_STATS.update({
        "attempts": 0,
        "triton_successes": 0,
        "fallbacks": 0,
        "reference_calls": 0,
        "anneal_dense_calls": 0,
        "last_backend": "never",
        "last_failure_stage": None,
        "last_failure_category": None,
        "last_error": None,
    })


def ternary_kernel_status():
    """Triton import와 실제 호출 성공/폴백을 구조화해 돌려준다."""
    def _distribution_version(name):
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            return None

    out = dict(_KERNEL_STATS)
    out.update({
        "has_triton": _HAS_TRITON,
        "triton_version": getattr(triton, "__version__", None) if _HAS_TRITON else None,
        "triton_module_file": getattr(triton, "__file__", None) if _HAS_TRITON else None,
        "triton_distribution": _distribution_version("triton"),
        "triton_windows_distribution": _distribution_version("triton-windows"),
        "triton_import_error": _TRITON_IMPORT_ERROR,
    })
    return out


def _triton_failure(x, wq, exc, stage, strict):
    """실패를 기록한다. strict면 reference 결과를 만들지 않고 원인을 보존해 중단한다."""
    global _KERNEL_WARNED
    category = _classify_triton_failure(exc, stage)
    detail = f"{type(exc).__name__}: {exc}"
    _KERNEL_STATS.update({
        "last_backend": "failed" if strict else "reference_fallback",
        "last_failure_stage": stage,
        "last_failure_category": category,
        "last_error": detail[:1000],
    })
    if strict:
        raise RuntimeError(
            f"Triton strict 계약 실패(stage={stage}, category={category}): {detail}"
        ) from exc
    _KERNEL_STATS["fallbacks"] += 1
    _KERNEL_STATS["reference_calls"] += 1
    if not _KERNEL_WARNED:
        print(f"[ternary_kernel] Triton 실패({category}) → 레퍼런스 폴백(이후 조용히): "
              f"{detail[:120]}")
        _KERNEL_WARNED = True
    return F.linear(x, wq.to(x.dtype))


# ---------------------------------------------------------------------------
# Triton forward 커널 (검증 전 사용 금지). x[M,K] @ wq[N,K]^T, wq=codes*alpha(그룹).
# BLOCK_K = group(128) 로 두어 k-블록 하나 = alpha 그룹 하나.
# ---------------------------------------------------------------------------
if _HAS_TRITON:
    @triton.jit
    def _tern_mm_kernel(X, CODES, ALPHA, Y, M, N, K,
                        sxm, sxk, scn, sck, san, sag, sym, syn,
                        BM: tl.constexpr, BN: tl.constexpr, G: tl.constexpr):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        offs_m = pid_m * BM + tl.arange(0, BM)
        offs_n = pid_n * BN + tl.arange(0, BN)
        offs_g = tl.arange(0, G)
        acc = tl.zeros((BM, BN), dtype=tl.float32)
        for kb in range(0, K, G):
            offs_k = kb + offs_g
            x = tl.load(X + offs_m[:, None] * sxm + offs_k[None, :] * sxk,
                        mask=(offs_m[:, None] < M) & (offs_k[None, :] < K), other=0.0)
            codes = tl.load(CODES + offs_n[:, None] * scn + offs_k[None, :] * sck,
                            mask=(offs_n[:, None] < N) & (offs_k[None, :] < K), other=0)
            alpha = tl.load(ALPHA + offs_n * san + (kb // G) * sag,
                            mask=offs_n < N, other=0.0)
            w = codes.to(tl.float32) * alpha[:, None]          # [BN, G]
            acc += tl.dot(x.to(tl.float32), tl.trans(w))       # [BM,G]@[G,BN]
        y = acc.to(tl.float32)
        tl.store(Y + offs_m[:, None] * sym + offs_n[None, :] * syn, y,
                 mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))

    def _triton_matmul(x2d, codes2d, alpha2d, group):
        M, K = x2d.shape
        N = codes2d.shape[0]
        if not x2d.is_cuda or not codes2d.is_cuda or not alpha2d.is_cuda:
            raise ValueError("Triton matmul inputs must all be CUDA tensors")
        if K % group or group <= 0 or (group & (group - 1)):
            raise ValueError(
                f"Triton BLOCK_K group must be a positive power-of-two divisor of K: K={K}, group={group}")
        if codes2d.shape != (N, K) or alpha2d.shape != (N, K // group):
            raise ValueError(
                f"Triton shape contract mismatch: x={tuple(x2d.shape)}, "
                f"codes={tuple(codes2d.shape)}, alpha={tuple(alpha2d.shape)}, group={group}")
        y = torch.empty((M, N), device=x2d.device, dtype=torch.float32)
        BM, BN = 64, 64
        grid = (triton.cdiv(M, BM), triton.cdiv(N, BN))
        _tern_mm_kernel[grid](
            x2d, codes2d, alpha2d, y, M, N, K,
            x2d.stride(0), x2d.stride(1), codes2d.stride(0), codes2d.stride(1),
            alpha2d.stride(0), alpha2d.stride(1), y.stride(0), y.stride(1),
            BM=BM, BN=BN, G=group)
        return y


def _ref_matmul(x, codes, alpha, group, dtype):
    """레퍼런스: dequant 후 F.linear. 기존 경로와 동일 결과(정확성 기준)."""
    O = codes.shape[0]
    wq = (codes.to(dtype) * alpha.to(dtype)).reshape(O, -1)   # [O, I] (활성 dtype로 통일)
    return F.linear(x, wq)


class _TernaryKernelLinear(torch.autograd.Function):
    """저비트 forward + STE 보존 backward. **삼진 어닐 반영** → 기존 경로와 값·gradient 모두 동일.
    anneal>=1(완전 삼진)일 때만 저비트 커널/레퍼런스 사용, anneal<1은 full-precision 블렌드(값)."""

    @staticmethod
    def forward(ctx, x, w, group, thr, clip, anneal, use_triton, strict):
        O, I = w.shape
        wg = w.reshape(O, I // group, group)
        aw = wg.abs()
        mask = (aw >= thr * aw.mean(dim=2, keepdim=True)).to(w.dtype)
        cnt = mask.sum(dim=2, keepdim=True).clamp_min(1.0)
        alpha = (aw * mask).sum(dim=2, keepdim=True) / cnt      # [O, G, 1]
        codes = (torch.sign(wg) * mask).to(torch.int8)          # [O, G, group]
        wq = (codes.to(w.dtype) * alpha).reshape(O, I)          # 삼진 값

        if anneal >= 1.0:                                       # 완전 삼진 → 저비트 경로
            eff = wq
            if use_triton:
                _KERNEL_STATS["attempts"] += 1
                if not _HAS_TRITON:
                    e = RuntimeError(f"Triton import unavailable: {_TRITON_IMPORT_ERROR}")
                    y = _triton_failure(x, wq, e, "import", strict)
                elif not x.is_cuda:
                    e = RuntimeError(f"Triton forward requires CUDA tensor, got {x.device}")
                    y = _triton_failure(x, wq, e, "device", strict)
                else:
                    try:
                        x2d = x.reshape(-1, I).contiguous()
                        codes2d = codes.reshape(O, I).contiguous()
                        alpha2d = alpha.reshape(O, I // group).contiguous().float()
                        y = _triton_matmul(x2d, codes2d, alpha2d, group).to(x.dtype)
                        y = y.reshape(*x.shape[:-1], O)
                        _KERNEL_STATS["triton_successes"] += 1
                        _KERNEL_STATS["last_backend"] = "triton"
                    except Exception as e:  # noqa: BLE001 - strict/telemetry가 원인을 보존한다
                        y = _triton_failure(x, wq, e, "launch", strict)
            else:
                y = F.linear(x, wq.to(x.dtype))
                _KERNEL_STATS["reference_calls"] += 1
                _KERNEL_STATS["last_backend"] = "reference"
        else:                                                  # 어닐 중: 기존 STE와 동일 블렌드(값)
            eff = wq + (1.0 - anneal) * (w - wq)
            y = F.linear(x, eff.to(x.dtype))
            _KERNEL_STATS["anneal_dense_calls"] += 1
            _KERNEL_STATS["last_backend"] = "dense_anneal"

        ctx.save_for_backward(x, aw, alpha, eff)
        ctx.meta = (O, I, group, clip)
        return y

    @staticmethod
    def backward(ctx, gy):
        x, aw, alpha, eff = ctx.saved_tensors
        O, I, group, clip = ctx.meta
        gx = gy @ eff.to(gy.dtype)                             # off 경로와 동일(값 eff)
        gw_full = gy.reshape(-1, O).t().float() @ x.reshape(-1, I).float()
        win = (1.0 / (1.0 + (aw / (clip * alpha).clamp_min(1e-8)).pow(4))).float()
        gw = (gw_full.reshape(O, I // group, group) * win).reshape(O, I)
        return gx, gw, None, None, None, None, None, None


def ternary_kernel_linear(x, w, cfg, anneal_t=None):
    """TLinear.forward 진입점. 어닐은 갱신된 스칼라 텐서를 우선 사용한다.

    이 prototype은 데이터 의존 분기가 있어 ``torch.compile``과 병용하지 않는다. trainer가
    해당 조합을 선제 거부하며, ``anneal_t`` 미제공 시에만 cfg 값을 사용한다.
    """
    anneal = anneal_t if anneal_t is not None else float(cfg.quant_anneal)
    group = int(getattr(cfg, "micro_group", 128) or w.shape[1])
    return _TernaryKernelLinear.apply(
        x, w, group, cfg.twn_thr_ratio, cfg.ste_clip,
        anneal, getattr(cfg, "ternary_kernel_triton", False),
        getattr(cfg, "ternary_kernel_strict", False))
