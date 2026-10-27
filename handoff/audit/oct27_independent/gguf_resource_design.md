# GPT2 GGUF 생성 자원 후속 — 실행 전 영향도와 선택

사용자96/97의 27일17시 CPU/GPU 권한에서 미완68의 남은 GPT2 자원을 확인한다. 기존18자원행/공식Core6를 다시 실행하지 않는다. 추가300M 금지·새취득/설치·원본변경·타정제편집·Git변경 제외를 유지한다.

대안A는 기존 Core6 op4를 토큰마다 호출하는 것이다. 구현은 가장 작지만 매번 KV를 비우고 prefix 전체를 다시 계산해 기존 cache-on 생성과 비교할 수 없다. B는 llama-bench/CLI의 처리율만 쓰는 것이다. 준비는 작지만 같은 질문의 실제 선택·TTFT·관찰/비관찰 ID 대응이 부족하다. **C는 기존 wire/소유정리 코드를 재사용한 별도 cache-on 생성 worker**다. 새 구현/회귀가 필요하지만 기존 평가 계약을 바꾸지 않고 원하는 자원을 확인할 수 있어 C를 선택한다.

총괄만 새 C++/Python/시험/프로필/SH를 작성한다. 정/반 보조는 지정 코드·API·작은 메타데이터를 읽기만 한다. 기존 C++/Core6의 source/기한/수치 guard는 변경하지 않는다. 기존 C++는 main을 다른 이름으로 포함해 wire/frame/deadline 도구만 재사용하고 옛 Runtime/옛 main은 새 모델 실행에서 호출하지 않는다.

대상은 이미 로컬인 enacimie GPT2 Q4_K_M의 고정 revision/바이트SHA다. llama-b11396의 기존 shared libraries와 고정 헤더를 재사용하며 새 compiler/package는 설치하지 않는다. 새 worker/binary는 자기 감사 경로에만 생성한다. CPU1은 GPU/KQV/op offload를 끄고 CUDA2는 GPU backend를 실제 확인한다. prefill512 batch→한토큰 cache-on, seq0/절대position, F32 KV/flash off/MTPoff, greedy다.

같은 의미의 한국어/영어 원문을 native token128/512로 맞추고 고정32의 워밍업1/무관찰3/관찰3을 대응한다. 자연4문항은64상한·실제EOS50256을 쓴다. 토크나이저가 달라 최종문자열까지 동일하다고 주장하지 않는다. observer는 native 실제argmax 시각과 IPC 수신시각을 모두 저장하며 native TTFT와 전체 wall TTFT를 분리한다. 자연답의 품질은 별도 정성관찰이며 새 벤치마크 점수가 아니다.

같은8토큰 prefix에서 cache-on/logits 경로와 fullprefix 재계산을 제한적으로 대응해 KV/위치오류를 찾고, 관찰/비관찰32 ID·종료를 비교한다. 불일치나오류/해제실패는9, 시간선결부족은8로 보존한다. 상한은 lane당1800초+정리60초이며 비용 이후 전체량을 축소하지 않는다. 17시 여유를 검산한다.

실행 전 반검토로 위의8토큰 proxy를 폐기했다. 실제 한영4문맥의128 및509+3=512 경계에서각4위치/합계16개전체어휘로짓을대응한다. 실제512문맥의뒤32생성은각step의KV절대위치와관찰/비관찰ID를별도로검사한다. 512다음 fullprefix수치대응은수행하지않으며 이한계를보고한다. bulk prefill의마지막출력은고정헤더의output_ids계약에따라 get_logits_ith(-1)을쓴다. 최초binary v1은모델미실행이며이수리는별도buildv2/원형을보존했다.

공개 API llama_model_size는 모델tensor 총bytes이며 실제상주가 아니다. exact native backend/KV buffer bytes는 미측정으로 남긴다. 반올림된 엔진capacity로그·GPU전역0.5초표본·소유worker RSS를 따로 기록하고 serialized state 크기를 KV상주라고 쓰지 않는다. parent의 PyTorch allocator0도 native 해제증거가 아니다. 소유worker exit/프로세스그룹종료/최종GPU idle을 확인한다.

문서/품질 영향은 자원표의 빈칸을 채우는 것뿐이다. 공식점수/정답/학습데이터와 기본 모델/backend/precision은 바꾸지 않는다. 공유CPU 부하와 관찰 오버헤드는 보고한다. 실행 전 CPU wire/정리/짝검사·compile self-test·소스봉인·정적을 거치고 실행종결/원답/미측정을 결과101의 별도 절에 기록한다.
