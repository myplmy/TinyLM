"""TinyLM-adapted NorMuon: 기존 Muon 뒤의 행별 EMA 정규화 후보.

공식 exact 포팅이나 논문 Algorithm 1이 아니다. 기존 비정규화 모멘텀,
Nesterov, NS5 연산 순서, 형상 스케일, None skip 및 gradient 불변을 유지한다.
NS 출력 O에 FP32 행별 제곱평균 EMA를 적용한 뒤 원 Frobenius norm을 복원한다.
AdamW routing과 trainer 기본값은 바꾸지 않으며 split_params를 그대로 재노출한다.

참고한 수학: https://arxiv.org/abs/2510.05491v1
공식 코드와의 차이: 공식 코드는 EMA 모멘텀, gradient 제자리 변경,
None의 zero 치환 및 Jordan 스케일을 사용한다. 참고 snapshot은
zichongli5/NorMuon@99f2ac72ee61a0e09514856a6dbaad2ecbdecab6 이다.
그 저장소의 코드는 복사하지 않았다.

설계 정정: 전역 weight/momentum staging은 사용하지 않는다. 입력과 기존
상태를 전수 선검증한 뒤 행렬별 계산ㆍ검증ㆍ적용한다. 후반 계산 오류이면
앞 행렬이나 현재 모멘텀 상태가 이미 바뀔 수 있으므로 예외 후 학습을 중단하고
정상 checkpoint에서 복원해야 한다. 전역 원자적 롤백은 보장하지 않는다.
영구 추가 상태는 row_v뿐이며 전체 학습의 속도ㆍ메모리ㆍ품질은 미검증이다.
"""
from __future__ import annotations

import math
from numbers import Integral, Real

import torch

from .muon import Muon, _newton_schulz, split_params, update_scale

__all__ = ["NorMuon", "split_params"]


def _finite(tensor, label):
    if not bool(torch.isfinite(tensor).all()):
        raise RuntimeError(f"NorMuon 학습 중단: {label}에 비유한 값이 있다.")


def _number(value, label, *, upper=None, positive=False):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{label}은 유한한 실수여야 한다.")
    value = float(value)
    if (not math.isfinite(value) or value < 0 or (positive and value == 0)
            or (upper is not None and value >= upper)):
        raise ValueError(f"{label}의 범위가 잘못되었다: {value!r}")
    return value


def _validate_group(group):
    required = {"lr", "weight_decay", "momentum", "beta2", "eps", "ns_steps",
                "nesterov", "scale_mode"}
    if not required.issubset(group):
        raise ValueError("NorMuon 설정 또는 재개 상태의 필수 항목이 없다.")
    for key in ("lr", "weight_decay"):
        _number(group[key], key)
    _number(group["momentum"], "momentum", upper=1)
    _number(group["beta2"], "beta2", upper=1)
    eps = _number(group["eps"], "eps", positive=True)
    # 실제 정규화는 FP32이므로 그 dtype에서도 양의 유한수여야 한다.
    eps32 = float(torch.tensor(eps, dtype=torch.float32, device="cpu"))
    if not math.isfinite(eps32) or eps32 <= 0:
        raise ValueError("eps는 FP32에서도 양의 유한수여야 한다.")
    if (isinstance(group["ns_steps"], bool)
            or not isinstance(group["ns_steps"], Integral) or group["ns_steps"] < 1):
        raise ValueError("ns_steps는 양의 정수여야 한다.")
    if not isinstance(group["nesterov"], bool):
        raise ValueError("nesterov는 bool이어야 한다.")
    update_scale(1, 1, group["scale_mode"])


def _parameter(parameter):
    if (not isinstance(parameter, torch.Tensor) or parameter.ndim != 2
            or not parameter.is_floating_point() or parameter.numel() == 0):
        raise ValueError("NorMuon은 비어 있지 않은 실수형 2D 파라미터만 받는다.")
    if parameter.layout != torch.strided:
        raise ValueError("NorMuon은 dense 파라미터만 받는다.")


