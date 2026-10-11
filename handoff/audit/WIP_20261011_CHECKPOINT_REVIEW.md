# WIP 20261011 체크포인트 보관 검토 — Z 호스트 여유 정정과 70개 개별 판정

- 검토일: 2026-10-11. 이번 사용자 A 선택은 목록 판정이며, 실제 체크포인트 삭제·변환·가상디스크 변경을 허가하지 않는다.
- 판정 정본은 [checkpoints.tsv](../../checkpoints.tsv)다. 이 문서는 이유/측정 범위를 설명하며 두 번째 운영 원장을 만들지 않는다.
- 정확 파일별 근거는 [검토 JSON](WIP_20261011_CHECKPOINT_REVIEW.json), 전수 참조/metadata snapshot은 [별도 JSON](WIP_20261011_CHECKPOINT_REFERENCE_SNAPSHOT.json)에 고정했다.
- 체크포인트 본문 로딩·변환·삭제 0. 별도로 허가되어 이미 끝난 P093B 표현 관찰은 재실행하지 않았다.

## 1. 649GiB 보고 오류의 정확한 원인

21:54:26 KST의 파일시스템 조회와 Windows 읽기 전용 조회를 대조했다.

| 측정 대상 | 위치/원천 | 여유 byte | GB(10^9) | GiB(2^30) | 의미 |
|---|---|---:|---:|---:|---|
| Linux ext4 내부 | /home/uranus/tinyLM, /dev/sdd | 697,763,786,752 | 697.76 | 649.84 | WSL 가상 파일시스템 안의 여유 |
| Z 호스트 실제 볼륨 | /mnt/z, Windows Z: | 381,991,079,936 | 381.99 | 355.76 | 실제 호스트의 남은 볼륨 공간 |

Windows 배포판 registry의 Ubuntu BasePath는 `Z:\WSL\Ubuntu`이고 VHD는 `Z:\WSL\Ubuntu\ext4.vhdx`다. Windows Get-Item의 파일 Length는 330,992,451,584byte(파일 논리 길이; 할당 extent 자체를 잰 값은 아님)다.
따라서 Linux의 649.84GiB를 Z드라이브의 실제 여유처럼 보고한 것은 잘못이다. 현재 300M 준비/체크포인트 예산은 **Z 호스트 약355.76GiB에서 다른 쓰기와 안전 여유를 뺀 값**을 기준으로 해야 한다.

