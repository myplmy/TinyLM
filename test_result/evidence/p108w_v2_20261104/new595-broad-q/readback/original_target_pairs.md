# P108 원본과 동결 수리의 실제 질문·답

새 규칙형 test128과 별도 일상16의 전체 대응 원답이다. 공식 벤치마크가 아니며 정답표는 test 선택에 사용하지 않았다.

## test_arithmetic_000

질문: 12+12의 값만 쓰세요.

기대답: 24

원본 답:

    13

수리 답:

    13

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_001

질문: What is 13+12? Write only the number.

기대답: 25

원본 답:

    13

수리 답:

    13+12

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_002

질문: 14+12의 값만 쓰세요.

기대답: 26

원본 답:

    15

수리 답:

    15

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_003

질문: What is 15+12? Write only the number.

기대답: 27

원본 답:

    15

수리 답:

    15+12

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_004

질문: 16+12의 값만 쓰세요.

기대답: 28

원본 답:

    13

수리 답:

    13

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

    10

수리 답:

    10

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_007

질문: What is 19+12? Write only the number.

기대답: 31

원본 답:

    20

수리 답:

    20

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_008

질문: 1+13의 값만 쓰세요.

기대답: 14

원본 답:

    13

수리 답:

    13

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

    14

수리 답:

    14

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_011

질문: What is 4+13? Write only the number.

기대답: 17

원본 답:

    13

수리 답:

    13

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_012

질문: 5+13의 값만 쓰세요.

기대답: 18

원본 답:

    13

수리 답:

    13

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_013

질문: What is 6+13? Write only the number.

기대답: 19

원본 답:

    13

수리 답:

    13

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_014

질문: 7+13의 값만 쓰세요.

기대답: 20

원본 답:

    13

수리 답:

    13

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_arithmetic_015

질문: What is 8+13? Write only the number.

기대답: 21

원본 답:

    8+13 is the number of the 8+13 pairs. It is the number of the pairs that are in the 8+13 pairs.
    8+13 is the number of the pairs that are in the 8+13 pairs. It is the number of the pairs that are in the 8+13 pairs.
    8+13 is the number of pairs that are in the 8+13 pairs. It is the number of pairs that are in the 8+13 pairs

수리 답:

    8+13 is the number of the 8+13 pairs. It is the number of the pairs that are in the number of the pairs that are in the number of the pairs that are in the number of the pairs that are in the number of the pairs that are in the number of the pairs that are in the number of the pairs that are in the number of the pairs that are in the number of the pairs that are in the number of the pairs that are in the

종료: MAX_NEW → MAX_NEW

## test_entity_000

질문: A201는 사과이고 B201는 당근입니다. B201는 무엇입니까? 단어만 쓰세요.

기대답: 당근

원본 답:

    B201

수리 답:

    B201

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_entity_001

질문: A202 is an apple and B202 is a carrot. What is B202? Write only the noun.

기대답: carrot

원본 답:

    B202

수리 답:

    B202

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_entity_002

질문: A203는 사과이고 B203는 당근입니다. B203는 무엇입니까? 단어만 쓰세요.

기대답: 당근

원본 답:

    B203

수리 답:

    B203

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_entity_003

질문: A204 is an apple and B204 is a carrot. What is B204? Write only the noun.

기대답: carrot

원본 답:

    B204 is a carrot. What is B204? Write only the noun. B204 is a carrot. What is B204?

수리 답:

    B204 is a carrot. What is B204? Write only the noun. B204 is a carrot. What is B204?

종료: STOP_SEQUENCE → STOP_SEQUENCE

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

    B206

수리 답:

    B206

종료: STOP_SEQUENCE → STOP_SEQUENCE

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

    B208 is a carrot. What is B208? Write only the noun. B208 is a carrot. What is B208?

수리 답:

    B208 is a carrot. What is B208? Write only the noun. B208 is a carrot. What is B208?

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_entity_008

질문: A209는 사과이고 B209는 당근입니다. B209는 무엇입니까? 단어만 쓰세요.

기대답: 당근

원본 답:

    B209

수리 답:

    B209

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_entity_009

질문: A210 is an apple and B210 is a carrot. What is B210? Write only the noun.

기대답: carrot

원본 답:

    B210

수리 답:

    B210

종료: STOP_SEQUENCE → STOP_SEQUENCE

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

    B212 is a carrot. What is B212? It is a carrot. What is B212? It is a carrot. What is B212? It is a carrot. What is B212? It is a carrot. What is B212? It is a carrot. What is B212? It is a carrot. What is B212? It is a carrot. What is B2

수리 답:

    B212 is a carrot. What is B212? It is a carrot. What is B212? It is a carrot. What is B212? It is a carrot. What is B212? It is a carrot. What is B212? It is a carrot. What is B212? It is a carrot. What is B212? It is a carrot. What is B2

종료: MAX_NEW → MAX_NEW

## test_entity_012

질문: A213는 사과이고 B213는 당근입니다. B213는 무엇입니까? 단어만 쓰세요.

기대답: 당근

원본 답:

    B213

수리 답:

    B213

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_entity_013

질문: A214 is an apple and B214 is a carrot. What is B214? Write only the noun.

기대답: carrot

원본 답:

    B214 is a carrot. What is B214? It is a carrot. What is B214? It is a carrot. What is B214? It is a carrot. What is B214? It is a carrot. What is B214? It is a carrot. What is B214? It is a carrot. What is B214? It is a carrot. What is B21

수리 답:

    B214 is a carrot. What is B214? It is a carrot. What is B214? It is a carrot. What is B214? It is a carrot. What is B214? It is a carrot. What is B214? It is a carrot. What is B214? It is a carrot. What is B214? It is a carrot. What is B21

종료: MAX_NEW → MAX_NEW

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

    B216

수리 답:

    B216

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_000

질문: 민수201는 운전하고 영희201는 요리합니다. 누가 요리합니까? 이름만 쓰세요.

기대답: 영희201

원본 답:

    민수201

수리 답:

    민수201

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_001

