# 1254536 보류 원문과 근거

대상 본문: /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/resume_guard_counter_20261102_v1/expanded_train_1254536_reviewed_v7.txt

| 원문 위치 | 보류 원문 또는 문장 | 처리 근거 |
|---|---|---|
| expanded_train_1254536_original_0001.txt:3-4 | `A boolean indicating if the code is running on Python 2.` / Python 3 대응 문장 | 상수/API 표제가 없어 어느 boolean을 뜻하는지 특정할 수 없다. |
| expanded_train_1254536_original_0001.txt:6-8 | `Possible class types...`, `Possible types for text data...`, `Type for representing (Unicode) textual data...` | 각 설명의 class/string/text API 이름이 빠져 있다. 이름을 추정해 채우지 않는다. |
| expanded_train_1254536_original_0001.txt:10-11 | `Here’s example usage of the module:` 및 flattened `import six def dispatch_types(value): ...` | 예제 본문과 statement/들여쓰기 경계가 결합됐다. lead-in도 손상된 코드만 가리킨다. |
| expanded_train_1254536_original_0001.txt:13-14 | `Get the function out of unbound method meth... Example usage:` 및 flattened `get_unbound_function` class/method example | accessor 표제가 빠져 있고 예제 경계가 손상됐다. 이름을 추정하지 않고 설명과 예제를 함께 보류한다. |
| expanded_train_1254536_original_0001.txt:15-27 | `Get...`, `Returns...`, `Calls...`, `Return...`로 시작하는 method/accessor 설명들 | 각 설명의 API 제목이 없어 어떤 helper 함수인지 판별할 수 없다. 문장 안에 쓰인 Python 2/3 대체 메서드명으로 누락된 six API를 만들지 않는다. |
| expanded_train_1254536_original_0001.txt:29-33 | `These functions smooth over...` 도입 및 `Execute code...`, `Print args...`, `Reraise an exception...` 설명 | 도입이 가리키는 함수들이 식별되지 않고 helper 표제가 빠져 있다. 그 범위의 설명을 복원하지 않는다. |
| expanded_train_1254536_original_0001.txt:34-35 | `Create a new class with base classes bases and metaclass metaclass...` 및 flattened `with_metaclass` class example | helper 표제와 code boundary가 손상된 직접 설명/예제다. |
| expanded_train_1254536_original_0001.txt:37-38 | `Example usage:` 및 flattened `@add_metaclass(Meta) class MyClass(object): pass` | 앞 문장의 add_metaclass 소개와 일반 class-decorator 설명은 v6에 유지했다. 손상된 decorator example은 별도 보류한다. |
| expanded_train_1254536_original_0002.txt:1-7 | `That code produces a class equivalent to` 및 Python 3/2 비교 class code; `like so:` 뒤의 Python 2.4/2.5 재대입 example | `That code produces...`는 앞서 보류한 decorator example을 직접 지시하므로 비교 코드만 독립 예제로 복원하지 않는다. `like so`도 손상된 example만 도입한다. |
| expanded_train_1254536_original_0002.txt:9-11 | b()/u() 설명과 Python 3.3 u-prefix 문장 | b()/u() 및 Python 판본 조건이 명시된 완결 설명이라 v7 본문에 유지했다. |
| expanded_train_1254536_original_0002.txt:12-15 | `Converts...` / `Return...`로 시작하는 byte helper 설명 | helper/API 이름이 소실되어 어느 변환 함수인지 식별할 수 없다. |
| expanded_train_1254536_original_0002.txt:16-22 | six.moves 일반 설명, `from six.moves import html_parser`, `from six.moves import reload_module`, urllib 설명 | 완결된 본문으로 v6에 유지했으며 이 hold 범위에는 포함하지 않는다. |
| expanded_train_1254536_original_0002.txt:23-27 | 이름/ Python 2/Python 3 열 제목과 값이 빠진 urllib module mapping table | table의 mapping 이름과 module 값이 결손되어 새 이름을 만들지 않았다. |
| expanded_train_1254536_original_0002.txt:29-31 | `Instances of the following classes...`와 이름 없이 `Create a mapping for six.moves...`로 이어지는 두 설명 | class/helper 이름이 빠져 어느 API를 설명하는지 확인할 수 없다. 완결된 일반 소개 `It is possible to add additional names...`는 본문에 남겼다. |

본문에는 일반 six 소개, 명시된 container 최대 크기 설명, Python 판본 차이, 명명된 Iterator 설명, add_metaclass 소개와 손상 예제를 가리키지 않는 설명, b()/u() 설명, 실제 six.moves import 및 urllib 설명을 유지했다. 누락 API 이름은 보충하지 않았다. 본문에 HOLD 표식·편집 지시·보관 설명은 없다.
