# P108 원본과 동결 수리의 실제 질문·답

새 규칙형 test128과 별도 일상16의 전체 대응 원답이다. 공식 벤치마크가 아니며 정답표는 test 선택에 사용하지 않았다.

## test_arithmetic_000

질문: 12+12의 값만 쓰세요.

기대답: 24

원본 답:

    16

수리 답:

    16

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_001

질문: What is 13+12? Write only the number.

기대답: 25

원본 답:

    13

수리 답:

    13

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_002

질문: 14+12의 값만 쓰세요.

기대답: 26

원본 답:

    16

수리 답:

    16

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_003

질문: What is 15+12? Write only the number.

기대답: 27

원본 답:

    15

수리 답:

    15

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_004

질문: 16+12의 값만 쓰세요.

기대답: 28

원본 답:

    12+12의 값만 쓰세요.

수리 답:

    12+12의 값만 쓰세요.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_005

질문: What is 17+12? Write only the number.

기대답: 29

원본 답:

    17

수리 답:

    17

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_006

질문: 18+12의 값만 쓰세요.

기대답: 30

원본 답:

    12

수리 답:

    12

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_007

질문: What is 19+12? Write only the number.

기대답: 31

원본 답:

    19

수리 답:

    19

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_008

질문: 1+13의 값만 쓰세요.

기대답: 14

원본 답:

    13+13

수리 답:

    13+13

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_009

질문: What is 2+13? Write only the number.

기대답: 15

원본 답:

    13

수리 답:

    13

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_010

질문: 3+13의 값만 쓰세요.

기대답: 16

원본 답:

    15

수리 답:

    15

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_011

질문: What is 4+13? Write only the number.

기대답: 17

원본 답:

    4+13

수리 답:

    4+13

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_012

질문: 5+13의 값만 쓰세요.

기대답: 18

원본 답:

    16

수리 답:

    16

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_013

질문: What is 6+13? Write only the number.

기대답: 19

원본 답:

    6+13

수리 답:

    6+13

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_014

질문: 7+13의 값만 쓰세요.

기대답: 20

원본 답:

    15

수리 답:

    15

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_015

질문: What is 8+13? Write only the number.

기대답: 21

원본 답:

    8+13

수리 답:

    8+13

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_entity_000

질문: A201는 사과이고 B201는 당근입니다. B201는 무엇입니까? 단어만 쓰세요.

기대답: 당근

원본 답:

    당근입니다.

수리 답:

    당근입니다.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_entity_001

질문: A202 is an apple and B202 is a carrot. What is B202? Write only the noun.

기대답: carrot

원본 답:

    B202 is a carrot. It is a carrot that is a carrot.

수리 답:

    B202 is a carrot. It is a carrot that is a carrot.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_entity_002

질문: A203는 사과이고 B203는 당근입니다. B203는 무엇입니까? 단어만 쓰세요.

기대답: 당근

원본 답:

    B203

수리 답:

    B203는 사과입니다.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_entity_003

질문: A204 is an apple and B204 is a carrot. What is B204? Write only the noun.

기대답: carrot

원본 답:

    B204 is a carrot. It is a carrot that is a carrot. It is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is

수리 답:

    B204 is a carrot. It is a carrot that is a carrot. It is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is

종료: MAX_NEW → MAX_NEW

## test_entity_004

질문: A205는 사과이고 B205는 당근입니다. B205는 무엇입니까? 단어만 쓰세요.

기대답: 당근

원본 답:

    B205

수리 답:

    B205

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_entity_005

질문: A206 is an apple and B206 is a carrot. What is B206? Write only the noun.

기대답: carrot

원본 답:

    B206 is a carrot. It is a carrot that is a carrot. It is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is

수리 답:

    B206 is a carrot. It is a carrot that is a carrot. It is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is

종료: MAX_NEW → MAX_NEW

## test_entity_006

질문: A207는 사과이고 B207는 당근입니다. B207는 무엇입니까? 단어만 쓰세요.

기대답: 당근

원본 답:

    B207

수리 답:

    B207

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_entity_007

질문: A208 is an apple and B208 is a carrot. What is B208? Write only the noun.

기대답: carrot

원본 답:

    B208 is a carrot. It is a carrot that is a carrot. It is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is

수리 답:

    B208 is a carrot. It is a carrot that is a carrot. It is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is

