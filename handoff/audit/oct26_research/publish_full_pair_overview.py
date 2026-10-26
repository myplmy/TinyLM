"""봉인된 공식 점수로 기존 9모델과 새 전체300M 두 모델의 표를 연결한다."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PATH = ROOT / "docs/research/20261023_모델별_벤치마크와_실제답변_종합.md"
old = PATH.read_text(encoding="utf-8")
if "## 15. 2026-10-26" in old:
    raise ValueError("overview already exists")
old_table = old.split("| 실제 실행본 | Core6 평균 (%) | 역할 |", 1)[1].split("\n\n", 1)[0]
old_rows = [line for line in old_table.splitlines() if line.startswith("|") and "---" not in line]
if len(old_rows) != 9:
    raise ValueError("historical nine models")
stats = json.loads((ROOT / "test_result/evidence/p106b_native_format_pair_stats_v1_20261026_json_recovery_v3/report.json").read_text())
lines = [
    "", "## 15. 2026-10-26 전체300M 두 팔을 추가한 현재 11실행본", "",
    "원 9모델의 완료 점수는 재실행하거나 다시 산출하지 않았다. 새 두 모델은 같은 초기값·형식자료·배치·schedule로 각300,023,808토큰 본학습을 끝낸 뒤 공식19,965문항을 평가했다. 같은6과제 평균이지만 외부 모델과의 학습량·엔진·양자화·구조 차이는 남는다.", "",
    "| 실제 실행본 | Core6 평균 (%) | 역할 |", "|---|---:|---|",
] + old_rows
for arm, label in [("format_muon", "TinyLM format+Muon 300M"), ("format_normuon", "TinyLM format+NorMuon 300M")]:
    lines.append(f"| {label} |{100 * stats['models'][arm]['mean6']:.4f}|10월26일 새 전체 본학습·기술 종료0, 품질 개선 미확인|")
lines += [
    "",
    "새 NorMuon−Muon 평균은−1.2474%p, 문항대응 pointwise95% 구간[−2.0408,−0.4531]이다. 새 두 팔의6과제 중 사전30검정 Holm 보정 뒤 남은 차이는 BoolQ 열세뿐이다. 나머지5개 동등성을 증명한 것은 아니다. 기존 Native595-Q 대비 새 Muon/NorMuon은−1.3742/−2.6216%p이며 학습량·원천이 달라 optimizer 인과 비교가 아니다. Falcon 대비 격차는−8.2696/−9.5170%p다.", "",
    "두 새 모델에서 PIQA·ARC-E는 단순 기준보다 높은 수치 신호가 있으나, ARC-C는 무작위/최빈 아래, Wino는 근접, BoolQ는 항상 yes보다 낮다. 전체 결과를 고분별력이나 일반 대화 개선으로 설명하지 않는다. 정확6과제·단순기준·30검정·모든 구간은 결과101 §§542~543과 봉인된 pair_stats_v3가 소유한다.", "",
    "### 실제 한국어·영어 첫 답", "",
    "총괄이 새 두 모델의 실제48답을 모두 읽었다. 두 모델 모두 한국어1+1·2+2·당근조회·영희의5개를 안정적으로 답하지 못했고 질문 재출력·위키 분류·문장 반복이 남았다. 영어도 정답 단어로 시작한 일부 사례와 사과 설명의 관련 정보는 있으나 반복·미종료가 이어져 대화 가능한 수준으로 보지 않는다. 각각20/24가128토큰 상한,4/24가EOS였다. 종료 성공과 내용 정답을 합치지 않는다.", "",
    "[질문·실제답 전문48건과 개별 판독](20261026_전체300M_두모델_실제48답_판독.md)을 별도로 보존했다. plain/ChatML의 첫답 비교이며 대화 이력을 누적한 멀티턴 시험은 아니다. 과거 실패 답을 지우거나 교정 답을 이번 평가 정답으로 대체하지 않았다.", "",
    "### 이번 결론과 남은 비교", "",
    "NorMuon을 기본으로 채택하지 않는다. raw+Muon 전체 본팔은 미실행이므로 형식 정제의 인과 이득도 미확정이다. 단순히 같은 작은 학습을 재실행하거나 benchmark 정답을 가르치지 않는다. 다음 품질 작업은 별도 TRAIN 원문의 위키 분류·중복 잔재 정제, 충분한 질문·근거·답/종료를 갖춘 자료 편입, 원문 능력 보존과 고정 평가를 함께 만족해야 한다. 새 Native300M 완료는 미완성 교사75M SFT×4epoch 완료를 뜻하지 않는다.", "",
]
with PATH.open("a", encoding="utf-8") as out:
    out.write("\n".join(lines))
print("overview models", len(old_rows) + 2)
