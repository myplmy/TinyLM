"""v12의 동일 분모 세 파이프라인과 SwiGLU+pack 관측기. 별도 OS timeout 900초가 필요하다."""
from __future__ import annotations

import time

STARTED = time.monotonic()

import contextlib
import gc
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import traceback
import types

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = Path(__file__).resolve()
ORIGINAL_DRIVER = ROOT / "scripts/diag_p102a_v12_kernels.py"
ORIGINAL_DRIVER_SHA = "590EF52CEA9722292F58B5572FB6CAAF6DDD102C649975262BA85DB3D243B972"
ORIGINAL_SOURCE_SHA = "D21DC21C647516A13B7FADCA87DAA4893943A59EC7DCAC8F46B9374BF5EA004B"
EVIDENCE = {
    "handoff/audit/WIP_20261025_V12_KERNEL_ROOT_CLOSURE.json":
        "19703B2DB830E2EBFC38ECB9D4078C12B672BA27EE05352009BD6CB9513CCE0A",
    "test_result/evidence/p102a_v12_kernel_v1_s1337_oct25a/report.json":
        "BB3B82110C7EF4EC1BC19D8111C1FF78E423BD50190857BB69ACE00D26042253",
    "test_result/evidence/p102a_v12_kernel_v1_s1337_oct25a/terminal.jsonl":
        "39461124BF61001E7AFD49748F6DF060E85F0D534D5A7A8E0DE623CCB8ADA67A",
}
OWN = ("scripts/diag_p102a_v12_matched_pipeline.py", "scripts/test_diag_p102a_v12_matched_pipeline.py")
PREFIX = "p102a_v12_matched_pipeline_v1_s1337_"
CONTRACT = "P102A_V12_MATCHED_PIPELINE_V1"
GROUP = 128
MAX_WALL = 870
WARMUP = 2
ROUNDS = 5
PIPELINE_PHASES = (
    "native_pipeline_before", "int_full_weight_pack_cold", "hybrid_weight_pack_cold",
    "hybrid_update_weight_reuse", "int_full_update_weight_reuse", "native_pipeline_after",
)
PRODUCER_PHASES = (
    "native_swiglu_pack_before", "fused_swiglu_pack", "native_swiglu_pack_after",
    "native_swiglu_pack_vjp", "fused_swiglu_pack_vjp",
)
_ORIGINAL = None
_LINK_ACTIVE = False


class Original:
    """정확 로컬 원형의 공개 모듈과 분리된 private 함수 묶음이다."""

    def __init__(self, module):
        self.module = module
        for name in ("source_receipt", "environment_metadata", "parser", "validate_args", "decide",
                     "Guard", "finalize_disposition"):
            setattr(self, name, getattr(module, name))


def original():
    global _ORIGINAL
    if ORIGINAL_DRIVER.is_symlink() or ORIGINAL_DRIVER.resolve() != ORIGINAL_DRIVER:
        raise ValueError("원 진단기의 정확 로컬 경로가 아니다")
    if ORIGINAL_DRIVER.stat().st_size >= 20_000_000:
        raise ValueError("원 진단기의 20MB 상한을 넘었다")
    raw = ORIGINAL_DRIVER.read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != ORIGINAL_DRIVER_SHA:
        raise ValueError("동결한 원 진단기 SHA가 달라졌다")
    if _ORIGINAL is None:
        spec = importlib.util.spec_from_file_location("_p102a_v12_matched_original", ORIGINAL_DRIVER)
        module = importlib.util.module_from_spec(spec)
        # 원형에는 module 등록을 요구하는 dataclass가 없다. sys.modules와 sys.path는 바꾸지 않는다.
        exec(compile(raw, str(ORIGINAL_DRIVER), "exec"), module.__dict__)
        _ORIGINAL = Original(module)
    return _ORIGINAL


