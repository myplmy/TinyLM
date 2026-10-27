# 큰어휘 기준선 재사용과 읽기 경로 수리

## 실제 근거와 원인

Stage4Wj65223/0은 export13.369초·CPU기준선94.501초·CUDA기준선33.445초를 완결했다. 두 파일은282,675,763B/28,920,689B이며 고유tensor storage282,589,348B/28,833,956B다. 이 시점에는 packed 정합/속도는 미측정이다.

이어 Stage4Wh49515/9는12.544초 뒤 `only new deployment/oracle safe loads allowed`로 끝났다. 새payload1회 로드는 성공했고 원CP읽기0·모델해제true·cleanup오류0이다. 새oracle을 읽을 때 Path.name이 전체 경로가 아니라 basename인 점을 파일핸들 name과 혼동했다. 실제수치 비교/전체자원행렬은 미실행이며 OOM/양자화품질 실패가 아니다.

## 세 대안과 선택

1. 기존35소스를 직접 고치고 export/두기준선을 새로 만든다. 단순하지만 수리와 관계없는 성공 단계를 다시 수행한다.
2. 기존35소스/프로필/파일/기준선/원오류를 동결하고, 새 진입기의 안전 경로 해석만 수리해 원 perform/suite를 재사용한다. 반복 계산과 원결과 덮기를 피하면서 새 로더의 실측을 분리한다. **이 안을 선택한다.**
3. basename을 허용하거나 전체 torch.load 제한을 끈다. 원CP 재유입과 계보 오류를 막지 못하므로 기각한다.

## 구현 경계와 선결

총괄만 새 `scripts/diag_p014e_large_vocab_resume.py`와 CPU 회귀를 편집한다. PathLike/문자열은 직접 resolve하고 실제 파일객체만 name을 읽는다. 두 경우 모두 기존 새payload/oracle 디렉터리 내부의 .pt와 weights_only=True만 허용한다. 원CP/다른경로/안전옵션누락/심볼릭링크탈출은 거부한다. 원packed decoder/샘플/수치오차/스레드/예산/기준선/제품코드는 바꾸지 않는다.

새source는 원35개와 새두파일을 모두 봉인한다. 원 profilev4와 export/baseCPU/baseCUDA/CPU오류의 실제파일SHA 및 source/profile계보를 검증한다. 새결과 namespace만 쓰며 export/기준선/원CP tensor 읽기/새학습/추가300M/정제/설치/다운로드/Git은0이다.

Stage4Wk CPU5400초와Stage4Wl CUDA1800초는 독립이다. CPU/GPU 모두 same-device·same-embedding함수의4문맥128/512/로짓16위치·고정16/예열1/측정3/관찰1·자연4답최대32·원rtol2e-5/atol2e-6 및ID/종료를 유지한다. 마감17시/정리180초·유휴GPU·원CP/파일/소스불변·해제0이 선결이며 작은모델지능 판정을 하지 않는다.

## 영향과 판정

새진입기·테스트·계획/결과/TSV/원장/명시정적만 변화한다. 기존317은 실행하지 않고 알려진 guard오류의 prepared 경로로 보류하며 새후속으로 대체한다. 실행된315/316/318만 명령 보존 뒤-done으로 기록하고 삭제0이다. 수치불일치는9, 예산부족은8로 보존하며 저장절감·속도·품질을 분리한다. 큰결과파일은20MB 아래 분할하고 payload는runs/deploy의Git제외로 둔다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.
