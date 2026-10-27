# P107 적응형 통계의 정·반 사전 읽기 명세

- 대상: 기존 `thesis_oct27_adamuon`/정, `antithesis_oct27_resources`/반. 요청모델gpt-6.1-sol/max이며실제공급자모델재검증을뜻하지않는다.
- 허용 읽기: `tinylm/train/adaptive_masking.py`, `hybrid_mntp.py`, `scripts/test_p107_adaptive_masking.py`, 이후총괄이만들 `scripts/diag_p107_adaptive_masking.py`, `scripts/test_p107_adaptive_driver.py`, `docs/research/20261027_적응형_masking의_통계와_재개계약.md`, P107계획, 공개AMLM논문과고정저자code텍스트.
- 자기감사로그읽기허용목록: `handoff/audit/oct27_independent/p107_adaptive_cpu_v1.log`, `p107_adaptive_cpu_v2.log`, `p107_adaptive_cpu_v3.log`, `p107_adaptive_cpu_v4.log`, `p107_adaptive_cpu_v5.log`. 아직없는파일의실행/통과를추정하지않는다. 새driver로그는범위를먼저추가한다.
- 행위: 지정파일의rg/sed/cat·웹일차문헌읽기와메시지회신만. 파일생성/편집·구현·시험/Python·모델/GPU·실제자료/토크나이저/체크포인트·정제담당전용경로/원장·설치/다운로드/Git/삭제·다른보조호출은금지한다.
- 정은공식hard식의MNTP gold위치·eligible기대량/확률제약·uniform/RNG·학습과분리된통계재개를검토한다. 반은partial폐기·미관측/중복·정규화/경계/동률·state손상·실제storage주장반례를검토한다.
- 총괄이CPU검사실제종료후만수리한다. 현재코드를동결하고관측/추정/미확인을구분한다. 통계단위는완료update이며원논문의200batch와같다고가정하지않는다. 합성그룹계측을실제언어/희귀도편향으로승격하지않는다.

- 후속 사전 읽기 확장: `handoff/audit/oct27_independent/p107_adaptive_cpu_v6.log`, `p107_long_ema_counterexample_v1.json`. 로그가 실제로 닫혔는지는 총괄의 회수 뒤에만 판단한다. 허용 행위는 위와 같은 읽기·회신뿐이며 실행·편집 권한은 추가하지 않는다.
- 첫 갱신 이전 상태 보완 후속의 사전 읽기: `handoff/audit/oct27_independent/p107_adaptive_cpu_v7.log`. 같은 읽기 전용 역할을 유지한다.