종료: MAX_NEW → MAX_NEW

## test_entity_008

질문: A209는 사과이고 B209는 당근입니다. B209는 무엇입니까? 단어만 쓰세요.

기대답: 당근

원본 답:

    B209

수리 답:

    B209 (신뢰)

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_entity_009

질문: A210 is an apple and B210 is a carrot. What is B210? Write only the noun.

기대답: carrot

원본 답:

    B210 is a carrot. It is a carrot that is a carrot. It is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is

수리 답:

    B210 is a carrot. It is a carrot that is a carrot.

종료: MAX_NEW → STOP_SEQUENCE

## test_entity_010

질문: A211는 사과이고 B211는 당근입니다. B211는 무엇입니까? 단어만 쓰세요.

기대답: 당근

원본 답:

    B211

수리 답:

    B211

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_entity_011

질문: A212 is an apple and B212 is a carrot. What is B212? Write only the noun.

기대답: carrot

원본 답:

    B212 is a carrot. It is a carrot that is a carrot.

수리 답:

    B212 is a carrot. It is a carrot that is a carrot.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_entity_012

질문: A213는 사과이고 B213는 당근입니다. B213는 무엇입니까? 단어만 쓰세요.

기대답: 당근

원본 답:

    B213

수리 답:

    B213 - 당근입니다.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_entity_013

질문: A214 is an apple and B214 is a carrot. What is B214? Write only the noun.

기대답: carrot

원본 답:

    B214 is a carrot. It is a carrot that is a carrot. It is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is a carrot that is

수리 답:

    B214 is a carrot. It is a carrot that is a carrot.

종료: MAX_NEW → STOP_SEQUENCE

## test_entity_014

질문: A215는 사과이고 B215는 당근입니다. B215는 무엇입니까? 단어만 쓰세요.

기대답: 당근

원본 답:

    B215

수리 답:

    B215

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_entity_015

질문: A216 is an apple and B216 is a carrot. What is B216? Write only the noun.

기대답: carrot

원본 답:

    B216 is a carrot. It is a carrot that is a carrot.

수리 답:

    B216 is a carrot. It is a carrot that is a carrot.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_000

질문: 민수201는 운전하고 영희201는 요리합니다. 누가 요리합니까? 이름만 쓰세요.

기대답: 영희201

원본 답:

    정지영

수리 답:

    정지영

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_001

질문: Alice202 drives and Bob202 cooks. Who cooks? Write only the name.

기대답: Bob202

원본 답:

    Alice202 drives

수리 답:

    Alice202 drives

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_002

질문: 민수203는 운전하고 영희203는 요리합니다. 누가 요리합니까? 이름만 쓰세요.

기대답: 영희203

원본 답:

    민수204

수리 답:

    민수204

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_003

질문: Alice204 drives and Bob204 cooks. Who cooks? Write only the name.

기대답: Bob204

원본 답:

    Alice204 drives

수리 답:

    Alice204 drives

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_004

질문: 민수205는 운전하고 영희205는 요리합니다. 누가 요리합니까? 이름만 쓰세요.

기대답: 영희205

원본 답:

    민수206

수리 답:

    민수206

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_005

질문: Alice206 drives and Bob206 cooks. Who cooks? Write only the name.

기대답: Bob206

원본 답:

    Alice206 drives

수리 답:

    Alice206 drives

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_006

질문: 민수207는 운전하고 영희207는 요리합니다. 누가 요리합니까? 이름만 쓰세요.

기대답: 영희207

원본 답:

    민수208

수리 답:

    민수208

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_007

질문: Alice208 drives and Bob208 cooks. Who cooks? Write only the name.

기대답: Bob208

원본 답:

    Alice208 drives

수리 답:

    Alice208 drives

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_008

질문: 민수209는 운전하고 영희209는 요리합니다. 누가 요리합니까? 이름만 쓰세요.

기대답: 영희209

원본 답:

    민수209

수리 답:

    민수209는 요리합니까? 이름만 쓰세요.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_009

질문: Alice210 drives and Bob210 cooks. Who cooks? Write only the name.

기대답: Bob210

원본 답:

    Alice210 drives

수리 답:

    Alice210 drives

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_010

질문: 민수211는 운전하고 영희211는 요리합니다. 누가 요리합니까? 이름만 쓰세요.

