"""PM001 moonshot: 1.25bpw 3:4 전용 CPU LUT linear.

이 모듈은 **추론 전용**이다. 학습 forward는 latent weight와 dense GEMM을 유지하며,
5-bit 저장 포맷을 사용하지 않는다. 네이티브 backend는 행별 packed stream을 직접
decode해 활성값 LUT를 조회하므로 `(O,I)` int8/fp32 가중치 사본을 만들지 않는다.

backend 계약:
  - ``native``: C++ 확장을 지연 빌드하고, 실패하면 크게 실패한다. 조용한 폴백 없음.
  - ``reference``: 같은 32-state LUT 수학을 PyTorch로 계산하는 정확성 대조군.
"""
from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import sys
import threading
from pathlib import Path

import torch

from .lut import SPARSE34_BLOCK, pack_sparse34_rows, unpack_sparse34_codes

_EXTENSION = None
_EXTENSION_ERROR: BaseException | None = None
_EXTENSION_LOCK = threading.Lock()
_PATTERN_CACHE: dict[tuple[str, torch.dtype], torch.Tensor] = {}
_SOURCE = Path(__file__).resolve().parent / "csrc" / "sparse34_lut_cpu.cpp"
_EXTENSION_NAME = "tinylm_sparse34_lut_cpu_v1"


class Sparse34KernelBuildError(RuntimeError):
    """네이티브 CPU 확장을 빌드하거나 로드하지 못했음을 명시적으로 알린다."""


def sparse34_cpu_environment() -> dict[str, object]:
    """빌드하지 않고 현재 interpreter의 네이티브 확장 전제만 보고한다."""
    return {
        "platform": platform.platform(),
        "python": sys.executable,
        "torch": torch.__version__,
        "source": str(_SOURCE),
        "source_exists": _SOURCE.is_file(),
        "ninja_module": importlib.util.find_spec("ninja") is not None,
        "ninja_executable": shutil.which("ninja"),
        "msvc_cl": shutil.which("cl") if os.name == "nt" else None,
        "loaded": _EXTENSION is not None,
        "last_error": None if _EXTENSION_ERROR is None else (
            f"{type(_EXTENSION_ERROR).__name__}: {_EXTENSION_ERROR}"
        ),
    }


def load_sparse34_cpu_extension(verbose: bool | None = None):
    """PyTorch C++ extension을 최초 native 호출 시 한 번만 빌드/로드한다.

    빌드 실패를 reference 경로로 숨기지 않는다. 실험 로그가 toolchain 실패를 커널
    성능처럼 기록하지 않게 하는 계약이다.
    """
    global _EXTENSION, _EXTENSION_ERROR
    if _EXTENSION is not None:
        return _EXTENSION
    with _EXTENSION_LOCK:
        if _EXTENSION is not None:
            return _EXTENSION
        if not _SOURCE.is_file():
            raise Sparse34KernelBuildError(f"C++ source가 없다: {_SOURCE}")
        try:
            from torch.utils.cpp_extension import load

            if verbose is None:
                verbose = os.environ.get("TINYLM_S34_BUILD_VERBOSE", "0") == "1"
            flags = ["/O2"] if os.name == "nt" else ["-O3", "-std=c++17"]
            _EXTENSION = load(
                name=_EXTENSION_NAME,
                sources=[str(_SOURCE)],
                extra_cflags=flags,
                with_cuda=False,
                verbose=bool(verbose),
            )
            return _EXTENSION
        except BaseException as exc:  # noqa: BLE001 - 원인을 보존해 사용자 실행 로그에 남긴다
            _EXTENSION_ERROR = exc
            raise Sparse34KernelBuildError(
                "3:4 CPU LUT C++ 확장 빌드/로드 실패. reference로 폴백하지 않았다. "
                f"환경={sparse34_cpu_environment()}"
            ) from exc


