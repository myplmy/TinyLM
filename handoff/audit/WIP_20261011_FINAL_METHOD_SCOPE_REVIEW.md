# 2026-10-11 최종 범위·방법 재감사

## 1. 정적7종을 실행하지 않은 이유

기존 감사는74항목 중67PASS/오류0/NOT_RUN7이다. ‘전수74종PASS’가 아니다.
체크포인트 역할 검토의 metadata 승인과 보호 데이터/전체 역사 run 본문 승인도 다르다.
시스템python 첫 시도에서 torch/numpy 부재 오류3이 있었고 기존 tlm_torch 환경으로 재검증했으며 설치/환경변경은 하지 않았다.

| 미실행 항목 | 정확한 이유 | 실제로 대신 확인한 범위 |
| --- | --- | --- |
| `check_heldout_defects` | 보호 datasets/TinyDataset의 held-out 본문을 읽는다. 해당 데이터 접근 승인이 없어 미실행. | 지정 원본과 CPU 합성 계약 검산만 수행. held-out 실제 품질 검증은 NOT_RUN. |
| `check_eval_pool` | 현재 코드는 BAT와 광범위 runs/logs의 pool_tokens 메타데이터를 읽는다. val.bin/train.bin 토큰 본문을 읽는다는 이전 이유는 잘못됐으며 정정한다. 전체 역사 run 메타데이터 접근은 이번 허용목록 밖이다. | 정확 지정 report·서명만 대조. BAT 위주 검사로 현재 WSL SH의 모든 풀 조건을 검증했다고 주장하지 않는다. |
| `registry --scan` | 전체 run JSON과 registry 목록을 스캔한다. --scan은 읽기 전용이지만 이번 정확 로그/역할 메타데이터 범위를 넘어 미실행. | 지정17 원본·짝 evidence·checkpoint 역할 메타데이터를 검산. --backfill/DB 변경 없음. |
| `check_handoff` | 소스가 CLAUDE.md를 환경 검사 원천으로 읽어 Codex 완전분리 경계에 맞지 않는다. 레거시 검사 실행을 건너뛰었다. | 독립 check_handoff_codex 및 그 회귀는 실제 실행. 기존 check_handoff의 PASS로 대체 표기하지 않는다. |
| `check_run_registry` | 전체 역사 run JSON의 학습/최종/중복 조건을 읽는다. 이번 허가된 정확 증거/68짝 메타데이터/417부모키 검토와 같지 않아 process-local 제외. | 공용 파일/화이트리스트는 변경하지 않고 이번 프로세스에만 제외 사유를 추가. 전체 registry 안정성 PASS 아님. |
| `plot_results --verify` | 옛 표의 수치와 광범위 run JSON을 대조한다. 이번 표현/trace 원본의 직접 검산과 무관하고 접근 범위 밖이다. | 이번 실제48forward/24생성 보고서를 직접 파생값과 대조. 옛 전체 표의 정합은 NOT_RUN. |
| `check_tag_arch` | 전체 run JSON의 태그·구조·설정을 검사하므로 범위 밖. | 이번 정확 부모 cfg16층/mode1/untied/CLA2·native 방문0..15·factor SHA를 실물에서 확인. |

특히 `check_eval_pool`의 이전 ‘cache/validation token 본문’ 설명은 **잘못된 이유**였다. 원 감사는 보존하고 이번 사유표/최종 process-local JSON에서 정정한다. 공용checker/화이트리스트·레거시환경문서는 변경/실행하지 않는다.
정적검사는GPT가허용범위를직접검증하는일이다. NOT_RUN7은사용자에게반복숙제로돌리는것이아니라접근경계를보존하는기록이다.

## 2. 기존 표현 관찰의 유효범위와 누락

- 48forward=8문항×3조건×2입력. 동일prompt은168위치/조건이며 text/tokenID를통제했다.
- 짧은문장13~31위치의중심화entropy rank상한은N−1이다.768차원전체의압축/붕괴량으로해석하지않는다.
- 각조건저장답을붙인입력은7/8문항에서다르다. en_math만세조건동일. 직접구조인과대조아님.
- final RMS hidden teacher-forced관찰은실제생성 로짓·EOS·KV·층별 onset을측정하지않았다. 따라서반복원인시험으로충분하지않았다.
- 뒤늦게원값을조용히고치지않고 [결과103 §11](../../test_result/103_20261010_P093B-MLP잔차와-삼진보정은-실행됐지만-복원문턱에-미달.md)에비교서명3개를추가했다. 코드/원형지문은유지한다.

## 3. 이번 추가 검사

[결과103 §12](../../test_result/103_20261010_P093B-MLP잔차와-삼진보정은-실행됐지만-복원문턱에-미달.md)와 [실제창 판독](WIP_20261011_LIVE_TRACE_REVIEW.json)이정본이다.
이번한정GPU최대600초권한으로약123초/본체115.916848초에24답을재현했다. 학습/save0·추가실행권한종료.
2186선택/같은prefix cacheOFF·owner KV/16층변화가실측됐고19행은exacttoken3연속,5행은값변경/목록나열로exact검사가놓쳤다. GPT가원24답을후행으로읽었다.

옛prefix변경0,옛답text/finish/count24/24일치이나cache argmax는2180/2186으로6차이다. 따라서기술정합8이지내용문턱실패/실행오류/시간상한소진이아니다. BF16/SDPA/행렬형태와구현원을구분하는고정precision후속은미실행이다.
동일prefix의선택차이/층별차이는관측이며특정층이반복을‘일으켰다’는개입증거가아니다. 정상대조/동일위상hidden전체벡터/attention확률은측정하지않았다.

## 4. 보존 경계

원형log/report·기존부모/보정·토크나이저·HF/cache·보호TinyDataset·타세션WIP·옛HANDOFF는불변이다.
실물3SH는동일본문-done에보존하고새추가삭제는하지않는다. 체크포인트177.83GiB는전부현재필수량이아니며9.6049GiB는삭제후보이지실제삭제/물리회수량이아니다.
마지막모델진단의관찰시간을순수생성속도로쓰지않는다. 개별결과파일은20,000,000bytes미만이다.