def _state(parameter, state, *, same_device=True):
    if not state:
        return
    if "buf" not in state or "row_v" not in state:
        raise ValueError("NorMuon 재개 상태에는 buf와 row_v가 모두 필요하다.")
    buf, row_v = state["buf"], state["row_v"]
    if (not isinstance(buf, torch.Tensor) or buf.shape != parameter.shape
            or not buf.is_floating_point() or buf.layout != torch.strided):
        raise ValueError("NorMuon buf의 형상 또는 dtype이 잘못되었다.")
    if (not isinstance(row_v, torch.Tensor)
            or row_v.shape != (parameter.shape[0], 1)
            or row_v.dtype != torch.float32 or row_v.layout != torch.strided):
        raise ValueError("NorMuon row_v는 출력 행 수 x 1의 FP32 상태여야 한다.")
    if same_device and (buf.device != parameter.device or row_v.device != parameter.device
                        or buf.dtype != parameter.dtype):
        raise ValueError("NorMuon 상태의 device 또는 모멘텀 dtype이 다르다.")
    _finite(buf, "모멘텀 상태")
    _finite(row_v, "행별 상태")
    if bool((row_v < 0).any()):
        raise ValueError("NorMuon row_v는 음수일 수 없다.")


def _row_normalize(orthogonal, row_v, beta2, eps):
    """현재 행렬의 row_v만 갱신한다. 입력 O는 변경하지 않는다."""
    values = orthogonal.float()
    _finite(values, "NS 출력")
    row_mean = values.square().mean(dim=-1, keepdim=True)
    _finite(row_mean, "행별 제곱평균")
    row_v.mul_(beta2).add_(row_mean, alpha=1 - beta2)
    _finite(row_v, "갱신된 행별 상태")
    normalized = values / (row_v.sqrt() + eps)
    _finite(normalized, "행별 정규화 출력")
    norm_before, norm_after = values.norm(), normalized.norm()
    _finite(norm_before, "정규화 전 norm")
    _finite(norm_after, "정규화 후 norm")
    normalized.mul_(norm_before / (norm_after + eps))
    _finite(normalized, "norm 복원 출력")
    return normalized