질문: Alice202 drives and Bob202 cooks. Who cooks? Write only the name.

기대답: Bob202

원본 답:

    Alice202

수리 답:

    Alice202

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_002

질문: 민수203는 운전하고 영희203는 요리합니다. 누가 요리합니까? 이름만 쓰세요.

기대답: 영희203

원본 답:

    민수203

수리 답:

    민수204

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_003

질문: Alice204 drives and Bob204 cooks. Who cooks? Write only the name.

기대답: Bob204

원본 답:

    Alice204

수리 답:

    Alice204 drives and Bob204 cooks.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_004

질문: 민수205는 운전하고 영희205는 요리합니다. 누가 요리합니까? 이름만 쓰세요.

기대답: 영희205

원본 답:

    민수205

수리 답:

    민수205

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_005

질문: Alice206 drives and Bob206 cooks. Who cooks? Write only the name.

기대답: Bob206

원본 답:

    Alice206

수리 답:

    Alice206

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_006

질문: 민수207는 운전하고 영희207는 요리합니다. 누가 요리합니까? 이름만 쓰세요.

기대답: 영희207

원본 답:

    민수207

수리 답:

    민수207

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_007

질문: Alice208 drives and Bob208 cooks. Who cooks? Write only the name.

기대답: Bob208

원본 답:

    Alice208

수리 답:

    Alice208

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_008

질문: 민수209는 운전하고 영희209는 요리합니다. 누가 요리합니까? 이름만 쓰세요.

기대답: 영희209

원본 답:

    민수209

수리 답:

    민수209

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_role_009

질문: Alice210 drives and Bob210 cooks. Who cooks? Write only the name.

기대답: Bob210

원본 답:

    Alice210

수리 답:

    Alice210

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

    Alice212

수리 답:

    Alice212

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

    Alice214

수리 답:

    Alice214 drives and Bob214 cooks.

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

    Alice216

수리 답:

    Alice216

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_000

질문: A201=참, B201=거짓입니다. A201 AND B201는? 참 또는 거짓만 쓰세요.

기대답: 거짓

원본 답:

    참

수리 답:

    참

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_001

질문: A202=true, B202=true. What is A202 AND B202? Write true or false.

기대답: true

원본 답:

    true

수리 답:

    true

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_002

질문: A203=참, B203=참입니다. A203 AND B203는? 참 또는 거짓만 쓰세요.

기대답: 참

원본 답:

    B203

수리 답:

    B203

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_003

질문: A204=true, B204=false. What is A204 AND B204? Write true or false.

기대답: false

원본 답:

    false

수리 답:

    false

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_004

질문: A205=참, B205=참입니다. A205 AND B205는? 참 또는 거짓만 쓰세요.

기대답: 참

원본 답:

    B205

수리 답:

    B205

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_005

질문: A206=true, B206=true. What is A206 AND B206? Write true or false.

기대답: true

원본 답:

    true

수리 답:

    true

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_006

질문: A207=참, B207=거짓입니다. A207 AND B207는? 참 또는 거짓만 쓰세요.

기대답: 거짓

원본 답:

    거짓

수리 답:

    거짓

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_007

질문: A208=true, B208=true. What is A208 AND B208? Write true or false.

기대답: true

원본 답:

    true

수리 답:

    true

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_008

질문: A209=참, B209=참입니다. A209 AND B209는? 참 또는 거짓만 쓰세요.

기대답: 참

원본 답:

    B209

수리 답:

    B209

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_009

질문: A210=true, B210=false. What is A210 AND B210? Write true or false.

기대답: false

원본 답:

    false

수리 답:

    false

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

    true

수리 답:

    true

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_012

질문: A213=참, B213=거짓입니다. A213 AND B213는? 참 또는 거짓만 쓰세요.

기대답: 거짓

원본 답:

    거짓

수리 답:

    거짓

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_boolean_013

질문: A214=true, B214=true. What is A214 AND B214? Write true or false.

기대답: true

원본 답:

    true

수리 답:

    true

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

    false

수리 답:

    false

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_000

질문: 사과가 12개 있습니다. 12개를 더 받았습니다. 지금 개수만 쓰세요.

기대답: 24

원본 답:

    13개

수리 답:

    13개

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_001

질문: There are 13 apples. You receive 12 more. Write only the new count.

기대답: 25

원본 답:

    12

수리 답:

    12

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_002

질문: 사과가 14개 있습니다. 12개를 더 받았습니다. 지금 개수만 쓰세요.

기대답: 26

원본 답:

    14개

수리 답:

    14개

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_003

질문: There are 15 apples. You receive 12 more. Write only the new count.

기대답: 27

원본 답:

    12

수리 답:

    12

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

    12

수리 답:

    12

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_006

질문: 사과가 18개 있습니다. 12개를 더 받았습니다. 지금 개수만 쓰세요.

기대답: 30

원본 답:

    18개

수리 답:

    18개

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_007

질문: There are 19 apples. You receive 12 more. Write only the new count.

기대답: 31

원본 답:

    12

수리 답:

    12

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_008

질문: 사과가 1개 있습니다. 13개를 더 받았습니다. 지금 개수만 쓰세요.

기대답: 14

원본 답:

    13개

수리 답:

    13개

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

    3개 있습니다. 14개

수리 답:

    3개 있습니다. 14개

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_011

질문: There are 4 apples. You receive 13 more. Write only the new count.

기대답: 17

원본 답:

    13

수리 답:

    13

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_012

질문: 사과가 5개 있습니다. 13개를 더 받았습니다. 지금 개수만 쓰세요.

기대답: 18

원본 답:

    5개

수리 답:

    5개

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_013

질문: There are 6 apples. You receive 13 more. Write only the new count.

기대답: 19

원본 답:

    13

수리 답:

    13

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_014

질문: 사과가 7개 있습니다. 13개를 더 받았습니다. 지금 개수만 쓰세요.

기대답: 20

원본 답:

    7개

수리 답:

    7개

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_update_015

