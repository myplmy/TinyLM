# AdaMuon 저자 NS 괄호와 V·정규화 정밀도를 분리한다

사용자158·원장55/56의 모델 없는 CPU 후속이다. 기존 FP32 V 실제 비용과 본학습 결과는 재실행하지 않는다. 기존 optimizer/trainer·실행 중 동결 소스를 수정하지 않고 새 수치 helper/시험/driver와 별도 evidence만 만든다.

## 권한·영향과 세 대안

| 안 | 내용 | 장점 | 한계·비용 |
|---|---|---|---|
| A | 기존 FP32 V 기술 결과만 유지 | 중복 실행 없음 | 공식 BF16 차이와 NS 괄호가 섞인 채 남음 |
| B | 같은 합성 행렬/gradient의 NS2×tail2 CPU 요인 대조 | 두 수치 축을 분리하고 실제 state 크기를 검산 | 모델/전체 trainer·품질·GPU 속도는 설명하지 못함; 선택 |
| C | 공식 분산 optimizer/새 본학습 실행 | 통신과 학습 효과까지 측정 가능 | 현재 GPU 자동검토/정식교과·추가300M 경계와 별도 환경 선결; 보류 |

새 쓰기 허용목록은 `scripts/p005b_adamuon_precision.py`, `scripts/test_p005b_adamuon_precision.py`, `scripts/diag_p005b_adamuon_precision.py`, `test_result/evidence/p005b_adamuon_precision_v1_20261117`, 현재 감사/계획·결과078·문서 연쇄다. 입력은 공개 저자 코드 판독 metadata와 기존 Muon/AdaMuon source SHA 및 새 합성 텐서뿐이다. 원 모델·데이터/CP/원로그·기본 trainer/flag는 바꾸지 않는다. CPU arithmetic만 수행하며 설치·다운로드/새 환경/학습/모델/GPU0이다.

## 1. 왜

기존 TinyLM 적응판은 FP32 V와 기존 NS를 사용한다. 저자 source를 현재 GitHub 도구로 읽어 commit `9c1ba5be86ebd7dd7464a0bc43b28daccf40279e`와 같은 main blob을 확인했다. 코드 blob `dd194bdb7fccf6bab5b5cfed3b3cba0df059c2af`, 그룹 blob `947149a50db6eaae92be9feddc8346ea874eb3a5`, Apache2 LICENSE blob `261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64`다. 예전의 main revision 미확인 기록은 당시 상태로 보존한다.

[저자 고정 코드](https://github.com/Chongjie-Si/AdaMuon/blob/9c1ba5be86ebd7dd7464a0bc43b28daccf40279e/adamuon.py)의 NS는 세제곱 항에서 scalar를 첫 Gram에 먼저 곱한다. 기존 NS는 Gram 제곱 뒤 scalar를 곱한다. 실수 대수식은 같지만 BF16의 곱셈/반올림 순서는 다르다. 저자 코드는 NS 이후 V·분모/최종 정규화도 BF16이며 기존 적응판은 FP32다. 이들을 V dtype 하나의 차이로 부르면 안 된다.

## 2. 질문

같은 FP32 master/gradient·모멘텀·NS5/계수·beta/Nesterov/WD에서 NS 괄호와 tail 정밀도 각각은 update/상태를 얼마나 바꾸는가? 네 조합의 첫 단계와 누적5단계, 영·None 정책 및 state6B/8B의 구분을 확인한다. None은 현재 helper의 범위 밖이고 별도 optimizer 계약으로 남긴다.

## 3. 예측

FP32 tail+기존 NS는 현 AdaMuon 클래스의 같은 합성 입력과 비트 동률일 것으로 예상한다. BF16 tail은 차이가 날 수 있으며 공식 괄호의 차이도 별개로 나타날 수 있다. 어느 쪽도 품질 우월/가속을 예측하지 않는다.

## 4. 단계

경계/상태·전치·sign/스케일 불변과 원값 보존의 CPU 계약을 먼저 확인한다. 고정 seed1337·3×7/7×3/8×8/32×64/64×32 다섯 형상·Nesterov 두 분기의 같은 gradient5회를 네 조합에 대응한다. 기존 FP32 V 클래스는 같은 합성 자료에만 대조하고 실제 모델 gradient의 완료 비용 진단은 반복하지 않는다. 각 단계 parameter·momentum/V/update SHA와 원소차이/유한·state bytes를 기록한다. 공식 분산 코드를 import/실행하지 않는다.

## 5. 판정

기존 NS/FP32 tail의5단계가 원 클래스와 비트 동일하고, 네 조합 전수의 유한/입력 불변·정확 state 크기와 실제 종료가 닫히면 이 수치 대조 완료다. 두 축의 효과는 같은 tail/NS끼리 비교한다. BF16 tail은 V와 분모/정규화 모두 바뀌는 축이며 V만의 순수효과로 부르지 않는다. 통신·None·state_dict·제품 trainer/공식 전체 실행은 NOT_RUN이다.

## 6. 비용

기존 CPU 환경·Torch2/interop1·최대300초/가용RAM1GiB·JSON20MB·작은 최종 NPZ다. CPU 시간/시점RSS는 기록하되 원 GPU 비용이나 정상상태 throughput과 비교하지 않는다. 원 모델/가중치/자료 읽기·body forward·학습·GPU0이다.

## 7. 실행

runlog078로 `unittest`→`diag_p005b_adamuon_precision prepare`→동결 source 보존→CPU `actual`→저장 readback 순서다. 새 학습 BAT/SH는 만들지 않는다. 현재16:40/17시 경계를 유지한다.

## 8. 한계

합성5형상/5gradient는 실제 전체 모델의 분포가 아니다. 저자의 분산/buffer 할당·4D convolution·파라미터 그룹·None assertion·통신 비용은 구현하지 않는다. 2D local helper의 V shape는 master와 같고 저자 flattened V와 원소/byte 대응만 한다. 저자 전체 optimizer exact port나 성능/본학습 품질 재현으로 부르지 않는다.

## 9. 이력

기존20+3 CPU/17.752초 GPU 기술 결과는 재사용한다. 새6계약/prepare/actual/저장readback은모두실제0이다. 실제200 local step/50기존클래스 합성step·원값불변/정확state6/8B와두축차이는관측했다. 다만 클래스동률은torch.equal 원소값검사였고 원계획의엄격한비트게이트는미계측/NOT_RUN이다. 전체기술입장으로승격하지않으며원소값동률과비트동률을구분한다. [결과078 §20](../../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md#p005b-adamuon-precision-factors)이실제수치·정정/한계를소유한다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

**후속 비트 계측 복구:** 원Wc의원소값검사만으로비트동률을단정한표현은정정/보존했다. 새We는원N0T0/클래스50단계만복원해양쪽uint8 view·150SHA=원저장150SHA를확인했고14:51:26KST 실제0·0.683902초다. 나머지세정책/전체4요인·실제모델gradient비용반복0이다. 원엄격비트게이트는이후속증거로통과했고현재합성local기술범위만닫았다. 최초미계측/원report필드과장과본학습·공식분산/제품통합미완은남긴다. 결과078§20.2가소유한다.
