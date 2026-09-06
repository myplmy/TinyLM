# Moonshot 전용 결과 영역

이 폴더는 `PMnnn__MOONSHOT__...` 실행 로그와 결과 분석만 담는다.

- 일반 결과 폴더 `test_result/`와 섞지 않는다.
- 사용자 실행 배치는 `scripts/runlog.py --outdir moonshot_result`를 명시한다.
- 성공한 PM 학습의 최소 provenance는 이 폴더의 `registry.tsv`에만 기록한다.
- 일반 `runs/registry.tsv`의 scan/backfill에는 PM 태그를 넣지 않는다.
- 실행 전에는 결과 문서를 만들거나 성능 결론을 적지 않는다.
- 향후 결과 분석 파일명은 `PMnnn__MOONSHOT__주제__RESULT.md` 형식을 쓴다.
- 결과 문서를 쓰기 전 `python scripts/new_moonshot_result.py <PM 로그 또는 PM번호>`를
  실행한다. 종료코드 3이면 새 파일을 만들지 않고 기존 문서에 다음 Stage 절을 추가한다.
- 이 브랜치의 결과를 main으로 merge하지 않는다. 별도 main 작업의 재검토 자료로만 쓴다.

현재 결과 문서:

- [`PM000__MOONSHOT__LATIN_GQA__RESULT.md`](PM000__MOONSHOT__LATIN_GQA__RESULT.md) — Stage0/Stage0B·sparse34 동적 계약 PASS, 전체 smoke는 check_links 1건 RED, Stage1 HOLD, 품질 미측정

PM001은 아직 사용자 실행 로그가 없으므로 결과 문서를 만들지 않았다.