기대답: 영희211

원본 답:

    민수211

수리 답:

    민수211

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_011

질문: Alice212 drives and Bob212 cooks. Who cooks? Write only the name.

기대답: Bob212

원본 답:

    Alice212 drives

수리 답:

    Alice212 drives

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_012

질문: 민수213는 운전하고 영희213는 요리합니다. 누가 요리합니까? 이름만 쓰세요.

기대답: 영희213

원본 답:

    민수214

수리 답:

    민수214

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_013

질문: Alice214 drives and Bob214 cooks. Who cooks? Write only the name.

기대답: Bob214

원본 답:

    Alice214 drives

수리 답:

    Alice214 drives

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_014

질문: 민수215는 운전하고 영희215는 요리합니다. 누가 요리합니까? 이름만 쓰세요.

기대답: 영희215

원본 답:

    민수215

수리 답:

    민수215

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_015

질문: Alice216 drives and Bob216 cooks. Who cooks? Write only the name.

기대답: Bob216

원본 답:

    Alice216 drives

수리 답:

    Alice216 drives

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_000

질문: A201=참, B201=거짓입니다. A201 AND B201는? 참 또는 거짓만 쓰세요.

기대답: 거짓

원본 답:

    참

수리 답:

    참, B201=거짓입니다. A201 AND B201는? 참, B201는? 참, B201는? 참, B201는? 참, B201는? 참, B201는? 참, B201는? 참, B201는? 참, B201은? 참, B201은? 참, B201은? 참, B201은? 참, B201은? 참, B201은? 참,

종료: STOP_SEQUENCE → MAX_NEW

## test_boolean_001

질문: A202=true, B202=true. What is A202 AND B202? Write true or false.

기대답: true

원본 답:

    A202 AND B202=true

수리 답:

    A202 AND B202=true

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_002

질문: A203=참, B203=참입니다. A203 AND B203는? 참 또는 거짓만 쓰세요.

기대답: 참

원본 답:

    참

수리 답:

    참

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_003

질문: A204=true, B204=false. What is A204 AND B204? Write true or false.

기대답: false

원본 답:

    A204 AND B204=false

수리 답:

    A204 AND B204=false

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_004

질문: A205=참, B205=참입니다. A205 AND B205는? 참 또는 거짓만 쓰세요.

기대답: 참

원본 답:

    참

수리 답:

    참

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_005

질문: A206=true, B206=true. What is A206 AND B206? Write true or false.

기대답: true

원본 답:

    A206 AND B206 =true, B206 =true, B206 =true. What is the relationship between the two?
    A206 AND B206 =true, B206 =true, B206 =true. What is the relationship between the two?

수리 답:

    A206 AND B206 =true, B206 =true, B206 =true. What is the relationship between the two?
    A206 AND B206 =true, B206 =true, B206 =true. What is the relationship between the two?

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_006

질문: A207=참, B207=거짓입니다. A207 AND B207는? 참 또는 거짓만 쓰세요.

기대답: 거짓

원본 답:

    참

수리 답:

    참

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_007

질문: A208=true, B208=true. What is A208 AND B208? Write true or false.

기대답: true

원본 답:

    A208 AND B208=true

수리 답:

    A208 AND B208=true

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_008

질문: A209=참, B209=참입니다. A209 AND B209는? 참 또는 거짓만 쓰세요.

기대답: 참

원본 답:

    참

수리 답:

    참

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_009

질문: A210=true, B210=false. What is A210 AND B210? Write true or false.

기대답: false

원본 답:

    A210 AND B210 =false

수리 답:

    A210 AND B210 =false

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_010

질문: A211=참, B211=참입니다. A211 AND B211는? 참 또는 거짓만 쓰세요.

기대답: 참

원본 답:

    참

수리 답:

    참

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_011

질문: A212=true, B212=true. What is A212 AND B212? Write true or false.

기대답: true

원본 답:

    A212 AND B212=true

수리 답:

    A212 AND B212=true

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_012

질문: A213=참, B213=거짓입니다. A213 AND B213는? 참 또는 거짓만 쓰세요.

기대답: 거짓

원본 답:

    참

수리 답:

    참

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_013

질문: A214=true, B214=true. What is A214 AND B214? Write true or false.

기대답: true

원본 답:

    A214 AND B214=true

