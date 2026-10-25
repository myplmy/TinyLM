"""고정 v12 커널의 모델 없는 수치·비용 관측기. 실제 실행은 별도 OS 감독 아래에서만 허용한다."""
from __future__ import annotations

import time

STARTED = time.monotonic()

import argparse
import ctypes
from datetime import datetime, timezone
import gc
import functools
import hashlib
import importlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import sys
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data_cache/p102a_shared_research/20261025/v12_archive"
ORIGINAL = ROOT / "tmp/llm_training_acceleration_prototype.zip"
ZIP_SHA = "E1397A0A2143B702EA187F492CF3B594636A62EA825F2DA383E9BC338FA8805E"
MANIFEST_SHA = "0D6C722F9CF03D7A874B4C57C609E48565A59CE566D2FCB53D7B45028399A0D6"
RUNTIME = ("v8_torch_backend.py", "v11_int8_backend.py", "v11_int8_kernels.py",
           "v11_reuse_kernels.py", "v12_code_reuse.py", "v12_kernels.py", "v12_swiglu.py")
OWN = ("scripts/diag_p102a_v12_kernels.py", "scripts/test_p102a_v12_kernels.py")
SUPERVISION = ("scripts/codex_smoke.py", "scripts/smoke_module.py", "scripts/smoke_execution_contract.py")
PREFIX = "p102a_v12_kernel_v1_s1337_"
HARD_STOP = datetime(2026, 10, 25, 4, tzinfo=timezone.utc)
MAX_FILE = 20_000_000
GROUP = 128
SHAPES = ((768, 2048), (2048, 768), (768, 192))


class Incomplete(RuntimeError):
    """미완료·미지원과 수치 관측 완료를 구분한다."""


class NumericMismatch(ArithmeticError):
    def __init__(self, detail):
        self.detail = detail
        super().__init__("원 구현의 수치 대조 불일치: " + json.dumps(detail, ensure_ascii=False))


