# P107 정·반 읽기 검토의 사전 위임 명세

- 사용자96/97과 기존 문헌·정·반 역할 허용을 따른다. 이 파일을 먼저 저장한 뒤 후속 호출한다.
- 요청 역할모델은 기존 `gpt-6.1-sol`/`max`이며 공급자실제모델을새로검증했다는뜻은아니다.
- 정 역할: `thesis_oct27_adamuon`. 원문MNTP shift/가시성·독립 CE mean·TinyLM CLA/checkpoint 대응이성립하는지검토한다.
- 반 역할: `antithesis_oct27_resources`. 정답누설·잘못된문서/PAD·empty target·중복forward STE·기존None호환성·실패경로의반례를찾는다.
- 허용 읽기: `tinylm/model/visibility.py`, `modules.py`, `transformer.py`, `tinylm/train/hybrid_mntp.py`, `scripts/test_p107_hybrid_mntp.py`, `docs/research/20261027_MNTP_가시성과_지도위치_구현계약.md`, `test_plan/P107_문서가시성과-shift를-분리한-causal-MNTP-계약.md`, `handoff/audit/oct27_independent/p107_hybrid_cpu_v1.log` 및 공개GPT-BERT논문/고정저자commit텍스트. 옛기본함수대조가필요하면 `handoff/audit/oct27_independent/p013_context_source_v2/tinylm/model/modules.py`와`transformer.py`만읽는다.
- `rg/sed/cat` 등허용파일텍스트읽기만가능하다. 편집·생성·구현·시험·Python실행·모델/GPU·체크포인트/토크나이저/학습원천·정제담당전용경로·설치/다운로드/Git/삭제·하위보조호출은모두금지한다.
- 결과는메시지로만근거위치·유효한반례·해석한계·권장수리를반환한다. 오류를직접수정하지않는다. 현재시험중소스를총괄도동결하며수리는실제종료회수뒤총괄이한다.
- 보조의검토완료는GPU/학습효과의완료가아니다. 별도후속driver는새허용파일명세를먼저추가한뒤에만검토한다.

## 시험 관측점 수리 알림의 로그 읽기 범위

총괄의 후속 설명 메시지에서 `p107_hybrid_cpu_v3.log` 읽기를 먼저 허용한 뒤 이 파일에 연결했다. 이 추가 로그 한 경로는 `file_receipt_recorded_after_dispatch=true`이며 최초 P107 사전 위임과 분리한다. v1/v2 실패와 v3 결과를 읽기만 하고 편집/실행 금지는 같다. 추가 범위는 이 로그와 이미 지정된 같은 코드의 총괄 수정분뿐이다. 이후 새로운 경로를 메시지에 넣기 전에 파일 허용목록부터 수정한다.

## 실제 비용 driver의 사전 추가 범위

이 절 저장 뒤 정·반에게 추가 읽기를 전달한다. 허용 경로는 `scripts/diag_p107_hybrid_mntp.py`, `scripts/test_p107_hybrid_driver.py`, `handoff/audit/oct27_independent/p107_driver_cpu_v1.log`, `p107_cpu_and_default_regressions_v1.log` 및 이미 지정된 같은 core/시험의 총괄 수정분이다. 기존 `scripts/diag_p106b_resource_matrix.py`의 frozen_model/cleanup 텍스트와 `scripts/diag_p013_context_curriculum.py`의 cleanup/failure helper 텍스트도 읽을 수 있다. 쓰기·Python/시험/모델 실행·자산/학습자료 접근·Git/설치/하위호출 금지는 그대로다.

총괄은22단위검증의관측기오류2건을각원소스/로그로보존한뒤시험만고쳤다. 후속은반검토의독립oracle제안에따라causal과masked를서로다른두모델에서한번씩미분한가중합과비교한다. driver는목표별전체micro target분모를먼저정해mean의단순평균을피하고,혼합에서도input16micro만실행한다. 작은학습품질판정과제품trainer통합은요청하지않는다.

## 입장·시간상한 검토의 사전 추가 helper

정 역할의 요청에 따라 같은 `scripts/diag_p106b_resource_matrix.py` 안의 `DEADLINE`, `Budget`, `wall`, `identity`, `read_ref`, `write_new`, `safe`, `digest`, `sha` 정의 텍스트도 읽기 허용한다. 새 helper 실행이나 그 참조 자산의 읽기는 허용하지 않는다. `handoff/audit/oct27_independent/p107_cpu_and_default_regressions_v2.log`의 읽기도 추가한다. 총괄은실제16134/부모0·68시험/OK를회수했고이로그는그것과연결된읽기자료다. 첫68시험의변수shadowing오류1은원로그/원test보존후수리했다. 이 절 저장 뒤 메시지로 추가 범위를 전달한다.