수리 답:

    A214 AND B214=true

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_014

질문: A215=참, B215=참입니다. A215 AND B215는? 참 또는 거짓만 쓰세요.

기대답: 참

원본 답:

    참

수리 답:

    참

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_015

질문: A216=true, B216=false. What is A216 AND B216? Write true or false.

기대답: false

원본 답:

    A216 AND B216 =true

수리 답:

    A216 AND B216 =true

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_000

질문: 사과가 12개 있습니다. 12개를 더 받았습니다. 지금 개수만 쓰세요.

기대답: 24

원본 답:

    개수만 쓰세요.

수리 답:

    개수만 쓰세요.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_001

질문: There are 13 apples. You receive 12 more. Write only the new count.

기대답: 25

원본 답:

    13 apples

수리 답:

    13 apples

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_002

질문: 사과가 14개 있습니다. 12개를 더 받았습니다. 지금 개수만 쓰세요.

기대답: 26

원본 답:

    개수만 쓰세요.

수리 답:

    개수만 쓰세요.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_003

질문: There are 15 apples. You receive 12 more. Write only the new count.

기대답: 27

원본 답:

    16 apples

수리 답:

    16 apples

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_004

질문: 사과가 16개 있습니다. 12개를 더 받았습니다. 지금 개수만 쓰세요.

기대답: 28

원본 답:

    16개

수리 답:

    16개

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_005

질문: There are 17 apples. You receive 12 more. Write only the new count.

기대답: 29

원본 답:

    16 apples

수리 답:

    16 apples

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_006

질문: 사과가 18개 있습니다. 12개를 더 받았습니다. 지금 개수만 쓰세요.

기대답: 30

원본 답:

    개수만 쓰세요.

수리 답:

    개수만 쓰세요.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_007

질문: There are 19 apples. You receive 12 more. Write only the new count.

기대답: 31

원본 답:

    20 apples

수리 답:

    20 apples

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_008

질문: 사과가 1개 있습니다. 13개를 더 받았습니다. 지금 개수만 쓰세요.

기대답: 14

원본 답:

    개수만 쓰세요.

수리 답:

    개수만 쓰세요.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_009

질문: There are 2 apples. You receive 13 more. Write only the new count.

기대답: 15

원본 답:

    13

수리 답:

    13

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_010

질문: 사과가 3개 있습니다. 13개를 더 받았습니다. 지금 개수만 쓰세요.

기대답: 16

원본 답:

    개수만 쓰세요.

수리 답:

    개수만 쓰세요.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_011

질문: There are 4 apples. You receive 13 more. Write only the new count.

기대답: 17

원본 답:

    5 apples

수리 답:

    5 apples

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_012

질문: 사과가 5개 있습니다. 13개를 더 받았습니다. 지금 개수만 쓰세요.

기대답: 18

원본 답:

    개수만 쓰세요.

수리 답:

    개수만 쓰세요.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_013

질문: There are 6 apples. You receive 13 more. Write only the new count.

기대답: 19

원본 답:

    6 apples

수리 답:

    6 apples

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_014

질문: 사과가 7개 있습니다. 13개를 더 받았습니다. 지금 개수만 쓰세요.

기대답: 20

원본 답:

    개수만 쓰세요.

수리 답:

    개수만 쓰세요.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_015

질문: There are 8 apples. You receive 13 more. Write only the new count.

기대답: 21

원본 답:

    12 apples

수리 답:

    12 apples

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_copy_000

질문: 다음 문자열을 그대로 복사하세요: key-201-value

기대답: key-201-value

원본 답:

    열대-20

수리 답:

    열대-20

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_copy_001

질문: Copy exactly this string: key-202-value

기대답: key-202-value

원본 답:

    Copy the string from the key-202-value
    Copy the string from the key-202-value
    Copy the string from the key-202-value
    Copy the string from the key-202-value
    Copy the string from the key-202-value
    Copy the string from the key-202-value
    Copy the string from the key-202-value
    Copy the string from

수리 답:

    Copy the string from the key-202-value
    Copy the string from the key-202-value
    Copy the string from the key-202-value
    Copy the string from the key-202-value
    Copy the string from the key-202-value
    Copy the string from the key-202-value
    Copy the string from the key-202-value
    Copy the string from

종료: MAX_NEW → MAX_NEW