class NorMuon(Muon):
    """TinyLM-adapted post-NS 행별 EMA 후보. 기본 trainer에는 연결하지 않는다.

    추가 상태 row_v는 FP32 (out, 1)이다. None gradient는 상태 생성ㆍWD까지
    모두 skip하며, 중복 물리 파라미터는 설정 오류로 거절한다.
    """

    def __init__(self, params, lr=2e-2, momentum=0.95, nesterov=True,
                 ns_steps=5, weight_decay=0.0, scale_mode="jordan", beta2=0.95,
                 eps=1e-10):
        _validate_group(dict(lr=lr, momentum=momentum, nesterov=nesterov,
                             ns_steps=ns_steps, weight_decay=weight_decay,
                             scale_mode=scale_mode, beta2=beta2, eps=eps))
        if isinstance(params, set):
            raise ValueError("파라미터 순서는 고정되어야 한다.")
        self._initial_beta2 = beta2
        self._initial_eps = eps
        super().__init__(params, lr=lr, momentum=momentum, nesterov=nesterov,
                         ns_steps=ns_steps, weight_decay=weight_decay, scale_mode=scale_mode)
        self.defaults.update(beta2=beta2, eps=eps)

    def add_param_group(self, param_group):
        group = dict(param_group)
        params = group["params"]
        if isinstance(params, set):
            raise ValueError("파라미터 순서는 고정되어야 한다.")
        params = [params] if isinstance(params, torch.Tensor) else list(params)
        group["params"] = params
        group.setdefault("beta2", self.defaults.get("beta2", self._initial_beta2))
        group.setdefault("eps", self.defaults.get("eps", self._initial_eps))
        _validate_group(dict(self.defaults, **group))
        seen = {id(p) for old in self.param_groups for p in old["params"]}
        for parameter in params:
            _parameter(parameter)
            if id(parameter) in seen:
                raise ValueError("같은 물리 파라미터를 두 번 업데이트할 수 없다.")
            seen.add(id(parameter))
        super().add_param_group(group)

    def _preflight(self):
        seen, active = set(), []
        for group in self.param_groups:
            _validate_group(group)
            for parameter in group["params"]:
                _parameter(parameter)
                if id(parameter) in seen:
                    raise ValueError("중복 물리 파라미터가 발견되었다.")
                seen.add(id(parameter))
                _finite(parameter, "파라미터")
                _state(parameter, self.state.get(parameter, {}))
                grad = parameter.grad
                if grad is None:
                    continue
                if (grad.layout != torch.strided or grad.shape != parameter.shape
                        or grad.dtype != parameter.dtype or grad.device != parameter.device):
                    raise ValueError("NorMuon gradient의 형상, dtype 또는 device가 다르다.")
                _finite(grad, "gradient")
                active.append((group, parameter))
        return active

    @torch.no_grad()
    def step(self, closure=None):
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()
        active = self._preflight()
        for group, parameter in active:
            grad = parameter.grad
            state = self.state[parameter]
            if not state:
                state["buf"] = torch.zeros_like(grad)
                state["row_v"] = torch.zeros((parameter.shape[0], 1),
                                               dtype=torch.float32, device=parameter.device)
            buf = state["buf"]
            buf.mul_(group["momentum"]).add_(grad)
            _finite(buf, "갱신된 모멘텀")
            direction = grad.add(buf, alpha=group["momentum"]) if group["nesterov"] else buf
            _finite(direction, "NS 입력")
            orthogonal = _newton_schulz(direction, steps=group["ns_steps"])
            update = _row_normalize(orthogonal, state["row_v"], group["beta2"], group["eps"])
            scale = update_scale(parameter.shape[0], parameter.shape[1], group["scale_mode"])
            decay, amount = 1 - group["lr"] * group["weight_decay"], group["lr"] * scale
            # 전역 복사 없이 실제 두 inplace 연산의 overflow를 보수적으로 차단한다.
            bound = (float(parameter.abs().max()) * abs(decay)
                     + float(update.abs().max()) * abs(amount))
            if (not math.isfinite(decay) or not math.isfinite(amount)
                    or not math.isfinite(bound) or bound > torch.finfo(parameter.dtype).max):
                raise RuntimeError("NorMuon 학습 중단: weight 업데이트 overflow 위험.")
            if group["weight_decay"]:
                parameter.mul_(decay)
            parameter.add_(update, alpha=-amount)
            _finite(parameter, "갱신된 파라미터")
            del direction, orthogonal, update
        return loss

    def load_state_dict(self, state_dict):
        groups = state_dict["param_groups"]
        if (len(groups) != len(self.param_groups)
                or any(len(a["params"]) != len(b["params"])
                       for a, b in zip(groups, self.param_groups))):
            raise ValueError("NorMuon 재개 파라미터 그룹이 일치하지 않는다.")
        rows = []
        for saved, current in zip(groups, self.param_groups):
            _validate_group(saved)
            for key, parameter in zip(saved["params"], current["params"]):
                state = state_dict["state"].get(key, {})
                _state(parameter, state, same_device=False)
                if state:
                    rows.append((parameter, state["row_v"]))
        super().load_state_dict(state_dict)
        # Optimizer의 일반 로더는 FP32 row_v도 parameter dtype으로 내린다.
        # 원본에서 직접 복구하여 BF16 파라미터의 재개 때도 정밀도를 보존한다.
        for parameter, row_v in rows:
            self.state[parameter]["row_v"] = row_v.detach().to(
                device=parameter.device, dtype=torch.float32).clone()