WSL의 동적 VHD는 실제 호스트 여유보다 큰 가상 용량을 표시할 수 있다. [Microsoft WSL 설명](https://learn.microsoft.com/en-us/windows/wsl/disk-space)이 이 차이를 명시한다. 이번 보고는 최초 ext4 수치를 버린 것이 아니라 측정 계층을 정정한 것이다.

## 2. 177.83GiB가 모두 현재 실행에 필요한가

**아니다.** 296파일·190,941,956,230byte = 177.83GiB는 실제 보유량이지 필수 최소량이 아니다. 현재 다음 P093B와 chat32 학생 경로가 정확히 고정한 부모 두 개의 합은 1,656,915,302byte = 1.54GiB다. 이것이 프로젝트 전체의 최소 보존량이라는 뜻도 아니다.

- d16 RMS4 부모: P093B 무학습 생성/공유/r64 대응의 같은 native 부모.
- dense chat32 P090B 부모: P106B 300M SFT와 P106D fixed/view 학생의 같은 초기화.
- 별도로 dense 계보·KD 부모, legacy 대조, 노이즈 판정자, 재귀 곡선, CPU/GQA/출처 쌍을 재현하려면 해당 가중치를 더 보존해야 한다.
- JSON/인쇄 손실이 같다는 사실만으로 두 모델의 가중치가 같거나 새 입력 평가가 대체된다고 주장할 수 없다.

일반 학습 저장 경로 [trainer.py](../../tinylm/train/trainer.py)의 blob은 model·cfg·step뿐 아니라 opt, 조건에 따라 opt_muon/ema도 담는다. 따라서 디스크 파일 byte는 배포 모델 가중치 byte·VRAM·RSS와 다르다. 이번에는 본문을 열지 않았으므로 optimizer만 제거하면 몇 GiB가 줄어드는지는 미측정이며, 그런 변환도 실행하지 않았다.

## 3. 참조 확인 범위와 첫 분류

가중치는 읽지 않고 regular/stat metadata, 기존 판정, 417개 학습 JSON의 부모/교사 key, 허용된 코드·계획·SH/BAT 622개를 읽었다. 테스트/검사/plot의 문자열은 실제 소비 literal에서 제외했다.

완전한 파일명만 찾았을 때 미참조처럼 보인 200개·148.89GiB에서 짧은 tag와 동적 경로 조립을 추가로 조사하니 130개가 연결됐다. 따라서 **문자열 참조 없음 = 삭제 가능**으로 판단하지 않았다. 열린 계획의 옛 설명/예약도 실제 현재 실행과 다를 수 있고, 템플릿 조립 경로는 조회에서 빠질 수 있다.

| 처음 역할 분류 | 파일 | GiB | 해석 |
|---|---:|---:|---|
| G0/G1/G3 부모·계보 보호 | 11 | 11.12 | 현 삭제기 보호 대상; 실제 실행 필수와 역사 재현을 다시 구분할 수 있으나 이번에는 유지 |
| 코드/계획에서 파일명·tag 참조 | 151 | 112.36 | 현재 151개 모두 필요하다는 뜻이 아님; 실제 소비/열린 축을 추적해야 함 |
| 위 소비 참조가 확인되지 않은 보관본 | 70 | 51.53 | 이번 A 선택으로 70개를 모두 개별 판정 |
| 이미 후보인 재생성 가능한 smoke | 64 | 2.82 | 정확 regular/보호/소비 확인 후 후보 유지, 삭제하지 않음 |

## 4. 70개 개별 판정 결과와 신규 후보

| 판정 | 파일 | GiB | 이번 동작 |
|---|---:|---:|---|
| 신규 delete 후보 | 9 | 6.79 | 목록만 변경, 실제 파일 보존 |
| 역사 재현 keep | 54 | 41.68 | 기존 포괄 final 문구를 파일별 실제 역할로 교체 |
| hold | 7 | 3.07 | 현재 음성 원형4개 유지 + 옛 영구보존3개를 미확정 후속으로 명확화 |

신규9개는 **같은 가중치의 복제본이 아니라 종료된 연구 분기의 보관 필요성을 낮춘 후보**다. 원 JSON, 원 로그, 고정 수치, 비교 부모와 명령은 보존한다. 실제 삭제하면 해당 팔의 새 입력 추론·가중치 재검증·정확 optimizer resume는 할 수 없고, Git/JSON만으로 가중치를 복구할 수 없다. 사용자의 별도 삭제 승인 전에 정리기를 실행하지 않는다.

| 신규 정확 후보 파일 | GiB | 판정 근거 |
|---|---:|---|
| `m100R1c_ko-en_300M_mC_a01.pt` | 0.71 | 결과042 §12에서 구 TinyLM KD alpha 실험 종결; alpha 곡선/원 JSON/정본 부모 보존 |
| `m100R1c_ko-en_300M_mC_a03.pt` | 0.71 | 결과042 §12에서 구 TinyLM KD alpha 실험 종결; alpha 곡선/원 JSON/정본 부모 보존 |
| `m100R1c_ko-en_300M_mC_a07.pt` | 0.71 | 결과042 §12에서 구 TinyLM KD alpha 실험 종결; alpha 곡선/원 JSON/정본 부모 보존 |
| `m100R1c_ko-en_300M_mC_r20ra_nokd.pt` | 0.71 | 결과041 §17.8에서 해당 reuse-attn 품질 분기 종결; 정상 재귀 비교 부모 보존 |
| `m100s10_ko-en_300M_p092_s1_dense30.pt` | 0.73 | 종료한 P092 팔; 결과083 §9~§13·원 JSON 보존, 후속 진단의 100M 대표3개는 그대로 유지 |
| `m100s10_ko-en_300M_p092_s1_dynamic25.pt` | 0.81 | 종료한 P092 팔; 결과083 §9~§13·원 JSON 보존, 후속 진단의 100M 대표3개는 그대로 유지 |
| `m100s10_ko-en_300M_p092_s1_dynamic50.pt` | 0.81 | 종료한 P092 팔; 결과083 §9~§13·원 JSON 보존, 후속 진단의 100M 대표3개는 그대로 유지 |
| `m100s10_ko-en_300M_p092_s1_static50.pt` | 0.81 | 종료한 P092 팔; 결과083 §9~§13·원 JSON 보존, 후속 진단의 100M 대표3개는 그대로 유지 |
| `m100s10_ko-en_300M_p092_s2_dynamic25.pt` | 0.81 | 종료한 P092 팔; 결과083 §9~§13·원 JSON 보존, 후속 진단의 100M 대표3개는 그대로 유지 |

전체 디스크 판정은 keep214·hold9·delete후보73이다. 기존 smoke64 + 신규9의 합계 후보는 **9.6049GiB**이며 실제 회수량은 **0GiB**다. 이는 Linux 파일의 논리 byte 합계이고 Z 호스트가 즉시 같은 양을 반환한다는 예측은 아니다.

## 5. 보존·보류를 남긴 구체 이유

- 재귀/어순 연구: eq 방문수·블록별/순환 쌍과 R2/R3는 같은 저장 크기라도 다른 학습 함수다. 사용자가 요청한 P070/P070B의 순차·반복·셔플·라우터 비교를 위한 기존 대조 앵커로 보존한다.
- 통계/시드: dnc_r1/r2/r3, 재귀 시드쌍, d8 시드는 기존 분해능·비결정성 추정의 다른 표본이다. 인쇄 val 일치만으로 하나를 복제본으로 삭제하지 않는다.
- 반복 epoch: p300_e1/e2/e4는 같은 corpus를 1/2/4회 본 별도 모델이다. 반복/증강 연구의 비교 근거로 보존한다.
- 레시피·형상·출처·GQA: 300M/600M·LR·RMS/Muon·seed·q_on/off·control/FineWeb2는 조건이 달라 하나의 현재 부모로 대체하지 않는다. 이는 역사 재현 선택이지 지금 학습에 전부 로딩한다는 뜻이 아니다.
- 최근 feedback 학생2개와 P106D v1 fixed/views2개는 현재 실패 원인 대조의 원형이어서 hold다. P106D 두 가중치에 짝 runs/logs JSON이 없다는 이유만으로 삭제하지 않고 결과104의 별도 evidence를 연결했다.
- mC_e128_nc는 품질 분기는 닫혔지만 속도 원인 후속이 미확정, mC_e192svd와 mC_optbf16는 옛 int8/상태 정밀도 후속의 비교 필요가 미확정이다. 영구 keep 대신 hold로 정정했다.

다음 표의 keep은 **현재 machine에 절대 영구 필수**라는 보장이 아니라, 현재 요청에서 재현 가치가 있어 유지한 운영 판정이다. 이를 더 줄일 수 있지만 해당 시드/곡선/구조의 새 평가 재현을 포기하거나 별도 검증한 외부 보관본을 확보하는 결정을 먼저 해야 한다.

## 6. 70파일의 개별 역할과 결과 근거

아래는 검토 스냅샷이며 후속 운영 판정은 checkpoints.tsv만 갱신한다.

| 파일 | 판정 | 역할 | 원결과 근거 |
|---|---|---|---|
| `m100R1c_ko-en_300M_eq_t20_ag8.pt` | keep | 재귀 구조 대조 | [059](../../test_result/059_20260827_P074-단계1-학습팔-넷이-전멸했다-설정이-그룹규약을-두-가지로-답했다.md) |
| `m100R1c_ko-en_300M_mC_a01.pt` | delete | 종료 분기 후보 | [042](../../test_result/042_20260813_P055-단계0-KD감사-A1만-유효하다.md) |
| `m100R1c_ko-en_300M_mC_a03.pt` | delete | 종료 분기 후보 | [042](../../test_result/042_20260813_P055-단계0-KD감사-A1만-유효하다.md) |
| `m100R1c_ko-en_300M_mC_a07.pt` | delete | 종료 분기 후보 | [042](../../test_result/042_20260813_P055-단계0-KD감사-A1만-유효하다.md) |
| `m100R1c_ko-en_300M_mC_cla1_ag4_r20_s2.pt` | keep | 시드/비결정성 판정자 | [039](../../test_result/039_20260809_P052-시드노이즈가-0.0006이다-분해능을-다시-유도해야-한다.md) |
| `m100R1c_ko-en_300M_mC_cla1_ag4_r20_s3b.pt` | keep | 시드/비결정성 판정자 | [039](../../test_result/039_20260809_P052-시드노이즈가-0.0006이다-분해능을-다시-유도해야-한다.md) |
| `m100R1c_ko-en_300M_mC_cla2_ag4_r20_s2.pt` | keep | 시드/비결정성 판정자 | [039](../../test_result/039_20260809_P052-시드노이즈가-0.0006이다-분해능을-다시-유도해야-한다.md) |
| `m100R1c_ko-en_300M_mC_cla2_ag4_r20_s3.pt` | keep | 시드/비결정성 판정자 | [039](../../test_result/039_20260809_P052-시드노이즈가-0.0006이다-분해능을-다시-유도해야-한다.md) |
| `m100R1c_ko-en_300M_mC_cla2_ag4_r30.pt` | keep | 재귀 품질/속도 곡선 | [047](../../test_result/047_20260814_P062-단계0-스케줄을-맞추니-0.2427이-돌아왔다.md), [014](../../test_result/014_20260731003000_P030-CPU추론실측-양자화오버헤드.md) |
| `m100R1c_ko-en_300M_mC_e128_nc.pt` | hold | 미확정 후속 | [060](../../test_result/060_20260828_P075-단계3-E128은-기각이다-랭크로-메모리를-사면-9배-비싸다.md) |
| `m100R1c_ko-en_300M_mC_e192svd.pt` | hold | 미확정 후속 | [030](../../test_result/030_20260807_P046-무KD-E128은-분해능의-20배-랭크축은-볼록하다.md) |
| `m100R1c_ko-en_300M_mC_optbf16.pt` | hold | 미확정 후속 | [035](../../test_result/035_20260807_P022B-단계0-per-tensor로도-FP8은-거의-공짜다.md) |
| `m100R1c_ko-en_300M_mC_r20ra_nokd.pt` | delete | 종료 분기 후보 | [041](../../test_result/041_20260813_P049-깊이가-산것은-MLP고-어텐션은-꺼졌다.md) |
| `m100R1c_ko-en_300M_mC_r30_nokd.pt` | keep | 재귀 품질/속도 곡선 | [047](../../test_result/047_20260814_P062-단계0-스케줄을-맞추니-0.2427이-돌아왔다.md), [014](../../test_result/014_20260731003000_P030-CPU추론실측-양자화오버헤드.md) |
| `m100R1c_ko-en_300M_p106b_s3l_feedback_a_s1337.pt` | hold | 현재 음성 대조 원형 | [101](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md), [104](../../test_result/104_20261010_P106D-규칙학습은-종료만-개선하고-교사는-라벨에-막혔다.md) |
| `m100R1d_ko-en_300M_mC_d36_ag2.pt` | keep | 어텐션 공유/CLA 대조 | [044](../../test_result/044_20260814_P057-어텐션타잉이-깊이의-효율을-5배-올린다.md), [058](../../test_result/058_20260823_P073-CLA2는-공짜가-아니다-어텐션-결과-전부가-교락됐다.md) |
| `m100R1d_ko-en_300M_mC_d36_ag4_cla1.pt` | keep | 어텐션 공유/CLA 대조 | [044](../../test_result/044_20260814_P057-어텐션타잉이-깊이의-효율을-5배-올린다.md), [058](../../test_result/058_20260823_P073-CLA2는-공짜가-아니다-어텐션-결과-전부가-교락됐다.md) |
| `m100_ko-en_300M_dnc_r1.pt` | keep | 시드/비결정성 판정자 | [049](../../test_result/049_20260820_P063-단계0-분해능은-조건마다-18배-다르다.md) |
| `m100_ko-en_300M_dnc_r2.pt` | keep | 시드/비결정성 판정자 | [049](../../test_result/049_20260820_P063-단계0-분해능은-조건마다-18배-다르다.md) |
| `m100_ko-en_300M_dnc_r3.pt` | keep | 시드/비결정성 판정자 | [049](../../test_result/049_20260820_P063-단계0-분해능은-조건마다-18배-다르다.md) |
| `m100_ko-en_300M_eq_t20_ag4.pt` | keep | 재귀 구조 대조 | [059](../../test_result/059_20260827_P074-단계1-학습팔-넷이-전멸했다-설정이-그룹규약을-두-가지로-답했다.md) |
| `m100s10_ko-en-control-v2_300M_p097_ctrl_v2_s2024.pt` | keep | 출처 시드쌍 | [090](../../test_result/090_20260919_P097-세-cache는-완성됐지만-학습은-0step이다.md) |
| `m100s10_ko-en-control-v2_300M_p097_ctrl_v2_s31415.pt` | keep | 출처 시드쌍 | [090](../../test_result/090_20260919_P097-세-cache는-완성됐지만-학습은-0step이다.md) |
| `m100s10_ko-en-fw2_300M_p097_fw2_s2024.pt` | keep | 출처 시드쌍 | [090](../../test_result/090_20260919_P097-세-cache는-완성됐지만-학습은-0step이다.md) |
| `m100s10_ko-en-fw2_300M_p097_fw2_s31415.pt` | keep | 출처 시드쌍 | [090](../../test_result/090_20260919_P097-세-cache는-완성됐지만-학습은-0step이다.md) |
| `m100s10_ko-en_300M_d14_cla2_norecur_muon20.pt` | keep | 레시피/형상/길이 전이 | [078](../../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md), [EXPERIMENT_BASELINES.md](../../docs/EXPERIMENT_BASELINES.md) |
| `m100s10_ko-en_300M_d14_cla2_norecur_rms4_lr15_s2024.pt` | keep | 레시피/형상/길이 전이 | [078](../../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md), [EXPERIMENT_BASELINES.md](../../docs/EXPERIMENT_BASELINES.md) |
| `m100s10_ko-en_300M_d14_cla2_norecur_rms4_lr15_s31415.pt` | keep | 레시피/형상/길이 전이 | [078](../../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md), [EXPERIMENT_BASELINES.md](../../docs/EXPERIMENT_BASELINES.md) |
| `m100s10_ko-en_300M_d14_cla2_norecur_rms4_s2024.pt` | keep | 레시피/형상/길이 전이 | [078](../../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md), [EXPERIMENT_BASELINES.md](../../docs/EXPERIMENT_BASELINES.md) |
| `m100s10_ko-en_300M_d14_cla2_norecur_rms4_s31415.pt` | keep | 레시피/형상/길이 전이 | [078](../../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md), [EXPERIMENT_BASELINES.md](../../docs/EXPERIMENT_BASELINES.md) |
| `m100s10_ko-en_300M_dense_chat32_p106d_ruleviews_v1_s1337_fixed.pt` | hold | 현재 음성 대조 원형 | [101](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md), [104](../../test_result/104_20261010_P106D-규칙학습은-종료만-개선하고-교사는-라벨에-막혔다.md) |
| `m100s10_ko-en_300M_dense_chat32_p106d_ruleviews_v1_s1337_views.pt` | hold | 현재 음성 대조 원형 | [101](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md), [104](../../test_result/104_20261010_P106D-규칙학습은-종료만-개선하고-교사는-라벨에-막혔다.md) |
| `m100s10_ko-en_300M_p060b_q_off_s1337.pt` | keep | GQA/backend 시드쌍 | [088](../../test_result/088_20260919_P060B-forced-GQA는-문턱을-못-넘었지만-default는-살았다.md), [P060B_WSL-native-SDPA-GQA-융합백엔드-재개.md](../../test_plan/P060B_WSL-native-SDPA-GQA-융합백엔드-재개.md) |
| `m100s10_ko-en_300M_p060b_q_off_s2024.pt` | keep | GQA/backend 시드쌍 | [088](../../test_result/088_20260919_P060B-forced-GQA는-문턱을-못-넘었지만-default는-살았다.md), [P060B_WSL-native-SDPA-GQA-융합백엔드-재개.md](../../test_plan/P060B_WSL-native-SDPA-GQA-융합백엔드-재개.md) |
| `m100s10_ko-en_300M_p060b_q_off_s31415.pt` | keep | GQA/backend 시드쌍 | [088](../../test_result/088_20260919_P060B-forced-GQA는-문턱을-못-넘었지만-default는-살았다.md), [P060B_WSL-native-SDPA-GQA-융합백엔드-재개.md](../../test_plan/P060B_WSL-native-SDPA-GQA-융합백엔드-재개.md) |
| `m100s10_ko-en_300M_p060b_q_on_s1337.pt` | keep | GQA/backend 시드쌍 | [088](../../test_result/088_20260919_P060B-forced-GQA는-문턱을-못-넘었지만-default는-살았다.md), [P060B_WSL-native-SDPA-GQA-융합백엔드-재개.md](../../test_plan/P060B_WSL-native-SDPA-GQA-융합백엔드-재개.md) |
| `m100s10_ko-en_300M_p060b_q_on_s2024.pt` | keep | GQA/backend 시드쌍 | [088](../../test_result/088_20260919_P060B-forced-GQA는-문턱을-못-넘었지만-default는-살았다.md), [P060B_WSL-native-SDPA-GQA-융합백엔드-재개.md](../../test_plan/P060B_WSL-native-SDPA-GQA-융합백엔드-재개.md) |
| `m100s10_ko-en_300M_p060b_q_on_s31415.pt` | keep | GQA/backend 시드쌍 | [088](../../test_result/088_20260919_P060B-forced-GQA는-문턱을-못-넘었지만-default는-살았다.md), [P060B_WSL-native-SDPA-GQA-융합백엔드-재개.md](../../test_plan/P060B_WSL-native-SDPA-GQA-융합백엔드-재개.md) |
| `m100s10_ko-en_300M_p092_s1_dense30.pt` | delete | 종료 분기 후보 | [083](../../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md), 진단 코드 ARMS |
| `m100s10_ko-en_300M_p092_s1_dynamic25.pt` | delete | 종료 분기 후보 | [083](../../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md), 진단 코드 ARMS |
| `m100s10_ko-en_300M_p092_s1_dynamic50.pt` | delete | 종료 분기 후보 | [083](../../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md), 진단 코드 ARMS |
| `m100s10_ko-en_300M_p092_s1_static50.pt` | delete | 종료 분기 후보 | [083](../../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md), 진단 코드 ARMS |
| `m100s10_ko-en_300M_p092_s2_dynamic25.pt` | delete | 종료 분기 후보 | [083](../../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md), 진단 코드 ARMS |
| `m100s10_ko-en_300M_p106b_s3k_feedback_chat32_s1337.pt` | hold | 현재 음성 대조 원형 | [101](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md), [104](../../test_result/104_20261010_P106D-규칙학습은-종료만-개선하고-교사는-라벨에-막혔다.md) |
| `m100s10_ko-en_600M_d14_cla2_norecur_rms4_t600.pt` | keep | 레시피/형상/길이 전이 | [078](../../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md), [EXPERIMENT_BASELINES.md](../../docs/EXPERIMENT_BASELINES.md) |
| `m100s12_ko-en_300M_d16_cla2_norecur_muon20_s2.pt` | keep | 레시피/형상/길이 전이 | [078](../../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md), [EXPERIMENT_BASELINES.md](../../docs/EXPERIMENT_BASELINES.md) |
| `m100s12_ko-en_300M_d16_cla2_norecur_rms4_s2.pt` | keep | 레시피/형상/길이 전이 | [078](../../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md), [EXPERIMENT_BASELINES.md](../../docs/EXPERIMENT_BASELINES.md) |
| `m100s12_ko-en_300M_d16_cla2_r20_p12_t300.pt` | keep | 독립 깊이/heldout 대조 | [067](../../test_result/067_20260831_P079-깊이는-20층에서도-포화하지-않았고-8층-dense-가-20층-타잉과-동급이다.md), [075](../../test_result/075_20260905_P088-토큰은-스텝이었고-full-val-은-학습데이터였다.md) |
| `m100s12_ko-en_300M_d16_dense_s2.pt` | keep | 독립 깊이/heldout 대조 | [067](../../test_result/067_20260831_P079-깊이는-20층에서도-포화하지-않았고-8층-dense-가-20층-타잉과-동급이다.md), [075](../../test_result/075_20260905_P088-토큰은-스텝이었고-full-val-은-학습데이터였다.md) |
| `m100s12_ko-en_600M_d16_cla2_norecur_rms4_t600.pt` | keep | 레시피/형상/길이 전이 | [078](../../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md), [EXPERIMENT_BASELINES.md](../../docs/EXPERIMENT_BASELINES.md) |
| `m100s14_ko-en_300M_d18_cla2_norecur_muon20.pt` | keep | 레시피/형상/길이 전이 | [078](../../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md), [EXPERIMENT_BASELINES.md](../../docs/EXPERIMENT_BASELINES.md) |
| `m100s14_ko-en_300M_d18_cla2_norecur_rms4.pt` | keep | 레시피/형상/길이 전이 | [078](../../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md), [EXPERIMENT_BASELINES.md](../../docs/EXPERIMENT_BASELINES.md) |
| `m100s14_ko-en_600M_d18_cla2_norecur_rms4_t600.pt` | keep | 레시피/형상/길이 전이 | [078](../../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md), [EXPERIMENT_BASELINES.md](../../docs/EXPERIMENT_BASELINES.md) |
| `m100s2_ko-en_300M_eq_d6_r80.pt` | keep | 재귀 구조 대조 | [059](../../test_result/059_20260827_P074-단계1-학습팔-넷이-전멸했다-설정이-그룹규약을-두-가지로-답했다.md) |
| `m100s4_ko-en_300M_d8_dense_s2.pt` | keep | 시드/비결정성 판정자 | [039](../../test_result/039_20260809_P052-시드노이즈가-0.0006이다-분해능을-다시-유도해야-한다.md) |
| `m100s4_ko-en_300M_d8_dense_s3.pt` | keep | 시드/비결정성 판정자 | [039](../../test_result/039_20260809_P052-시드노이즈가-0.0006이다-분해능을-다시-유도해야-한다.md) |
| `m100s4_ko-en_300M_eq_d8_r20.pt` | keep | 재귀 구조 대조 | [059](../../test_result/059_20260827_P074-단계1-학습팔-넷이-전멸했다-설정이-그룹규약을-두-가지로-답했다.md) |
| `m100s4_ko-en_300M_eq_d8_r30.pt` | keep | 재귀 구조 대조 | [059](../../test_result/059_20260827_P074-단계1-학습팔-넷이-전멸했다-설정이-그룹규약을-두-가지로-답했다.md) |
| `m100s4_ko-en_300M_eq_d8_r60.pt` | keep | 재귀 구조 대조 | [059](../../test_result/059_20260827_P074-단계1-학습팔-넷이-전멸했다-설정이-그룹규약을-두-가지로-답했다.md) |
| `m100s8_ko-en_300M_d12_cla2_norecur_muon20.pt` | keep | 레시피/형상/길이 전이 | [078](../../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md), [EXPERIMENT_BASELINES.md](../../docs/EXPERIMENT_BASELINES.md) |
| `m100s8_ko-en_300M_d12_cla2_norecur_rms4.pt` | keep | 레시피/형상/길이 전이 | [078](../../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md), [EXPERIMENT_BASELINES.md](../../docs/EXPERIMENT_BASELINES.md) |
| `m100s8_ko-en_300M_d12_cla2_r20_adamw.pt` | keep | 레시피/형상/길이 전이 | [078](../../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md), [EXPERIMENT_BASELINES.md](../../docs/EXPERIMENT_BASELINES.md) |
| `m100s8_ko-en_300M_d12_cla2_r20_muon20_s2.pt` | keep | 레시피/형상/길이 전이 | [078](../../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md), [EXPERIMENT_BASELINES.md](../../docs/EXPERIMENT_BASELINES.md) |
| `m100s8_ko-en_300M_d12_cla2_r20_p300_e1.pt` | keep | 1/2/4epoch 대조 | [073](../../test_result/073_20260904_P087-두-번째-epoch은-과적합-없이-0.1155를-준다.md) |
| `m100s8_ko-en_300M_d12_cla2_r20_p300_e2.pt` | keep | 1/2/4epoch 대조 | [073](../../test_result/073_20260904_P087-두-번째-epoch은-과적합-없이-0.1155를-준다.md) |
| `m100s8_ko-en_300M_d12_cla2_r20_p300_e4.pt` | keep | 1/2/4epoch 대조 | [073](../../test_result/073_20260904_P087-두-번째-epoch은-과적합-없이-0.1155를-준다.md) |
| `m100s8_ko-en_300M_d12_cla2_r20_rms4_s2.pt` | keep | 레시피/형상/길이 전이 | [078](../../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md), [EXPERIMENT_BASELINES.md](../../docs/EXPERIMENT_BASELINES.md) |
| `m100s8_ko-en_300M_d12_dense_s2.pt` | keep | 독립 깊이/heldout 대조 | [067](../../test_result/067_20260831_P079-깊이는-20층에서도-포화하지-않았고-8층-dense-가-20층-타잉과-동급이다.md), [075](../../test_result/075_20260905_P088-토큰은-스텝이었고-full-val-은-학습데이터였다.md) |
| `m100s8_ko-en_600M_d12_cla2_r20_muon20_t600.pt` | keep | 레시피/형상/길이 전이 | [078](../../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md), [EXPERIMENT_BASELINES.md](../../docs/EXPERIMENT_BASELINES.md) |
| `m100s8_ko-en_600M_d12_cla2_r20_rms4_t600.pt` | keep | 레시피/형상/길이 전이 | [078](../../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md), [EXPERIMENT_BASELINES.md](../../docs/EXPERIMENT_BASELINES.md) |

## 7. 검증·공간 반환의 한계

- metadata 재실사296개·파일 byte 총합 일치, 심볼릭 링크/새 가중치 생성 없음.
- `ckpt_audit.py` 조회: 디스크296/표600행·누락0. 전체600행에는 이미 디스크에 없는 역사 행도 있으므로 이를 현재 파일 수로 세지 않는다.
- 현 후보73은 부모/교사 보호와 실제 소비를 다시 확인했다. 미래 삭제 직전에는 실행 중 writer·최신 TSV·계보·inode/mtime/크기를 재검증해야 한다.
- WSL 파일 삭제 후 호스트 공간 반환은 sparse VHD 상태/압축 등에 따라 달라진다. 현재 sparse 상태와 실제 회수량은 미측정이며, WSL shutdown/fstrim/compact를 실행하지 않았다. [Microsoft sparse VHD 설명](https://devblogs.microsoft.com/commandline/windows-subsystem-for-linux-september-2023-update/), [compact vdisk 조건](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/compact-vdisk)을 참고한다.
- Ubuntu 안의 파일을 같은 Z드라이브의 다른 폴더로 단순 이동하면 저장 위치만 바뀌므로 호스트 전체 절감 방법으로 보장하지 않는다.
- 타 세션 WIP·보호 TinyDataset·HF/cache/원본 체크포인트를 수정하지 않았다.

### 현재 정적 검증

동일 작업의 전수 정적검사는 `tlm_torch` Python으로 67종 PASS/오류0/권한 밖7종 NOT_RUN이다. [환경 감사](WIP_20261011_EXECUTION_DISK_ENV_STATIC_AUDIT.json)와 [시스템 Python 첫 실패 원형](WIP_20261011_EXECUTION_DISK_STATIC_AUDIT.json)을 함께 보존한다. 첫 실패3개는 시스템 Python에 torch/numpy가 없어서였으며, 패키지 설치나 검사 면제 대신 이미 제공된 환경에서 재검증했다. WIP 회귀28·TSV 이관 회귀4·합성 정리기5경우도 통과했다. 실제 체크포인트 삭제나 새 smoke의 증거는 아니다.
