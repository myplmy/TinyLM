# expanded_train:151121 보류 원형

후보가 원문과 바이트 동일한 지정 입력에서 §13.3 아래 다음 세 연속 설명은 명령명/주체가 없는 상태로 남아 있다. `Like Set Variable`과 `Like Bind Key`는 비교 대상을 가리키지만 누락된 명령의 이름은 특정하지 않는다. 따라서 이 블록 전체를 본문에서 분리하고 `Set Variable`이나 다른 명령의 설명으로 귀속하지 않았다.

> Like Set Variable, this command prompts for the name of a Hemlock variable and an expression. Like Bind Key, this command prompts for a place: mode, buffer or local. The result of evaluating the expression is defined to be the value of the named variable in the specified place.
>
> This command is most useful for making mode or buffer local bindings of variables. Redefining a variable in a mode or buffer will create a customization that takes effect only when in that mode or buffer.
>
> Unlike Set Variable, the variable name need not be the name of an existing variable: new variables may be defined. If the variable is already defined in the current environment, Hemlock copies the documentation and hooks to the new definition.

다른 명명된 명령 설명, 실제 Bind Key 동작 목록, 명시된 옵션·키 표기와 Lisp 예제는 원문 그대로 유지했다. 누락된 명령명은 추정하지 않았다.