질문: There are 8 apples. You receive 13 more. Write only the new count.

기대답: 21

원본 답:

    13

수리 답:

    13

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_copy_000

질문: 다음 문자열을 그대로 복사하세요: key-201-value

기대답: key-201-value

원본 답:

    {"answer": "key"}}
    }
    
    {"key": "key"}}
    }
    
    {"key": "key"}}
    }
    {"key": "key"}}
    }
    {"key": "key"}}
    }
    {"key": "key"}}
    }
    {"key": "key"}}
    }
    {"

수리 답:

    {"answer": "key"}}
    {"key": "key"}
    {"key": "key"}
    {"key": "key"}
    {"key": "key"}
    {"key": "key"}
    {"key": "key"}
    {"key": "key"}
    {"key": "key"}
    {"key"

종료: MAX_NEW → MAX_NEW

## test_copy_001

질문: Copy exactly this string: key-202-value

기대답: key-202-value

원본 답:

    The key-202-value indicator is a string that is not used in a string, but is used to indicate the value of the string. The key-202-value indicator is a string that is not used in a string, and is used to indicate the value of the string. The key-202-value indicator is a string that is not used in a string, and is used to indicate the value of the string. The key-202-

수리 답:

    The key-202-value indicator is a string that is not a string that is not a key-end. The key-end is a string that is not a key-end, and the key-end is a string that is not a key-end. The key-end is a string that is not a key-end, and the key-end is a string that is not a key-end. The key-end is a string that is not

종료: MAX_NEW → MAX_NEW

## test_copy_002

질문: 다음 문자열을 그대로 복사하세요: key-203-value

기대답: key-203-value

원본 답:

    {"answer": "key"}

수리 답:

    {"answer": "key"}

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_copy_003

질문: Copy exactly this string: key-204-value

기대답: key-204-value

원본 답:

    The key-204-value indicator is a string that is not used in a string. The key-204-value indicator is a string that is not used in a string. The key-204-value indicator is a string that is not used in a string. The key-204-value indicator is a string that is not used in a string. The key-204-value indicator is a string that is not used in a string. The

수리 답:

    The key-204-value indicator is a string that is not a string that is not a key-204-value indicator. The key-204-value indicator is a string that is not a key-204-value indicator. The key-204-value indicator is a string that is not a key-204-value indicator. The key-204-value indicator is a string that is not a key-204-value indicator

종료: MAX_NEW → MAX_NEW

## test_copy_004

질문: 다음 문자열을 그대로 복사하세요: key-205-value

기대답: key-205-value

원본 답:

    {"answer": "key"}

수리 답:

    {"answer": "key"}

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_copy_005

질문: Copy exactly this string: key-206-value

기대답: key-206-value

원본 답:

    keyboarding()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()()

수리 답:

    The key-206-value indicator is a string that is not used in a string. The key-206-value indicator is a string that is not used in a string. The key-206-value indicator is a string that is not used in a string. The key-206-value indicator is a string that is not used in a string. The key-206-value indicator is a string that is not used in a string. The

종료: MAX_NEW → MAX_NEW

## test_copy_006

질문: 다음 문자열을 그대로 복사하세요: key-207-value

기대답: key-207-value

원본 답:

    {"answer": "key"}}
    }
    
    {"key": "key"}}
    }
    
    {"key": "key"}}
    }
    {"key": "key"}}
    }
    {"key": "key"}}
    }
    {"key": "key"}}
    }
    {"key": "key"}}
    }
    {"

수리 답:

    {"answer": "key"}}
    }
    
    {"key": "key"}}
    }
    
    {"key": "key"}}
    }
    {"key": "key"}}
    }
    {"key": "key"}}
    }
    {"key": "key"}}
    }
    {"key": "key"}}
    }
    {"

종료: MAX_NEW → MAX_NEW

## test_copy_007

질문: Copy exactly this string: key-208-value

기대답: key-208-value

원본 답:

    The key-208-value is a string that is used to create a string that is not used by a string. The key-208-value is a string that is used to create a string that is not used by a string. The key-208-value is a string that is used to create a string that is not used by a string. The key-208-value is a string that is used to create a string that is not used

수리 답:

    The key-208-value is a string that is not used in a string, but is used to create a string that is not used in a string. The key-208-value is a string that is not used in a string that is not used in a string that is not used in a string that is not used in a string that is not used in a string that is not used in a string that is not used in a string that is not used

종료: MAX_NEW → MAX_NEW

## test_copy_008

질문: 다음 문자열을 그대로 복사하세요: key-209-value

기대답: key-209-value

원본 답:

    {"answer": "key"}}
    }
    
    {"key": "key"}}
    }
    
    {"key": "key"}}
    }
    {"key": "key"}}
    }
    {"key": "key"}}
    }
    {"key": "key"}}
    }
    {"key": "key"}}
    }
    {"

수리 답:

    {"answer": "key"}

종료: MAX_NEW → STOP_SEQUENCE

## test_copy_009

질문: Copy exactly this string: key-210-value

기대답: key-210-value

원본 답:

    The key-210-value indicator is a string that is not a string that is not a key-210-value indicator. The key-210-value indicator is a string that is not a key-210-value indicator. The key-210-value indicator is a string that is not a key-210-value indicator. The key-210-value indicator is a string that is not a key-210-value indicator

수리 답:

    The key-210-value indicator is a string that is not a string that is not a key-210-value indicator. The key-210-value indicator is a string that is not a key-210-value indicator. The key-210-value indicator is a string that is not a key-210-value indicator. The key-210-value indicator is a string that is not a key-210-value indicator

종료: MAX_NEW → MAX_NEW

## test_copy_010

질문: 다음 문자열을 그대로 복사하세요: key-211-value

기대답: key-211-value

원본 답:

    {"answer": "key"}

수리 답:

    {"answer": "key"}

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_copy_011

질문: Copy exactly this string: key-212-value

기대답: key-212-value

원본 답:

    The key-212-value indicator is a string that is not used in a string. The key-212-value indicator is used to indicate the string that is not used in a string. The key-212-value indicator is used to indicate the string that is not used in a string. The key-212-value indicator is used to indicate the string that is not used in a string. The key-212-value indicator is used to

수리 답:

    The key-212-value indicator is a string that is not used in a string. The key-212-value indicator is a string that is not used in a string. The key-212-value indicator is a string that is not used in a string. The key-212-value indicator is a string that is not used in a string. The key-212-value indicator is a string that is not used in a string. The

종료: MAX_NEW → MAX_NEW

## test_copy_012

질문: 다음 문자열을 그대로 복사하세요: key-213-value

기대답: key-213-value

원본 답:

    {"answer": "key"}

수리 답:

    {"answer": "key"}}
    }
    
    {"key": "key"}}
    }
    
    {"key": "key"}}
    }
    {"key": "key"}}
    }
    {"key": "key"}}
    }
    {"key": "key"}}
    }
    {"key": "key"}}
    }
    {"

종료: STOP_SEQUENCE → MAX_NEW

## test_copy_013

질문: Copy exactly this string: key-214-value

기대답: key-214-value

원본 답:

    The key-214-value indicator is a string that is not used in a string that is not used in a string that is not used in a string that is not used in a string that is not used in a string that is not used in a string that is not used in a string that is not used in a string that is not used in a string that is not used in a string that is not used in a string that is not used in a string that

수리 답:

    The key-214-value indicator is a string that is not used in a string. The key-214-value indicator is a string that is not used in a string. The key-214-value indicator is a string that is not used in a string. The key-214-value indicator is a string that is not used in a string. The key-214-value indicator is a string that is not used in a string. The

종료: MAX_NEW → MAX_NEW

## test_copy_014

질문: 다음 문자열을 그대로 복사하세요: key-215-value

기대답: key-215-value

원본 답:

    {"answer": "key"}

수리 답:

    {"answer": "key"}

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_copy_015

질문: Copy exactly this string: key-216-value

기대답: key-216-value

원본 답:

    The key-216-value indicator is a string that is not used in a string with a key of value of 0.5. The key-216-value indicator is a string that is not used in a string with a key of value of 0.5. The key-216-value indicator is a string that is not used in a string with a key of value of 0.5. The key-216-value indicator is a string that

수리 답:

    The string is a string that is used to create a new string, and the string is a string that is used to create a new string. The string is a string that is used to create a new string, and the string is a string that is used to create a new string. The string is a string that is used to create a new string, and the string is a string that is used to create a new string. The string is a string that is used to

종료: MAX_NEW → MAX_NEW

## test_repeat_000

질문: 201을 공백으로 구분해 정확히 세 번 쓰세요.

기대답: 201 201 201

원본 답:

    
    1. 
    1. 
    2. 
    3. 
    4. 
    5. 
    6. 
    7. 
    8. 
    9. 
    10. 
    11. 
    12. 
    13. 
    15. 
    16. 
    17. 
    18. 
    19. 
    20. 
    20. 
    21. 
    22. 
    22. 

수리 답:

    
    1. 
    1. 
    1. 
    1. 
    1. 
    1. 
    1. 
    1. 
    1. 
    1. 
    1. 
    1. 
    1. 
    1. 
    1. 
    1. 
    1. 
    1. 
    1. 
    1. 
    1. 
    1. 
    1. 
    1. 

종료: MAX_NEW → MAX_NEW

## test_repeat_001

질문: Write 202 exactly three times, separated by spaces.

기대답: 202 202 202

원본 답:

    The first is the space between two spaces. The space between two spaces is called the space between two spaces. The space between two spaces is called the space between spaces between two spaces. The space between spaces between two spaces is called the space between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces

수리 답:

    The first is the space between two spaces. The space between two spaces is called the space between two spaces. The space between two spaces is called the space between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between

종료: MAX_NEW → MAX_NEW

## test_repeat_002

질문: 203을 공백으로 구분해 정확히 세 번 쓰세요.

기대답: 203 203 203

원본 답:

    
    214 
    
    226 
    
    227 
    
    229 
    
    2210 
    
    2211 
    
    2212 
    
    2213 
    
    2214 
    
    2215 
    
    2216 
    
    2217 
    
    2219 
    
    2219 
    
    2220 
    
    2221 
    
    2221 
    
    2222 
    
    2222 
    

수리 답:

    
    204

종료: MAX_NEW → STOP_SEQUENCE

## test_repeat_003

질문: Write 204 exactly three times, separated by spaces.

기대답: 204 204 204

원본 답:

    The first time you have a problem with a space, the space is called a space. The space is called a space, and the space is called a space. The space is called a space. The space is called a space. The space is called a space. The space is called a space. The space is called a space. The space is called a space. The space is called a space. The space is called a space. The space is called a space.

수리 답:

    The first is the space between two spaces. The space between two spaces is called the space between two spaces. The space between two spaces is called the space between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between

종료: MAX_NEW → MAX_NEW

## test_repeat_004

질문: 205을 공백으로 구분해 정확히 세 번 쓰세요.

기대답: 205 205 205

원본 답:

    
    206

수리 답:

    
    207

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_repeat_005

질문: Write 206 exactly three times, separated by spaces.

기대답: 206 206 206

원본 답:

    The first is the space between two spaces. The space between two spaces is called the space between two spaces. The space between two spaces is called the space between spaces between two spaces. The space between spaces between two spaces is called the space between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces

수리 답:

    The first is the space between two spaces. The space between two spaces is called the space between two spaces. The space between two spaces is called the space between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between

종료: MAX_NEW → MAX_NEW

## test_repeat_006

질문: 207을 공백으로 구분해 정확히 세 번 쓰세요.

기대답: 207 207 207

원본 답:

    
    214 
    
    226 
    
    229 
    
    2211 
    
    2212 
    
    2213 
    
    2214 
    
    2216 
    
    2217 
    
    2219 
    
    2219 
    
    2220 
    
    2221 
    
    2221 
    
    2222 
    
    2222 
    
    2222 
    
    2222 
    
    2222 
    

수리 답:

    
    214 
    
    226 
    
    227 
    
    229 
    
    2211 
    
    2212 
    
    2213 
    
    2214 
    
    2215 
    
    2216 
    
    2217 
    
    2219 
    
    2219 
    
    2220 
    
    2221 
    
    2221 
    
    2222 
    
    2222 
    
    2222 
    

종료: MAX_NEW → MAX_NEW

## test_repeat_007

질문: Write 208 exactly three times, separated by spaces.

기대답: 208 208 208

원본 답:

    The first is the space between two spaces. The space between two spaces is called the space between two spaces. The space between two spaces is called the space between spaces between two spaces. The space between spaces between two spaces is called the space between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces

수리 답:

    The first is the space between two spaces. The space between two spaces is called the space between two spaces. The space between two spaces is called the space between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between spaces between

종료: MAX_NEW → MAX_NEW

## test_repeat_008

질문: 209을 공백으로 구분해 정확히 세 번 쓰세요.

기대답: 209 209 209

원본 답:

    
    209 
    
    2차 분할
    2차 분할
    2차 분할
    3차 분할
    4차 분할
    5차 분할
    6차 분할
    7차 분할
    8차 분할
    9차 분할
    10차 분할
    11차 분할
    13차 분할
    14차 분할
    16차 분할
    17차 분할
    18차 분할
    19차 분할
    20차 분할
    21차 분할
    22차 분할
    22차 분할
    22차 분할

수리 답:

    
    209 
    
    2차 분할
    2차 분할
    2차 분할
    3차 분할
    4차 분할
    5차 분할
    6차 분할
    7차 분할
    8차 분할
    9차 분할
    10차 분할
    11차 분할
    12차 분할
    13차 분할
    14차 분할
    16차 분할
    17차 분할
    18차 분할
    19차 분할
    20차 분할
    21차 분할
    22차 분할
    22차 분할

종료: MAX_NEW → MAX_NEW

## test_repeat_009

질문: Write 210 exactly three times, separated by spaces.

기대답: 210 210 210

원본 답:

    double spaces are separated by spaces.
    
    The spaces are separated by spaces.
    
    The spaces are separated by spaces.
    
    The spaces are separated by spaces.
    
    The spaces are separated by spaces.
    
    The spaces are separated by spaces.
    
    The spaces are separated by spaces.
    
    The spaces are separated by spaces.
    
    The spaces are separated by spaces.
    
    The spaces are separated by spaces.
    
    The spaces are separated

수리 답:

    distant between spaces.
    
    The spaces are separated by spaces.
    
    The spaces are separated by spaces.
    
    The spaces are separated by spaces.
    
    The spaces are separated by spaces.
    
    The spaces are separated by spaces.
    
    The spaces are separated by spaces.
    
    The spaces are separated by spaces.
    
    The spaces are separated by spaces.
    
    The spaces are separated by spaces.
    
    The spaces are separated by spaces.

종료: MAX_NEW → MAX_NEW

## test_repeat_010

질문: 211을 공백으로 구분해 정확히 세 번 쓰세요.

기대답: 211 211 211

원본 답:

    
    같이 보기 
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2

수리 답:

    
    같이 보기 
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2

종료: MAX_NEW → MAX_NEW

## test_repeat_011

질문: Write 212 exactly three times, separated by spaces.

기대답: 212 212 212

원본 답:

    double spaces are separated by spaces.
    
    Here's a simple example:
    
    1. The space between two spaces is separated by spaces.
    2. The space between two spaces is separated by spaces.
    3. The space between two spaces is separated by spaces.
    4. The space between two spaces is separated by spaces.
    5. The space between two spaces is separated by spaces.
    6. The space between two spaces is separated by spaces.

수리 답:

    double spaces are separated by spaces.
    
    Here's a simple example:
    
    1. The space is separated by spaces.
    2. The spaces are separated by spaces.
    3. The spaces are separated by spaces.
    4. The spaces are separated by spaces.
    5. The spaces are separated by spaces.
    6. The spaces are separated by spaces.
    7. The spaces are separated by spaces.
    9. The spaces are separated by

종료: MAX_NEW → MAX_NEW

## test_repeat_012

질문: 213을 공백으로 구분해 정확히 세 번 쓰세요.

기대답: 213 213 213

원본 답:

    
    같이 보기 
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2

수리 답:

    
    같이 보기 
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2차 세계 대전 기간 동안 전쟁 범죄
     제2

종료: MAX_NEW → MAX_NEW

## test_repeat_013

질문: Write 214 exactly three times, separated by spaces.

기대답: 214 214 214

원본 답:

    double spaces are separated by spaces.
    
    The first two times, separated by spaces, are separated by spaces.
    
    The second times, separated by spaces, are separated by spaces.
    
    The second times, separated by spaces, are separated by spaces.
    
    The third times, separated by spaces, are separated by spaces.
    
    The third times, separated by spaces, are separated by spaces.
    
    The third times, separated by spaces, are

수리 답:

    double spaces are separated by spaces.
    
    The first two times, separated by spaces, are separated by spaces.
    
    The second times, separated by spaces, are separated by spaces.
    
    The second times, separated by spaces, are separated by spaces.
    
    The third times, separated by spaces, are separated by spaces.
    
    The third times, separated by spaces, are separated by spaces.
    
    The third times, separated by spaces, are

종료: MAX_NEW → MAX_NEW

## test_repeat_014

질문: 215을 공백으로 구분해 정확히 세 번 쓰세요.

기대답: 215 215 215

원본 답:

    
    315 
    
    315 
    
    415 
    
    515 
    
    615 
    
    715 
    
    715 
    
    815 
    
    915 
    
    1015 
    
    1115 
    
    1215 
    
    1315 
    
    1415 
    
    1515 
    
    1515 
    
    1615 
    
    1715 
    
    1715 
    
    1815 
    
    19pine 
    
    20pine 
    
    20pine 
    
    21pine 

수리 답:

    
    같이 보기 
    
    외부 링크 
    
    대한민국 제17대 국회의원 선거
    대한민국 제18대 국회의원 선거
    대한민국 제19 대통령 선거
    대한민국 제20 대통령 선거
    대한민국 제21 대통령 선거
    대한민국 제22 대통령 선거
    대한민국 제23 대통령 선거
    대한민국 제24 대통령 선거
    대한민국 제25 대통령 선거
    대한민국 제26 대통령 선거
    대한민국 제27 대통령 선거
    대한민국 제28 대통령 선거
    대한민국 제30 대통령 선거
    대한민국 제32 대통령 선거
    대한민국

종료: MAX_NEW → MAX_NEW

## test_repeat_015

질문: Write 216 exactly three times, separated by spaces.

기대답: 216 216 216

원본 답:

    double spaces are separated by spaces.
    
    1. The spaces are separated by spaces.
    2. The spaces are separated by spaces.
    3. The spaces are separated by spaces.
    4. The spaces are separated by spaces.
    5. The spaces are separated by spaces.
    6. The spaces are separated by spaces.
    7. The spaces are separated by spaces.
    9. The spaces are separated by spaces.
    10. The spaces are

수리 답:

    double spaces are separated by spaces.
    
    1. spaces are separated by spaces.
    2. spaces are separated by spaces.
    3. spaces are separated by spaces.
    4. spaces are separated by spaces.
    5. spaces are separated by spaces.
    6. spaces are separated by spaces.
    7. spaces are separated by spaces.
    8. spaces are separated by spaces.
    9. spaces are separated by spaces.
    10. spaces are

종료: MAX_NEW → MAX_NEW

## test_format_000

질문: 12+12의 값을 문자열로 answer 항목 하나인 JSON으로 쓰세요.

기대답: {"answer":"24"}

원본 답:

    JSON

수리 답:

    JSON

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_format_001

질문: Write 13+12 as JSON with only the key answer and a string value.

기대답: {"answer":"25"}

원본 답:

    The key answer is:
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the

수리 답:

    The key answer is a string value that is not the key answer. The key answer is a string that is not the key answer. The key answer is a string that is not the key answer. The key answer is a string that is not the key answer. The key answer is a string that is not the key answer. The key answer is a string that is not the key answer. The key answer is a string that is not the key answer. The key answer is

종료: MAX_NEW → MAX_NEW

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

    The key answer is a string value that is not the key answer. The key answer is a string that is not the key answer. The key answer is a string that is not the key answer. The key answer is a string that is not the key answer. The key answer is a string that is not the key answer. The key answer is a string that is not the key answer. The key answer is a string that is not the key answer. The key answer is

수리 답:

    The key answer is a string value that is not the key answer. The key answer is a string that is not the key answer. The key answer is a string that is not the key answer. The key answer is a string that is not the key answer. The key answer is a string that is not the key answer. The key answer is a string that is not the key answer. The key answer is a string that is not the key answer. The key answer is

종료: MAX_NEW → MAX_NEW

## test_format_004

질문: 16+12의 값을 문자열로 answer 항목 하나인 JSON으로 쓰세요.

기대답: {"answer":"28"}

원본 답:

    JSON

수리 답:

    JSON

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_format_005

질문: Write 17+12 as JSON with only the key answer and a string value.

기대답: {"answer":"29"}

원본 답:

    JSON is a Java language that is used in the Java language for Java language development. JSON is a Java language that is used in the Java language for Java language development.
    
    JSON is a Java language that is used in the Java language for Java language development. JSON is a Java language that is used in the Java language for Java language development.
    
    JSON is a Java language that is used in the Java language for Java

수리 답:

    JSON is a Java language that is used by many languages, including Java, Java, and Java. It is used by many languages, including Java, Java, and Java.

종료: MAX_NEW → STOP_SEQUENCE

## test_format_006

질문: 18+12의 값을 문자열로 answer 항목 하나인 JSON으로 쓰세요.

기대답: {"answer":"30"}

원본 답:

    JSON

수리 답:

    JSON

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_format_007

질문: Write 19+12 as JSON with only the key answer and a string value.

기대답: {"answer":"31"}

원본 답:

    JSON is a Java language that is spoken by many languages. JSON is a Java language that is spoken by many languages. JSON is a Java language that is spoken by many languages.
    
    JSON is a Java language that is spoken by many languages. JSON is a Java language that is spoken by many languages. JSON is a Java language that is spoken by many languages.
    
    JSON is a Java language that

수리 답:

    JSON is a Java language that is spoken by many languages. JSON is a Java language that is spoken by many languages. JSON is a Java language that is spoken by many languages.
    
    JSON is a Java language that is spoken by many languages. JSON is a Java language that is spoken by many languages. JSON is a Java language that is spoken by many languages.
    
    JSON is a Java language that

종료: MAX_NEW → MAX_NEW

## test_format_008

질문: 1+13의 값을 문자열로 answer 항목 하나인 JSON으로 쓰세요.

기대답: {"answer":"14"}

원본 답:

    JSON

수리 답:

    JSON

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_format_009

질문: Write 2+13 as JSON with only the key answer and a string value.

기대답: {"answer":"15"}

원본 답:

    The key answer is:
    
    JSON is the JSON key answer.
    
    JSON is the JSON key answer.
    
    JSON is the JSON key answer.
    
    JSON is the JSON key answer.
    
    JSON is the JSON key answer.
    
    JSON is the JSON key answer.
    
    JSON is the JSON key answer.

수리 답:

    The key answer is:
    
    JSON is the JSON key answer.
    
    JSON is the JSON key answer.
    
    JSON is the JSON key answer.
    
    JSON is the JSON key answer.
    
    JSON is the JSON key answer.
    
    JSON is the JSON key answer.
    
    JSON is the JSON key answer.

종료: MAX_NEW → MAX_NEW

## test_format_010

질문: 3+13의 값을 문자열로 answer 항목 하나인 JSON으로 쓰세요.

기대답: {"answer":"16"}

원본 답:

    
    JSON은 다음과 같은 값을 문자열로 구분한다.
    
     JSON은 다음과 같은 값을 문자열로 구분한다.
     JSON은 다음과 같은 값을 문자열로 구분한다.
     JSON은 다음과 같은 값을 문자열로 구분한다.
     JSON은 다음과 같은 값을 문자열로 구분한다.
     JSON은 다음과 같은 값을 문자열로 구분한다.
     JSON은 다음과 같은 값을 문자열로 구분

수리 답:

    
    JSON은 다음과 같은 값을 문자열로 구분한다.
    
     JSON은 다음과 같은 값을 문자열로 구분한다.
     JSON은 다음과 같은 값을 문자열로 구분한다.
     JSON은 다음과 같은 값을 문자열로 구분한다.
     JSON은 다음과 같은 값을 문자열로 구분한다.
     JSON은 다음과 같은 값을 문자열로 구분한다.
     JSON은 다음과 같은 값을 문자열로 구분

종료: MAX_NEW → MAX_NEW

## test_format_011

질문: Write 4+13 as JSON with only the key answer and a string value.

기대답: {"answer":"17"}

원본 답:

    The key answer is:
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the

수리 답:

    The key answer is:
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the

종료: MAX_NEW → MAX_NEW

## test_format_012

질문: 5+13의 값을 문자열로 answer 항목 하나인 JSON으로 쓰세요.

기대답: {"answer":"18"}

원본 답:

    
    JSON은 다음과 같은 값을 문자열로 구분한다.
    
    JSON은 다음과 같은 값을 문자열로 구분한다.
    
    JSON은 다음과 같은 값을 문자열로 구분한다.
    
    JSON은 다음과 같은 값을 문자열로 구분한다.
    
    JSON은 다음과 같은 값을 문자열로 구분한다.
    
    JSON은 다음과 같은 값을 문자열로 구분한다.
    
    JSON은 다음과

수리 답:

    
    JSON은 다음과 같은 값을 문자열로 구분한다.
    
     JSON은 다음과 같은 값을 문자열로 구분한다.
     JSON은 다음과 같은 값을 문자열로 구분한다.
     JSON은 다음과 같은 값을 문자열로 구분한다.
     JSON은 다음과 같은 값을 문자열로 구분한다.
     JSON은 다음과 같은 값을 문자열로 구분한다.
     JSON은 다음과 같은 값을 문자열로 구분

종료: MAX_NEW → MAX_NEW

## test_format_013

질문: Write 6+13 as JSON with only the key answer and a string value.

기대답: {"answer":"19"}

원본 답:

    The key answer is:
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the

수리 답:

    The key answer is:
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the

종료: MAX_NEW → MAX_NEW

## test_format_014

질문: 7+13의 값을 문자열로 answer 항목 하나인 JSON으로 쓰세요.

기대답: {"answer":"20"}

원본 답:

    JSON

수리 답:

    JSON

종료: STOP_SEQUENCE → STOP_SEQUENCE

## test_format_015

질문: Write 8+13 as JSON with only the key answer and a string value.

기대답: {"answer":"21"}

원본 답:

    The key answer is:
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the JSON key.
    
    JSON is the

수리 답:

    The key answer is a string value that is not the key answer. The key answer is a string that is not the key answer. The key answer is a string that is not the key answer. The key answer is a string that is not the key answer. The key answer is a string that is not the key answer. The key answer is a string that is not the key answer. The key answer is a string that is not the key answer. The key answer is

종료: MAX_NEW → MAX_NEW

## open_000

질문: 1+1은?

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    2+1은?

수리 답:

    2+1은?

종료: STOP_SEQUENCE → STOP_SEQUENCE

## open_001

질문: 2+2는?

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    3는?

수리 답:

    3는.

종료: STOP_SEQUENCE → STOP_SEQUENCE

## open_002

질문: A는 사과고 B는 당근이다. B는 무엇인가? 답만 쓰세요.

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    B는 당근이다. B는 당근이다.
    
    같이 보기 
     당근
     당근
     당근
     당근
     당근
     당근
     당근
     당근
     당근
     당근
     당근
     당근
     당근
     당근
     당근
     당근
     당근
     당근
     당근
     당근
     당근
     당근
     당근
     당근
     당근
     당근
     당

수리 답:

    B는 사과고 B가 당근이다. B는 당근이다. B는 당근이다. B는 당근이다. B는 당근이다. B는 당근이다. B는 당근이다. B는 당근이다. B는 당근이다. B는 당근이다. B는 당근이다. B는 당근이다. B는 당근이다. B는 당근이다. B는 당근이다. B는

종료: MAX_NEW → MAX_NEW

## open_003

질문: 문맥: 민수는 사과 3개, 영희는 사과 5개를 가지고 있습니다. 영희의 사과는 몇 개입니까?

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:

수리 답:

    두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:두통:

종료: MAX_NEW → MAX_NEW

## open_004

질문: 사과에 대해 두 문장으로 알려줘.

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    
    이외에도 사과를 다르게 한 문장으로 알려줘.
    
    각주
    
    같이 보기 
     사과
     사과
     사과
     사과
     사과
     사과
     사과
     사과
     사과
     사과
     사과
     사과
     사과
     사과
     사과
     사과
     사과
     사과
     사과
     사과
     사과
     사과
     사과
     사과
     사과

수리 답:

    사과: 
    {"answer": """}
    }
    
    {""""}
    
    {"""}
    }
    
    {"""}
    }
    
    {"""}
    }
    
    {"""}
    }
    
    {"""}
    }
    
    {"""}
    }
    
    {"""}
    }
    
    {"""}

