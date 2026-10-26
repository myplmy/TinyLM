# HOLD 복구의 재현 경로

기준은 `root_adoptions_v3.json`과 `data_cache/p106b_hold_recovery_v1_20261026_goalc/proposals_v3/complete.json`이다. 원형3파일·토크나이저·부모cache_v1·전체스캔·각코드SHA와실제수동txt가모두남아있어야한다. 원형URL/기사ID나새사실을복원한결과가아니다. 대량txt/캐시는로컬data_cache에만두고관련작은감사/코드/문서만Git에선별한다.

## 원형과 수동 판단

- `review_source_proof_all_v3.json`:685원형패킷의전체입력/토크나이저/구간SHA·디코딩바이트를대조했다.
- `review_coverage_receipt_v1.json`:511목적원문과그당시27독립검토표/468행을분리계수했다. 후행postbuild9행/재독3행은별도보존한다.
- `root_literal_repair_proof_v2.json`:22개구체수정범위/조건비교다. 초기v1음성2개도남아있다.
- `postbuild_literal_repair_proof_v3.json`:생성후9문서의마크업/출생정보·오독재판독등13검사다. 앞v2의순수빈행차이음성은삭제하지않았다.
- `root_adoptions_v3.json`:현재수동453원문SHA와실제본문경로/SHA·이유·검토·기존부정버전을연결한다. 이전v1/v2명세를덮지않았다.
- `interwiki_literal_repair_proof_v1.json`:교육용구문을유지하며네고아예고만분리한추가1건의정확구절검산이다. 다른452판정과생산7코드가같고,독립검토의역할입력범위혼동과철회를연결한다.

## CPU 캐시 재생성

현재 `cache_v5`는이번실행의write-once출력이다. 재현할때에는존재하지않는별도이름을사용한다. 동일이름을덮거나삭제해재실행하지않는다. 다음은모델/GPU를실행하지않는CPU데이터명령이다.

```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B scripts/p106b_hold_revision.py build --adoptions /home/uranus/tinyLM/handoff/audit/hold_recovery_20261026_goalc/root_adoptions_v3.json --proposal-name proposals_v3 --output-name cache_repro_v1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B scripts/p106b_hold_revision.py verify --output-name cache_repro_v1
```

build는기존채택본문/기존제외의보존과부모HOLD817,494구간전량회계를확인한다. 원형/정제VAL exact·기존VAL경계·256-ID/stride128구간을검사하며새VAL때문에기존TRAIN을몰래제외하지않는다. verify는전체채택문서를원형/정제문에서재생성하고EOS/예약토큰/문서경계/직렬화/분할중복/합계/동결SHA를독립확인한다. 실행시간이들어가는metadataSHA까지동일하다는주장이아니라같은채택본문/토큰을재생성할수있다는뜻이다.

## 최종 계측과 정적검사

실제완료된cache_v5의built/verified/recovery_verified가생긴뒤에만최종계측을실행한다. `aggregate_recovery.py`는전체분모/같은채택집합/순수편집과부분구간보류/선택효과·잔여HOLD사유·문자대리지표를분리한다. `collect_postbuild_residuals.py`는새채택의희소구조신호를문맥검토용으로추릴뿐오류라고확정하지않는다.

정적검사는이디렉터리의`run_scoped_static.py`와정확명시파일목록을사용한다. 이전기본adapter는Git해시/제어문자만한정했으며링크검사의전체문서순회를뒤늦게발견했다. 새adapter는링크입력/수리힌트색인까지한정하고원래검사의판정조건은유지한다. `STATIC_SCOPE_AND_LINKS.md`와첫69/1/6·회복70/0/6증거를함께읽는다. 공유코드조회전체의OS격리나전체worktree clean은증명하지않는다.

원형/기존cache/원로그/checkpoint삭제0·모델가중치/GPU/학습0이며추가300M금지는유지한다. 새TRAIN양은새고유대화/SFT량·사실성·모델품질이나실제학습승인이아니다.