def aware(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("시간대가 있는 마감시각이 필요하다")
    return result.astimezone(timezone.utc)


class Guard:
    def __init__(self, deadline, seconds, *, started=None, now=None, clock=None, reserve=0.):
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.clock = clock or time.monotonic
        self.deadline = aware(deadline) if isinstance(deadline, str) else deadline
        if self.deadline.tzinfo is None or not 60 <= seconds <= 900:
            raise ValueError("시간대와 60~900초 상한이 필요하다")
        if not self.now() < self.deadline <= HARD_STOP:
            raise ValueError("현재 승인 시간창 안의 마감시각이 필요하다")
        self.started = self.clock() if started is None else started
        self.seconds, self.reserve = seconds, reserve
        self.check("시간창 입장")

    def remaining(self):
        return min((self.deadline - self.now()).total_seconds(),
                   self.seconds - (self.clock() - self.started)) - self.reserve

    def check(self, phase):
        if self.remaining() <= 0:
            raise TimeoutError("시간창을 넘었다: " + phase)


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest().upper()


def digest(path, guard=None):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            if guard:
                guard.check("원형 바이트 읽기")
            block = stream.read(1024 * 1024)
            if not block:
                break
            result.update(block)
    return result.hexdigest().upper()


def safe_file(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError("정상 원형 파일이 아니다: " + str(path))
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise ValueError("저장소 밖의 경로는 거부한다")
    for parent in path.parents:
        if parent == ROOT:
            break
        if parent.is_symlink():
            raise ValueError("심볼릭 링크 경로는 거부한다")
    return resolved


def source_receipt(guard=None):
    """표준 라이브러리만 사용하며 파일을 생성하거나 Torch/CUDA를 import하지 않는다."""
    archive_sha = digest(safe_file(ORIGINAL), guard)
    if archive_sha != ZIP_SHA:
        raise ValueError("원 ZIP SHA가 달라졌다")
    manifest_path = safe_file(ARCHIVE / "v12_manifest.json")
    if digest(manifest_path, guard) != MANIFEST_SHA:
        raise ValueError("원 manifest SHA가 달라졌다")
    runtime = {}
    with zipfile.ZipFile(ORIGINAL) as packed:
        members = packed.namelist()
        for name in RUNTIME:
            if guard:
                guard.check("의존 소스 검산")
            path = safe_file(ARCHIVE / name)
            if path.stat().st_size >= MAX_FILE:
                raise ValueError("의존 소스 크기 상한을 넘었다")
            matches = [n for n in members if n == name or n.endswith("/" + name)]
            if len(matches) != 1:
                raise ValueError("ZIP 안의 정확 소스가 유일하지 않다: " + name)
            raw = packed.read(matches[0])
            expected = hashlib.sha256(raw).hexdigest().upper()
            actual = digest(path, guard)
            if actual != expected:
                raise ValueError("추출 소스가 원 ZIP과 다르다: " + name)
            runtime[name] = actual
    own = {name: digest(safe_file(ROOT / name), guard) for name in OWN}
    supervision = {name: digest(safe_file(ROOT / name), guard) for name in SUPERVISION}
    material = dict(original_zip_sha256=archive_sha, manifest_sha256=MANIFEST_SHA,
                    runtime_source_sha256=runtime, driver_source_sha256=own,
                    supervision_source_sha256=supervision)
    return dict(**material, source_sha256=identity(material))


def environment_metadata():
    packages = {}
    for name in ("torch", "triton"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return dict(python=sys.version, executable=sys.executable, packages=packages,
                archive_record=dict(torch="2.14.1+cpu", triton="3.8"),
                compatibility_note="원형 CPU 기록과 현재 설치의 차이를 실제 CUDA 검사 대상으로 남긴다")


def validate_args(args):
    if not re.fullmatch(re.escape(PREFIX) + r"[a-z0-9_]{1,48}", args.tag or ""):
        raise ValueError("새로운 지정 접두사의 태그가 필요하다")
    if args.original_zip_sha256 != ZIP_SHA or not re.fullmatch(r"[0-9A-Fa-f]{64}", args.source_sha256 or ""):
        raise ValueError("정확한 원 ZIP 및 소스 SHA가 필요하다")
    if not 1 <= args.warmup <= 3 or not 2 <= args.measure <= 10:
        raise ValueError("워밍업 1~3회와 측정 2~10회가 필요하다")
    if os.environ.get("TRITON_INTERPRET") not in (None, "", "0"):
        raise ValueError("실행에서 CPU 인터프리터 대체는 허용하지 않는다")


def assert_receipt(actual, expected):
    if actual["source_sha256"] != expected.upper():
        raise ValueError("검산 이후 소스 바이트가 달라졌다")


def target_path(tag):
    target = ROOT / "test_result/evidence" / tag
    if target.exists() or target.is_symlink():
        raise FileExistsError("기존 namespace는 덮어쓰지 않는다: " + str(target))
    if target.parent.is_symlink() or not target.parent.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("출력 경로가 저장소 밖을 가리킨다")
    return target


def write_new(path, value, guard):
    guard.check("직렬화 전")
    text = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if len(text.encode()) >= MAX_FILE:
        raise ValueError("출력 파일 20MB 상한을 넘었다")
    guard.check("새 파일 쓰기 전")
    with path.open("x", encoding="utf-8") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    guard.check("새 파일 쓰기 후")
    with path.open(encoding="utf-8") as stream:
        restored = json.load(stream)
    guard.check("새 파일 재읽기 후")
    if restored != value:
        raise ValueError("저장·재읽기 결과가 다르다")


def append_terminal(path, value):
    """기존 표지를 바꾸지 않고 뒤의 veto를 보존한다."""
    data = json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n"
    if len(data.encode()) >= 100_000 or (path.exists() and path.stat().st_size + len(data.encode()) >= MAX_FILE):
        raise ValueError("종결 원장 크기 상한을 넘었다")
    with path.open("a", encoding="utf-8") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def emit(value, guard, output=None):
    guard.check("표준출력 전")
    output = output or sys.stdout
    output.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n")
    output.flush()
    guard.check("표준출력 후")


def admission(guard, allowed=()):
    guard.check("GPU 입장 조회 전")
    result = subprocess.run(["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=max(.01, min(5., guard.remaining())))
    guard.check("GPU 입장 조회 후")
    if result.returncode or len(result.stdout) > 100_000:
        raise Incomplete("GPU 입장 조회가 완결되지 않았다: " + result.stderr[:2000])
    pids = []
    for line in result.stdout.splitlines():
        if line.strip():
            if not line.strip().isdigit():
                raise Incomplete("해석할 수 없는 GPU 프로세스 응답")
            pids.append(int(line.strip()))
    foreign = sorted(set(pids) - {os.getpid(), *allowed})
    if foreign:
        raise Incomplete("다른 GPU 계산 프로세스가 있다: " + str(foreign))
    return dict(observed_compute_pids=pids, foreign_compute_pids=foreign)


def import_runtime(guard):
    guard.check("Torch import 전")
    torch = importlib.import_module("torch")
    guard.check("Torch import 후")
    if not torch.cuda.is_available():
        raise Incomplete("실제 CUDA가 없어 실행하지 않았다")
    if torch.cuda.get_device_capability() != (8, 9):
        raise Incomplete("원 커널 대상 SM89와 다르다")
    sys.path.insert(0, str(ARCHIVE))
    loaded = {}
    for name in RUNTIME:
        guard.check("원 의존 소스 import 전")
        key = name[:-3]
        prior = sys.modules.get(key)
        if prior is not None and Path(getattr(prior, "__file__", "")).resolve() != (ARCHIVE / name).resolve():
            raise ValueError("다른 같은 이름의 모듈이 이미 있다: " + key)
        loaded[key] = importlib.import_module(key)
        guard.check("원 의존 소스 import 후")
    if any(n == "tinylm.model" or n.startswith("tinylm.model.") for n in sys.modules):
        raise ValueError("모델 모듈이 이 커널 전용 프로세스에 로딩됐다")
    return torch, loaded


def finite(torch, *values):
    if not all(bool(torch.isfinite(value).all()) for value in values):
        raise FloatingPointError("유한하지 않은 커널 결과")


def primitive_forward(torch, function):
    with torch.no_grad():
        return function()


def exact(torch, actual, expected, label):
    if actual.shape != expected.shape or actual.dtype != expected.dtype or not torch.equal(actual.cpu(), expected.cpu()):
        detail = dict(label=label, actual_shape=list(actual.shape), expected_shape=list(expected.shape),
                      actual_dtype=str(actual.dtype), expected_dtype=str(expected.dtype))
        if actual.shape == expected.shape and actual.numel():
            left, right = actual.detach().double().cpu(), expected.detach().double().cpu()
            finite(torch, left, right)
            detail.update(differing_elements=int(left.ne(right).sum()), max_abs=float((left - right).abs().max()))
        raise NumericMismatch(detail)
    return dict(bitwise_equal=True, elements=actual.numel(), dtype=str(actual.dtype))


def approximation(torch, actual, expected):
    finite(torch, actual, expected)
    delta = actual.double() - expected.double()
    norm = float(expected.double().norm())
    maximum, relative = float(delta.abs().max()), float(delta.norm()) / max(norm, 1e-300)
    if not all(math.isfinite(value) for value in (norm, maximum, relative)):
        raise FloatingPointError("근사차의 집계 수치가 유한하지 않다")
    return dict(max_abs=maximum, relative_l2=relative,
                exact_elements=int(actual.eq(expected).sum()), elements=actual.numel(),
                acceptance_threshold=None, quality_claim=False)


def chosen(tuned):
    config = getattr(tuned, "best_config", None)
    if config is None:
        raise Incomplete("실제 선택한 autotune tile을 회수하지 못했다")
    return dict(kwargs=dict(config.kwargs), num_warps=config.num_warps,
                num_stages=config.num_stages, fallback_used=False)


def measure(torch, fn, guard, *, warmup, rounds):
    """첫 호출·컴파일과 정상 반복을 나누며 이벤트 및 동기 wall을 함께 기록한다."""
    records, output = [], None
    for index in range(1 + warmup + rounds):
        guard.check("측정 전")
        torch.cuda.synchronize()
        before_a, before_r = torch.cuda.memory_allocated(), torch.cuda.memory_reserved()
        prior_a, prior_r = torch.cuda.max_memory_allocated(), torch.cuda.max_memory_reserved()
        torch.cuda.reset_peak_memory_stats()
        start_event, end_event = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
        start = time.perf_counter()
        start_event.record()
        output = fn()
        end_event.record()
        torch.cuda.synchronize()
        elapsed = (time.perf_counter() - start) * 1000.
        guard.check("측정 및 동기화 후")
        records.append(dict(phase="first_call_compile_autotune" if index == 0 else "warmup" if index <= warmup else "measured",
            synchronized_wall_ms=elapsed, cuda_event_interval_ms=start_event.elapsed_time(end_event),
            allocated_before=before_a, reserved_before=before_r,
            peak_allocated_before_reset=prior_a, peak_reserved_before_reset=prior_r,
            allocated_after=torch.cuda.memory_allocated(), reserved_after=torch.cuda.memory_reserved(),
            peak_allocated_absolute=torch.cuda.max_memory_allocated(), peak_reserved_absolute=torch.cuda.max_memory_reserved()))
    return output, dict(samples=records, timing_scope="원 함수·할당을 포함한 호출; 이벤트는 호스트 간격을 포함할 수 있는 GPU 시각 구간",
                        memory_scope="이 단계 진입 때 살아 있던 대조 텐서를 포함한 프로세스 allocator 절대값")


def _subset(torch, count, maximum=8):
    return torch.linspace(0, count - 1, min(maximum, count), device="cuda").long().unique()


def _pack_comparison(torch, actual, expected, rows, *, weight=False):
    q, s, h, lo, sh, sl, bad = actual
    if bool(bad):
        raise FloatingPointError("원 pack이 입력 조건 위반을 보고했다")
    pairs = ((q[rows], expected.rows.codes), (s[rows], expected.rows.scale),
             (h[rows], expected.high), (sh[rows], expected.sh))
    if not weight:
        pairs += ((lo[rows], expected.low), (sl[rows], expected.sl))
    return [exact(torch, a, b, "pack") for a, b in pairs]


def case(torch, mods, m, k, n, args, guard, result=None):
    core, kernels, reuse = (mods[x] for x in ("v12_code_reuse", "v12_kernels", "v11_reuse_kernels"))
    base = mods["v11_int8_backend"]
    result = {} if result is None else result
    result.update(M=m, K=k, N=n, group=GROUP, dtype="torch.bfloat16", phases={},
                  implementation_checks={}, native_approximation={}, complete=False, active_phase="input_allocation")
    result["fixed_pack_launch"] = dict(BLOCK=kernels.triton.next_power_of_2(k), GROUP=GROUP,
        num_warps=8 if k >= 2048 else 4, enable_fp_fusion=False, fallback_used=False)
    guard.check("형상 입력 할당 전")
    generator = torch.Generator(device="cuda").manual_seed(1337 + m + k + n)
    x = torch.randn((m, k), generator=generator, device="cuda", dtype=torch.bfloat16)
    alpha = torch.rand((n, k // GROUP, 1), generator=generator, device="cuda") * .1 + .001
    w = (torch.randint(-1, 2, (n, k // GROUP, GROUP), generator=generator, device="cuda") * alpha).reshape(n, k).bfloat16()
    gy = torch.randn((m, n), generator=generator, device="cuda", dtype=torch.bfloat16)
    versions = (x._version, w._version, gy._version)
    def timed(name, fn):
        result["active_phase"] = name
        value, receipt = measure(torch, fn, guard, warmup=args.warmup, rounds=args.measure)
        result["phases"][name] = receipt
        result["last_completed_phase"] = name
        return value
    def pack(value, weight=False):
        return kernels.pack(value, torch.bfloat16, GROUP, 2, weight, True)
    def forward(px, pw):
        return kernels.forward_gemm(px[2], px[3], px[4], px[5], pw[2], pw[4], 2, GROUP, torch.bfloat16)
    native_y = timed("native_forward_before", lambda: torch.nn.functional.linear(x, w))
    native_dx = timed("native_dx_before", lambda: gy @ w)
    native_dw = timed("native_dw_before", lambda: gy.T @ x)
    def native_pipeline():
        return torch.nn.functional.linear(x, w), gy @ w, gy.T @ x
    timed("native_forward_backward_pipeline_before", native_pipeline)
    # 같은 BF16 값을 FP32 용기에 옮긴 대조다. 실제 학습 master weight는 열지 않는다.
    x_float, w_float = x.float(), w.float()
    converted_x = timed("input_fp32_to_bf16_conversion", lambda: x_float.bfloat16())
    converted_w = timed("weight_fp32_to_bf16_conversion", lambda: w_float.bfloat16())
    result["implementation_checks"]["input_compute_conversion"] = exact(torch, converted_x, x, "입력 compute 변환")
    result["implementation_checks"]["weight_compute_conversion"] = exact(torch, converted_w, w, "가중치 compute 변환")
    px = timed("activation_pack_and_compute_conversion", lambda: pack(x))
    pw = timed("weight_pack_cold", lambda: pack(w, True))
    sx = torch.arange(m, device="cuda") if m == 32 else _subset(torch, m)
    sw = torch.arange(n, device="cuda") if m == 32 else _subset(torch, n)
    ref_x = core.pack_cpu(x[sx].cpu(), torch.bfloat16, GROUP, 2, binary=True)
    ref_w = core.pack_cpu(w[sw].cpu(), torch.bfloat16, GROUP, 2, True, True)
    result["implementation_checks"]["activation_pack"] = _pack_comparison(torch, px, ref_x, sx)
    result["implementation_checks"]["weight_pack"] = _pack_comparison(torch, pw, ref_w, sw, weight=True)
    candidate_y = timed("forward_gemm_update_weight_reuse", lambda: forward(px, pw))
    result["chosen_forward_tile"] = chosen(kernels._forward_tuned)
    reference_y = core.group_forward(ref_x.high, ref_x.low, ref_x.sh, ref_x.sl,
        ref_w.high, ref_w.sh, 2, GROUP, "cpu_int8", torch.bfloat16)
    result["implementation_checks"]["forward_reference"] = exact(torch, candidate_y[sx][:, sw], reference_y, "전방 원 CPU 식")
    result["reference_coverage"] = dict(input_rows=sx.cpu().tolist(), output_rows=sw.cpu().tolist(),
        reduction_axis="전체", sampled_output_only=m != 32,
        integer_reference_operands="원 GPU pack의 코드를 CPU 정수식에 투입; pack 원식의 별도 대조 범위도 이 행 목록에 명시")
    result["native_approximation"]["forward"] = approximation(torch, candidate_y, native_y)
    def backward_pack():
        return reuse.pack_weighted_gradients(gy, px[1], pw[1])
    gx, gw, bad = timed("weighted_gradient_pack", backward_pack)
    if bool(bad):
        raise FloatingPointError("원 gradient pack 조건 위반")
    right_x, right_w = pw[0].T, px[0].T
    def adjoint(a, right):
        return kernels.gradient_gemm(a, right, torch.bfloat16, torch.bfloat16)
    dx = timed("dx_strided_gemm", lambda: adjoint(gx, right_x))
    result["chosen_dx_tile"] = chosen(kernels._gradient_tuned)
    dw = timed("dw_strided_gemm", lambda: adjoint(gw, right_w))
    result["chosen_dw_tile"] = chosen(kernels._gradient_tuned)
    dx_float = timed("dx_bf16_rounding_then_fp32_output", lambda:
        kernels.gradient_gemm(gx, right_x, torch.bfloat16, torch.float32))
    result["chosen_dx_fp32_tile"] = chosen(kernels._gradient_tuned)
    dw_float = timed("dw_bf16_rounding_then_fp32_output", lambda:
        kernels.gradient_gemm(gw, right_w, torch.bfloat16, torch.float32))
    result["chosen_dw_fp32_tile"] = chosen(kernels._gradient_tuned)
    result["implementation_checks"]["dx_fp32_output_rounding"] = exact(torch, dx_float, dx.float(), "dX BF16 뒤 FP32 경계")
    result["implementation_checks"]["dw_fp32_output_rounding"] = exact(torch, dw_float, dw.float(), "dW BF16 뒤 FP32 경계")
    # 명시 복사와 strided 소비를 같은 원 함수로 비교한다. 새 정수곱 식은 만들지 않는다.
    cx = timed("dx_right_explicit_copy", lambda: right_x.contiguous())
    cw = timed("dw_right_explicit_copy", lambda: right_w.contiguous())
    dense_dx = timed("dx_explicit_copy_gemm", lambda: adjoint(gx, cx))
    result["chosen_dx_copied_tile"] = chosen(kernels._gradient_tuned)
    dense_dw = timed("dw_explicit_copy_gemm", lambda: adjoint(gw, cw))
    result["chosen_dw_copied_tile"] = chosen(kernels._gradient_tuned)
    result["implementation_checks"]["transpose_free_dx"] = exact(torch, dx, dense_dx, "전치 없는 dX")
    result["implementation_checks"]["transpose_free_dw"] = exact(torch, dw, dense_dw, "전치 없는 dW")
    # 전체 reduction을 유지한 선택행 CPU 원식은 큰 형상에서도 CPU 대형 행렬곱을 피한다.
    cols = torch.arange(k, device="cuda") if m == 32 else _subset(torch, k)
    gx_ref = base.quantize_rows(gy[sx].cpu().float() * pw[1].cpu()[None, :])
    gw_ref = base.quantize_rows((gy[:, sw].cpu().float() * px[1].cpu()[:, None]).T)
    result["reference_coverage"]["gradient_output_columns"] = cols.cpu().tolist()
    result["implementation_checks"]["gx_codes"] = exact(torch, gx.codes[sx], gx_ref.codes, "dX gradient 코드")
    result["implementation_checks"]["gx_scale"] = exact(torch, gx.scale[sx], gx_ref.scale, "dX gradient scale")
    result["implementation_checks"]["gw_codes"] = exact(torch, gw.codes[sw], gw_ref.codes, "dW gradient 코드")
    result["implementation_checks"]["gw_scale"] = exact(torch, gw.scale[sw], gw_ref.scale, "dW gradient scale")
    result["implementation_checks"]["dx_cpu_reference"] = exact(torch, dx[sx][:, cols],
        core.gradient_cpu(gx_ref, right_x[cols].cpu(), torch.bfloat16, torch.bfloat16), "dX 원 CPU 식")
    result["implementation_checks"]["dw_cpu_reference"] = exact(torch, dw[sw][:, cols],
        core.gradient_cpu(gw_ref, right_w[cols].cpu(), torch.bfloat16, torch.bfloat16), "dW 원 CPU 식")
    result["native_approximation"].update(dx=approximation(torch, dx, native_dx), dw=approximation(torch, dw, native_dw))
    timed("forward_pipeline_cold", lambda: forward(pack(x), pack(w, True)))
    timed("forward_pipeline_update_weight_reuse", lambda: forward(pack(x), pw))
    timed("forward_pipeline_fp32_containers_cold", lambda: forward(pack(x_float), pack(w_float, True)))
    timed("forward_pipeline_fp32_input_update_weight_reuse", lambda: forward(pack(x_float), pw))
    def complete(reuse_weight):
        ap = pack(x)
        wp = pw if reuse_weight else pack(w, True)
        y = forward(ap, wp)
        a, b, bad = reuse.pack_weighted_gradients(gy, ap[1], wp[1])
        return y, adjoint(a, wp[0].T), adjoint(b, ap[0].T), bad
    outputs = timed("forward_backward_pipeline_update_weight_reuse", lambda: complete(True))
    if bool(outputs[-1]):
        raise FloatingPointError("전체 커널 경로의 원 조건 위반")
    cold_outputs = timed("forward_backward_pipeline_weight_pack_cold", lambda: complete(False))
    if bool(cold_outputs[-1]):
        raise FloatingPointError("가중치 pack을 포함한 전체 경로의 원 조건 위반")
    timed("native_forward_backward_pipeline_after", native_pipeline)
    result["pipeline_denominators"] = dict(
        native="BF16 입력·가중치 준비 뒤 전방+dX+dW를 한 호출로 측정; pack 없음",
        candidate_update_weight_reuse="입력 pack·전방·gradient pack·dX·dW를 한 호출로 측정; 가중치 pack은 앞서 준비",
        candidate_weight_pack_cold="입력·가중치 pack·전방·gradient pack·dX·dW를 한 호출로 측정",
        exclusions="모델·STE·optimizer·head·checkpoint 및 학습 master gradient 아님",
        synchronized_wall_sum_is_not_pipeline_ratio=True)
    # 후보 뒤 역순으로 기준선 세 번을 독립 측정해 순서 드리프트를 남긴다.
    timed("native_dw_after", lambda: gy.T @ x)
    timed("native_dx_after", lambda: gy @ w)
    timed("native_forward_after", lambda: torch.nn.functional.linear(x, w))
    if versions != (x._version, w._version, gy._version):
        raise ValueError("측정 중 같은 입력 바이트가 변경됐다")
    result["tensor_payload_bytes"] = dict(x=x.numel()*x.element_size(), w=w.numel()*w.element_size(),
        gy=gy.numel()*gy.element_size(), scope="입력 세 텐서만; 실제 peak는 각 측정의 allocator 절대값")
    result["conversion_scope"] = "BF16 compute operand 기준과 같은 값을 담은 FP32 용기 기준을 분리; 학습 master gradient가 아님"
    result["complete"] = True
    return result


def producer_case(torch, mods, m, args, guard, result=None):
    swiglu, core = mods["v12_swiglu"], mods["v12_code_reuse"]
    result = {} if result is None else result
    result.update(M=m, K=2048, phases={}, complete=False, active_phase="input_allocation")
    result["fixed_producer_launch"] = dict(BLOCK=2048, GROUP=GROUP, num_warps=8,
                                            enable_fp_fusion=False, fallback_used=False)
    guard.check("producer 입력 할당 전")
    generator = torch.Generator(device="cuda").manual_seed(1337 + m)
    g = torch.randn((m, 2048), device="cuda", dtype=torch.bfloat16, generator=generator).requires_grad_()
    u = torch.randn((m, 2048), device="cuda", dtype=torch.bfloat16, generator=generator).requires_grad_()
    dy = torch.randn((m, 2048), device="cuda", dtype=torch.bfloat16, generator=generator)
    phases = result["phases"]
    def timed(name, fn):
        result["active_phase"] = name
        output, phases[name] = measure(torch, fn, guard, warmup=args.warmup, rounds=args.measure)
        result["last_completed_phase"] = name
        return output
    # 전방 원시 연산 두 팔에서 모두 autograd graph 생성을 제외한다.
    primitive = functools.partial(primitive_forward, torch)
    timed("native_swiglu_before", lambda: primitive(lambda: torch.nn.functional.silu(g) * u))
    output = timed("fused_swiglu_pack", lambda: primitive(lambda: swiglu.launch(g, u, GROUP)))
    y, q, scale, h, lo, sh, sl, bad = output
    if bool(bad):
        raise FloatingPointError("원 producer 조건 위반")
    native = primitive(lambda: torch.nn.functional.silu(g) * u)
    ulp = (y.view(torch.int16).int() - native.view(torch.int16).int()).abs()
    ulp = torch.where((y == 0) & (native == 0), 0, ulp)
    finite(torch, y, native)
    worst = int(ulp.max())
    if worst > 1:
        raise NumericMismatch(dict(label="원 v12 producer의 CUDA BF16 ULP", max_bf16_ulps=worst,
                                   original_v12_local_ulp_limit=1, differing_elements=int(y.ne(native).sum())))
    rows = _subset(torch, m)
    ref = core.pack_cpu(y[rows].cpu(), torch.bfloat16, GROUP, 2, binary=True)
    packs = _pack_comparison(torch, (q, scale, h, lo, sh, sl, bad), ref, rows)
    def native_vjp():
        value = torch.nn.functional.silu(g) * u
        return torch.autograd.grad(value, (g, u), dy)
    def fused_vjp():
        value = swiglu._SwiGLU.apply(g, u, "cuda", GROUP)[0]
        return torch.autograd.grad(value, (g, u), dy)
    a = timed("native_forward_vjp", native_vjp)
    b = timed("fused_forward_vjp", fused_vjp)
    checks = [exact(torch, x, z, "SwiGLU 원 VJP") for x, z in zip(a, b)]
    timed("native_swiglu_after", lambda: primitive(lambda: torch.nn.functional.silu(g) * u))
    result.update(pack_checks=packs, vjp_checks=checks,
        native_forward_difference=approximation(torch, y, native), max_bf16_ulps=worst,
        original_v12_local_ulp_limit=1, complete=True,
        primitive_forward_grad_enabled=False, vjp_autograd_measured_separately=True,
        scope="생성·pack·원 pointwise VJP만; SAC·모델·optimizer·언어 품질은 실행하지 않음")
    return result


def observations(torch, mods, args, guard, result=None):
    result = {} if result is None else result
    result.update(cases=[], producers=[], expansion_requested=args.expand, expansion_completed=False,
                  model_created=False, checkpoint_reads=0, checkpoint_writes=0, quality_claim=False, adopted=False)
    for m in ((32, 8192) if args.expand else (32,)):
        for k, n in SHAPES:
            guard.check("다음 형상 전")
            item = {}
            result["cases"].append(item)
            case(torch, mods, m, k, n, args, guard, item)
            gc.collect()
        item = {}
        result["producers"].append(item)
        producer_case(torch, mods, m, args, guard, item)
        gc.collect()
        if m == 32:
            result["canary_complete"] = True
    result["expansion_completed"] = args.expand
    return result


def worker(args):
    if os.environ.get("TINYLM_V12_KERNEL_WORKER") != str(os.getppid()):
        raise ValueError("OS 감독 프로세스를 거치지 않은 worker는 거부한다")
    guard = Guard(args.deadline, args.max_wall_sec, started=float(args._started), reserve=15.)
    target = ROOT / "test_result/evidence" / args.tag
    report = dict(schema="P102A_V12_KERNEL_OBSERVATION_V1", tag=args.tag, status="INCOMPLETE", intended_exit=9,
                  quality_claim=False, adopted=False, model_created=False, checkpoint_reads=0, checkpoint_writes=0)
    torch, code = None, 9
    try:
        pins = source_receipt(guard)
        assert_receipt(pins, args.source_sha256)
        report["sources"] = pins
        report["environment_metadata"] = environment_metadata()
        report["admission"] = admission(guard, allowed=(os.getppid(),))
        torch, mods = import_runtime(guard)
        report["runtime"] = dict(torch=torch.__version__, triton=importlib.import_module("triton").__version__,
                                 device=torch.cuda.get_device_name(), capability=list(torch.cuda.get_device_capability()),
                                 fallback_used=False)
        report["observations"] = {}
        observations(torch, mods, args, guard, report["observations"])
        assert_receipt(source_receipt(guard), args.source_sha256)
        report.update(status="OBSERVATION_COMPLETE_NOT_ADOPTED", intended_exit=0)
        code = 0
    except BaseException as error:
        report.update(status="ERROR_OR_UNSUPPORTED", exception_class=type(error).__name__,
                      exception=str(error), original_traceback=traceback.format_exc(), intended_exit=9)
        if isinstance(error, NumericMismatch):
            report.update(status="IMPLEMENTATION_NUMERICAL_NEGATIVE", numerical_detail=error.detail)
        # cleanup이나 저장이 추가로 실패해도 최초 예외를 원로그에 먼저 보존한다.
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
    finally:
        if torch is not None:
            try:
                gc.collect()
                torch.cuda.synchronize()
                torch.cuda.empty_cache()
                report["cleanup"] = dict(allocated=torch.cuda.memory_allocated(), reserved=torch.cuda.memory_reserved(),
                    peak_allocated_since_last_phase_reset=torch.cuda.max_memory_allocated(),
                    peak_reserved_since_last_phase_reset=torch.cuda.max_memory_reserved(),
                                          scope="원형 모듈은 남지만 커널 관측 함수의 지역 텐서는 해제한 프로세스")
            except BaseException as error:
                report["cleanup_error"] = dict(exception_class=type(error).__name__, exception=str(error),
                                               original_traceback=traceback.format_exc())
                report.update(status="ERROR_OR_UNSUPPORTED", intended_exit=9)
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()
                code = 9
        guard.check("cleanup 후")
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        write_new(target / "report.json", report, guard)
        emit(dict(status=report["status"], intended_exit=code), guard)
    return code


def decide(report, actual_exit):
    if (type(actual_exit) is not int or actual_exit != 0 or report.get("intended_exit") != 0
            or report.get("status") != "OBSERVATION_COMPLETE_NOT_ADOPTED"
            or report.get("quality_claim") is not False or report.get("adopted") is not False):
        return 9
    observations_ = report.get("observations", {})
    expanded = observations_.get("expansion_requested")
    if type(expanded) is not bool or observations_.get("expansion_completed") is not expanded:
        return 9
    expected_m = [32, 8192] if expanded else [32]
    if (not observations_.get("canary_complete") or len(observations_.get("cases", ())) != 3 * len(expected_m)
            or any(not item.get("complete") for item in observations_.get("cases", ()))
            or len(observations_.get("producers", ())) != len(expected_m)
            or any(not item.get("complete") for item in observations_.get("producers", ()))):
        return 9
    if [(item.get("M"), item.get("K"), item.get("N")) for item in observations_["cases"]] != [
            (m, k, n) for m in expected_m for k, n in SHAPES]:
        return 9
    if [item.get("M") for item in observations_["producers"]] != expected_m:
        return 9
    if report.get("cleanup_error") or report.get("exception_class"):
        return 9
    return 0


def process_tools():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    # 모델 없는 기존 소유 Popen·그룹 종료 계약을 그대로 재사용한다.
    return importlib.import_module("scripts.codex_smoke")


def run_owned_worker(command, env, logfile, guard, *, factory=None, tools=None, state=None):
    tools = process_tools() if tools is None else tools
    def monitor():
        guard.check("소유 worker 감독")
        if guard.remaining() <= 8.:
            raise tools.BudgetExpired("종결·그룹 정리 예약에 도달했다")
        if logfile.stat().st_size >= MAX_FILE:
            raise ValueError("worker 원로그 크기 상한을 넘었다")
    previous = signal.getsignal(signal.SIGTERM)
    installed = previous != signal.SIG_IGN
    def interrupted(signum, frame):
        raise KeyboardInterrupt("소유 worker의 종료 요청")
    state = {} if state is None else state
    try:
        if installed:
            signal.signal(signal.SIGTERM, interrupted)
        current = guard.clock()
        return tools.run_child(command, root=ROOT, env=env,
            work_expires=current + guard.remaining() - 8.,
            expires=current + guard.remaining() - 3., clock=guard.clock,
            monitor=monitor, process_factory=factory, state_sink=state)
    except BaseException as error:
        state.update(adapter_error=dict(exception_class=type(error).__name__, exception=str(error),
                                        original_traceback=traceback.format_exc()), unsafe_process_state=True)
        raise
    finally:
        if installed:
            try:
                signal.signal(signal.SIGTERM, previous)
            except BaseException as error:
                state.update(adapter_cleanup_error=dict(exception_class=type(error).__name__, exception=str(error),
                    original_traceback=traceback.format_exc()), unsafe_process_state=True)


def worker_limits(owner_pid):
    # worker 및 원 컴파일러가 단일 파일 20MB 상한을 OS에서 넘을 수 없게 한다.
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_FILE - 1, MAX_FILE - 1))
    # 부모의 강제 종료 때 worker 본인을 중단한다. compiler 그룹 정리의 대체 근거는 아니다.
    library = ctypes.CDLL(None, use_errno=True)
    if library.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "부모 종료 시 worker 중단 설정 실패")
    if os.getppid() != owner_pid:
        os.kill(os.getpid(), signal.SIGKILL)


def finalize_disposition(terminal, summary, guard):
    code = summary["intended_supervisor_exit"]
    try:
        guard.check("최종 출력 전")
        emit(summary, guard)
        append_terminal(terminal, dict(event="FINAL_DISPOSITION", intended_supervisor_exit=code,
            actual_worker_exit=summary["actual_worker_exit"], at=datetime.now(timezone.utc).isoformat()))
        guard.check("최종 표지 저장 후")
    except BaseException as caught:
        code = 9
        append_terminal(terminal, dict(event="TERMINAL_VETO", intended_supervisor_exit=9,
            actual_worker_exit=summary["actual_worker_exit"], exception_class=type(caught).__name__,
            exception=str(caught), at=datetime.now(timezone.utc).isoformat()))
    return code


def supervise(args, guard):
    validate_args(args)
    pins = source_receipt(guard)
    assert_receipt(pins, args.source_sha256)
    target = target_path(args.tag)
    guard.check("namespace 생성 전")
    target.mkdir()
    write_new(target / "admission.json", dict(sources=pins, environment=environment_metadata(),
        deadline=args.deadline, max_wall_sec=args.max_wall_sec, os_supervisor=True,
        started_monotonic=guard.started, worker_publication_reserve_sec=15), guard)
    terminal = target / "terminal.jsonl"
    supervision = {}
    code, actual_exit, error = 9, None, None
    try:
        command = [sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()), "--_worker",
            "--tag", args.tag, "--deadline", args.deadline, "--max-wall-sec", str(args.max_wall_sec),
            "--source-sha256", args.source_sha256, "--original-zip-sha256", args.original_zip_sha256,
            "--warmup", str(args.warmup), "--measure", str(args.measure), "--_started", str(guard.started)]
        if args.expand:
            command.append("--expand")
        env = dict(os.environ, TINYLM_V12_KERNEL_WORKER=str(os.getpid()), PYTHONDONTWRITEBYTECODE="1",
                   TRITON_CACHE_DIR=str(target / "triton_cache"), TORCHINDUCTOR_CACHE_DIR=str(target / "torch_cache"))
        with (target / "worker.log").open("xb") as stream:
            def factory(argv, **options):
                return subprocess.Popen(argv, **options, stdout=stream, stderr=subprocess.STDOUT,
                    preexec_fn=functools.partial(worker_limits, os.getpid()))
            run_owned_worker(command, env, target / "worker.log", guard, factory=factory, state=supervision)
            actual_exit = supervision.get("returncode")
        if (supervision.get("status") != "COMPLETE" or supervision.get("unsafe_process_state")
                or supervision.get("process_started") is not True):
            raise Incomplete("소유 프로세스 그룹의 정상 종결을 확인하지 못했다: " + str(supervision.get("error")))
        path = target / "report.json"
        if path.stat().st_size >= MAX_FILE:
            raise ValueError("결과 크기 상한을 넘었다")
        report = json.loads(path.read_text(encoding="utf-8"))
        guard.check("보고서 재읽기 후")
        assert_receipt(report.get("sources", {}), args.source_sha256)
        assert_receipt(source_receipt(guard), args.source_sha256)
        code = decide(report, actual_exit)
    except BaseException as caught:
        error = dict(exception_class=type(caught).__name__, exception=str(caught), original_traceback=traceback.format_exc())
    finally:
        actual_exit = supervision.get("returncode", actual_exit)
        append_terminal(terminal, dict(event="WORKER_ACTUAL_EXIT", actual_worker_exit=actual_exit,
            intended_supervisor_exit=code, error=error, supervision=supervision,
            at=datetime.now(timezone.utc).isoformat()))
    return finalize_disposition(terminal, dict(tag=args.tag,
        status="OBSERVATION_COMPLETE_NOT_ADOPTED" if code == 0 else "INCOMPLETE_OR_ERROR",
        actual_worker_exit=actual_exit, intended_supervisor_exit=code, output=str(target)), guard)


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    modes = result.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check-only", action="store_true")
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--_worker", action="store_true", help=argparse.SUPPRESS)
    result.add_argument("--tag")
    result.add_argument("--deadline")
    result.add_argument("--max-wall-sec", type=int)
    result.add_argument("--source-sha256")
    result.add_argument("--original-zip-sha256")
    result.add_argument("--expand", action="store_true")
    result.add_argument("--warmup", type=int, default=1)
    result.add_argument("--measure", type=int, default=2)
    result.add_argument("--_started", help=argparse.SUPPRESS)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.check_only:
            receipt = source_receipt()
            print(json.dumps(dict(status="CHECK_ONLY_SOURCE_VERIFIED", sources=receipt,
                environment=environment_metadata(), torch_imported="torch" in sys.modules,
                cuda_executed=False, model_created=False, files_written=0), ensure_ascii=False, allow_nan=False))
            return 0
        validate_args(args)
        guard = Guard(args.deadline, args.max_wall_sec, started=STARTED)
        return worker(args) if args._worker else supervise(args, guard)
    except BaseException as error:
        print(json.dumps(dict(status="INCOMPLETE_OR_ERROR", intended_exit=9,
            exception_class=type(error).__name__, exception=str(error)), ensure_ascii=False), file=sys.stderr, flush=True)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
