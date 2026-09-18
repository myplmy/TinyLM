# 제안 — TinyLM 학습환경을 WSL2 Linux로 단계적으로 이관한다

> **작성일**: 2026-09-15  
> **최종 수정일**: 2026-09-18
> **상태**: ✅사용자 승인·진행 중 / M2R 정적 PASS / WSL agent와 관찰한 hook 범위 `ACTIVE_VERIFIED` / M3 사용자 범위 예외 종결(manual compact 검증 제외, 전체 증거 `PARTIAL`) / M4·M5 `NOT_RUN`
> **분류**: 작업환경 / 실행기반 / 실험 재현성  
> **실험번호**: `PNone`  
> **실험계획 비대상 사유**: 이 문서는 환경 이관 의사결정 제안이다. 승인 뒤 필요한 교량 실험은 기존 계획의 환경 단계 또는 별도 승인된 실험계획으로 등록한다.

---

## 1. 배경 — 왜 지금 이 제안을 하나

Windows의 현재 학습환경과 WSL2의 후보 환경은 PyTorch·CUDA 주버전은 맞지만 런타임과
지원 백엔드가 같지 않다.

| 축 | Windows 현재 | WSL2 후보 | 의미 |
|---|---|---|---|
| PyTorch | `2.10.0` | `2.10.0+cu130` | 표기는 거의 같아도 wheel·확장 ABI는 별도 확인 대상 |
| CUDA build | `13.0` | `13.0` | 큰 축은 일치 |
| cuDNN runtime | `9.19.0` | `9.15.1` | 커널 선택·결정성·속도 조건이 달라질 수 있음 |
| cuSPARSELt | OFF | ON | P025B native 2:4 게이트를 다시 열 수 있는 직접 차이 |
| Triton | Windows `triton-windows 3.7.1.post27` | Linux `triton 3.6.0` | 같은 import 이름이어도 배포판·버전·생성 커널이 다름 |
| FlashAttention | 미확인/미설치 | `tlm_torch`에서 distribution 미검출 | Linux가 설치 가능성이 높은 것이지 현재 설치·동작한 것은 아님 |

이번 세션의 읽기 전용 실사에서 `Ubuntu`는 실행 중인 WSL2 배포판이고, 후보 인터프리터는
`/home/uranus/miniforge3/envs/tlm_torch/bin/python`이었다. 그 환경에서 Python 3.10.19,
PyTorch 2.10.0+cu130, Triton 3.6.0, NumPy 2.2.6, tokenizers 0.22.2,
datasets 5.0.0, transformers 5.14.1을 확인했다. `flash-attn` 배포판은 확인되지 않았다.
이것은 **설치 메타데이터 실사**이지 GPU kernel E2E PASS가 아니다.

P025B Stage0b는 Windows에서 import를 넘은 뒤 `cuSPARSELt not supported`로 native 2:4
첫 호출이 막혔다([결과 082](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md)).
반대로 Linux 우선인 FlashAttention·Triton·cuSPARSELt 생태계는 WSL2 이관의 실익을 만든다.
FlashAttention 공식 저장소도 Linux를 요구조건으로 두고 Windows 지원은 추가 검증이 필요한
상태라고 명시한다.

## 2. 목적 — 무엇을 알아내거나 얻으려 하나

Windows에서 축적한 결과와 보호 경계를 잃지 않으면서, WSL2의 Linux-native CUDA 백엔드를
사용할 수 있는 **단일 정본·단계적 전환 경로**를 만들고 환경 차이를 실험 효과로 오인하지 않게 한다.

## 3. 성과물 — 승인하면 무엇이 생기나

| 산출물 | 형태 |
|---|---|
| Windows/WSL 환경 잠금표 | Python·torch·CUDA·cuDNN·Triton·cuSPARSELt·FlashAttention·driver·GPU의 양쪽 snapshot |
| WSL 호환성 패치 | 경로·셸·훅·검사기·실행기의 OS 분기. 이 제안 승인과 별도 구현 범위 확정 뒤 작성 |
| 교량 판정 | 같은 모델·데이터 풀·토크나이저·seed·스케줄의 Windows↔WSL 대조 결과 |
| backend 게이트 | P025B 2:4, P022C FP8, attention backend의 지원·정확성·속도·VRAM 표 |
| 운영 문서 | canonical worktree, 캐시·체크포인트, 백업, 업데이트, 장애 복구, Codex E2E 절차 |

승인한다고 곧바로 WSL이 새 정본이 되는 것은 아니다. **교량 대조와 새 Codex E2E를 통과한
시점에만** 정본 전환 여부를 다시 승인한다.

## 4. 비용

| 항목 | 양 |
|---|---:|
| GPU | ⚙6~12 GPU-h — 교량 1쌍과 backend micro/E2E 후보. 전면 재실험은 포함하지 않음 |
| AI 작업 | ⚙8~16 h — 경로·셸·훅·검사기 이식과 정적 fixture |
| ★사용자가 직접 해야 하는 일 | WSL 설정 전환·재시작, 패키지 설치 승인, GPU 스모크·교량 실험, 최종 정본 전환 승인 |
| 디스크 | ⚙저장소 1복제 + Linux 환경·빌드 캐시 20~60 GiB; 데이터·체크포인트는 별도 승인 전 복제 0 |

용량은 FlashAttention 소스 빌드 캐시와 CUDA 확장에 따라 크게 달라진다. WSL2 VHD는 자동으로
커질 수 있으므로 상한·회수 절차를 먼저 정해야 한다.

## 5. 원리·근거

**우리 실측**