## test_copy_002

질문: 다음 문자열을 그대로 복사하세요: key-203-value

기대답: key-203-value

원본 답:

    {"answer": "add"}

수리 답:

    {"answer": "add"}

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_copy_003

질문: Copy exactly this string: key-204-value

기대답: key-204-value

원본 답:

    Copy the string from the key-204-value
    Copy the string from the key-204-value
    Copy the string from the key-204-value
    Copy the string from the key-204-value
    Copy the string from the key-204-value
    Copy the string from the key-204-value
    Copy the string from the key-204-value
    Copy the string from

수리 답:

    Copy the string from the key-204-value
    Copy the string from the key-204-value
    Copy the string from the key-204-value
    Copy the string from the key-204-value
    Copy the string from the key-204-value
    Copy the string from the key-204-value
    Copy the string from the key-204-value
    Copy the string from

종료: MAX_NEW → MAX_NEW

## test_copy_004

질문: 다음 문자열을 그대로 복사하세요: key-205-value

기대답: key-205-value

원본 답:

    {"answer": "add"}

수리 답:

    {"answer": "add"}

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_copy_005

질문: Copy exactly this string: key-206-value

기대답: key-206-value

원본 답:

    Copy the string from the key-206-value
    Copy the string from the key-206-value
    Copy the string from the key-206-value
    Copy the string from the key-206-value
    Copy the string from the key-206-value
    Copy the string from the key-206-value
    Copy the string from the key-206-value
    Copy the string from

수리 답:

    Copy the string from the key-206-value
    Copy the string from the key-206-value
    Copy the string from the key-206-value
    Copy the string from the key-206-value
    Copy the string from the key-206-value
    Copy the string from the key-206-value
    Copy the string from the key-206-value
    Copy the string from

종료: MAX_NEW → MAX_NEW

## test_copy_006

질문: 다음 문자열을 그대로 복사하세요: key-207-value

기대답: key-207-value

원본 답:

    {"answer": "add"}

수리 답:

    {"answer": "add"}

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_copy_007

질문: Copy exactly this string: key-208-value

기대답: key-208-value

원본 답:

    Copy the string from the key-208-value
    Copy the string from the key-208-value
    Copy the string from the key-208-value
    Copy the string from the key-208-value
    Copy the string from the key-208-value
    Copy the string from the key-208-value
    Copy the string from the key-208-value
    Copy the string from

수리 답:

    Copy the string from the key-208-value
    Copy the string from the key-208-value
    Copy the string from the key-208-value
    Copy the string from the key-208-value
    Copy the string from the key-208-value
    Copy the string from the key-208-value
    Copy the string from the key-208-value
    Copy the string from

종료: MAX_NEW → MAX_NEW

## test_copy_008

질문: 다음 문자열을 그대로 복사하세요: key-209-value

기대답: key-209-value

원본 답:

    {"answer": "add"}

수리 답:

    {"answer": "add"}

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_copy_009

질문: Copy exactly this string: key-210-value

기대답: key-210-value

원본 답:

    Copy the string from the key-210-value of the key-210-value of the key-210-value of the key-210-value of the key-210-value of the key-210-value of the key-210-value of the key-210-value of the key-210-value of the key-210-value of the key-210-value of the key-

수리 답:

    Copy the string from the key-210-value of the key-210-value of the key-210-value of the key-210-value of the key-210-value of the key-210-value of the key-210-value of the key-210-value of the key-210-value of the key-210-value of the key-210-value of the key-

종료: MAX_NEW → MAX_NEW

## test_copy_010

질문: 다음 문자열을 그대로 복사하세요: key-211-value

기대답: key-211-value

원본 답:

    {"answer": "add"}

수리 답:

    {"answer": "add"}

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_copy_011

질문: Copy exactly this string: key-212-value

기대답: key-212-value

원본 답:

    Copy the string from the key-212-value of the key-212-value of the key-212-value of the key-212-value of the key-212-value of the key-212-value of the key-212-value of the key-212-value of the key-212-value of the key-212-value of the key-212-value of the key-

수리 답:

    Copy the string from the key-212-value

종료: MAX_NEW → STOP_SEQUENCE

## test_copy_012

질문: 다음 문자열을 그대로 복사하세요: key-213-value

기대답: key-213-value

원본 답:

    {"answer": "add"}

