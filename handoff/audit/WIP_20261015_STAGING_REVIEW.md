# 2026-10-15 선별 staging 판단

현재 작업 착수의 미추적 파일은 낡은 runtime capsule 한 개였다. 로컬 복구용으로 ignore했고 삭제하지 않았다.
현재 변경은 이 작업의 코드·계획·실측·인계와 명령을 보존한 완료 SH 정리다.

| 종류 | 판단 | 근거 |
|---|---|---|
| 독립 실험/CPU검산 코드·root SH | 선별추적 | 실제 동작 경로와 재현에 필요; 제품 기본과 분리 |
| 결과101·계획/목록·기준표·방법론·COMPASS | 선별추적 | 조건·실측·미실행·한계를 같은 수준으로 유지 |
| 작은 corpus/cost/train/test/CPU report | 선별추적 | 실제 입력/지도량·원형 SHA·실측분모의 근거 |
| 완료된 자기소유 raw | 선별추적 | 종료코드와 실행명령의 원형; 진행 중 raw는 종료 전 commit 안 함 |
| teacher 원형/사고·다량원문·학생원답 | 로컬제외 | 별도 HF/evidence/local 보존; 필요한 소형집계/제한판독만추적 |
| 기존/새 CPT·native/캐시·feature tensors | 로컬제외 | 대량/사용자소유·재생성 산출물이며 코드와 SHA로 연결 |
| 처음의정적실패·고유한flag/인계/날짜실패·freeze감사 | 보존 | 발견·수리와실제권한범위를구분하는증거 |
| 중복한 operational READY 감사3개 | 정확경로ignore | 같은문제/중간PASS를반복해Git에쌓지않음;삭제하지않고고유실패와freeze감사유지 |
| 외부2WIP·보호TinyDataset·환경설정 | 변경0 | 현재목표의범위가아님 |

명시 경로만 staging한다. HF/runs/data_cache/보호데이터/개인캡슐은 포함하지 않는다.
20MB를 넘는 Git blob은 허용하지 않으며 원문 JSONL도 ShardWriter의20MB 상한으로 분할한다.
core.filemode=false라 새 실행SH의 인덱스실행비트는명시적으로확인한다. 설정을전역변경하지않는다.

## 07시대 추가 판단

조건부 네 팔의 종료 원형/소형 report와 새 원천v2 inventory/deck는 추적한다.
동결 표현의 진단 코드는 추적하지만 진행 중 GPU 원형은 종료 전 staging하지 않는다.
첫 진단의 CPU-cache/CUDA 순서 오류는 원형·정확한 v1 전체코드 복구 JSON을 추적해 수리와 구분한다.
CPU/정적 통과로 이 GPU 오류를 찾았다고 주장하지 않는다.
원천 JSONL/사고·특징 NPY·CPT는 기존 HF/runs/local 제외 정책을 그대로 적용한다.

## 09시대 추가 판단

동결 특징/요인 판독의 작은 report·layout 전량 감사·새 lossless deck/pilot 요약과 종료 raw를 선별한다.
cap panel console은 실제 source 파생 Q/A를 출력하므로 정확한 패턴만 ignore하고 원형은 로컬 보존한다.
HF 원문/교사답/사고/특징·학습가중치를 추적하지 않는다. 진행 중090609 로그도 아직 staging하지 않는다.
새 --thinking의 exp1행은 신규 실험 CLI 등급 metadata이며 검사기/환경 동작을 수리한 것이 아니다.
phase2 완료18SH의 복구/삭제명세와 원형SHA 검산도 추적한다. 이번 삭제는 SH만이며 CPT/데이터 삭제0이다.
