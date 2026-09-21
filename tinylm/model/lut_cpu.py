"""Explicitly selected native CPU backend for TinyLM's 5-trit LUT format.

The extension is compiled lazily only when ``lut_backend='native_cpu'`` is
selected.  Reference behavior remains the default and build/runtime failures
are fail-closed rather than silently falling back to the slow Python path.
The v1 kernel builds the 243-state activation table through base-3 incremental
updates and releases the Python GIL while native work is running.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import tempfile

import torch

_EXTENSION = None


def source_path() -> Path:
    return Path(__file__).resolve().parent.parent / "csrc" / "lut_cpu.cpp"


def extension_name() -> str:
    digest = hashlib.sha256(source_path().read_bytes()).hexdigest()[:12]
    return f"tinylm_lut_cpu_{digest}"


def _load_without_ninja(*, verbose: bool = False):
    """Build the tiny extension directly when the optional Ninja package is absent."""
    from torch.utils.cpp_extension import include_paths, library_paths

    compiler = os.environ.get("CXX") or shutil.which("c++") or shutil.which("g++")
    if not compiler:
        raise RuntimeError("native CPU LUT requires a C++17 compiler; c++/g++ not found")
    name = extension_name()
    base = Path(os.environ.get("TORCH_EXTENSIONS_DIR") or tempfile.gettempdir())
    build = base / name / "manual"
    build.mkdir(parents=True, exist_ok=True)
    suffix = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
    output = build / f"{name}{suffix}"
    if not output.is_file():
        includes = include_paths() + [sysconfig.get_paths()["include"]]
        libraries = library_paths()
        command = [
            compiler, "-shared", "-fPIC", "-O3", "-march=native", "-std=c++17",
            str(source_path()), "-o", str(output),
            f"-DTORCH_EXTENSION_NAME={name}",
            f"-D_GLIBCXX_USE_CXX11_ABI={int(torch._C._GLIBCXX_USE_CXX11_ABI)}",
        ]
        command.extend(f"-I{path}" for path in includes)
        command.extend(f"-L{path}" for path in libraries)
        command.extend(f"-Wl,-rpath,{path}" for path in libraries)
        command.extend(["-ltorch_python", "-ltorch", "-ltorch_cpu", "-lc10"])
        completed = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=False,
        )
        if verbose:
            print("[lut-native] " + " ".join(command))
            print(completed.stdout)
            print(completed.stderr)
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(
                f"native CPU LUT direct C++ build failed rc={completed.returncode}: {detail[-2000:]}"
            )
    spec = importlib.util.spec_from_file_location(name, output)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load native CPU LUT extension: {output}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_extension(*, verbose: bool = False):
    global _EXTENSION
    if _EXTENSION is None:
        from torch.utils.cpp_extension import load

        try:
            _EXTENSION = load(
                name=extension_name(),
                sources=[str(source_path())],
                extra_cflags=["-O3", "-march=native"],
                verbose=verbose,
            )
        except RuntimeError as exc:
            if "Ninja is required" not in str(exc):
                raise
            _EXTENSION = _load_without_ninja(verbose=verbose)
    return _EXTENSION


def lut_linear_native_cpu(
    x: torch.Tensor,
    codes: torch.Tensor,
    i_pad: int,
    alpha: torch.Tensor,
    *,
    verbose_build: bool = False,
) -> torch.Tensor:
    if x.device.type != "cpu" or codes.device.type != "cpu" or alpha.device.type != "cpu":
        raise RuntimeError("lut_backend=native_cpu is CPU-only")
    if x.dtype != torch.float32:
        raise RuntimeError(f"lut_backend=native_cpu requires float32 activations, got {x.dtype}")
    if codes.dtype != torch.uint8:
        raise RuntimeError(f"lut_backend=native_cpu requires uint8 codes, got {codes.dtype}")
    if alpha.dtype != torch.float32 or alpha.ndim not in (1, 2):
        raise RuntimeError("lut_backend=native_cpu requires float32 per-row alpha")
    if alpha.ndim == 2 and alpha.shape[1] != 1:
        raise RuntimeError("lut_backend=native_cpu v0 supports alpha shape [O] or [O,1]")
    extension = load_extension(verbose=verbose_build)
    return extension.lut_linear_cpu(x, codes, alpha, int(i_pad))