수리 답:

    {"answer": "add"}

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_copy_013

질문: Copy exactly this string: key-214-value

기대답: key-214-value

원본 답:

    Copy the string from the key-214-value
    Copy the string from the key-214-value
    Copy the string from the key-214-value
    Copy the string from the key-214-value
    Copy the string from the key-214-value
    Copy the string from the key-214-value
    Copy the string from the key-214-value
    Copy the string from

수리 답:

    Copy the string from the key-214-value
    Copy the string from the key-214-value
    Copy the string from the key-214-value
    Copy the string from the key-214-value
    Copy the string from the key-214-value
    Copy the string from the key-214-value
    Copy the string from the key-214-value
    Copy the string from

종료: MAX_NEW → MAX_NEW

## test_copy_014

질문: 다음 문자열을 그대로 복사하세요: key-215-value

기대답: key-215-value

원본 답:

    {"answer": "add"}

수리 답:

    {"answer": "add"}

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_copy_015

질문: Copy exactly this string: key-216-value

기대답: key-216-value

원본 답:

    Copy the string from the key-216-value

수리 답:

    Copy the string from the key-216-value

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_repeat_000

질문: 201을 공백으로 구분해 정확히 세 번 쓰세요.

기대답: 201 201 201

원본 답:

    20

수리 답:

    20

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_repeat_001

질문: Write 202 exactly three times, separated by spaces.

기대답: 202 202 202

원본 답:

    1:1

수리 답:

    1:1

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_repeat_002

질문: 203을 공백으로 구분해 정확히 세 번 쓰세요.

기대답: 203 203 203

원본 답:

    217

수리 답:

    217

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_repeat_003

질문: Write 204 exactly three times, separated by spaces.

기대답: 204 204 204

원본 답:

    1:1

수리 답:

    1:1

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_repeat_004

질문: 205을 공백으로 구분해 정확히 세 번 쓰세요.

기대답: 205 205 205

원본 답:

    125

수리 답:

    125

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_repeat_005

질문: Write 206 exactly three times, separated by spaces.

기대답: 206 206 206

원본 답:

    1:1

수리 답:

    1:1

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_repeat_006

질문: 207을 공백으로 구분해 정확히 세 번 쓰세요.

기대답: 207 207 207

원본 답:

    280

수리 답:

    280

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_repeat_007

질문: Write 208 exactly three times, separated by spaces.

기대답: 208 208 208

원본 답:

    1:1

수리 답:

    1:1

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_repeat_008

질문: 209을 공백으로 구분해 정확히 세 번 쓰세요.

기대답: 209 209 209

원본 답:

    215

수리 답:

    215

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_repeat_009

질문: Write 210 exactly three times, separated by spaces.

기대답: 210 210 210

원본 답:

    1:1

수리 답:

    1:1

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_repeat_010

질문: 211을 공백으로 구분해 정확히 세 번 쓰세요.

기대답: 211 211 211

원본 답:

    280

수리 답:

    280

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_repeat_011

질문: Write 212 exactly three times, separated by spaces.

기대답: 212 212 212

원본 답:

    1:1

수리 답:

    1:1

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_repeat_012

질문: 213을 공백으로 구분해 정확히 세 번 쓰세요.

기대답: 213 213 213

원본 답:

    123

수리 답:

    123

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_repeat_013

질문: Write 214 exactly three times, separated by spaces.

기대답: 214 214 214

원본 답:

    1. Write the following sentence:
    
    1. What is the relationship between the two worlds?
    2. What is the relationship between the two worlds?
    3. What is the relationship between the two worlds?
    4. What is the relationship between the two worlds?
    5. What is the relationship between the two worlds?
    6. What is the relationship between the two worlds?
    7. What is the relationship between the two worlds?
    8. What

수리 답:

    1. Write the following sentence:
    
    1. What is the relationship between the two worlds?
    2. What is the relationship between the two worlds?
    3. What is the relationship between the two worlds?
    4. What is the relationship between the two worlds?
    5. What is the relationship between the two worlds?
    6. What is the relationship between the two worlds?
    7. What is the relationship between the two worlds?
    8. What

종료: MAX_NEW → MAX_NEW

## test_repeat_014

질문: 215을 공백으로 구분해 정확히 세 번 쓰세요.

기대답: 215 215 215

