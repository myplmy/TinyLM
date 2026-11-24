# 별도 byte head의 CPU 초기값·미분 계약

사용자158/원장63의독립CPU선결이다. BabyLM GPU평가와다른과제이며거절된평가를대체/우회하지않는다. 모델본체/체크포인트실행/GPU0,정확한기존safetensors의head행렬하나만읽는다. 원strict/HPA음성과별도byte정책을유지한다.

| 안 | 내용 | 장점 | 한계·영향 | 비용 |
|---|---|---|---|---|
| A | 매핑명세만보존 | 추가tensor계산없음 | 초기값/미분은계속미확인 | 완료재사용 |
| B | CPU에서정확head tensor1개/새32768행mean과전체FP64oracle·작은head-only VJP | 모델본체없이값·분모·동결배선을검증 | 합성hidden이므로언어품질/HPA/학생학습과다름 | 최대5분/약4GiB,선택 |
| C | teacher/student모델또는GPU를열어native입장/학습 | 후속실물검증가능 | 현재GPU검토거절과원HPA음성때문에보류 | 수행안함 |

권한/영향:새CPU driver/evidence·결과/원장/계획만신설·갱신한다. 기존`p106b_dvlm_head.initialize_head`/`independent_row_oracle`/`head_gradient_probe`와기존6CPU계약을재사용하고고정소스는바꾸지않는다. 새부분은정확BF16tensor하나의선택읽기/FP32 source SHA 대조·전체행oracle/독립FP64 head VJP·소유참조해제와자원기록이다. 원HF파일/CP/tokenizer/cache/다른세션은읽기외변경없음이다. 새로운head나gradient tensor는메모리에만존재하고가중파일/CP는저장하지않는다. 데이터마이그레이션·새runtime/패키지·GPU영향없음이다. 문서정본은101/원P106B·기준표·방법론/COMPASS/목록이다. 비교는고정초기화계산대독립계산이며학습이득판정이아니다. 후속의native HPA/본학습품질은여전히미완이다.

## 1. 왜

새byte정책은전체32768매핑명세와독립byte검산까지만닫았다. 실제초기head값이원teacher행평균과맞고head-only 미분이teacher/hidden/값을수정하지않는지확인한다.

## 2. 질문

원teacher head SHA를재구성하는가? 전체32768행이별도CPU FP64평균과원tol에서같은가? 전체32768 logits에대한head gradient가독립FP64공식과같고원tensor/hidden은불변인가?

## 3. 예측

실제행렬도기존작은6계약과같은평균/미분을기대하나BF16→FP32 source SHA·큰행수/mean누적·전체어휘softmax차이가실패할수있다. 원atol1e-5/rtol1e-4를완화하지않는다. 성공도합성hidden의배선이며품질예측이아니다.

## 4. 단계

1. 기존CPU6/source SHA·새byte명세/독립검산·teacher originalasset SHA를확인한다. safetensors header에서`model.embed_tokens.weight`의BF16/[151936,1024]와config tying을고정한다.
2. CPU가용4GiB/5분gate뒤safetensors에서그tensor하나만읽어FP32로바꾼다. rawFP32 SHA는원native보고의81B47D…4E7과정확같아야한다. 어떤모델클래스도만들지않는다.
3. 기존chunk128 mean init으로32768×1024 FP32새Parameter를만들고기존독립row oracle가모든행의CPU FP64mean을직접계산한다.
4. 고정8basis hidden은열0/1/2/17/127/255/511/1023에0.125/0.25를교대로넣는다. target은byte행처음4개+shared행처음2개+native ID0/32767로출력전에정한다. head-only full32768 CEmean/backward1회·optimizer0을수행한다. 별도FP64 fullsoftmax/onehot/mean outer-product VJP와원tol대조한다.
5. teacher/hidden/head원값SHA불변·teacher/hidden grad없음·모든grad finite/nonzero·torch CUDA미초기화·CPU참조해제를확인하고metadata만저장한다.

## 5. 판정

원sourceSHA/전체행oracle/독립VJP/불변·동결/모델0·GPU0·참조해제가필수다. 실패와실제종료를보존한다. 전체HPA통과·원7재개·언어품질/새학습이득·배포메모리는판정하지않는다.

## 6. 비용

CPU최대5분/가용RAM4GiB선결·source1.192GB파일읽기/선택BF16head311164928B·FP32teacher622329856B·새head134217728B/동일크기grad다. 전체RSS는직접기록하고이합계를실측RSS나배포footprint로쓰지않는다. JSON20MB이하/새head가중파일0이다.

## 7. 실행

기존CPU환경의새`diag_p106b_dvlm_head_byte_values.py prepare/actual`만runlog101로기록한다. 학습배치나GPU명령은만들지않는다. CPU전체가현재16:40경계전에들어와야한다.

## 8. 한계

합성hidden8개/한backward는native학생본문이나HPA·교사연산비/본학습안정성을검증하지않는다. 초기byte평균의언어의미·실제새품질도미확인이다. PyTorch CPU할당/OS RSS와모바일상주/packed저장/KV를구별한다.

## 9. 이력

앞선byte명세/독립검산완료를재사용한다. 현재실제weight init/VJP는NOT_RUN이다. 새source/profile와정확head source를봉인한뒤에만수행한다.

preflight:학습0/모델0으로training steps/pool계산적용없음이다. 새tag/source·전체32768행/동결·독립oracle/원tol·CPU예산을명시한다. 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.


### 실제·예측 대조

13:21:28~35KST CPU실제6.913215초/종료0이다. exact원teacher FP32 SHA가같고전32768행평균의위반행0/최대차1.8626451492e-9·합성8 fullhead VJP의위반원소0/최대차1.4779288904e-12로원tol을통과했다. 원teacher/hidden/newhead값불변·teacher/hidden grad없음·소유tensor참조해제/CUDA미초기화다. 단계1~5의기술범위완료/§3의값·미분예측은이조건에서관측했다. 모델본문/실제native학생학습/언어품질·원HPA통과는그대로미검증이다. 원helper의GPU참조문구는일반문구이고이번tensor device는모두CPU다. [결과101§624](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-head-byte-values-cpu).
