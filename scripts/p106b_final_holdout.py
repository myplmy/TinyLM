"""독립 FINAL200/DEV20의 결정적 작성. 평가용이며 학습·교사 입력으로 사용하지 않는다."""
from collections import Counter
import hashlib
import json
import random
import re

CATEGORIES = ('context', 'extract', 'format', 'reasoning', 'everyday')
SCHEMA = 'P106B_FINAL200_FIRST_RESPONSE_V1'
MODELS = ('native595-q', 'new595-broad-q')
MAX_NEW = 96

# 고정 일상 지시와 내용 기준. 지식 문답이나 외부 사실 판정으로 사용하지 않는다.
DAILY = (
    ('동료에게 보낼 짧은 아침 인사 한 문장을 써 주세요.', 'Write one short morning greeting to a coworker.', '아침 인사/동료에게 적절한 말투'),
    ('우산을 빌려준 친구에게 감사하는 한 문장을 써 주세요.', 'Write one sentence thanking a friend for lending you an umbrella.', '우산 대여에 대한 감사'),
    ('약속에 5분 늦을 것 같다고 친구에게 알려 주세요.', 'Tell a friend that you expect to be five minutes late.', '5분 지각을 알리는 메시지'),
    ('잘 못 들었으니 다시 말해 달라고 정중하게 요청해 주세요.', 'Politely ask someone to repeat what you could not hear.', '다시 말해 달라는 정중한 요청'),
    ('비가 오는 날 집 안에서 할 수 있는 활동을 두 개 제안해 주세요.', 'Suggest two activities to do indoors on a rainy day.', '실내에서 가능한 활동 두 가지'),
    ('빌린 책을 늦게 돌려줘서 미안하다는 문장을 써 주세요.', 'Write an apology for returning a borrowed book late.', '늦은 책 반납에 대한 사과'),
    ('작은 실수를 해서 속상한 친구에게 짧게 격려해 주세요.', 'Briefly encourage a friend who is upset about a small mistake.', '친구에게 공감/격려'),
    ('이번 모임에는 참석할 수 없다고 정중하게 거절해 주세요.', 'Politely decline an invitation because you cannot attend this time.', '참석 불가를 정중하게 전달'),
    ('함께 일한 동료의 도움에 고마움을 표현해 주세요.', 'Express thanks to a coworker for their help on a shared task.', '동료의 도움에 대한 감사'),
    ('집중해야 해서 잠시 조용히 해 달라고 정중하게 말해 주세요.', 'Politely ask for quiet because you need to concentrate.', '집중을 위한 조용한 환경 요청'),
    ('새로 이사 온 이웃에게 건넬 짧은 환영 인사를 써 주세요.', 'Write a short welcome greeting to a new neighbor.', '새 이웃 환영'),
    ('친구에게 주말에 산책하자고 제안해 주세요.', 'Invite a friend to take a walk this weekend.', '주말 산책 제안'),
    ('분실물을 주워 준 사람에게 감사 인사를 써 주세요.', 'Thank someone who found and returned your lost item.', '분실물 반환에 대한 감사'),
    ('전화할 수 없으니 문자로 연락해 달라고 요청해 주세요.', 'Ask someone to contact you by text because you cannot take a call.', '전화 대신 문자 연락 요청'),
    ('일정을 확인한 뒤 내일 답하겠다고 정중하게 알려 주세요.', 'Politely say you will check your schedule and reply tomorrow.', '일정 확인/내일 회신 두 조건'),
    ('친구의 생일을 축하하는 한 문장을 써 주세요.', 'Write one sentence wishing a friend a happy birthday.', '생일 축하'),
    ('차례를 기다리는 사람들에게 잠시만 기다려 달라고 안내해 주세요.', 'Ask people waiting in line to wait a little longer.', '잠시 대기 안내'),
    ('오래 연락하지 못한 친구에게 안부를 묻는 문장을 써 주세요.', 'Write a message asking how a friend you have not contacted in a while is doing.', '친구 안부 질문'),
    ('같이 쓰는 물건은 사용 후 제자리에 두자고 제안해 주세요.', 'Suggest putting shared items back in their place after use.', '공용 물건 사용 후 정리 제안'),
    ('오늘 도와줄 수는 없지만 내일은 돕겠다고 말해 주세요.', 'Say that you cannot help today but can help tomorrow.', '오늘 불가/내일 가능 두 조건'),
    ('늦은 시간 소음 때문에 잠을 못 자니 소리를 줄여 달라고 정중하게 요청해 주세요.', 'Politely ask for less noise late at night because you are trying to sleep.', '야간 소음 감소 요청'),
    ('택배를 대신 받아 준 이웃에게 감사 메시지를 써 주세요.', 'Write a thank-you message to a neighbor who accepted a delivery for you.', '택배 수령에 대한 감사'),
)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest().upper()