종료: MAX_NEW → MAX_NEW

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

    안녕하세요. 오늘 처음 대화합니다. 이 대화에서는 안녕하세요. 이 대화에서는 안녕하세요. 이 대화에서는 안녕하세요. 이 대화에서는 안녕하세요. 이 대화에서는 안녕하세요. 이 대화에서는 안녕하세요. 이 대화에서는 안녕하세요. 이 대화에서는 안녕하세요. 이 대화에서는 안녕하세요. 이 대화에서는 안녕하세요. 이 대화에서는 안녕하

수리 답:

    안녕하세요. 오늘 처음 대화합니다. 이 대화에서는 안녕하세요. 이 대화에서는 안녕하세요. 이 대화에서는 안녕하세요. 이 대화에서는 안녕하세요. 이 대화에서는 안녕하세요. 이 대화에서는 안녕하세요. 이 대화에서는 안녕하세요. 이 대화에서는 안녕하세요. 이 대화에서는 안녕하세요. 이 대화에서는 안녕하세요. 이 대화에서는 안녕하

종료: MAX_NEW → MAX_NEW

## open_007

질문: 어제 산 그 물건은 어디에 두면 좋을까요?

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    어제 산 그 물건은 어디에 두면 좋을까요?

수리 답:

    어제 산 그 물건은 어디에 두면 좋을까요?

