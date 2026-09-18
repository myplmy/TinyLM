#!/usr/bin/env bash
# TinyLM WSL 공통 Python 선택기.
# 학습·검증 스크립트는 임의의 system python으로 떨어지지 않고 tlm_torch만 사용한다.

tinylm_python() {
    local candidate=""

    if [[ -n "${TINYLM_PYTHON:-}" ]]; then
        candidate="${TINYLM_PYTHON}"
        if [[ ! -x "${candidate}" ]]; then
            printf '[STOP] TINYLM_PYTHON is not executable: %s\n' "${candidate}" >&2
            return 2
        fi
        printf '%s\n' "${candidate}"
        return 0
    fi

    if [[ -n "${CONDA_PREFIX:-}" && "${CONDA_PREFIX##*/}" == "tlm_torch" ]]; then
        candidate="${CONDA_PREFIX}/bin/python"
        if [[ -x "${candidate}" ]]; then
            printf '%s\n' "${candidate}"
            return 0
        fi
    fi

    candidate="${HOME}/miniforge3/envs/tlm_torch/bin/python"
    if [[ -x "${candidate}" ]]; then
        printf '%s\n' "${candidate}"
        return 0
    fi

    printf '%s\n' '[STOP] WSL tlm_torch Python was not found.' >&2
    printf '%s\n' '       Activate tlm_torch or set TINYLM_PYTHON to its interpreter.' >&2
    return 2
}
