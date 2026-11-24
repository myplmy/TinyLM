# DVLM 실제 음성과 같은 첫 표본의 종료/형상 진단

## 관측과 복구 가능한 범위

원 Stage7dv0Wd는실제exit1이다. 첫KO alm_000000의845 PTS/294그룹을측정한뒤원tol에서teacher445원소/private444원소·104그룹이실패해나머지7개를중지했다. 표본JSON과6.45MB벡터는보존됐지만마지막loading_info의set직렬화오류로main report가쓰이지않았다. 종료후NVML점조회에는compute PID가없었다. 원v1의최종메모리해시/allocator값은닫힌과정에서회수할수없으며추정하지않는다.

[독립 저장벡터 판독](../../handoff/audit/research_20261117_01a1e647/DVLM_NATIVE_PARTIAL_READBACK_v1.json)은같은원tol의teacher445/private444/104그룹을재확인했다. 같은첫token의두표준causal참조(물리길이419/1)도1원소미달이지만같은PTS안의같은token/위치/한token문맥은정확일치했다. 따라서계산형상의영향을의심할근거가있으나모든차이의원인이나mask정합을확정하지않는다. 원음성은그대로다.

## 세 대안

| 안 | 이득 | 제약 | 판단 |
|---|---|---|---|
| A | 저장음성/해제점조회만기록 | 모델재실행0 | 실제출력head SHA와종료메모리증거는계속없음 |
| B, 선택 | 원첫표본1개만별도version에서종료기록/형상대조 | 같은수학/문턱으로보고서와계산형상대조를회수 | fresh진단이며원v1의누락을소급복구하지않음 |
| C | 문턱완화또는원8전체재개 | 빨리통과한표를만들수있음 | 원게이트/실패정책에어긋나수행하지않음 |

## 새 version의 정확 변경

`diag_p106b_dvlm_native_closure_v2.py`는원v1소스/profile/벡터를수정하지않는다. 별도Python과정에서출력BASE/PROFILE/SCHEMA와추가source목록만새namespace로결합한다. source/time/input/원tol guard는수정하지않고먼저원v1 verify를통과해야한다. 원8개의사전순서를읽되정확첫음성표본만선택한다. 바뀐순서/양성/다른표본은거부한다.

보고writer는기존검증된`diag_p106b_external_core6.write_json`을재사용해set을무손실목록으로정규화한다. 모든write는새namespace로제한하고원v1에는쓰지못한다. main report는expected_cases1·원7NOT_RUN을반드시표시하며다시직렬화가실패해도원primary상태/exit를최소실패JSON에남긴다. 원고정`native_case`를호출하고원passed게이트를바꾸지않는별도형상대조만추가한다.

형상대조는같은native419 token뒤에masked padding을붙여845길이로만든표준causal경로다. 원419대padded845,PTS native대padded845와첫token참조를같은atol1e-5/rtol1e-4에서기록한다. 이대조가통과해도원래unpadded참조게이트나전체8개가통과한것으로바꾸지않는다.

## 영향과 권한

사용자158의17시승인안에서새wrapper/6계약·새profile/evidence·런처와소유문서만추가한다. 원제품·모델/CP/토크나이저·입력·frozen v1·타정제·보호데이터·설치/Git/삭제는변경하지않는다. 코드축은실행과정내명시binding과writer범위에한정하고검사축은lossless set/범위밖거부/8개오표기거부/보조실패보존/첫음성선택이다. 데이터축은같은원첫표본,문서축은계획/원로그/결과/원장,부채축은동결v1과새진단을분리하는것이다. GPU는직렬이며원최대20분/16:40새계산중지/17시회수와정확free VRAM8GiB입장을유지한다.

새6계약후원native6을새binding에서확인한다. 이전PTS21은동결해계승하며반복하지않는다. 새진단의모델state/head SHA·원source·해제는fresh증거로기록한다. head mapping/학습과전체DVLM품질은여전히별도선결이다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 준비v2의 추가 형식 실패와 명시v3

v2의새6/원native6은모두통과했으나profile writer가실제`torch.__version__`의문자열하위형`TorchVersion`을거부해prepare1로끝났다. GPU/실물모델은0이며v2 initial_plan만있고profile은없다. 원v2 source/실패raw/partial namespace를보존한다.

별도`diag_p106b_dvlm_native_closure_v3.py`/새namespace는문자열하위형만primitive str로무손실정규화한다. 임의객체를문자열로감추거나nonfinite값을허용하지않는다. 새7번째시험은가짜문자열대신실제runtime_identity 전체를직렬화한다. 새7+원native6을해당binding에서확인하고기존PTS21을계승한다. 같은첫음성1개/원문턱/7NOT_RUN/20분·16:40/17시경계는바꾸지않는다. 이것은준비형식수정이며원수치음성의통과나전체suite재개가아니다.

## v3 회수와 모델 없는 작업공간 진단

v3 actual은11:00:28KST exit9다. 보고서저장은성공했고원teacher445/private444음성은재현됐다. source/assets불변·실제모델state동일·출력head SHA/tied/key와모델해제를회수했다. 같은845길이표준padded causal과PTS native419행은정확동률이고419대845 표준참조는원문턱445원소미달이다. 원unpadded게이트를PASS로바꾸지않는다.

종료allocator33554432B/reserved62914560B가남아엄격해제게이트는실패했다. [설치판과같은Torch2.10의원소스](https://github.com/pytorch/pytorch/blob/v2.10.0/aten/src/ATen/cuda/CublasHandlePool.cpp)는환경값의SIZE×1024×COUNT를작업공간으로잡고과정내map을clear하는함수를제공한다. 현재`:4096:8`의계산값은32MiB이고설치판의clear API존재를CUDA초기화없이확인했다. 이계산만으로실제원인을확정하지않는다.

세대안은원값을설명없이남기기,모델없는작은행렬1회로작업공간가설을검증하기,같은모델을다시실행하기다. 두번째를선택한다. 소유GPU과정의64×64 FP32곱1회후tensor/empty_cache만제거한값과기존process-local cuBLAS clear후값을비교한다. 모델/CP/학습0·60초상한·새namespace에관측값만기록한다. 전역GPUreset/다른과정cache/라이브러리소스·환경파일은변경하지않는다. 예상32MiB와다르면그값을그대로보존한다. 원v3의exit9와원수치음성은변경하지않으며전체smoke/E2E로부르지않는다.