종료: STOP_SEQUENCE → STOP_SEQUENCE

## open_008

질문: What is an apple? Answer in one sentence.

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    A apple is a fruit that is not a fruit that is not a fruit that is not a fruit that is not a fruit that is not a fruit that is not a fruit that is not a fruit that is not a fruit that is not a fruit that is not a fruit that is not a fruit that is not a fruit that is not a fruit that is not a fruit that is not a fruit that is not a fruit that is not a fruit that is not a fruit that

수리 답:

    The apple is a small, small, and dense fruit that can grow up to 2 feet tall. It is a fruit that can grow up to 2 feet tall. It is a small, dense fruit that can grow up to 2 feet tall. It is a fruit that can grow up to 2 feet tall. It is a fruit that can grow up to 2 feet tall. It is a fruit that can grow up to 2 feet tall. It is a fruit that can grow up

종료: MAX_NEW → MAX_NEW

## open_009

질문: What is basketball?

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    The basketball is a game that is played by a player in a basketball field. The basketball is played by a player in a basketball field, such as a basketball field, or by a player in a basketball field. The basketball is played by a player in a basketball field, such as a basketball field, or by a player in a basketball field. The basketball is played by a player in a basketball field, such as

수리 답:

    The basketball is a game that is played by a player who is not a basketball player. The basketball is a game that is played by a player who is not a basketball player. The basketball is a game that is played by a player who is not a basketball player. The basketball is a game that is played by a player who is not a basketball player. The basketball is a game that is played by a player who is not a

