"""Fresh synthetic scope probes; evaluation only, never router inputs or TRAIN."""


FACTS = (
    ("kr_capital", "ko", "대한민국", "대한민국의 수도", "서울", "속한 대륙", "아시아", "화폐 단위", "원"),
    ("fr_capital_ko", "ko", "프랑스", "프랑스의 수도", "파리", "속한 대륙", "유럽", "화폐 단위", "유로"),
    ("water_ko", "ko", "물", "물의 화학식", "H2O", "1기압에서 어는 온도", "0도", "1기압에서 끓는 온도", "100도"),
    ("earth_ko", "ko", "지구", "지구가 공전하는 별의 이름", "태양", "자연 위성의 이름", "달", "자전 주기", "하루"),
    ("de_capital_ko", "ko", "독일", "독일의 수도", "베를린", "속한 대륙", "유럽", "화폐 단위", "유로"),
    ("it_capital_ko", "ko", "이탈리아", "이탈리아의 수도", "로마", "속한 대륙", "유럽", "화폐 단위", "유로"),
    ("oxygen_ko", "ko", "산소", "산소 분자의 화학식", "O2", "원자 번호", "8", "원소 기호", "O"),
    ("moon_ko", "ko", "달", "달이 공전하는 행성의 이름", "지구", "영어 이름", "Moon", "표면에 대기가 풍부한지 여부", "아니오"),
    ("de_capital_en", "en", "Germany", "the capital city of Germany", "Berlin", "continent", "Europe", "currency", "euro"),
    ("it_capital_en", "en", "Italy", "the capital city of Italy", "Rome", "continent", "Europe", "currency", "euro"),
    ("oxygen_en", "en", "oxygen", "the molecular formula of oxygen gas", "O2", "atomic number", "8", "element symbol", "O"),
    ("moon_en", "en", "the Moon", "the planet orbited by the Moon", "Earth", "kind of object (star or satellite)", "satellite", "whether it is a star", "no"),
)


def normalized(text):
    return "".join(text.split()).casefold()


def row(identifier, family, language, question, *, expected=None,
        scope_expected=False, content_answer=None, **extra):
    return dict(id=identifier, family=family, language=language, question=question,
                expected=expected, scope_expected=scope_expected,
                content_answer=content_answer, split="FRESH_FROZEN_DIAGNOSTIC", **extra)


