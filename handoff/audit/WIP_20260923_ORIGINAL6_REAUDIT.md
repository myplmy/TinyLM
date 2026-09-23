# 2026-09-23 원래 6항목 연속작업 재감사

현재 열린 [작업원장](../WIP_20260923_작업원장.md)과 직전 [핸드오프](../202609231842_HANDOFF.md)를 이었다. 새 핸드오프 파일은 만들지 않았다. 정적 구현과 사용자 GPU·모델 관찰을 분리한다.

| 원래 지시 | 확인한 실물·근거 | 이번 조치 | 남은 경계 |
|---|---|---|---|
| (1) smoke 필요 여부 | 마지막 사용자 [202609230016 로그](../../smoketest_logs/202609230016_smoke_a01e376.txt)는 당시 42팔·실패 0·계측 오류 0. 이후 trainer/SFT와 이번 infer loader가 변경됨 | **현재 작업트리 smoke는 REQUIRED_USER_RUN**으로 판정; WIP 21은 완료로 닫지 않음 | Codex 실행 금지. 현재 정적 성공을 smoke PASS로 승격하지 않음 |
| (2) 기존 권장·P092 | [결과 083 §10](../../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md)에서 세 sparse 팔의 30M→100M gap 감소·ms/step·bool mask 상주 누락·실제 파일 크기를 분리. old Stage3W는 [TSV](../../experiments.tsv)와 frontier에 계속 존재 | [Stage3Wb SH](../../run_P092_Stage3Wb_resident_speed_diagnostic.sh)와 [진단기](../../scripts/diag_p092_resident_speed.py) 작성. 사용자 선택은 진단→관측된 원인 수정→동일조건 300M 한 시드 | 옛 Stage3W 3시드는 HOLD. Stage3Wb GPU·배포 실측 및 뒤의 수정·한 시드는 NOT_RUN |
| (3) 핸드오프 A안 | [조건부 승인 제안서](../../proposal/20260923_동일-WIP-연속작업-핸드오프-중복생성-재발방지-제안서-approved-on-going.md) | session-handoff 스킬과 Codex 02의 CONTINUE/RECOVERY_READ/FINAL_HANDOFF 문구만 보완. 새 핸드오프 0건 | B안 생성기 차단은 미승인·미구현; 재발 시 재검토 |
| (4) P029/P100/frontier 신규 SH | [P029 Stage2W](../../run_P029_Stage2W_wiki_eos_panel.sh), [P100 Stage0W](../../run_P100_Stage0W_capability_baseline.sh), [frontier R1](WIP_20260923_CONTINUATION_FRONTIER_R1.json) | 두 원답안 패널과 P092 진단을 TSV에 등록. 115 physical/index/frontier, 충돌 0. 기존 P097 Stage4와 P092 Stage3W 모두 목록에 남음 | SH 정적·자산 경로만 확인; 실제 답안·GPU 결과 NOT_RUN |
| (5) 데이터 편중 로드맵 | [결과 090 §8/§13](../../test_result/090_20260919_P097-세-cache는-완성됐지만-학습은-0step이다.md), [결과 073](../../test_result/073_20260904_P087-두-번째-epoch은-과적합-없이-0.1155를-준다.md) | [승인 로드맵 §9.3](../../proposal/20260923_40MiB-실질지능-다축-검증-로드맵-제안서-approved-on-going.md)에 G0/G1a/G1b/G2의 기검증·미검증을 분리하고 40MiB A 구조+RMS4/WD/LR+호환 SFT 조합을 우선 후보로 명시 | 데이터 무관 판정·SFT 이후 지능 개선·40MiB 최종 적격은 NOT_RUN |
| (6) WIP 12 Aya | [공개 원천 감사](../../docs/20260923_한영일-SFT-멀티턴-공개원천-선별과-확보-감사.md)와 비보호 HF manifest | 고정 한국어 train 두 조각 973,675,125 byte 취득·3,605,618 후보/21 출처 감사. WIP 12/26은 원천 확보 범위로 완료 | source별 권리·품질·중복·PII·오염과 한국어 다회전/SFT 학습은 P090 별도 게이트로 계속 NOT_RUN |

추가 지시의 [체크포인트 직접 재판정](WIP_20260923_CHECKPOINT_REVIEW.md)은 실물 359건 중 `delete` 후보 142건·60.677 GiB, `keep` 217건, 미등록 0·실물 hold 0이다. WSL cleanup은 동일 프로세스 preview와 대문자 YES로 보호했으나 실제 삭제는 0건이다. 기존 핸드오프 §8 메시지를 보존하고 §8.1에 이번 미커밋 변경의 한국어 커밋 메시지를 분리했다.

정적 검사는 현재 코드의 구문·규약만 증명한다. 모델/GPU/P029·P092·P097·P100 실행, 새 smoke, cleanup, staging·commit·push는 AI가 수행하지 않았다.
