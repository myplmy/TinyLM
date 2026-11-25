"""Author disjoint bilingual rule families and bind a single changed observation."""

from dataclasses import dataclass
from random import Random
from typing import Callable


@dataclass(frozen=True)
class Family:
    name: str
    rule: tuple[str, str]
    fact: tuple[str, str]
    question: tuple[str, str]
    passes: Callable[[int, int, int], bool]


TRAIN = (
    Family("museum", ("The museum admits groups of at least {limit} visitors.", "박물관은 인원이 {limit}명 이상인 단체를 입장시킵니다."),
           ("A group has {value} visitors.", "이 단체의 인원은 {value}명입니다."),
           ("Will this group be admitted?", "이 단체가 입장할 수 있나요?"), lambda value, limit, extra: value >= limit),
    Family("shelf", ("The records shelf accepts boxes weighing at most {limit} units.", "문서 선반에는 무게가 {limit}단위 이하인 상자만 놓을 수 있습니다."),
           ("The box weighs {value} units.", "상자의 무게는 {value}단위입니다."),
           ("Can this box be put on the shelf?", "이 상자를 선반에 놓을 수 있나요?"), lambda value, limit, extra: value <= limit),
    Family("badge", ("The garden issues a pass when the badge number is exactly {limit}.", "정원은 명찰 번호가 정확히 {limit}일 때만 통행증을 발급합니다."),
           ("This badge number is {value}.", "이 명찰의 번호는 {value}입니다."),
           ("Does this badge qualify for a pass?", "이 명찰로 통행증을 받을 수 있나요?"), lambda value, limit, extra: value == limit),
    Family("greenhouse", ("The greenhouse remains open at readings from {limit} through {upper}, inclusive.", "온실의 수치가 {limit}부터 {upper}까지이면 온실을 엽니다. 양 끝값을 포함합니다."),
           ("The reading is {value}.", "현재 수치는 {value}입니다."),
           ("Should the greenhouse be open?", "온실을 열어야 하나요?"), lambda value, limit, extra: limit <= value <= limit + extra),
    Family("stock", ("The club places an order if the delivered count plus {extra} reserved units reaches {limit} in total.", "받은 수량에 예약한 {extra}개를 더해 {limit}개 이상이면 동아리가 주문합니다."),
           ("The delivered count was {value}.", "받은 물건은 {value}개입니다."),
           ("Does the club place the order?", "동아리가 주문하나요?"), lambda value, limit, extra: value + extra >= limit),
    Family("calibration", ("The meter passes if twice its reading is strictly below {double}.", "계기 수치에 2를 곱한 값이 {double} 미만이면 검사를 통과합니다."),
           ("The meter reading is {value}.", "계기 수치는 {value}입니다."),
           ("Does this meter pass?", "이 계기가 검사를 통과하나요?"), lambda value, limit, extra: value < limit),
    Family("tickets", ("Choose only a receipt numbered {limit} or {upper} for the drawing.", "번호가 {limit} 또는 {upper}인 영수증만 추첨에 넣습니다."),
           ("The receipt number is {value}.", "영수증 번호는 {value}입니다."),
           ("Is the receipt eligible for the drawing?", "이 영수증을 추첨에 넣나요?"), lambda value, limit, extra: value in (limit, limit + extra)),
    Family("bridge", ("Vehicles with a blue permit may cross only when they carry fewer than {limit} crates.", "파란 허가증이 있는 차량은 상자가 {limit}개 미만일 때만 다리를 건널 수 있습니다."),
           ("The vehicle has a blue permit and carries {value} crates.", "차량에 파란 허가증이 있고 상자가 {value}개 있습니다."),
           ("May this vehicle cross the bridge?", "이 차량이 다리를 건널 수 있나요?"), lambda value, limit, extra: value < limit),
)

HOLDOUT = (
    Family("harbor", ("Launch before the reading reaches {limit}; stop at {limit} and above.", "수치가 {limit}에 닿기 전에만 배를 띄웁니다. {limit} 이상이면 중단합니다."),
           ("The tide monitor shows {value}.", "조수 계기에 {value}가 표시됩니다."),
           ("May the harbor launch the boat now?", "지금 배를 띄울 수 있나요?"), lambda value, limit, extra: value < limit),
    Family("duty", ("The second worker adds {extra} units. The job is complete only when the combined amount exceeds {limit}.", "둘째 작업자가 {extra}단위를 더합니다. 합계가 {limit}을 초과해야 작업이 완료됩니다."),
           ("The first worker supplied {value} units.", "첫째 작업자는 {value}단위를 냈습니다."),
           ("Is this job complete?", "이 작업이 완료됐나요?"), lambda value, limit, extra: value + extra > limit),
    Family("archive", ("Open the compartment only when the current index differs from the locked index {limit}.", "현재 색인 번호가 잠금 번호 {limit}와 다를 때만 칸을 엽니다."),
           ("The current index is {value}.", "현재 색인 번호는 {value}입니다."),
           ("May the compartment be opened?", "이 칸을 열 수 있나요?"), lambda value, limit, extra: value != limit),
    Family("signal", ("A safe signal must land strictly between {limit} and {upper}; either boundary is unsafe.", "신호 수치는 {limit}보다 크고 {upper}보다 작아야 안전합니다. 양 경계는 안전하지 않습니다."),
           ("The signal reading is {value}.", "신호 수치는 {value}입니다."),
           ("Is this signal safe?", "이 신호가 안전한가요?"), lambda value, limit, extra: limit < value < limit + extra),
)


def make_cases(families, per_family, seed):
    rng = Random(seed)
    cases = []
    for family in families:
        for language_index, language in enumerate(("en", "ko")):
            thresholds = rng.sample(range(25, 105), per_family)
            for serial, limit in enumerate(thresholds):
                extra = rng.randrange(3, 11)
                neighborhood = range(limit - extra - 3, limit + extra + 4)
                values = [rng.choice([value for value in neighborhood if family.passes(value, limit, extra) == outcome])
                          for outcome in (True, False)]
                fields = dict(limit=limit, extra=extra, upper=limit + extra, double=2 * limit)
                distractor = ("The date printed at the top is for filing." if language == "en"
                              else "맨 위에 인쇄된 날짜는 보관용입니다.")
                instruction = "Answer only Yes or No." if language == "en" else "예 또는 아니요만 쓰세요."
                facts = [family.fact[language_index].format(value=value) for value in values]
                rule = family.rule[language_index].format(**fields)
                question = family.question[language_index]
                prompts = ["\n".join((distractor, rule, fact, question, instruction)) for fact in facts]
                cases.append(dict(id=f"{family.name}-{language}-{serial}", family=family.name,
                                  language=language, rule=rule, question=question, prompts=prompts))
    rng.shuffle(cases)
    return cases