def check_prior_evidence(closure, report, events):
    """과거 종료0을 현재 실행 성공이나 새 채택으로 승격하지 않는다."""
    for value in (closure.get("actual_root_exit"), closure.get("actual_worker_exit")):
        if type(value) is not int or value != 0:
            raise ValueError("과거 실제 종료가 정상0이 아니다")
    if (closure.get("source_sha256") != ORIGINAL_SOURCE_SHA
            or closure.get("source_receipt_unchanged") is not True
            or closure.get("status") != "OBSERVATION_COMPLETE_NOT_ADOPTED"
            or closure.get("quality_claim") is not False or closure.get("adopted") is not False):
        raise ValueError("과거 root 종결 계약이 다르다")
    if (report.get("sources", {}).get("source_sha256") != ORIGINAL_SOURCE_SHA
            or report.get("status") != "OBSERVATION_COMPLETE_NOT_ADOPTED"
            or type(report.get("intended_exit")) is not int or report["intended_exit"] != 0
            or report.get("quality_claim") is not False or report.get("adopted") is not False
            or report.get("model_created") is not False
            or report.get("checkpoint_reads") != 0 or report.get("checkpoint_writes") != 0):
        raise ValueError("과거 보고서의 원형·종결 계약이 다르다")
    if (not events or events[-1].get("event") != "FINAL_DISPOSITION"
            or any(item.get("event") == "TERMINAL_VETO" for item in events)):
        raise ValueError("과거 종결에 거부 표지가 있거나 마지막 표지가 없다")
    actual = [item for item in events if item.get("event") == "WORKER_ACTUAL_EXIT"]
    if len(actual) != 1 or actual[0].get("error") is not None:
        raise ValueError("과거 실제 worker 종료 기록이 유일하지 않거나 오류가 있다")
    for item in (actual[0], events[-1]):
        if type(item.get("actual_worker_exit")) is not int or item["actual_worker_exit"] != 0:
            raise ValueError("과거 worker 실제 종료가 정상0이 아니다")
        if type(item.get("intended_supervisor_exit")) is not int or item["intended_supervisor_exit"] != 0:
            raise ValueError("과거 supervisor 종료 판정이 정상0이 아니다")


def source_receipt(guard=None, *, owner=None):
    owner = owner or original()
    base = owner.module
    upstream = owner.source_receipt(guard)
    base.assert_receipt(upstream, ORIGINAL_SOURCE_SHA)
    if base.identity({key: value for key, value in upstream.items() if key != "source_sha256"}) != ORIGINAL_SOURCE_SHA:
        raise ValueError("원 source identity의 내부 필드가 일치하지 않는다")
    contents = {}
    for name, expected in EVIDENCE.items():
        if guard:
            guard.check("과거 종결 증거 읽기 전")
        path = base.safe_file(ROOT / name)
        if path.stat().st_size >= base.MAX_FILE:
            raise ValueError("과거 증거 파일의 20MB 상한을 넘었다")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest().upper() != expected:
            raise ValueError("과거 종결 증거 SHA가 달라졌다: " + name)
        contents[name] = raw.decode("utf-8")
        if guard:
            guard.check("과거 종결 증거 읽기 후")
    names = tuple(EVIDENCE)
    closure, report = (json.loads(contents[name]) for name in names[:2])
    events = [json.loads(line) for line in contents[names[2]].splitlines() if line.strip()]
    if closure.get("report_sha256") != EVIDENCE[names[1]] or closure.get("terminal_sha256") != EVIDENCE[names[2]]:
        raise ValueError("root 종결과 보고서·terminal의 SHA 연결이 다르다")
    check_prior_evidence(closure, report, events)
    own = {}
    for name in OWN:
        path = base.safe_file(ROOT / name)
        if path.stat().st_size >= base.MAX_FILE:
            raise ValueError("새 소스 파일의 20MB 상한을 넘었다")
        own[name] = base.digest(path, guard)
    material = dict(contract=CONTRACT, original_sources=upstream, prior_evidence_sha256=EVIDENCE,
                    companion_source_sha256=own)
    return dict(**material, source_sha256=base.identity(material))