def dataset():
    singles = []
    for fact, lang, subject, relation, answer, r1, a1, r2, a2 in FACTS:
        if lang == "ko":
            questions = [
                f"짧은 상식 확인입니다. {relation}에 해당하는 이름이나 기호를 적어 주세요. 답 한 개만 필요합니다.",
                f"답안의 빈칸을 채워 주세요: {relation}은(는) [빈칸]입니다. 빈칸에 들어갈 내용만 적으세요.",
                f"내가 찾는 것은 {relation}입니다. 해당 답만 한 줄로 알려 주실 수 있나요?",
                f"{relation}을(를) 알려 주면서, 그 대상과 관계가 드러나는 완전한 한국어 문장 한 개로 답해 주세요.",
            ]
            negatives = [
                f"{subject}에 대해 이번에는 수도나 공전 대상, 분자식이 아닌 다른 항목을 묻습니다. {r1}만 적어 주세요.",
                f"새 확인 항목은 {subject}의 {r2}입니다. 그 항목의 답만 적으세요.",
                f"관측 기록: {subject} 항목의 일련번호는 37입니다. 방금 기록에 적힌 일련번호만 답하세요.",
                f"새 관리 기록에서 {subject} 항목의 담당자는 나래라고 정했습니다. 이 기록의 담당자 이름만 답하세요.",
            ]
            negative_answers = [a1, a2, "37", "나래"]
        else:
            questions = [
                f"A brief factual check: please identify {relation}. Return just that name or formula.",
                f"Complete this entry: {relation} = [blank]. Write only the missing entry.",
                f"I am looking for {relation}. Could you give just the answer on one line?",
                f"State {relation} in one complete English sentence that names the subject and its relation.",
            ]
            negatives = [
                f"This is a different field about {subject}: what is its {r1}? Give just that field.",
                f"For {subject}, report its {r2} rather than its capital, orbital target, or molecular formula.",
                f"Record: the inventory number for {subject} is 37. Return only the inventory number in this record.",
                f"A new record assigns Nora to manage the {subject} entry. Return only the manager's name in that record.",
            ]
            negative_answers = [a1, a2, "37", "Nora"]
        for i, question in enumerate(questions):
            singles.append(row(f"target:{fact}:{i}", "target", lang, question,
                expected=answer if i < 3 else None, scope_expected=True,
                content_answer=answer, fact=fact, full_sentence_requested=i == 3))
        for i, (question, gold) in enumerate(zip(negatives, negative_answers)):
            singles.append(row(f"boundary:{fact}:{i}", "same_subject_other_relation", lang,
                question, expected=gold, fact=fact, provided_context=i >= 2))
    ko = [
        "친구가 감기에 걸렸다고 합니다. 걱정하는 마음을 담아 짧게 한 문장으로 말해 주세요.",
        "친구에게 빌린 책을 오늘 돌려주지 못합니다. 사과와 새 약속을 자연스럽게 적어 주세요.",
        "아이에게 우산을 챙기는 이유를 쉽게 한 문장으로 설명해 주세요.",
        "달리기 전에 몸을 푸는 까닭을 간단하게 설명해 주세요.",
        "누군가 문을 잡아 주었을 때 할 수 있는 감사 인사를 써 주세요.",
        "처음 만난 이웃에게 반갑게 인사하는 문장을 써 주세요.",
        "'창문 닫아'를 더 공손한 부탁 한 문장으로 바꾸어 주세요.",
        "'물이 필요합니다'라는 뜻을 유지하면서 다른 문장 구조로 말해 주세요.",
        "'늦었지만 끝까지 해냈다'가 어떤 상황인지 쉬운 말로 풀어 주세요.",
        "'천천히 걸으세요'라는 요청을 아이에게 친절하게 전달해 주세요.",
        "연필과 지우개는 쓰임새가 어떻게 다른가요? 짧게 설명해 주세요.",
        "식탁과 의자의 쓰임을 각각 짧게 설명해 주세요.",
        "뜨거운 그릇을 맨손으로 잡지 말아야 하는 이유를 알려 주세요.",
        "밤에 잘 때 방의 밝기를 낮추는 이유를 간단히 설명해 주세요.",
        "'수진은 웃으며 동생에게 선물을 건넸다' 다음에 어울리는 문장 하나를 지어 주세요.",
        "'버스가 떠나기 직전에 정우가 도착했다' 뒤에 이어질 법한 한 문장을 써 주세요.",
        "길을 잃은 여행자가 도움을 구하려고 합니다. 사용할 수 있는 질문 한 문장을 써 주세요.",
        "음식 주문을 잘못 받았을 때 정중히 확인하는 말을 써 주세요.",
        "종이 상자를 다시 사용하는 예를 하나 자연스러운 문장으로 알려 주세요.",
        "남은 음식을 냉장고에 넣는 이유를 짧게 설명해 주세요.",
        "책을 읽는 것과 소리 내어 읽는 것의 차이를 쉬운 말로 설명해 주세요.",
        "비 오는 길에서 뛰지 말라는 말을 이유와 함께 한 문장으로 써 주세요.",
        "회의가 십 분 늦어진다는 소식을 참가자에게 공손하게 전해 주세요.",
        "새로 이사 온 친구에게 동네 도서관을 권하는 문장 하나를 써 주세요.",
    ]
    en = [
        "A friend says they feel unwell. Write one short, caring sentence to them.",
        "You cannot return a borrowed book today. Apologize and suggest returning it tomorrow.",
        "Explain to a child why bringing an umbrella can be useful.",
        "In one sentence, explain why warming up before running is useful.",
        "Write a polite thank-you to someone who held a door open for you.",
        "Write a friendly greeting to a neighbor you are meeting for the first time.",
        "Rewrite 'Close the window' as a polite request without changing the action.",
        "Express 'I need some water' with a different sentence structure and the same meaning.",
        "Explain 'She was late, but she finished the task' in simple language.",
        "Tell a young child to walk slowly in a kind way.",
        "Briefly explain how a pencil and an eraser have different uses.",
        "Describe the different uses of a table and a chair in one sentence.",
        "Explain why someone should not pick up a hot bowl with bare hands.",
        "Give a simple reason for making a bedroom darker at bedtime.",
        "Continue this story with one natural sentence: Mina smiled and handed her brother a gift.",
        "Continue this story with one sentence: Owen arrived just before the bus left.",
        "Write one question a lost traveler could use to ask for help.",
        "Politely tell a server that you may have received the wrong meal.",
        "Give one everyday example of reusing a cardboard box.",
        "Briefly explain why leftover food is often put in a refrigerator.",
        "Explain the difference between reading silently and reading aloud.",
        "Write one sentence asking someone not to run on a wet path, including a reason.",
        "Politely inform participants that their meeting will start ten minutes late.",
        "Write a sentence recommending a neighborhood library to a new resident.",
    ]
    for lang, questions in (("ko", ko), ("en", en)):
        for i, question in enumerate(questions):
            singles.append(row(f"sentence:{lang}:{i}", "open_sentence", lang, question,
                human_semantic_review=True))
    for i in range(16):
        lang = "ko" if i % 2 == 0 else "en"; a, b = 6+i, 8+2*i
        question = (f"새 검산 문제입니다. {a}에 {b}를 더한 정수 하나만 써 주세요." if lang == "ko" else
                    f"A new arithmetic check: add {b} to {a}. Return only the integer.")
        singles.append(row(f"arithmetic:{i}", "arithmetic", lang, question,
            expected=str(a+b), calculation=dict(operation="add", left=a, right=b)))
    for i in range(16):
        lang = "ko" if i % 2 == 0 else "en"; answer = str(19+i)
        question = (f"새 장부에는 서아의 상자가 {19+i}개, 도윤의 상자가 {42+i}개라고 적혀 있습니다. 서아의 상자 수만 답하세요." if lang == "ko" else
                    f"A fresh ledger lists {19+i} boxes for Eve and {42+i} for Finn. Return only Eve's number of boxes.")
        singles.append(row(f"lookup:{i}", "provided_role", lang, question, expected=answer))
    for i in range(8):
        lang = "ko" if i % 2 == 0 else "en"; value = "K"+str(217+i)
        q = (f"인용 연습입니다. 따옴표 안의 코드만 그대로 복사하세요: '{value}'." if lang == "ko" else
             f"Copy only the code enclosed in quotes, keeping its spelling: '{value}'.")
        singles.append(row(f"copy:{i}", "normal_copy", lang, q, expected=value))
        value = (("두근", "딩동", "천천히", "반짝") if lang == "ko" else
                 ("tap", "go", "again", "blue"))[i//2]
        answer = " ".join([value]*3)
        q = (f"정상 반복 요청입니다. '{value}'을 공백으로 구분해 정확히 세 번 적으세요. 다른 말은 쓰지 마세요." if lang == "ko" else
             f"This intentionally asks for repetition: write '{value}' exactly three times, separated by spaces. Add nothing else.")
        singles.append(row(f"repeat:{i}", "normal_repetition", lang, q, expected=answer))
        value = str(57+i); answer = '{"answer":"'+value+'"}'
        q = (f"숫자 {value}를 문자열 값으로 갖는 answer 항목 하나의 JSON 객체만 쓰세요." if lang == "ko" else
             f"Return just a JSON object with one field called answer and the string value {value}.")
        singles.append(row(f"json:{i}", "json_format", lang, q, expected=answer))
    missing = [
        "그 사람에게 언제 연락하면 될까요? 상대가 누구인지와 상황은 아직 말하지 않았습니다.",
        "그 건물에 가려면 어디에서 내려야 하나요? 어느 건물인지는 아직 알려 드리지 않았습니다.",
        "내 서류가 언제 도착하나요? 배송 기록이나 접수 정보는 제공하지 않았습니다.",
        "이 오류를 고쳐 주세요. 사용한 프로그램과 오류 문구는 아직 보내지 않았습니다.",
        "When should I call that person? I have not identified the person or the situation.",
        "Which stop should I use for that building? I have not said which building I mean.",
        "When will my documents arrive? I have provided no tracking or submission details.",
        "Please fix this error. I have not yet supplied the program name or the error message.",
    ]
    for i, question in enumerate(missing):
        singles.append(row(f"missing:{i}", "missing_information", "ko" if i < 4 else "en",
            question, human_semantic_review=True))
    conversations = [
        [("ko", "새 대화를 시작합니다. 프랑스의 수도 이름 한 개만 답해 주세요.", "파리", True),
         ("ko", "방금 물은 나라를 독일로 바꾸겠습니다. 이제 수도 이름 한 개만 답해 주세요.", "베를린", True),
         ("ko", "같은 나라의 새 기록에 관리 번호가 73이라고 적혀 있습니다. 이번에는 그 관리 번호만 답하세요.", "73", False)],
        [("ko", "지안은 파란 연필 4개, 우진은 빨간 연필 9개를 가졌습니다. 우진의 연필 수만 답하세요.", "9", False),
         ("ko", "우진의 연필이 이제 6개로 바뀌었습니다. 우진의 새 연필 수만 답하세요.", "6", False),
         ("ko", "지안의 연필 수는 바꾸지 않았습니다. 지안의 연필 수만 답하세요.", "4", False)],
        [("en", "Start a fresh conversation: name only the planet orbited by the Moon.", "Earth", True),
         ("en", "Now the inventory record assigns number 61 to that same object. Return only its inventory number.", "61", False),
         ("en", "Return to the first factual question, without the inventory record. Name just that planet again.", "Earth", True)],
        [("en", "The blue box has 12 cards and the green box has 7. Give only the green box's count.", "7", False),
         ("en", "Update only the blue box to 15 cards. What is the green box's count now? Give just the number.", "7", False),
         ("en", "Now change the green box to 10 cards. Give only its new count.", "10", False)],
    ]
    dialogs = []
    for i, conversation in enumerate(conversations):
        dialogs.append([row(f"dialog:{i}:{j}", "actual_history", lang, question,
            expected=answer, scope_expected=scope_expected, conversation=i, turn=j+1)
            for j, (lang, question, answer, scope_expected) in enumerate(conversation)])
    return dict(singles=singles, dialogs=dialogs, official=False, training_allowed=False)


def validate(value, previous_questions=()):
    rows = value["singles"] + [r for d in value["dialogs"] for r in d]
    if len(value["singles"]) != 208 or len(rows) != 220 or len(value["dialogs"]) != 4:
        raise ValueError("declared fresh probe membership differs")
    if any(len(d) != 3 for d in value["dialogs"]) or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("distinct IDs and four complete3-turn conversations required")
    keys = [normalized(r["question"]) for r in rows]
    if len(set(keys)) != len(keys):
        raise ValueError("new questions are duplicated")
    previous = {normalized(q) for q in previous_questions}
    if previous.intersection(keys):
        raise ValueError("fresh diagnostic repeats a checked old question")
    for r in rows:
        if type(r["scope_expected"]) is not bool or r["language"] not in ("ko", "en"):
            raise ValueError("typed scope and language metadata required")
    return rows