종료: MAX_NEW → MAX_NEW

## open_010

질문: Alice has three apples. Bob has five apples. How many apples does Bob have?

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    two apples

수리 답:

    two apples

종료: STOP_SEQUENCE → STOP_SEQUENCE

## open_011

질문: What is the capital of France?

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    The capital of France is Paris. It is the capital of France, and the capital of France is Paris. It is the capital of France, and the capital of France is Paris.

수리 답:

    The capital of France is Paris. It is the capital of France, and the capital of France is Paris. It is the capital of France, and the capital of France is Paris. It is the capital of France, and the capital of France is Paris. It is the capital of France, and the capital of France is Paris. It is the capital of France, and the capital of France is Paris. It is the capital of France, and the capital of France is Paris

종료: STOP_SEQUENCE → MAX_NEW

## open_012

질문: Explain why plants need sunlight in two sentences.

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    The answer to this question is, "wave" is the answer.
    "wave" is the answer to "wave" in the sentence.
    "wave" is the answer to "wave" in the sentence.
    "wave" is the answer to "wave" in the sentence.
    "wave" is the answer to "wave" in the sentence.
    "wave" is the answer to "wave"

수리 답:

    The answer is simple, but not simple. The answer is simple.
    
    1. Plants need sunlight to grow.
    2. Plants need sunlight to grow.
    3. Plants need sunlight to grow.
    4. Plants need sunlight to grow.
    5. Plants need sunlight to grow.
    6. Plants need sunlight to grow.
    7. Plants need sunlight to grow.
    8. Plants need sunlight to grow.
    9. Plants need sunlight to grow.