def _validate(x: torch.Tensor, packed: torch.Tensor, alpha: torch.Tensor,
              group: int) -> tuple[int, int, int]:
    if x.ndim < 1:
        raise ValueError("x는 마지막 축이 input feature인 텐서여야 한다.")
    if packed.ndim != 2 or packed.dtype != torch.uint8:
        raise ValueError(f"packed는 uint8 (O,row_bytes)여야 한다: {packed.shape}, {packed.dtype}")
    if alpha.ndim != 2:
        raise ValueError(f"alpha는 (O,I/group)여야 한다: {alpha.shape}")
    if not x.is_floating_point() or not alpha.is_floating_point():
        raise ValueError(f"x와 alpha는 부동소수점이어야 한다: {x.dtype}/{alpha.dtype}")
    out_features, in_features = packed.shape[0], x.shape[-1]
    if out_features <= 0:
        raise ValueError(f"out_features는 양수여야 한다: {out_features}")
    if in_features % SPARSE34_BLOCK:
        raise ValueError(f"in_features={in_features}는 4의 배수여야 한다.")
    if group <= 0 or group % SPARSE34_BLOCK or in_features % group:
        raise ValueError(
            f"group={group}은 4의 양의 배수이고 in_features={in_features}를 나눠야 한다.")
    n_blocks = in_features // SPARSE34_BLOCK
    row_bytes = (n_blocks * 5 + 7) // 8
    if packed.shape[1] != row_bytes:
        raise ValueError(
            f"packed row_bytes 불일치: expected={row_bytes}, got={packed.shape[1]}")
    if alpha.shape != (out_features, in_features // group):
        raise ValueError(
            f"alpha shape 불일치: expected={(out_features, in_features // group)}, "
            f"got={tuple(alpha.shape)}")
    if not (x.device == packed.device == alpha.device):
        raise ValueError(f"x/packed/alpha device가 같아야 한다: {x.device}/{packed.device}/{alpha.device}")
    return out_features, in_features, n_blocks


def sparse34_pattern_table(device=None, dtype=torch.float32) -> torch.Tensor:
    """code ``zero_pos*8 + sign_bits`` 순서의 고정 32x4 패턴표."""
    device = torch.device(device or "cpu")
    key = (str(device), dtype)
    hit = _PATTERN_CACHE.get(key)
    if hit is not None:
        return hit
    codes = torch.arange(32, device=device, dtype=torch.int64)
    zero_pos = codes // 8
    sb = codes % 8
    signs = torch.stack([(sb // 4) % 2, (sb // 2) % 2, sb % 2], dim=1)
    values = (signs * 2 - 1).to(dtype)
    table = torch.zeros(32, SPARSE34_BLOCK, device=device, dtype=dtype)
    keep = torch.ones(32, SPARSE34_BLOCK, device=device, dtype=torch.bool)
    keep.scatter_(1, zero_pos.unsqueeze(1), False)
    table[keep] = values.reshape(-1)
    _PATTERN_CACHE[key] = table
    return table


def sparse34_lut_linear_reference(x: torch.Tensor, packed: torch.Tensor,
                                  alpha: torch.Tensor, group: int = 128,
                                  out_chunk: int = 0) -> torch.Tensor:
    """32-state PyTorch LUT 대조군. packed code만 풀고 가중치 행렬은 만들지 않는다."""
    out_features, in_features, n_blocks = _validate(x, packed, alpha, group)
    shape = x.shape
    x2 = x.reshape(-1, in_features)
    batch = x2.shape[0]
    patterns = sparse34_pattern_table(x.device, x.dtype)
    lut = torch.einsum(
        "bjg,pg->bjp", x2.reshape(batch, n_blocks, SPARSE34_BLOCK), patterns
    )
    codes = unpack_sparse34_codes(packed, n_blocks).to(torch.int64)
    per_alpha = group // SPARSE34_BLOCK

    def _slice(o0: int, o1: int) -> torch.Tensor:
        idx = codes[o0:o1].t().unsqueeze(0).expand(batch, n_blocks, o1 - o0)
        selected = lut.gather(2, idx)
        grouped = selected.reshape(batch, -1, per_alpha, o1 - o0).sum(2)
        scaled = grouped * alpha[o0:o1].to(x.dtype).t().unsqueeze(0)
        return scaled.sum(1)

    step = out_chunk if 0 < out_chunk < out_features else out_features
    parts = [_slice(o, min(o + step, out_features)) for o in range(0, out_features, step)]
    y = parts[0] if len(parts) == 1 else torch.cat(parts, dim=1)
    return y.reshape(*shape[:-1], out_features)


def sparse34_lut_linear(x: torch.Tensor, packed: torch.Tensor, alpha: torch.Tensor,
                        group: int = 128, backend: str = "native",
                        out_chunk: int = 0) -> torch.Tensor:
    """3:4 packed linear. ``native``는 CPU float32 전용이며 폴백하지 않는다."""
    out_features, in_features, _ = _validate(x, packed, alpha, group)
    if backend == "reference":
        return sparse34_lut_linear_reference(x, packed, alpha, group, out_chunk)
    if backend != "native":
        raise ValueError(f"backend는 native/reference 중 하나여야 한다: {backend}")
    if x.device.type != "cpu":
        raise ValueError(f"native 3:4 LUT는 CPU 전용이다: x.device={x.device}")
    if x.dtype != torch.float32:
        raise ValueError(
            f"native 3:4 LUT Stage0는 float32 activation 전용이다: x.dtype={x.dtype}")
    if alpha.dtype != torch.float32:
        raise ValueError(f"native 3:4 LUT alpha는 float32여야 한다: {alpha.dtype}")
    if torch.is_grad_enabled() and x.requires_grad:
        raise RuntimeError(
            "native 3:4 LUT는 추론 전용이며 autograd backward를 구현하지 않는다. "
            "torch.no_grad()/inference_mode()에서 호출하거나 reference backend를 사용하세요.")
    ext = load_sparse34_cpu_extension()
    shape = x.shape
    x2 = x.reshape(-1, in_features).contiguous()
    y = ext.sparse34_lut_linear(
        x2, packed.contiguous(), alpha.contiguous(), int(in_features), int(group)
    )
    return y.reshape(*shape[:-1], out_features)


def sparse34_lut_workspace_bytes(batch_rows: int, in_features: int) -> int:
    """네이티브 활성 LUT workspace: B * (I/4) * 32 * fp32."""
    if batch_rows < 0 or in_features < 0 or in_features % SPARSE34_BLOCK:
        raise ValueError("batch_rows는 0 이상, in_features는 4의 배수여야 한다.")
    return batch_rows * (in_features // SPARSE34_BLOCK) * 32 * 4


__all__ = [
    "Sparse34KernelBuildError",
    "load_sparse34_cpu_extension",
    "pack_sparse34_rows",
    "sparse34_cpu_environment",
    "sparse34_lut_linear",
    "sparse34_lut_linear_reference",
    "sparse34_lut_workspace_bytes",
    "sparse34_pattern_table",
]
