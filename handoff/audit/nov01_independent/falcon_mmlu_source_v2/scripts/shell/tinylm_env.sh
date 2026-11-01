#!/usr/bin/env bash
# TinyLM WSL 공통 Python·native PATH 선택기.
# 학습·검증 스크립트는 임의의 system python으로 떨어지지 않고 tlm_torch만 사용한다.
#
# WSL은 기본적으로 Windows PATH를 뒤에 붙인다. 그 안에 탐색할 수 없는 mount 항목이
# 하나라도 있으면 Python의 execvp("nvcc")가 FileNotFoundError 대신 PermissionError를
# 반환할 수 있다. PyTorch 2.10 Inductor는 compile artifact에 CUDA 정보를 붙이면서 nvcc를
# 조회하고 PermissionError는 처리하지 않으므로 첫 compile 전에 죽는다. 실험 launcher는
# Linux native toolchain만 써야 하므로 /mnt/<drive>/... 항목만 제거한다.

tinylm_prepare_native_path() {
    local entry=""
    local filtered=""
    local old_ifs="${IFS}"

    if [[ -z "${WSL_DISTRO_NAME:-}" ]] && ! grep -qi microsoft /proc/sys/kernel/osrelease 2>/dev/null; then
        return 0
    fi
    IFS=':'
    for entry in ${PATH:-}; do
        case "${entry}" in
            /mnt/[A-Za-z]/*) continue ;;
            "") continue ;;
        esac
        case ":${filtered}:" in
            *":${entry}:"*) ;;
            *) filtered="${filtered:+${filtered}:}${entry}" ;;
        esac
    done
    IFS="${old_ifs}"
    PATH="${filtered}"
    export PATH
}

tinylm_prepare_native_path

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