def particle(word, consonant, vowel):
    code = ord(word[-1])
    closed = 0xAC00 <= code <= 0xD7A3 and (code - 0xAC00) % 28 != 0
    return word + (consonant if closed else vowel)


def build(split='final'):
    if split not in ('final', 'dev'):
        raise ValueError('FINAL/DEV만 작성')
    rng = random.Random(2026110107 if split == 'final' else 2026110119)
    count, offset = (20, 0) if split == 'final' else (2, 100)
    rows = []
    for language in ('ko', 'en'):
        ko = language == 'ko'
        names = ['소담', '가온', '보람', '다온', '하린', '도윤', '서진', '유진'] if ko else ['Mina', 'Lena', 'Noah', 'Owen', 'Aria', 'Luca', 'Nora', 'Theo']
        colors = ['빨강', '파랑', '초록', '노랑', '보라', '주황', '하양', '검정'] if ko else ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'white', 'black']
        places = ['서랍', '가방', '상자', '선반', '책상', '의자'] if ko else ['drawer', 'bag', 'box', 'shelf', 'desk', 'chair']
        for category in CATEGORIES:
            for i in range(count):
                n = rng.randint(3, 34) + offset + i * 7
                m = rng.randint(2, 11) + offset
                a, b, c = rng.sample(names, 3)
                first, second = rng.sample(colors, 2)
                location, previous = rng.sample(places, 2)
                rule, reference, required_repetition = 'exact', None, False
                if category == 'context':
                    if i % 4 == 0:
                        prompt = (f'문맥: {a}의 공은 {first}, {b}의 공은 {second}입니다. {b}의 공 색깔은 무엇입니까? 색깔만 쓰세요.' if ko else
                                  f'Context: {a} has a {first} ball and {b} has a {second} ball. What color is {b}\'s ball? Write only the color.')
                        reference = second
                    elif i % 4 == 1:
                        prompt = (f'열쇠는 처음에 {previous}에 있었습니다. 이후 {particle(a, "이", "가")} 열쇠를 옮겼고, 새 장소는 {location}입니다. 지금 열쇠는 어디에 있습니까? 장소만 쓰세요.' if ko else
                                  f'The key was in the {previous}. Then {a} moved the key to the {location}. Where is the key now? Write only the place.')
                        reference = location
                    elif i % 4 == 2:
                        prompt = (f'{a}의 스승은 {b}입니다. {c}의 스승은 {a}입니다. {c}의 스승은 누구입니까? 이름만 쓰세요.' if ko else
                                  f'{b} is the mentor of {a}. {a} is the mentor of {c}. Who is the mentor of {c}? Write only the name.')
                        reference = a
                    else:
                        prompt = (f'{particle(a, "은", "는")} 연필 {n}개를, {particle(b, "은", "는")} 연필 {m}개를 갖고 있습니다. {particle(a, "은", "는")} 연필을 몇 개 갖고 있습니까? 숫자만 쓰세요.' if ko else
                                  f'{a} has {n} pencils, and {b} has {m} pencils. How many pencils does {a} have? Write only the number.')
                        reference = str(n)
                    rubric = '제시한 사실/대상/마지막 위치를 정확히 조회하고 요구한 답만 출력'
                elif category == 'extract':
                    code = f'NX{n}K{m}'
                    if i % 4 == 0:
                        prompt = (f'담당: {a}; 보관코드: {code}; 비품 수: {m}. 보관코드만 그대로 출력하세요.' if ko else
                                  f'Contact: {a}; storage code: {code}; item count: {m}. Output only the storage code exactly.')
                        reference = code
                    elif i % 4 == 1:
                        word = rng.choice(['river', 'garden', 'window', 'pencil']) + str(n)
                        prompt = (f'다음 영문 문자열을 모두 대문자로 바꾸세요. 설명은 쓰지 마세요: {word}' if ko else
                                  f'Convert this string to uppercase. Give only the converted string: {word}')
                        reference = word.upper()
                    elif i % 4 == 2:
                        prompt = (f'순서대로 적힌 숫자는 {m}, {n + 4}, {n}입니다. 마지막 숫자만 쓰세요.' if ko else
                                  f'The numbers in order are {m}, {n + 4}, {n}. Write only the last number.')
                        reference = str(n)
                    else:
                        prompt = (f'목록: {a}, {b}, {c}. 마지막 이름만 쓰세요.' if ko else
                                  f'List: {a}, {b}, {c}. Write only the last name.')
                        reference = c
                    rubric = '제시된 값/순서/대소문자 변환을 정확히 수행; 다른 답 추가 없음'
                elif category == 'format':
                    if i % 4 == 0:
                        first = colors[i // 4 if split == 'final' else 5]
                        prompt = (f'답 내용은 {first}입니다. answer 하나를 키로 갖고 답 내용을 문자열 값으로 넣은 JSON 객체만 쓰세요.' if ko else
                                  f'The answer content is {first}. Output only a JSON object with one key, answer, whose string value is that content.')
                        rule, reference = 'json', dict(answer=first)
                    elif i % 4 == 1:
                        prompt = (f'이름은 {a}, 개수는 {n}입니다. name 문자열과 count 정수를 갖는 JSON 객체만 쓰세요.' if ko else
                                  f'The name is {a} and the count is {n}. Output only a JSON object with a name string and a count integer.')
                        rule, reference = 'json', dict(name=a, count=n)
                    elif i % 4 == 2:
                        word = (['똑똑', '안녕', '고마워', '환영', '또각'] if ko else
                                ['knock', 'hello', 'thanks', 'welcome', 'tap'])[i // 4]
                        prompt = (f'다음 단어를 정확히 세 번 쓰고 단어 사이에는 공백 한 칸만 넣으세요. 다른 내용은 쓰지 마세요. 단어: {word}' if ko else
                                  f'Write {word} exactly three times, separated by single spaces. Write nothing else.')
                        reference, required_repetition = ' '.join([word] * 3), True
                    else:
                        prompt = (f'첫째 줄에는 {a}, 둘째 줄에는 {b}만 쓰세요. 두 줄 외 다른 내용은 쓰지 마세요.' if ko else
                                  f'Write only {a} on the first line and {b} on the second line. Add nothing else.')
                        reference = a + chr(10) + b
                    rubric = '주어진 내용과 명시한 JSON/반복/두줄 형식을 모두 충족'
                elif category == 'reasoning':
                    if i % 4 == 0:
                        prompt = (f'{n}+{m}의 값은 무엇입니까? 정수만 쓰세요.' if ko else f'What is {n}+{m}? Write only the integer.')
                        reference = str(n + m)
                    elif i % 4 == 1:
                        prompt = (f'{n}×{m}의 값을 계산하세요. 정수만 쓰세요.' if ko else f'What is {n} times {m}? Write only the integer.')
                        reference = str(n * m)
                    elif i % 4 == 2:
                        left, right = bool(i % 3), bool(i % 5)
                        expression, value = [
                            ('A AND (NOT B)', left and not right),
                            ('A OR B', left or right), ('NOT A', not left),
                            ('A XOR B', left != right), ('A AND B', left and right)][i // 4]
                        truth = lambda v: ('참' if v else '거짓') if ko else ('true' if v else 'false')
                        prompt = (f'A는 {truth(left)}, B는 {truth(right)}입니다. {expression}의 값은 무엇입니까? XOR는 두 값이 다를 때 참입니다. 참 또는 거짓만 쓰세요.' if ko else
                                  f'A is {truth(left)} and B is {truth(right)}. What is {expression}? XOR is true when the values differ. Write only true or false.')
                        reference = truth(value)
                    else:
                        prompt = (f'상자에 공 {n}개가 있습니다. {m}개를 더 넣은 뒤 {m + 1}개를 꺼냈습니다. 남은 공의 개수만 정수로 쓰세요.' if ko else
                                  f'A box has {n} balls. Add {m} balls, then remove {m + 1} balls. Write only the remaining integer count.')
                        reference = str(n - 1)
                    rubric = '명시한 수/불 조건의 결과를 정확히 계산하고 요구한 답만 출력'
                else:
                    item = DAILY[i if split == 'final' else 20 + i]
                    prompt, rubric = item[0 if ko else 1], item[2]
                    rule = 'manual'
                rows.append(dict(id=f'{split}_{language}_{category}_{i:02d}', split=split, language=language,
                                 category=category, prompt=prompt, match_rule=rule, reference=reference,
                                 rubric=rubric, required_repetition=required_repetition))
    return rows


def validate(final, dev):
    expected = Counter({(lang, cat): 20 for lang in ('ko', 'en') for cat in CATEGORIES})
    expected_dev = Counter({(lang, cat): 2 for lang in ('ko', 'en') for cat in CATEGORIES})
    if (Counter((r['language'], r['category']) for r in final) != expected
            or Counter((r['language'], r['category']) for r in dev) != expected_dev):
        raise ValueError('FINAL200/DEV20의 언어·유형 분모가 다름')
    all_rows = final + dev
    if len({r['id'] for r in all_rows}) != len(all_rows):
        raise ValueError('문항 ID 중복')
    if len({r['prompt'] for r in all_rows}) != len(all_rows):
        raise ValueError('FINAL/DEV 안팎의 질문 중복')
    for row in all_rows:
        if not row['prompt'].strip() or row['match_rule'] not in ('exact', 'json', 'manual'):
            raise ValueError('정의되지 않은 문항/판독 규칙')
        if row['match_rule'] == 'manual' and row['reference'] is not None:
            raise ValueError('열린 답을 단일 문자열 정답으로 취급하지 않음')
        if row['match_rule'] == 'exact' and (not isinstance(row['reference'], str) or not row['reference']):
            raise ValueError('정확 문자열 정답은 비어 있지 않은 문자열')
        if row['match_rule'] == 'json' and not isinstance(row['reference'], dict):
            raise ValueError('명시 JSON 정답은 객체')
    if any(r['split'] != 'final' for r in final) or any(r['split'] != 'dev' for r in dev):
        raise ValueError('FINAL/DEV 분할 표기 오류')
    return dict(final_rows=len(final), dev_rows=len(dev), final_sha256=digest(final), dev_sha256=digest(dev),
                counts={lang: dict(Counter(r['category'] for r in final if r['language'] == lang)) for lang in ('ko', 'en')},
                train_usage='PROHIBITED_EVALUATION_ONLY', generated_from_public_benchmark=False)


def reference_match(answer, case):
    if case['match_rule'] == 'manual':
        return None
    if case['match_rule'] == 'exact':
        return answer.strip() == case['reference']
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('중복 JSON key')
            result[key] = value
        return result
    try:
        # canonical JSON은 정수/실수·bool/정수의 Python equality 혼동도 피한다.
        actual = json.loads(answer.strip(), object_pairs_hook=unique)
        return canonical(actual) == canonical(case['reference'])
    except (ValueError, TypeError):
        return False


def review_signals(answer, metadata, case):
    return dict(empty=not bool(answer.strip()), limit_reached=metadata.get('finish_reason') == 'MAX_NEW',
                role_delimiter_candidate='<|' in answer or '|>' in answer,
                repeated_phrase_candidate=bool(re.search(r'(.{2,40})\1\1', answer)),
                required_repetition=case['required_repetition'],
                prompt_copy_candidate=len(case['prompt']) > 15 and case['prompt'] in answer,
                automatic_failure_or_quality_verdict=False)
