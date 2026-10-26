# 종결 시점의 공유 검사 두 건과 이번 데이터 범위

`HOLD_RECOVERY_PRECOMMIT_STATIC_AUDIT.json`은실제종료1·68PASS/2ERROR/6NOT_RUN이다. 앞선동결코드단계의70/0/6을현재공유저장소전체PASS로재사용하지않는다. 두검사를직접재실행해아래실패를확인했다. 이번복구코드7파일·본문/캐시·원형해시와는별개이며,원래실패를수정완료나PASS로바꾸지않는다.

| 검사 | 정확한 대상 | 증거와 상태 | 운영 영향 | 권장 조치 | 대안 | 승인 주체 |
|---|---|---|---|---|---|---|
| check_hf_redirect | scripts/test_adamuon.py | import tinylm 앞의 sys.path.insert가 없다는 실제종료1; 이번수정대상아님 | 해당별도파일의직접실행경로가미검증 | 원소유작업에서실제import경로를수정/검산 | 이번데이터종결에서는글로벌검사를NOT_RUN으로범위밖처리하고실패원형보존 | 해당파일소유자/사용자 |
| check_smoke_diag | 기존사용자스모크20261025205941_smoke_codex_oct26_after_normuon_v2_ab21d36.txt | 실제종료1; execution source pins differ 및 check_handoff/check_smoke블록부재 | 과거스모크로그를현재공유소스의새PASS로쓸수없음 | 원소유세션/사용자가현재조건의스모크필요성을판단 | 이번CPU데이터goal은GPU스모크제외이므로직접재실행/옛로그수리없이NOT_RUN | 사용자/동적실행소유세션 |

후행한정감사는동일원검사함수의판정기준을유지하며위두검사를명시NOT_RUN으로보고한다. 첫2ERROR는그대로보존하고해결됐다고하지않는다. 이번데이터에필요한원형/채택전부재생성·EOS/경계·split·정확중복·SHA·원로그/문서역참조는실제검산0이다. 독립모델·HF다운로드·사용자GPU스모크나타세션의완료를증명하지않는다.
