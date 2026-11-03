# expanded_train:340343 원형 보류

실제 표/이벤트 목록을 예고하지만 없는 표와, 평탄화된 실행 예제 및 그 직접 결과 설명을 원형으로 보존한다.

```text
The following table describes the events that cause a Delete, Insert, or Update trigger to occur.
The following example creates an Update trigger which prevents values greater than 50 from being entered in the maxordamt field in the customer table. An error message is generated when the first REPLACE command is executed because the value for the maxordamt field is greater than 50. The second REPLACE command does not generate an error because the value for the maxordamt field is less than or equal to 50.
CLOSE DATABASES OPEN DATABASE (HOME(2) + 'data\testdata') USE customer && Open customer table * Set trigger on maxordamt field to fail with values <= 50 CREATE TRIGGER ON customer FOR UPDATE AS maxordamt <= 50 ON ERROR && Restore the system error handler WAIT WINDOW "Press a key to test trigger with value of 60"+CHR(13); +"When you get the error message, press Ignore." REPLACE maxordamt WITH 60 && Displays an error message ? maxordamt WAIT WINDOW "Press a key to test with value of 50." REPLACE maxordamt WITH 50 && Value is accepted ? maxordamt DELETE TRIGGER ON customer FOR UPDATE && Remove the trigger
```

## 근거

CREATE TRIGGER의 FOR DELETE | INSERT | UPDATE, AS lExpression, lExpression의 Boolean 참/거짓 조건, SET SAFETY/ON ERROR, AERROR()·TABLEUPDATE()와 명명 필드 관계를 보존했다. 표가 존재하지 않으므로 이벤트 표를 예고하는 한 문장만 분리했다. 마지막 예제는 실제 전체 프로그램이 한 줄로 평탄화되어 있고, 값 60/50을 넣은 특정 실행/오류 관측을 함께 주장한다. 이 예제와 그 결과 설명만 묶어 원형 보류했으며 줄바꿈이나 실행 흐름을 재구성하지 않았다. 수치와 주장은 sidecar 원형에 남겼다.
