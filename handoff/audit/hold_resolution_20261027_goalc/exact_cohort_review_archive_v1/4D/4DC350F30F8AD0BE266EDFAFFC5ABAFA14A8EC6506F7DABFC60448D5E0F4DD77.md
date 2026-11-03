# 155499 원형 보류

`<ctype.h>`의 설명 뒤에 실제 함수 이름 셀이 없는 표 설명을 원형 보류했다. 없는 API명을 설명문/외부 지식으로 채우거나 각 설명에 임의 함수를 귀속하지 않았다.

```text
|Tests||In the form
Return a nonzero number for true and zero for false.
||test for alphanumeric character|
||test for alphabetic character|
||test for blank character (new in C99)|
||test for control character|
||test for digit. Not locale-specific.|
||test for graphic character, excluding the space character.|
||test for lowercase character|
||test for printable character, including the space character.|
||test for punctuation character|
||test for any whitespace character|
||test for uppercase character|
||test for hexadecimal digit. Not locale-specific.|
|Character conversion||in the form
Return the converted character unless it is not alphabetic.
||convert character to lowercase|
||convert character to uppercase|
The Single Unix Specification Version 3 adds functions similar to the above:
||test that the parameter is between 0 and 127|
||converts a character to ASCII|
```

두 일반 반환 설명은 표제의 실제 말만 재사용해 본문에 독립 문장으로 남겼다. 실제로 채워진 `isxdigit`, 두 `isdigit` 매크로 예시, locale 설명, unsigned-char/EOF 조건은 본문에 보존했다. 코드/표 항목을 실행하거나 검증하지 않았다.
