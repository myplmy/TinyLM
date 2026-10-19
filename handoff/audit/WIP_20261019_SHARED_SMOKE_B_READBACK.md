# 격리 스모크 B 검사 결과

승인 범위의 판독·모의 실행 배선을 구현했다. 최종 회귀164개는 실패0·오류0이며 모델·실제 자식·호스트 신호·보호 자료·네트워크 사용0이다. 증거는 STATIC_ONLY다. 새 full은 registry 경로의 추가 승인·검증 전 코드 HOLD8로 차단한다.

## 실제 로그와 호환

16·17·19일 로그3개를 현재 판독기로 다시 확인해 해시·명령 순서·종료의 오류0, 대체2개씩을 확인했다. 19일의 원래 합성 파일 전후 지문은 NOT_CAPTURED다. 이전2개의 합성 지문도 전역 등록표 전체 보존으로 확대하지 않는다.

수정2개와 신설4개의 Python 파일, 운영 옵션 --deadline-utc 등록1행이 변경 범위다. 사용자 BAT/SH·tool_smoke.bat·check_smoke.py·summarize_smoke.py·runlog.py·registry.py와 기존3실행기는959a674의 Git 정규화 내용과 같다. BAT 작업트리 CRLF와 blob LF를 원바이트 동일로 부르지 않으며 실제 SHA도 따로 보존했다.

정본106action·44child·33train의 학습 인자·순서·대기는 유지했다. 기존 두 대체는 다음과 같다.

- 옛 handoff 검사 대신 Codex 독립 검사: 같은 프로그램이나 항상 같은 판정은 아니다.
- check_smoke.main의 로그 폴더만 격리 JSON으로 연결: 필드·값·배치 산식·VRAM 기준은 불변이다.

별도 session ID 아래 runtime/evidence를 배타 예약하고 원로그는 smoketest_logs에 둔다. 오프라인·W&B 비활성 등의 명시 환경이 있으므로 사용자 셸 전체와 같다는 뜻은 아니다. 환경 기록만 허용 변수로 제한하며 자식은 부모 환경을 상속한다. 보안 sandbox가 아니다.

## stdout 검토

새 Conda나 worktree는 만들지 않는다. 같은 실행·전체 자식 stdout·전체 원로그를 유지하고 GPT에 반환하는 도구 응답만 요약한다. 단계·종료·오류·로그 위치를 먼저 읽고 실제 답안이나 traceback은 필요할 때 원문을 읽는다. 실험 결과는 줄임 화면이 아니라 자식 종료코드와 최종 영수증으로 확인한다.

실제 터미널의 compact 모드는 아직 구현하지 않았다. 실제 stdout을 줄이면 I/O 비용과 벽시계가 달라질 수 있어 비교 팔은 같은 모드를 써야 한다. head 때문에 SIGPIPE로 끝내거나 grep의 종료코드를 실험 코드로 오인하지 않는다.

## 회귀와 한계

잔류 프로세스 그룹·반복 중단·시작된 작업의 반환 경계·생성 후 handle 미회수·신호 상속·링크 선조·준비 시간·절대시계와 분할 대기를 시험했다. handle이 없으면 UNKNOWN/unsafe로 중단하며 임의 PID나 안전 종료를 주장하지 않는다.

실제 writer가 만든 임시 영수증으로 float 시간상한을 확인했다. 모순된 COMPLETE/UNKNOWN, 정리중단, 누락 unsafe, summary NaN·누락 시간, 짧은 대기, 전체보다 큰 직렬 시간, 불완전 raw·SHA·인자·환경·합성지문 범위 오염을 거부한다. namespace import도 우연한 scripts 경로에 기대지 않는다.

과거 모의시험 수를 실제 GPU 증거로 합산하지 않는다. 초기157의 network counter는 socket 차단 전이었고 최종164는 connect/connect_ex/create_connection/urlopen을 명시 차단했다. 모두 임시 자료·가짜 프로세스 시험이다.

전수 정적의 최초 새 옵션 미등록1오류는 표에 등록하여 수리했다. RECHECK는68PASS·0ERROR·6NOT_RUN이다. 현재 WIP 결합은 별도 STATIC_FINAL 감사로 남긴다. 미실행은 보호 held-out, 넓은 cache/VAL, 전체 registry, plotting, tag/arch, 레거시 handoff다. Codex 독립 handoff는 정적으로 실행했다.

## 남은 승인

registry.py가 TINYLM_DIR를 무시해 같은 tag의 옛 JSON이 있으면 전역 등록표를 수정할 수 있는 조건부 소스 위험이 있다. 과거 오염을 관측한 것은 아니다. 원래 등록표·체크포인트·캐시를 열어 수정하거나 복구하지 않았다.

별도 회신 전에는 registry 소스 수정·새 full을 하지 않는다. 권장 추가 범위는 런타임 경로와 전용 CPU 회귀뿐이며 기본 사용자 경로는 유지하는 것이다. 현재는 --execute도 HOLD를 우회하지 못한다.

근거: 같은 WIP_20261019 접두사의 SHARED_SMOKE_B_SCOPE·PRIOR_HISTORY_REVIEW·REGISTRY_SCOPE_FINDING·FINAL_GUARDED_TESTS·PRESERVED_SOURCES·STATIC_RECHECK/FINAL 감사. 학생8470실답은 결과101 §313~318의 별도 증거다.