def validate_args(args, owner):
    owner.validate_args(args)
    if (type(args.max_wall_sec) is not int or not 60 <= args.max_wall_sec <= MAX_WALL
            or args.warmup != WARMUP or args.measure != ROUNDS):
        raise ValueError("내부 최대870초·워밍업2·측정5 계약이 필요하다")


def metadata(owner):
    result = owner.environment_metadata()
    result.update(companion_contract=CONTRACT, external_os_timeout_required=True,
                  external_os_timeout_sec=900, internal_max_wall_sec=MAX_WALL,
                  original_driver_sha256=ORIGINAL_DRIVER_SHA,
                  original_source_sha256=ORIGINAL_SOURCE_SHA,
                  bootstrap=dict(entrypoint=str(ENTRYPOINT), private_original_module=owner.module.__name__,
                                 observations_module=observations.__module__, source_module=source_receipt.__module__,
                                 shared_public_original_module_modified=False,
                                 private_globals_restore_contract="호출 뒤 finally에서 원 객체 복원"),
                  parent_sigkill_all_descendants_cleanup_guaranteed=False)
    return result


def parser(owner):
    result = owner.parser()
    result.description = __doc__
    result.set_defaults(warmup=WARMUP, measure=ROUNDS, max_wall_sec=MAX_WALL)
    return result


@contextlib.contextmanager
def linked(owner=None, *, state=None):
    """원 worker와 supervisor가 새 프로세스에서도 이 진입점을 다시 호출하게 연결한다."""
    global _LINK_ACTIVE
    if _LINK_ACTIVE:
        raise RuntimeError("중첩된 private 진단기 연결은 거부한다")
    owner = owner or original()
    base = owner.module
    replacements = dict(__file__=str(ENTRYPOINT), STARTED=STARTED, PREFIX=PREFIX,
                        source_receipt=lambda guard=None: source_receipt(guard, owner=owner),
                        environment_metadata=lambda: metadata(owner), parser=lambda: parser(owner),
                        validate_args=lambda args: validate_args(args, owner),
                        observations=lambda *args, **kwargs: observations(*args, **kwargs, base=base),
                        decide=lambda report, actual_exit: decide(report, actual_exit, owner))
    if state is not None:
        state["guards"] = []

        def tracked_guard(*args, **kwargs):
            guard = owner.Guard(*args, **kwargs)
            state["guards"].append(guard)
            return guard

        def deferred_publication(terminal, summary, guard):
            if "publication" in state:
                raise RuntimeError("최종 종결 게시가 두 번 요청됐다")
            state["publication"] = (terminal, dict(summary), guard)
            return summary["intended_supervisor_exit"]

        # 복원 작업까지 시간창에 청구한 뒤 원 finalizer를 그대로 호출한다.
        replacements.update(Guard=tracked_guard, finalize_disposition=deferred_publication)
    saved = {name: getattr(base, name) for name in replacements}
    _LINK_ACTIVE = True
    try:
        for name, value in replacements.items():
            setattr(base, name, value)
        yield base
    finally:
        for name, value in reversed(tuple(saved.items())):
            setattr(base, name, value)
        _LINK_ACTIVE = False


def pack_operand(torch, mods, value, mode, weight=False):
    if mode not in ("int_full", "hybrid"):
        raise ValueError("원형의 INT 전방 또는 native 전방 모드가 필요하다")
    terms = 2 if mode == "int_full" else 0
    return mods["v12_kernels"].pack(value, torch.bfloat16, GROUP, terms, weight, terms == 2)