원본 답:

    215

수리 답:

    215

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_repeat_015

질문: Write 216 exactly three times, separated by spaces.

기대답: 216 216 216

원본 답:

    1:1

수리 답:

    1:1

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_format_000

질문: 12+12의 값을 문자열로 answer 항목 하나인 JSON으로 쓰세요.

기대답: {"answer":"24"}

원본 답:

    16

수리 답:

    16

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_format_001

질문: Write 13+12 as JSON with only the key answer and a string value.

기대답: {"answer":"25"}

원본 답:

    13

수리 답:

    13

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_format_002

질문: 14+12의 값을 문자열로 answer 항목 하나인 JSON으로 쓰세요.

기대답: {"answer":"26"}

원본 답:

    16

수리 답:

    16

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_format_003

질문: Write 15+12 as JSON with only the key answer and a string value.

기대답: {"answer":"27"}

원본 답:

    16

수리 답:

    16

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_format_004

질문: 16+12의 값을 문자열로 answer 항목 하나인 JSON으로 쓰세요.

기대답: {"answer":"28"}

원본 답:

    16

수리 답:

    16

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_format_005

질문: Write 17+12 as JSON with only the key answer and a string value.

기대답: {"answer":"29"}

원본 답:

    16

수리 답:

    16

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_format_006

질문: 18+12의 값을 문자열로 answer 항목 하나인 JSON으로 쓰세요.

기대답: {"answer":"30"}

원본 답:

    
    같이 보기 
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자

수리 답:

    
    같이 보기 
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자
     숫자

종료: MAX_NEW → MAX_NEW

## test_format_007

질문: Write 19+12 as JSON with only the key answer and a string value.

기대답: {"answer":"31"}

원본 답:

    126

수리 답:

    126

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_format_008

질문: 1+13의 값을 문자열로 answer 항목 하나인 JSON으로 쓰세요.

기대답: {"answer":"14"}

원본 답:

    1+13

수리 답:

    1+13

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_format_009

질문: Write 2+13 as JSON with only the key answer and a string value.

기대답: {"answer":"15"}

원본 답:

    13

수리 답:

    13

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_format_010

질문: 3+13의 값을 문자열로 answer 항목 하나인 JSON으로 쓰세요.

기대답: {"answer":"16"}

원본 답:

    4+13

수리 답:

    4+13

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_format_011

질문: Write 4+13 as JSON with only the key answer and a string value.

기대답: {"answer":"17"}

원본 답:

    10+13

수리 답:

    10+13

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_format_012

질문: 5+13의 값을 문자열로 answer 항목 하나인 JSON으로 쓰세요.

기대답: {"answer":"18"}

원본 답:

    113

수리 답:

    113

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_format_013

질문: Write 6+13 as JSON with only the key answer and a string value.

기대답: {"answer":"19"}

원본 답:

    13

수리 답:

    13

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_format_014

질문: 7+13의 값을 문자열로 answer 항목 하나인 JSON으로 쓰세요.

기대답: {"answer":"20"}

원본 답:

    8

수리 답:

    8

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_format_015

질문: Write 8+13 as JSON with only the key answer and a string value.

기대답: {"answer":"21"}

원본 답:

    11+13

수리 답:

    113

종료: STOP_SEQUENCE → STOP_SEQUENCE

## open_000

질문: 1+1은?

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    1+1은?

수리 답:

    1+1은?

종료: STOP_SEQUENCE → STOP_SEQUENCE

## open_001

질문: 2+2는?

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    2+2

수리 답:

    2+2

종료: STOP_SEQUENCE → STOP_SEQUENCE

## open_002

질문: A는 사과고 B는 당근이다. B는 무엇인가? 답만 쓰세요.

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    B는 사과고입니다.

수리 답:

    B는 사과고입니다.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## open_003

질문: 문맥: 민수는 사과 3개, 영희는 사과 5개를 가지고 있습니다. 영희의 사과는 몇 개입니까?

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    사과의 사과의 사과의 사과는 사과

수리 답:

    사과의 사과의 사과의 사과는 사과

종료: STOP_SEQUENCE → STOP_SEQUENCE

## open_004

질문: 사과에 대해 두 문장으로 알려줘.

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    두 문장으로 알려줘

수리 답:

    두 문장으로 알려줘