| 근거 | 값 | 출처 |
|---|---|---|
| Windows native 2:4 게이트 | import PASS, 첫 native 호출 `cuSPARSELt not supported` | [결과 082 §6](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md) |
| WSL 후보 환경 | Ubuntu/WSL2, Python 3.10.19, torch 2.10.0+cu130, Triton 3.6.0 | 이번 세션의 읽기 전용 설치 메타데이터 실사 |
| 현재 Codex 훅 | Windows는 `commandWindows`와 PowerShell wrapper, POSIX는 `python3` 경로 | [`.codex/hooks.json`](../.codex/hooks.json) |
| 현재 정본 루트 | WSL `/home/uranus/tinyLM`; Windows `Z:\TinyLM`은 같은 위치를 가리키는 편의 링크 | 사용자 이관 사실, Git root 실사, [`Codex 06`](../ai_dev_tool/Codex/06_Codex용_프로젝트지침과_메모리.md) |

**외부 근거**

- OpenAI의 [ChatGPT Windows 앱 안내](https://learn.chatgpt.com/docs/windows/windows-app)는
  Windows native agent가 필요할 때 `wsl` CLI를 쓸 수 있고, agent 자체를 WSL2로 전환하려면
  설정에서 agent environment를 바꾼 뒤 앱을 재시작해야 한다고 설명한다. 통합 터미널 셸 설정과
  agent 실행환경은 별도다.
- OpenAI의 [Codex sandbox 안내](https://learn.chatgpt.com/docs/sandboxing)는 Windows native와
  WSL2가 서로 다른 sandbox 구현을 쓰며, WSL2/Linux에서는 `bubblewrap` 설치를 우선 권장한다고
  설명한다. 따라서 기존 Windows 훅 E2E는 WSL에서 자동 승계되지 않는다.
- Microsoft의 [WSL 파일시스템 안내](https://learn.microsoft.com/en-us/windows/wsl/filesystems)는
  Linux 도구를 주로 쓸 때 저장소를 Linux 파일시스템에 두는 편이 빠르며 `/mnt/<drive>`의
  교차 파일시스템 I/O에는 비용이 있다고 안내한다.
- PyTorch의 [semi-structured sparse 문서](https://docs.pytorch.org/docs/stable/sparse)는
  2:4 sparse tensor가 CUDA·dtype·shape 제약과 backend별 packed representation을 갖는
  prototype 기능임을 명시한다. 라이브러리가 보인다는 사실만으로 TinyLM E2E 가속을 주장할 수 없다.
- FlashAttention의 [공식 저장소](https://github.com/Dao-AILab/flash-attention)는 Linux를 요구조건으로
  두고 Windows 빌드는 추가 검증이 필요하다고 한다. 다만 현재 WSL `tlm_torch`에 패키지가 없으므로
  이관과 설치 완료를 같은 판정으로 묶으면 안 된다.

## 6. 방법

### 6.1 단계별 게이트

| 단계 | 무엇 | 비용 | ★다음으로 가는 조건 |
|---|---|---:|---|
| M0 동결·목록화 | Windows HEAD·dirty 파일·환경 lock·외부 캐시·체크포인트 위치를 **읽기 전용**으로 기록 | ⚙1 h | 보호 데이터 이동 0, 복구 지점과 단일 정본 후보 명시 |
| M1 WSL 후보 복제 | 사용자 승인 뒤 Linux ext4의 `~/code/TinyLM`에 깨끗한 clone/worktree를 만든다. Windows 작업트리를 복사본 정본으로 동시에 쓰지 않음 | ⚙1~2 h | Git tree hash와 추적 파일 내용이 Windows 기준과 일치 |
| M2 플랫폼 정적 호환 | 경로·`python.exe`·`.bat`·PowerShell·CRLF·대소문자·훅을 목록화하고 Linux용 entrypoint와 fixture를 별도 구현; `bubblewrap`·user namespace 선결 확인 | ⚙4~8 h | Windows·Linux 정적 검사 양쪽 PASS, Linux sandbox fail-open 0, 한쪽 수정이 다른 쪽 계약을 깨지 않음 |
| M3 Codex WSL E2E | Desktop 설정을 WSL로 바꾸고 재시작한 새 세션에서 AGENTS·17 skill·정상/차단/WIP/compact probe를 다시 관찰 | 사용자 ⚙0.5 h | WSL 세션에서 실패·fail-open 0. 기존 Windows `ACTIVE_VERIFIED`와 별도 증거로 기록 |
| M4 backend 무학습 게이트 | 정확 interpreter로 torch/CUDA/cuDNN/Triton/cuSPARSELt/FlashAttention import·지원·수치 일치·메모리 계측 | ⚙0.5 GPU-h | crash/NaN/incorrect output 0, backend별 지원 상태를 실제 호출로 구분 |
| M5 교량 대조 | 동일 checkpoint 평가와, 필요 시 동일 seed의 짧은 dense reference 1쌍을 Windows/WSL에서 실행 | ⚙2~4 GPU-h | 품질 차가 현 계열 자 안이고 속도·VRAM은 환경별 새 기준으로 분리됨 |
| M6 후보 재개 | P025B Stage0b, P022C FP8, SDPA/FlashAttention 순으로 각각 gate→E2E | ⚙3~8 GPU-h | 앞 단계 PASS인 backend만 후속 계획 개방 |
| M7 정본 전환 승인 | 결과·운영 비용을 보고 사용자가 Windows 유지/WSL 전환을 결정 | 사용자 결정 | canonical worktree 정확히 1개, 이전 트리는 archive/read-only |

이번 요청에서는 M0의 일부 실사와 문서 작성만 했다. 설치·복제·패치·스모크·GPU 실행과
실험 배치 작성은 모두 `NOT_RUN`이다.

### 6.2 Codex Desktop에서의 실제 접근 방식

1. **현재 방식**: Windows native agent가 `Z:\TinyLM`을 열고 필요할 때 `wsl.exe -d Ubuntu -- ...`를
   호출한다. 현재 sandbox에서는 WSL 읽기 명령도 승인이 필요했다. 이것은 `tlm_torch`를 자동 활성화하지
   않으므로 `/home/uranus/miniforge3/envs/tlm_torch/bin/python`을 정확히 지정해야 한다.
2. **WSL agent 방식**: Desktop 설정의 Agent environment를 WSL로 변경하고 앱을 재시작한다.
   Linux 저장소는 `\\wsl$\Ubuntu\home\uranus\code\TinyLM`으로 프로젝트에 추가할 수 있다.
3. **검증 포인트**: 화면에서 WSL을 선택한 것, 통합 터미널이 WSL인 것, 도구 호출의 실제 `uname`이
   Linux인 것은 서로 대체 증거가 아니다. 새 세션의 tool workdir·Python path·sandbox probe를 함께 본다.
4. **Codex 상태**: Windows 앱은 Windows 쪽 Codex home을 사용하지만, WSL에서 별도로 실행한 CLI는
   기본적으로 Linux `~/.codex`를 사용한다. 인증·설정·세션을 공유할지는 명시적으로 선택하고,
   처음부터 디렉터리 전체를 양방향 동기화하지 않는다. 공유가 필요하면 공식 안내의 `CODEX_HOME`
   방식과 최소 파일 목록을 별도 승인·검증한다.

### 6.3 Windows 작업디렉터리의 처리

- **전환 전**: `Z:\TinyLM`을 유일 정본으로 유지하고 WSL에서는 `/mnt/z/TinyLM`을 읽는 호환성
  탐색까지만 한다. 장시간 Linux 빌드·학습 성능의 최종 수치는 이 mounted 경로에서 확정하지 않는다.
- **시험 전환**: Linux ext4에 별도 깨끗한 clone을 만들되, 같은 변경을 Windows와 WSL 양쪽에서
  병렬 편집하지 않는다. branch/commit 또는 bundle 같은 명시적 경계로만 전달한다.
- **최종 전환**: M0~M6와 사용자 승인을 통과하면 WSL clone 하나를 canonical로 지정한다.
  Windows 트리는 즉시 삭제하지 않고 read-only 복구본으로 두며, 제거는 별도 승인 사항이다.
- `datasets/TinyDataset/**`, 체크포인트, HF/W&B 캐시는 이번 제안 승인만으로 옮기지 않는다.
  독립 데이터 프로젝트 여부와 artifact 정책이 확정된 뒤 manifest+hash를 갖춘 별도 이관으로 처리한다.

### 6.4 기존 실험 결과의 보존·재실험 규칙

**버릴 결과는 없다.** 기존 결과는 `environment=Windows-cu130-cudnn9.19` 층의 역사적 증거로
보존한다. 다만 다음과 같이 사용 범위를 바꾼다.

| 결과 유형 | WSL 이관 뒤 처리 |
|---|---|
| 품질·loss, backend 비의존 | 교량 대조가 자 안이면 계속 사용. 자 밖이면 환경층을 분리하고 의사결정 후보만 재실행 |
| tok/s·ms/step·VRAM·RSS | Windows 수치를 WSL 성능으로 이식 금지. 후보 backend와 배포 기준을 WSL에서 재측정 |
| Windows 미지원으로 막힌 P025B | 실패를 삭제하지 않고 Windows 조건의 유효 결과로 보존; WSL Stage0b를 별도 조건으로 재개 |
| P022C FP8 순수 GEMM | WSL에서 backend 지원·정확성·pure GEMM을 다시 확인한 뒤 TinyLM E2E로 진행 |
| SDPA/FlashAttention | 같은 attention 수학·mask·dtype의 정확성 대조가 먼저. 설치 성공은 속도·품질 PASS가 아님 |
| 모델 순위·기본값 | 교량 1쌍이 자 안이면 전면 재실험 금지; 순위 경계나 기본값 후보만 선택 재확인 |

cuDNN 9.19.0↔9.15.1, Triton 3.7.1↔3.6.0, filesystem 위치는 모두 조건축이다.
WSL에서 결과가 좋아져도 알고리즘 효과와 환경 효과를 합산해 기존 방법론의 성과로 쓰지 않는다.

### 6.5 향후 관리 계약

- canonical repo·Python interpreter·CUDA stack을 핸드오프마다 자동 추측하지 않고 환경 snapshot으로
  기록한다.
- `requirements`만으로 CUDA extension을 고정했다고 주장하지 않는다. torch wheel, driver,
  toolkit/nvcc, cuDNN, cuSPARSELt, Triton, FlashAttention build hash를 분리한다.
- Windows와 WSL 캐시를 공유하지 않는다. HF 데이터 캐시·torch extensions·Triton cache는 OS별
  경로를 둔다.
- WSL 업데이트·driver·torch/extension 변경 뒤 backend microtest와 사용자 스모크를 다시 요구한다.
- 백업은 Git 추적 코드와 대용량 artifact를 분리하며, WSL VHD 자체만을 유일 백업으로 삼지 않는다.
- Desktop과 WSL CLI가 서로 다른 Codex home을 쓸 수 있으므로 어느 쪽이 훅 신뢰·인증·세션 정본인지
  운영표에 적는다. 동기화는 비밀·인증자료를 포함할 수 있어 별도 사용자 승인 없이 자동화하지 않는다.

## 7. 거절하면 못 하는 것

Windows 환경에서 이미 가능한 dense·Muon·평가 실험은 계속할 수 있다. 다만 현재 Windows에서
막힌 cuSPARSELt native 2:4의 동일 PyTorch 경로, 공식적으로 Linux 중심인 FlashAttention,
Linux Triton/CUDA 확장의 일관된 개발·검증은 제한된다. P025B의 **native 가속 주장**은 다른
지원 backend가 확인되지 않는 한 계속 닫힌다.

## 8. 위험 — 실행하면 무엇이 잘못될 수 있나

| 위험 | 어떻게 드러나나 | 완화 |
|---|---|---|
| 두 정본 분기 | Windows·WSL에서 서로 다른 dirty 변경 | canonical 1개, 전달은 commit/bundle, 양쪽 동시 편집 금지 |
| 환경 효과를 기법 이득으로 오인 | 같은 코드인데 loss·speed·VRAM 변화 | 교량 dense control, 환경 서명, 품질과 성능 계층 분리 |
| mounted-drive 병목 | `/mnt/z`에서 Git·데이터로더·빌드가 느림 | 탐색만 mounted 경로, 최종 Linux 작업은 ext4; 저장 위치를 결과에 기록 |
| 훅 안전경계 상실 | `commandWindows` PASS를 Linux에서도 PASS로 간주 | Linux hook/fixture 및 새 세션 E2E를 처음부터 재실행 |
| 경로·대소문자·줄끝 회귀 | `Z:\`, `.bat`, CRLF, case-only 이름에서 실패 | 정적 path inventory와 OS별 entrypoint; Git tree/hash 대조 |
| 확장 ABI 불일치 | import 성공 뒤 첫 CUDA 호출 crash/undefined symbol | import와 실제 kernel call을 분리한 M4, exact build metadata |
| FlashAttention 과대평가 | 설치만 되고 TinyLM mask/head/dtype가 미지원 | 정확성→메모리→속도→학습 순의 gate |
| sparse 수치 오판 | mask-only dense와 native packed를 같은 결과로 보고 | storage/backend signature와 peak VRAM·temporary dense 명시 |
| 데이터·체크포인트 손실 | 무승인 복사·이동·중복 삭제 | 보호 경로 별도 승인, manifest/hash, 원본 삭제는 마지막 별도 승인 |
| WSL VHD 팽창 | 빌드·캐시 후 Windows 디스크 부족 | 사전 용량 상한, 캐시 분리, 사용자가 승인한 회수 절차 |

## 9. 대안

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| **A** | Windows `Z:\TinyLM`을 정본으로 유지하고 WSL은 `/mnt/z/TinyLM` 도구 호출에만 사용 | 이력·Windows 배치·훅 변경이 작고 단일 트리 | 교차 filesystem I/O, WSL-native 개발의 일부 이점 상실, agent는 계속 Windows sandbox |
| **B** | 즉시 `~/code/TinyLM`으로 옮기고 Codex agent도 WSL로 전환 | Linux CUDA 생태계와 ext4 성능을 곧바로 사용 | 현재 훅·배치·경로·E2E가 한 번에 무효화되고 복구·교락 위험 최대 |
| **C** | **단계적 이관**: Windows 정본 동결 → WSL clean clone → 정적/E2E/backend/교량 gate → 사용자 최종 cutover | 환경 효과를 분리하고 되돌릴 수 있으며 기존 결과를 보존 | 일정 기간 두 환경 관리 비용과 교량 GPU 비용 발생 |
| **D** | Windows 유지, Linux 전용 backend만 Docker/원격 Linux에서 단발 검증 | 본 저장소 이관 최소화 | 동일 GPU·파일시스템·Codex 훅 재현이 약하고 운영 경로가 하나 더 늘어남 |

### ★권장안과 근거

**C안**을 권장한다. 이관의 핵심 이익은 cuSPARSELt·FlashAttention·Triton 자체가 아니라
그 기능을 **기존 결과와 비교 가능한 조건에서 안전하게 검증하는 것**이다. B안은 가장 빠르지만
Windows에서 이미 검증한 경로·훅·실험 조건을 동시에 바꿔 원인을 분리하기 어렵다. C안은 M4에서
cuSPARSELt가 실제로 열리지 않거나 M5 교량이 자 밖이면 정본 전환 없이 중단할 수 있다.

## 10. 2026-09-16 실제 이관 뒤 재감사와 수정 계획

사용자가 기존 TinyLM 디렉터리 전체를 `/home/uranus/tinyLM`으로 이관했다. 원안의 “Windows
정본을 유지한 채 WSL clean clone을 만든다”는 미래형 전제는 현재 상태와 다르다. 다만 **파일
이동 완료와 운영 전환 완료는 다르다.** 확인 범위와 미확인 범위를 다음처럼 분리한다.

### 10.1 확인된 사실과 증거 한계

| 항목 | 관측 | 판정 |
|---|---|---|
| 정본 후보·저장 | `/home/uranus/tinyLM`, Git root 일치, ext4(`/dev/sdd`) | WSL 정본 후보 확인 |
| 커널 | `6.6.87.2-microsoft-standard-WSL2` | WSL2 확인 |
| 지정 Python | `/home/uranus/miniforge3/envs/tlm_torch/bin/python` 3.10.19 | 이번 Python 정적 도구에만 사용 |
| 핵심 패키지 | torch 2.10.0+cu130, Triton 3.6.0, NumPy 2.2.6, tokenizers 0.22.2, datasets 5.0.0, transformers 5.14.1 | import·버전만 확인 |
| sparse 패키지 | `nvidia-cusparselt-cu13` 0.8.0 | 설치만 확인; native 호출 `NOT_RUN` |
| FlashAttention | distribution 미검출 | 설치·호환성 `NOT_RUN` |
| Codex fixture | guard 22 PASS·Windows launcher 1 SKIP, compact 14 PASS, environment unit 13 PASS | `STATIC_ONLY` |

`datasets/TinyDataset/**`는 열거·해시·검사하지 않았다. 전체 디렉터리를 옮겼다는 사용자 사실을
보호 데이터 내용 동일성 검증으로 승격하지 않는다. GPU·모델·학습·스모크와 CUDA backend 실제
호출도 하지 않았다.

### 10.2 드러난 이관 결함

`tlm_torch`로 `.codex/check_environment.py`를 실행한 결과는 **32개 중 PASS 30, FAIL 1,
NOT_RUN 1**이었다.

1. `00_WORKING_RULES.md` 양 언어판의 선언일은 2026-09-14인데 이관 mtime은 2026-09-15라
   날짜 검사가 FAIL했다. 내용 변경이 아니라 복사 시각을 의미 변경으로 읽은 오탐이다. Linux
   이관 뒤에는 승인된 B2 계약대로 Git 내용일을 1차 근거, mtime을 보조 경고로 써야 한다.
2. `find_git_bash()`가 Windows `bash.exe`만 찾아 WSL의 `/usr/bin/bash`를 보지 못해 NOT_RUN이다.
   Linux에서는 POSIX bash를 검사하고 Windows 제품명인 Git Bash 검사는 비적용으로 구분해야 한다.
3. 현재 Desktop 작업 메타데이터는 여전히 `Z:\TinyLM`이다. `wsl.exe`로 파일을 읽은 사실은
   WSL agent·sandbox·프로젝트 훅 활성화 증거가 아니다.
4. WSL에는 현재 `rg`와 `pwsh`가 없다. Linux 대체 경로 또는 설치 결정을 별도로 해야 한다.
5. 실험 정본은 Windows `.bat`다. 이번 작업에서는 사용자 지시대로 배치파일을 신설·수정하지
   않았고, WSL에 파일이 있다는 이유로 직접 실행 가능하다고 주장하지 않는다.

### 10.3 Codex Desktop 훅 활성화 절차

Desktop의 agent environment를 Ubuntu WSL2로 고르고
`\\wsl$\Ubuntu\home\uranus\tinyLM`(또는 같은 배포판의 `\\wsl.localhost` 경로)을 프로젝트로
연 뒤 **새 작업**을 시작한다. 현재 `Z:` 기반 작업을 그대로 재사용하지 않는다.

1. workdir `/home/uranus/tinyLM`과 Linux `uname`을 확인한다.
2. `/hooks`에서 project-local `.codex/hooks.json` enabled를 확인한다.
3. 정확한 새 hash와 diff를 검토한 뒤 그 hash만 trust한다.
4. 정상 probe와 루트·`scripts/` 위험 쓰기 차단 probe를 실행한다. 차단은 셸 전 deny이고
   probe 파일이 없어야 한다.
5. WIP 결합, manual compact, 새 작업 auto compact를 각각 확인한다. fixture PASS로
   `ACTIVE_VERIFIED`를 대신하지 않는다.

프로젝트 훅은 프로젝트 `.codex` 계층이 trusted일 때만 로드되고 내용 변경 뒤에는 새 hash 신뢰가
필요하다. Linux에서는 `command`, Windows에서는 `commandWindows`를 쓴다. 현 hooks.json에는
양쪽이 있으므로 Desktop 설정·새 작업·hash 신뢰가 우선이며 훅 파일을 먼저 고칠 근거는 없다.

### 10.4 수정된 단계 계획

| 단계 | 현재 상태 | 다음 조치 | 통과 조건 |
|---|---|---|---|
| M1R 이관 원점 고정 | 사용자 완료·부분 감사 | Windows 트리 보존/읽기전용, HEAD·dirty·artifact 위치 확인 | 정본 1개와 복구 원점 명시 |
| M2R 검사 보수 | 결함 확인·미구현 | 별도 승인 뒤 mtime 오탐·Linux bash 검출을 fixture부터 수정 | `check_environment` FAIL 0 |
| M3 Desktop E2E | `E2E_NOT_RUN` | Ubuntu WSL 새 작업에서 hash 신뢰·probe | 실패·fail-open 0, probe 잔존 0 |
| M4 backend | `NOT_RUN` | 사용자가 `tlm_torch`로 CUDA/cuSPARSELt/Triton/FlashAttention 실제 호출 | 지원·정확성·메모리 분리 |
| M5 교량 | `NOT_RUN` | 동일 checkpoint 평가와 최소 dense 대조 | 품질 자 안, 속도·VRAM 환경별 분리 |
| M6 운영 전환 | 보류 | M2R~M5 뒤 사용자 승인 | WSL 단일 정본과 Windows 사본 역할 확정 |

### 10.5 갱신된 권장안

이미 물리 이관이 끝났으므로 C안의 복제 여부를 다시 결정하지 않는다. **C안의 게이트를 복구
절차로 재해석한 C-R안**을 권장한다. M2R·M3 전에는 Codex 환경을 `ACTIVE_VERIFIED`로 부르지
않고 M4·M5 전에는 Windows 결과를 Linux backend 성능으로 이식하지 않는다. 기존 결과는 버리지
않고 환경 서명을 보존하며 환경 민감 수치만 최소 교량 대조 뒤 다시 해석한다.

## 11. 2026-09-17 승인 구현과 ChatGPT Desktop 전환 절차

이 절은 1~10절의 제안·재감사 뒤 실제 승인·구현한 범위다. 이번 단계에서는 공통 실행
기반만 만들고 개별 실험용 BAT/SH는 만들지 않았다.

### 11.1 구현한 공통 실행 기반

| 항목 | 구현 | 증거 수준 |
|---|---|---|
| Python | `scripts/shell/tinylm_env.sh`: `TINYLM_PYTHON` → 활성 `tlm_torch` → `$HOME/miniforge3/envs/tlm_torch/bin/python`; system fallback 거부 | 정적·회귀 PASS |
| 큐 | 기존 `run_queue.bat`·`experiments.tsv`를 보존하고 `run_queue.sh`·`scripts/queue_menu_linux.py` 추가. 일반 항목은 모두 실행 후 실패 집계, smoke는 `stop`·`collect`·`warn`을 사용자에게 질문 | 감사 오류 0·runnable 6·회귀 10/10 PASS; 실제 큐 `NOT_RUN` |
| Linux 메뉴 | TSV의 native `.sh` 또는 `.bat`와 같은 stem의 `.sh`가 실제로 있을 때만 노출; 실험 companion 자동 생성 금지 | 감사 오류 0; 현재 6건 runnable |
| cleanup | `run_cleanup_checkpoints.sh`: dry-run 뒤 정확한 대문자 `YES`에서만 삭제 단계 진입 | 구문 PASS; 실제 cleanup `NOT_RUN` |
| smoke | `run_smoke_check.sh`: 기존 BAT의 runlog 95개·대기 8개를 엄격 파싱, 미지원 실행문 거부 | parse PASS; GPU·모델 `NOT_RUN` |
| Windows smoke | `run_smoke_check.bat`가 `summarize_smoke.py` 실패를 큐에 반환 | 정적 회귀 PASS; E2E `NOT_RUN` |
| 환경 검사 | POSIX Bash 발견, PowerShell 부재 `NOT_RUN`, WSL mtime 정보값 분리 | mock 회귀 PASS |
| 비밀 경로 | W&B 키는 Windows 기본값 보존, WSL은 `TL_WANDB_KEY_FILE` 명시값만 사용 | 회귀 PASS; 비밀 접근 0 |

Windows BAT는 제거하지 않았다. 개별 실험의 WSL 실행은 별도 승인·preflight 뒤 같은 stem의
`.sh`를 하나씩 작성해야 하며, 이번 구현은 `.bat`를 WSL interop으로 자동 실행하지 않는다.

### 11.2 Desktop 설정 실사

허용된 전역 설정을 읽기 전용으로 확인한 현재 값은 다음과 같다.

```toml
[desktop]
integratedTerminalShell = "wsl"
runCodexInWindowsSubsystemForLinux = false

[windows]
sandbox = "elevated"
```

hook state는 `Z:\TinyLM\.codex\hooks.json`에 묶여 있고 `PreToolUse`, `PreCompact`,
`SessionStart`가 모두 `enabled = false`였다. 즉 통합 터미널만 WSL이며 Codex agent는 아직
Windows runtime이다. 과거 `Z:` hash는 현재 WSL canonical project의 활성·신뢰 증거가 아니다.
저장소 hooks.json은 Linux `command`와 Windows `commandWindows`를 이미 가지므로 소스 변경보다
Desktop runtime 전환과 현재 project identity의 exact-hash 재검토가 먼저다.

### 11.3 ChatGPT Desktop에서 사용자가 수행할 순서

1. Desktop **Settings → Codex**에서 **Run Codex in WSL**을 켠다. 통합 터미널 설정은 대체물이 아니다.
2. 앱이 요구하면 재시작한다.
3. 기존 `Z:` 탭 대신 `\\wsl.localhost\Ubuntu\home\uranus\tinyLM` 또는 같은 위치의
   `\\wsl$\Ubuntu\home\uranus\tinyLM`을 프로젝트로 다시 열고 새 작업을 만든다.
4. 새 작업에서 읽기 전용으로 `pwd`, `uname -a`, `git rev-parse --show-toplevel`,
   `/home/uranus/miniforge3/envs/tlm_torch/bin/python -c "import sys; print(sys.executable)"`를
   확인한다. 기대 루트는 `/home/uranus/tinyLM`, 기대 Python은 지정 `tlm_torch`다.
5. Desktop hook review 화면/명령에서 project-local `.codex/hooks.json`의 출처와 diff를 보고
   세 hook를 enable한 뒤 현재 hash만 trust한다. 공식 문서는 CLI `/hooks`를 명시하므로 Desktop
   빌드가 별도 browser를 노출하지 않으면 통합 WSL 터미널의 Codex `/hooks`로 같은 프로젝트를
   검토한다. 전역 설정 파일에 hash를 수동 복사하지 않는다.
6. 다시 새 작업을 열어 AGENTS 적용, 17 skills, 정상 probe, 루트·`scripts/` 위험쓰기 차단,
   WIP 직접수정 차단, manual/auto compact를 관찰한다. fail-open 0·probe 파일 0이어야 한다.
7. 전부 실제 관찰되기 전에는 WSL Codex를 `ACTIVE_VERIFIED`로 올리지 않는다.

OpenAI 공식 문서상 WSL2에서는 Codex가 native Windows sandbox 대신 Linux 환경에서 실행되고,
저장소는 `/home/...` 아래가 권장된다. Desktop local environment는 저장소 루트 `.codex`에
저장되며, project-local hook는 그 layer가 trusted이고 정확한 현재 hash가 신뢰될 때만 실행된다.

### 11.4 `Z:\TinyLM` 링크의 사용 범위

`Z:\TinyLM` 링크는 Explorer·기존 문서 링크·Windows BAT의 편의 경로로는 충분하다. 그러나
Linux sandbox, hook project identity/hash, ext4 I/O, `tlm_torch` backend, shell 실행권한의
증거는 아니다. 역사 로그·결과·P8 표의 `Z:`는 당시 기록으로 보존하고 활성 지침·실행 코드만
WSL canonical 또는 플랫폼 분기로 갱신한다. 일반 문서를 일괄 치환하지 않는다.

### 11.5 현재 게이트

- M2R 공통 기반: `STATIC_ONLY`; 환경 검사 `PASS 31 / FAIL 0 / NOT_RUN 1`(WSL의 PowerShell parser 부재), 새 회귀·구문 검사 PASS.
- 전체 `check_static_all.py`: 보호 데이터 검사를 포함하므로 이번 범위에서는 `NOT_RUN`.
- M3 Desktop WSL agent runtime: 2026-09-18 새 task의 Linux·WSL2·Ubuntu·Bash 실제 관찰로 `ACTIVE_VERIFIED`.
- M3 PreToolUse 위험쓰기 보호: 요청된 정상 1건과 루트·`scripts/` 차단 2건, Bash·`apply_patch`
  WIP 직접쓰기 deny, 정상 `wip.py` 경로 범위에서 `ACTIVE_VERIFIED`.
- compact: exact WIP hash의 자동 compact 상태 캡슐 주입은 현재 task에서 실제 관찰했다.
  manual compact는 `NOT_RUN`이며, 2026-09-18 사용자가 수행 계획 없음·검증 제외를 결정했다.
  따라서 이 항목은 M3 사용자 승인 범위의 운영 종결을 막지 않지만, 전체 경로 증거는 `PARTIAL`이고
  manual 경로를 `ACTIVE_VERIFIED`로 부르지 않는다.
- `run_smoke_check.sh`: 사용자가 먼저 `202609182225_smoke_4ff08ef.txt`를 실행했다. 전체
  42팔 중 41팔과 모든 모델·합성 팔, 계측 필드 계약은 통과했지만, `check_handoff.py`가 Linux `.sh` 4개를
  `.bat`만 인식하는 코드로 누락해 예상시간을 `0.0h`로 오계산했고 48h 미달 사유도
  없어 종합은 42팔 중 1개 FAIL·summarize exit 1이었다. 파서를 `.bat`/`.sh` 공통으로
  교정하여 합계 `0.4h`와 정당한 미달 사유를 기록한 로컬 커밋 `82dad38`을 만들었다. 이어
  `202609182307_smoke_82dad38.txt`에서 42/42 PASS, exit-0 오류표지 0, 계측 계약 0,
  summarize exit 0을 확인했다. 이후 queue 정책 파일 변경은 이 로그보다 늦으므로 그 변경의
  whole-tree smoke로 소급하지 않으며, 해당 queue 동작은 표적 회귀로 따로 판정한다.
- `run_queue.sh`: 선택한 일반 gate를 실패와 관계없이 모두 순차 실행하고 실패 목록을 합산해
  최종 exit 4로 반환한다. smoke가 선택됐으면 실행 전에 사용자가 `stop`(즉시 중단·실패),
  `collect`(나머지 실행 뒤 실패), `warn`(나머지 실행·smoke만 전체 실패에서 제외) 중 하나를
  명시한다. 이 실행 정책은 실패한 smoke를 PASS로 바꾸지 않는다. 회귀 10/10은 PASS지만 실제
  전체 gate queue는 `E2E_NOT_RUN`이다.
- `run_cleanup_checkpoints.sh`: 사용자 삭제 실행 전용, `NOT_RUN`.
- M4 backend·M5 교량: `NOT_RUN`.

## 12. 2026-09-18 새 WSL task 실제 관찰과 현재 이관 상태

### 12.1 agent runtime과 정적 선결

새 ChatGPT Desktop task에서 저장소 명령이 실제 Linux 환경 안에서 실행되는 것을 확인했다.

| probe | 실제 관찰 | 판정 |
|---|---|---|
| `pwd` | `/home/uranus/tinyLM` | canonical WSL workdir PASS |
| `uname -a` | Linux, Microsoft WSL2 kernel | WSL2 agent runtime PASS |
| `echo "$WSL_DISTRO_NAME"` | `Ubuntu` | 대상 배포판 PASS |
| `command -v bash` | `/usr/bin/bash` | POSIX shell PASS |

사용자는 활성화된 `tlm_torch`에서 정적 선결 결과를 회신했다. 이후 이번 변경을 반영한 상태에서도
같은 환경 검사와 shell 진입점 검사를 다시 실행해 범위를 분리했다.

| 검사 | 회신 결과 | 판정 |
|---|---|---|
| `.codex/check_environment.py` | 초기 회신과 현재 재검사 모두 `checks=32 PASS=31 FAIL=0 NOT_RUN=1` | 정적 선결 PASS; `pwsh` 부재 PowerShell parser 1건은 `NOT_RUN` 유지 |
| `scripts/check_shell_entrypoints.py` | 초기 `4`, 현재 신규 gate `.sh` 포함 `8` PASS | Linux queue·smoke·gate entrypoint 정적 PASS |

정적 PASS는 모델·GPU·smoke의 동적 성공을 뜻하지 않는다. 또한 PowerShell source 검사를 하지
못한 한 건을 PASS로 합산하지 않는다.

### 12.2 hook probe의 실제 결과

사용자는 project hook 전부를 trusted·enabled로 전환했다고 알렸다. UI 상태 자체를 이 task가
별도로 읽은 것은 아니지만, 다음 PreToolUse 동작을 실제 tool call에서 관찰했다.

| 순서 | 요청 | 실제 결과 | 판정 |
|---:|---|---|---|
| 1 | 파일을 만들지 않고 `printf 'a\nb\n'` | `a`, `b` 출력, exit `0` | 정상 명령 허용 PASS |
| 2 | 루트 `.codex/hook-probe.txt` 쓰기 | shell 실행 전에 `Command blocked by PreToolUse hook`; shell exit code 없음 | 사전 deny PASS |
| 3 | `scripts/.codex/hook-probe.txt` 쓰기 | shell 실행 전에 같은 PreToolUse deny; shell exit code 없음 | 사전 deny PASS |
| 잔존 | 보호 경로를 prune한 `find`와 두 정확한 Git 경로 확인 | probe 파일 `0`, Git 상태 `0` | 부산물 없음 |
| 경고 | 세 probe의 hook 출력 | fail-open·`systemMessage` 경고 `0` | fail-open 없음 |

따라서 **현재 hash·현재 WSL task의 요청된 PreToolUse 정상/위험쓰기 범위만**
`ACTIVE_VERIFIED`다. 이후 같은 task에서 WIP 직접쓰기 Bash/apply_patch deny와 정상 `wip.py`
경로도 실제 관찰했지만, 이 결과를 모든 matcher나 manual compact 성공으로 확대하지 않는다.

### 12.2a WIP guard·compact와 최신 smoke 추가 관찰

| 항목 | 실제 관찰 | 판정 |
|---|---|---|
| 허용 WIP 경로 | `scripts/wip.py`를 통한 capsule 갱신 | PASS |
| Bash 직접쓰기 | shell 실행 전에 deny, shell exit code 없음 | `ACTIVE_VERIFIED` |
| `apply_patch` 직접쓰기 | tool 실행 전에 deny, WIP hash 불변 | `ACTIVE_VERIFIED` |
| auto compact | exact 열린 WIP의 8필드 hash-verified capsule 재주입 | 해당 자동 경로 PASS |
| manual compact | Codex가 앱 lifecycle action을 직접 만들 수 없음 | `NOT_RUN`; 사용자 결정으로 검증 범위 제외·실행 불요 |
| 최초 user smoke | `202609182225_smoke_4ff08ef.txt`: 전체 42팔 중 41 PASS·handoff 정책 1 FAIL, 모델·합성 팔과 계약 오류 0, summarize exit 1 | `.sh` 시간 오계산과 미달 사유 누락을 교정한 역사 증거 |
| 교정 후 user smoke | `202609182307_smoke_82dad38.txt`: 전체 42팔 PASS, exit-0 오류표지 0, 계약 0, summarize exit 0 | `82dad38` 범위 PASS; 이후 queue 정책 변경으로 확대 금지 |

직접쓰기 probe 전후 WIP SHA-256은
`1a3f15d66cbc59a58aec9d1182c103f686137633804c98d5e5438c74057087b0`로 같았다. 이 증거는
해당 task·hook hash의 WIP guard와 auto compact 경로에 한정한다. manual compact는 사용자가
검증 범위에서 제외했으므로 운영 종결의 선결은 아니지만, 미실행 경로가 있으므로 M3 전체를
`ACTIVE_VERIFIED`로 승격하지 않는다.

### 12.3 단계별 현재 판정

| 단계 | 2026-09-18 판정 | 남은 것 |
|---|---|---|
| M1R 물리 이관·canonical workdir | 사용자 이관 완료, 새 task workdir `ACTIVE_VERIFIED` | Windows 사본의 장기 역할은 최종 운영 승인 때 확정 |
| M2R 공통 실행 기반 | `STATIC_ONLY` PASS (`31/0/1`, shell entrypoint `8`) | PowerShell source는 별도 Windows 증거 또는 선택적 `pwsh`; 전체 보호 데이터 suite는 미실행 |
| M3a Desktop WSL agent | `ACTIVE_VERIFIED` | 현재 project/runtime가 바뀌면 재검증 |
| M3b PreToolUse 정상·위험쓰기·WIP guard | 관찰한 probe 범위 `ACTIVE_VERIFIED` | 다른 matcher로 일반화 금지 |
| M3c SessionStart·PreCompact·compact | auto compact exact-WIP 재주입 PASS, manual `NOT_RUN`·사용자 제외 | 사용자 승인 범위는 예외 종결; manual 경로를 PASS로 승격 금지 |
| M3d model smoke | `202609182307`의 `82dad38` 범위 42/42 PASS·오류표지 0·계약 0·summarize exit 0 | 이후 queue 정책은 회귀 10/10·shell 8/8로 별도 검증; 현재 dirty tree whole-smoke는 사용자 선택 |
| M4 backend | `NOT_RUN` | CUDA/cuSPARSELt/Triton/FlashAttention 실제 호출과 수치·메모리 |
| M5 교량 | `NOT_RUN` | 동일 checkpoint 평가와 필요시 최소 dense 대조 |
| M6 운영 전환 | 진행 중 | 전체 gate queue 결과·M4·M5 뒤 사용자 최종 승인 |

이관을 한 문장으로 요약하면 **“저장소와 Codex agent는 WSL로 전환됐고 요청된 PreToolUse·
WIP guard·auto compact는 범위별로 작동했으며, `82dad38` 교정 후 smoke도 42/42 PASS지만,
전체 기능 gate queue·backend·Windows↔WSL 교량·최종 전환 승인은 남았다”**다. manual compact는
사용자 결정으로 검증 범위에서 제외되었으며, 그 경로를 PASS로 승격하지 않는다.

### 12.4 다음 순서

1. hooks.json 또는 Desktop project identity가 바뀌지 않았다면 이번 세 probe를 반복할 필요는 없다.
2. 사용자 소유 `./run_queue.sh`를 열고 현재 gate menu id `1 2 3 5`를 함께 선택한다. id `4`
   cleanup은 제외한다. 현재 dirty tree smoke도 다시 보려면 id `0`을 앞에 추가하며, 이 경우
   화면의 `stop`·`collect`·`warn` 설명을 보고 실패 정책을 사용자가 직접 선택한다. 전체 출력을
   회신하고, smoke를 포함했을 때만 새 smoke 로그도 함께 회신한다.
3. manual compact는 사용자 결정으로 검증 범위에서 제외됐으며 재요청 전에는 실행·검증하지 않는다.
   이 예외 종결을 manual 경로 PASS나 M3 전체 `ACTIVE_VERIFIED`로 다시 쓰지 않는다.
4. 일반 gate는 한 queue에서 모두 결과를 수집하되 항목별로 따로 판정한다. `warn`이나 queue
   exit 0은 smoke PASS를 뜻하지 않으며, 실패한 gate의 후속 단계와 M5 교량을 자동으로 열지 않는다.