def pipeline(torch, mods, x, w, dy, mode, weight_pack=None, *, tiles=None, base=None):
    """원 연산을 연결할 뿐 새 정수곱·미분식·허용차를 정의하지 않는다."""
    if mode == "native":
        return torch.nn.functional.linear(x, w), dy @ w, dy.T @ x, ()
    ap = pack_operand(torch, mods, x, mode)
    wp = weight_pack if weight_pack is not None else pack_operand(torch, mods, w, mode, True)
    kernels = mods["v12_kernels"]
    if mode == "int_full":
        y = kernels.forward_gemm(ap[2], ap[3], ap[4], ap[5], wp[2], wp[4], 2, GROUP, torch.bfloat16)
        if tiles is not None:
            tiles["forward"] = base.chosen(kernels._forward_tuned)
    else:
        y = torch.nn.functional.linear(x, w)
    gx, gw, bad = mods["v11_reuse_kernels"].pack_weighted_gradients(dy, ap[1], wp[1])
    dx = kernels.gradient_gemm(gx, wp[0].T, torch.bfloat16, torch.bfloat16)
    if tiles is not None:
        tiles["dx"] = base.chosen(kernels._gradient_tuned)
    dw = kernels.gradient_gemm(gw, ap[0].T, torch.bfloat16, torch.bfloat16)
    if tiles is not None:
        tiles["dw"] = base.chosen(kernels._gradient_tuned)
    # scalar bad의 호스트 전송은 측정 한 호출 안에 넣지 않는다.
    return y, dx, dw, (ap[-1], wp[-1], bad)


def check_outputs(torch, base, output):
    if len(output) != 4:
        raise ValueError("전방·dX·dW·원 flag 출력이 필요하다")
    base.finite(torch, *output[:3])
    if any(bool(flag) for flag in output[3]):
        raise FloatingPointError("원형 pack의 입력 조건 위반")


def cpu_reference(torch, mods, x, w, dy):
    """같은 입력의 원 _Linear CPU 전방·VJP를 모델 없이 직접 호출한다."""
    core = mods["v12_code_reuse"]
    cx, cw = x.detach().cpu().requires_grad_(), w.detach().cpu().requires_grad_()
    session = types.SimpleNamespace(backend="cpu_int8", terms=2, group=GROUP, backward_mm=0,
                                    check=lambda: None)
    session.activation = lambda value, compute: core.pack_cpu(value, compute, GROUP, 2, binary=True)
    session.weight_pack = lambda value, key, compute: core.pack_cpu(value, compute, GROUP, 2, True, True)
    y = core._Linear.apply(cx, cw, session, "matched_cpu_reference")
    dx, dw = torch.autograd.grad(y, (cx, cw), dy.detach().cpu())
    return y.detach(), dx, dw