종료: STOP_SEQUENCE → STOP_SEQUENCE

## open_005

질문: 농구란 무엇인가?

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    농구란 무엇인가?

수리 답:

    농구란 무엇인가?

종료: STOP_SEQUENCE → STOP_SEQUENCE

## open_006

질문: 안녕하세요. 오늘 처음 대화합니다.

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    안녕하세요. 오늘 처음 대화합니다.

수리 답:

    안녕하세요. 오늘 처음 대화합니다.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## open_007

질문: 어제 산 그 물건은 어디에 두면 좋을까요?

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    산 그 물건은 어디에 두면 좋을까요?

수리 답:

    산 그 물건은 어디에 두면 좋을까요?

종료: STOP_SEQUENCE → STOP_SEQUENCE

## open_008

질문: What is an apple? Answer in one sentence.

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    A apple is a fruit that is grown in the United States. It is grown in the United States from a tree that is grown in the United States.

수리 답:

    A apple is a fruit that is grown in the United States. It is grown in the United States from a tree that is grown in the United States.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## open_009

질문: What is basketball?

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    A basketball is a game where players play a ball and then they play it. The game is played by a player who plays the ball and then they play it. The game is played by a player who plays the ball and then they play it.

수리 답:

    A basketball is a game where players play a ball and then they play it. The game is played by a player who plays the ball and then they play it. The game is played by a player who plays the ball and then they play it.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## open_010

질문: Alice has three apples. Bob has five apples. How many apples does Bob have?

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    Something that can't be done with a apple. Bob has five apples.
    Alice has five apples.
    Alice has five apples.
    Alice has five apples.
    Alice has five apples.
    Alice has five apples.
    Alice has five apples.
    Alice has five apples.
    Alice has five apples.
    Alice has five apples.
    Alice has five apples.
    Alice has five apples.
    Al

수리 답:

    Something that can't be done with a apple. Bob has five apples.
    Alice has five apples.
    Alice has five apples.
    Alice has five apples.
    Alice has five apples.
    Alice has five apples.
    Alice has five apples.
    Alice has five apples.
    Alice has five apples.
    Alice has five apples.
    Alice has five apples.
    Alice has five apples.
    Al

종료: MAX_NEW → MAX_NEW

## open_011

질문: What is the capital of France?

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    The capital of France is the capital of the United Kingdom of Great Britain.

수리 답:

    The capital of France is the capital of the United Kingdom of Great Britain.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## open_012

질문: Explain why plants need sunlight in two sentences.

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    Sure, here's a simple example of how plants need sunlight in two sentences.
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

수리 답:

    Sure, here's a simple example of how plants need sunlight in two sentences.
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

종료: MAX_NEW → MAX_NEW

## open_013

질문: Hello. Please introduce yourself briefly.

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    Hello, and I am so grateful for your assistance.
    
    Thank you for your assistance.
    
    Thank you for your assistance.
    
    Thank you for your assistance.
    
    Thank you for your assistance.
    
    Thank you for your assistance.
    
    Thank you for your assistance.
    
    Thank you for your assistance.
    
    Thank you for your assistance.
    
    Thank you for your assistance.
    
    Thank you for your assistance.
    
    Thank

수리 답:

    Hello, and I am so grateful for your assistance.
    
    Thank you for your assistance.
    
    Thank you for your assistance.
    
    Thank you for your assistance.
    
    Thank you for your assistance.
    
    Thank you for your assistance.
    
    Thank you for your assistance.
    
    Thank you for your assistance.
    
    Thank you for your assistance.
    
    Thank you for your assistance.
    
    Thank you for your assistance.
    
    Thank

종료: MAX_NEW → MAX_NEW

## open_014

질문: I changed the number from 3 to 4. What is 2 plus the new number?

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    2 plus the new number.

수리 답:

    2 plus the new number.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## open_015

질문: Write the word blue exactly three times, separated by spaces.

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    The word blue is a combination of the two words.

수리 답:

    The word blue is a combination of the two.
    
    The word blue is a combination of the two.
    
    The word blue is a combination of the two.
    
    The word blue is a combination of the two.
    
    The word blue is a combination of the two.
    
    The word blue is a combination of the two.
    
    The word blue is a combination of the two.
    
    The word blue is a combination of the two.
    

종료: STOP_SEQUENCE → MAX_NEW

