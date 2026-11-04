# expanded_train:906 보류 원형

아래 C 예제는 함수 블록 경계와 문자열/버퍼 선언 상태가 완결된 예제로 읽히지 않으며, 그 코드만 직접 시연하는 문장이다. 원저자의 오류인지 추출 손상인지 판정하지 않고 실행하지 않았다. 완결된 `memchr` 서명·인자·설명과 반환 조건은 후보에서 보존한다. 잘린 관련 항목 세 줄도 대상이 완결되지 않아 본문에 두지 않는다.

> /* memchr example */
> int main ()
> char * pch;
> char str = "Example string";
> pch = (char*) memchr (str, 'p', strlen(str));
> printf ("'p' found at position %d.\n", pch-str+1);
> printf ("'p' not found.\n");
>
> - Compare two blocks of memory (function
> - Locate first occurrence of character in string (function
> - Locate last occurrence of character in string (function