def linear_case(torch, mods, m, k, n, args, guard, result=None, *, base):
    result = {} if result is None else result
    result.update(M=m, K=k, N=n, group=GROUP, dtype="torch.bfloat16", phases={},
                  implementation_checks={}, native_approximation={}, complete=False)
    result["fixed_pack_launch"] = dict(BLOCK=mods["v12_kernels"].triton.next_power_of_2(k), GROUP=GROUP,
        num_warps=8 if k >= 2048 else 4, enable_fp_fusion=False, fallback_used=False,
        int_terms=2, hybrid_terms=0)
    guard.check("동일 입력 할당 전")
    generator = torch.Generator(device="cuda").manual_seed(1337 + m + k + n)
    x = torch.randn((m, k), generator=generator, device="cuda", dtype=torch.bfloat16)
    alpha = torch.rand((n, k // GROUP, 1), generator=generator, device="cuda") * .1 + .001
    w = (torch.randint(-1, 2, (n, k // GROUP, GROUP), generator=generator, device="cuda") * alpha).reshape(n, k).bfloat16()
    dy = torch.randn((m, n), generator=generator, device="cuda", dtype=torch.bfloat16)
    versions = (x._version, w._version, dy._version)

    def timed(name, callback):
        result["active_phase"] = name
        value, receipt = base.measure(torch, callback, guard, warmup=args.warmup, rounds=args.measure)
        result["phases"][name] = receipt
        result["last_completed_phase"] = name
        return value

    outputs = {}
    outputs[PIPELINE_PHASES[0]] = timed(PIPELINE_PHASES[0], lambda: pipeline(torch, mods, x, w, dy, "native"))
    prepared = {}
    for mode in ("int_full", "hybrid"):
        prepared[mode] = timed(mode + "_weight_pack_preparation", lambda mode=mode: pack_operand(torch, mods, w, mode, True))
        if bool(prepared[mode][-1]):
            raise FloatingPointError("원형 가중치 pack 조건 위반")
    for name, mode, reuse in ((PIPELINE_PHASES[1], "int_full", False), (PIPELINE_PHASES[2], "hybrid", False),
                             (PIPELINE_PHASES[3], "hybrid", True), (PIPELINE_PHASES[4], "int_full", True)):
        outputs[name] = timed(name, lambda mode=mode, reuse=reuse:
            pipeline(torch, mods, x, w, dy, mode, prepared[mode] if reuse else None))
        check_outputs(torch, base, outputs[name])
    outputs[PIPELINE_PHASES[-1]] = timed(PIPELINE_PHASES[-1], lambda: pipeline(torch, mods, x, w, dy, "native"))
    check_outputs(torch, base, outputs[PIPELINE_PHASES[0]])
    check_outputs(torch, base, outputs[PIPELINE_PHASES[-1]])
    checks = result["implementation_checks"]
    native, integers, hybrid = (outputs[PIPELINE_PHASES[index]] for index in (0, 4, 3))
    checks["native_before_after"] = [base.exact(torch, a, b, "native 두 독립 측정")
        for a, b in zip(native[:3], outputs[PIPELINE_PHASES[-1]][:3])]
    for name, canonical in ((PIPELINE_PHASES[1], integers), (PIPELINE_PHASES[2], hybrid)):
        checks[name + "_reuse_exact"] = [base.exact(torch, a, b, "cold와 reuse 원 구현")
            for a, b in zip(outputs[name][:3], canonical[:3])]
    checks["hybrid_forward_native"] = base.exact(torch, hybrid[0], native[0], "hybrid native 전방")
    checks["hybrid_gradients_original_int"] = [base.exact(torch, a, b, "hybrid 원 INT gradient")
        for a, b in zip(hybrid[1:3], integers[1:3])]
    ap_int, ap_hybrid = (pack_operand(torch, mods, x, mode) for mode in ("int_full", "hybrid"))
    checks["same_row_codes_and_scales"] = [base.exact(torch, a, b, "terms0/2 행 코드와 scale")
        for left, right in ((ap_int, ap_hybrid), (prepared["int_full"], prepared["hybrid"]))
        for a, b in zip(left[:2], right[:2])]
    result["full_cpu_reference"] = m == 32
    if m == 32:
        guard.check("M32 원 CPU 식 전수 대조 전")
        reference = cpu_reference(torch, mods, x, w, dy)
        checks["full_original_cpu_reference"] = [base.exact(torch, a, b, "같은 입력의 원 _Linear CPU 식")
            for a, b in zip(integers[:3], reference)]
        guard.check("M32 원 CPU 식 전수 대조 후")
    result["chosen_tiles"] = {}
    for mode in ("int_full", "hybrid"):
        tile = {}
        checked = pipeline(torch, mods, x, w, dy, mode, prepared[mode], tiles=tile, base=base)
        check_outputs(torch, base, checked)
        result["chosen_tiles"][mode] = tile
    result["chosen_tile_scope"] = "동일 형상·dtype·stride의 고정 autotune cache에서 별도 호출로 회수; 이 호출을 정상 반복 시간에 더하지 않음"
    for mode, value in (("int_full", integers), ("hybrid", hybrid)):
        result["native_approximation"][mode] = {name: base.approximation(torch, a, b)
            for name, a, b in zip(("forward", "dx", "dw"), value[:3], native[:3])}
    if versions != (x._version, w._version, dy._version):
        raise ValueError("측정 중 동일 입력의 버전이 바뀌었다")
    result["pipeline_denominators"] = dict(
        native="동일 BF16 입력·가중치·dy의 F.linear+dX+dW 한 호출; pack 없음",
        int_full="원 terms2 block2_pow2 pack+원 전방+weighted gradient pack+dX+dW 한 호출",
        hybrid="원 native 모드 terms0 행 pack+F.linear+동일 weighted gradient pack+dX+dW 한 호출",
        weight_pack_cold="입력과 가중치 pack 모두 포함; 디스크·모델·장치 캐시 전체 cold를 뜻하지 않음",
        update_weight_reuse="입력 pack 포함; 원 가중치 pack을 같은 update 안에서 재사용하는 분모",
        exclusions="모델·STE·AMP master gradient fan-in·optimizer·head·checkpoint·학습 품질을 실행하지 않음",
        memory="살아 있는 native·INT·hybrid 참조 텐서를 포함한 allocator 절대값; 모델 VRAM 효과 아님",
        first_call="새 함수의 첫 호출; 앞선 원 canary나 pack 준비에서 컴파일한 커널은 재사용 가능",
        synchronized_wall_sum_is_not_pipeline_ratio=True)
    result["weight_pack_payload_bytes"] = {mode: sum({value.untyped_storage().data_ptr():
        value.untyped_storage().nbytes() for value in packed}.values()) for mode, packed in prepared.items()}
    result["complete"] = True
    return result


def producer_forward(torch, mods, g, u, fused):
    with torch.no_grad():
        if fused:
            return mods["v12_swiglu"].launch(g, u, GROUP)
        y = torch.nn.functional.silu(g) * u
        return (y, *mods["v12_kernels"].pack(y, torch.bfloat16, GROUP, 2, False, True))


def producer_vjp(torch, mods, g, u, dy, fused):
    if fused:
        output = mods["v12_swiglu"]._SwiGLU.apply(g, u, "cuda", GROUP)
        value, flag = output[0], output[-1]
    else:
        value = torch.nn.functional.silu(g) * u
        with torch.no_grad():
            flag = mods["v12_kernels"].pack(value.detach(), torch.bfloat16, GROUP, 2, False, True)[-1]
    return torch.autograd.grad(value, (g, u), dy), flag


def producer_ulp(torch, base, actual, expected):
    if actual.dtype != torch.bfloat16 or expected.dtype != torch.bfloat16 or actual.shape != expected.shape:
        raise ValueError("원 producer의 동일 BF16 형상이 필요하다")
    base.finite(torch, actual, expected)
    ulp = (actual.view(torch.int16).int() - expected.view(torch.int16).int()).abs()
    ulp = torch.where((actual == 0) & (expected == 0), 0, ulp)
    worst = int(ulp.max())
    if worst > 1:
        raise base.NumericMismatch(dict(label="원 producer BF16 ULP", max_bf16_ulps=worst,
                                       original_v12_local_ulp_limit=1))
    return worst


def producer_case(torch, mods, m, args, guard, result=None, *, base):
    result = {} if result is None else result
    result.update(M=m, K=2048, group=GROUP, phases={}, complete=False, implementation_checks={})
    guard.check("동일 producer 입력 할당 전")
    generator = torch.Generator(device="cuda").manual_seed(1337 + m)
    g = torch.randn((m, 2048), generator=generator, device="cuda", dtype=torch.bfloat16).requires_grad_()
    u = torch.randn((m, 2048), generator=generator, device="cuda", dtype=torch.bfloat16).requires_grad_()
    dy = torch.randn((m, 2048), generator=generator, device="cuda", dtype=torch.bfloat16)
    versions = (g._version, u._version, dy._version)

    def timed(name, callback):
        result["active_phase"] = name
        value, receipt = base.measure(torch, callback, guard, warmup=args.warmup, rounds=args.measure)
        result["phases"][name] = receipt
        result["last_completed_phase"] = name
        return value

    native = timed(PRODUCER_PHASES[0], lambda: producer_forward(torch, mods, g, u, False))
    fused = timed(PRODUCER_PHASES[1], lambda: producer_forward(torch, mods, g, u, True))
    after = timed(PRODUCER_PHASES[2], lambda: producer_forward(torch, mods, g, u, False))
    for output in (native, fused, after):
        base.finite(torch, *output[:-1])
        if bool(output[-1]):
            raise FloatingPointError("원 producer pack의 입력 조건 위반")
        if output[0].requires_grad:
            raise ValueError("전방 원시 연산에서 autograd graph가 생성됐다")
    y, reference = fused[0], native[0]
    worst = producer_ulp(torch, base, y, reference)
    checks = result["implementation_checks"]
    checks["native_before_after"] = [base.exact(torch, a, b, "unfused producer 독립 두 측정")
                                      for a, b in zip(native, after)]
    packed_y = mods["v12_kernels"].pack(y, torch.bfloat16, GROUP, 2, False, True)
    if bool(packed_y[-1]):
        raise FloatingPointError("fused 출력의 원 pack 조건 위반")
    checks["fused_pack_own_y_exact"] = [base.exact(torch, a, b, "fused 자신의 y와 원 pack")
                                      for a, b in zip(fused[1:], packed_y)]
    rows = torch.arange(m, device="cuda") if m == 32 else base._subset(torch, m)
    cpu_pack = mods["v12_code_reuse"].pack_cpu(y[rows].cpu(), torch.bfloat16, GROUP, 2, binary=True)
    checks["original_cpu_pack"] = base._pack_comparison(torch, fused[1:], cpu_pack, rows)
    a = timed(PRODUCER_PHASES[3], lambda: producer_vjp(torch, mods, g, u, dy, False))
    b = timed(PRODUCER_PHASES[4], lambda: producer_vjp(torch, mods, g, u, dy, True))
    if bool(a[1]) or bool(b[1]):
        raise FloatingPointError("별도 VJP의 원 pack 조건 위반")
    base.finite(torch, *a[0], *b[0])
    checks["original_vjp_exact"] = [base.exact(torch, left, right, "원 SwiGLU VJP") for left, right in zip(a[0], b[0])]
    result["native_forward_difference"] = base.approximation(torch, y, reference)
    result["cross_arm_pack_difference"] = {name: base.approximation(torch, left, right)
        for name, left, right in zip(("row_codes", "row_scale", "high", "low", "high_scale", "low_scale"), fused[1:7], native[1:7])}
    result.update(max_bf16_ulps=worst, original_v12_local_ulp_limit=1,
                  primitive_forward_grad_enabled=False, vjp_autograd_measured_separately=True,
                  pack_cpu_reference_rows=rows.cpu().tolist(),
                  fixed_producer_launch=dict(BLOCK=2048, GROUP=GROUP, num_warps=8, enable_fp_fusion=False, fallback_used=False),
                  denominator="양쪽 모두 동일 y와 7개 pack 출력을 반환; native pointwise만의 시간과 나누지 않음",
                  vjp_denominator="양쪽 모두 pointwise+동일 pack+원 pointwise VJP; 별도 계측",
                  numerical_contract="전방 원 BF16 1ULP·finite, 자신의 y에 대한 pack exact, 원 VJP exact; 두 팔 간 pack 차는 채택 문턱 없는 기술 수치")
    if versions != (g._version, u._version, dy._version):
        raise ValueError("producer 측정 중 동일 입력의 버전이 바뀌었다")
    result["complete"] = True
    return result


def observations(torch, mods, args, guard, result=None, *, base):
    result = {} if result is None else result
    result.update(companion_contract=CONTRACT, cases=[], producers=[], canary_complete=False,
                  expansion_requested=args.expand, expansion_completed=False,
                  model_created=False, checkpoint_reads=0, checkpoint_writes=0, quality_claim=False, adopted=False)
    for m in ((32, 8192) if args.expand else (32,)):
        for k, n in base.SHAPES:
            guard.check("다음 동일 분모 형상 전")
            item = {}
            result["cases"].append(item)
            linear_case(torch, mods, m, k, n, args, guard, item, base=base)
            gc.collect()
        item = {}
        result["producers"].append(item)
        producer_case(torch, mods, m, args, guard, item, base=base)
        gc.collect()
        if m == 32:
            result["canary_complete"] = True
    result["expansion_completed"] = args.expand
    return result


def exact_checks(value):
    if isinstance(value, list):
        return bool(value) and all(exact_checks(item) for item in value)
    return isinstance(value, dict) and value.get("bitwise_equal") is True


def complete_measurement(value):
    samples = value.get("samples", ()) if isinstance(value, dict) else ()
    expected = ["first_call_compile_autotune"] + ["warmup"] * WARMUP + ["measured"] * ROUNDS
    if [item.get("phase") for item in samples] != expected:
        return False
    for item in samples:
        for key in ("synchronized_wall_ms", "cuda_event_interval_ms"):
            number = item.get(key)
            if type(number) not in (int, float) or not math.isfinite(number) or number < 0:
                return False
    return True


def decide(report, actual_exit, owner):
    if owner.decide(report, actual_exit) != 0:
        return 9
    observed = report.get("observations", {})
    if observed.get("companion_contract") != CONTRACT:
        return 9
    for item in observed["cases"]:
        if any(not complete_measurement(item.get("phases", {}).get(name)) for name in PIPELINE_PHASES):
            return 9
        required = ("native_before_after", "int_full_weight_pack_cold_reuse_exact", "hybrid_weight_pack_cold_reuse_exact",
                    "hybrid_forward_native", "hybrid_gradients_original_int", "same_row_codes_and_scales")
        if any(not exact_checks(item.get("implementation_checks", {}).get(name)) for name in required):
            return 9
        if item.get("M") == 32 and (item.get("full_cpu_reference") is not True
                or not exact_checks(item.get("implementation_checks", {}).get("full_original_cpu_reference"))):
            return 9
    for item in observed["producers"]:
        if (any(not complete_measurement(item.get("phases", {}).get(name)) for name in PRODUCER_PHASES)
                or item.get("primitive_forward_grad_enabled") is not False
                or item.get("vjp_autograd_measured_separately") is not True
                or item.get("original_v12_local_ulp_limit") != 1
                or type(item.get("max_bf16_ulps")) is not int or not 0 <= item["max_bf16_ulps"] <= 1
                or any(not exact_checks(item.get("implementation_checks", {}).get(name))
                       for name in ("native_before_after", "fused_pack_own_y_exact", "original_cpu_pack", "original_vjp_exact"))):
            return 9
    return 0


def main(argv=None):
    state, owner = {}, None
    try:
        owner = original()
        with linked(owner, state=state) as base:
            code = base.main(argv)
        if "publication" in state:
            terminal, summary, guard = state["publication"]
            if code != summary["intended_supervisor_exit"]:
                summary.update(intended_supervisor_exit=9, status="INCOMPLETE_OR_ERROR")
            return owner.finalize_disposition(terminal, summary, guard)
        if code == 0:
            for guard in state.get("guards", ()):
                guard.check("private 모듈 복원 후 실제 반환 전")
        return code
    except BaseException as error:
        detail = dict(status="INCOMPLETE_OR_ERROR", intended_exit=9, exception_class=type(error).__name__,
                      exception=str(error), original_traceback=traceback.format_exc())
        if owner is not None and "publication" in state:
            terminal, summary, _ = state["publication"]
            try:
                owner.module.append_terminal(terminal, dict(event="TERMINAL_VETO", intended_supervisor_exit=9,
                    actual_worker_exit=summary.get("actual_worker_exit"), **detail))
            except BaseException as cleanup:
                detail["terminal_cleanup_error"] = dict(exception_class=type(cleanup).__name__, exception=str(cleanup),
                                                        original_traceback=traceback.format_exc())
        print(json.dumps(detail, ensure_ascii=False), file=sys.stderr, flush=True)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