종료: MAX_NEW → MAX_NEW

## open_013

질문: Hello. Please introduce yourself briefly.

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    The first step in the journey to the world of science is to understand the nature of the universe. The universe is a complex complex, with many different types of objects, including stars, galaxies, and galaxies. The universe is a complex complex, with many different types of objects, including stars, galaxies, and galaxies. The universe is a complex complex, with many different types of objects, including stars, galaxies, and galaxies. The universe is a complex complex, with many different

수리 답:

    The first step in the journey to the world of science is to understand the nature of the universe. The universe is a complex system of laws, laws, and systems that govern the universe. The universe is a complex system of laws, laws, and systems that govern the universe. The universe is a complex system of laws, laws, and systems that govern the universe. The universe is a complex system of laws, laws, and systems that govern the universe. The universe is a

종료: MAX_NEW → MAX_NEW

## open_014

질문: I changed the number from 3 to 4. What is 2 plus the new number?

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    4 plus the new number

수리 답:

    4 plus the new number

종료: STOP_SEQUENCE → STOP_SEQUENCE

## open_015

질문: Write the word blue exactly three times, separated by spaces.

기대답: 자동 정답 미지정; 총괄 판독 대상

원본 답:

    The blue is three times, separated by spaces.
    The blue is three times, separated by spaces.
    The blue is three times, separated by spaces.
    The blue is three times, separated by spaces.
    The blue is three times, separated by spaces.
    The blue is three times, separated by spaces.
    The blue is three times, separated by spaces.
    The blue is three times, separated by spaces.
    The blue is three times, separated by

수리 답:

    The blue is three times, separated by spaces.
    The blue is three times, separated by spaces.
    The blue is three times, separated by spaces.
    The blue is three times, separated by spaces.
    The blue is three times, separated by spaces.
    The blue is three times, separated by spaces.
    The blue is three times, separated by spaces.
    The blue is three times, separated by spaces.
    The blue is three times, separated by

종료: MAX_NEW → MAX_NEW

