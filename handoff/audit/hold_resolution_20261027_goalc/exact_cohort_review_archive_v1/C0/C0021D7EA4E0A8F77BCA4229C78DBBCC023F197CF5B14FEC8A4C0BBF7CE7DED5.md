# 419118 보류 원형

| 원문 구간 | 보류 근거 |
|---|---|
| `This code will remain indented because it is part of our open() block of code.` | 값과 코드가 소실된 초기화 예제를 직접 설명한다. |
| `quantities =  ingredients = ` | 변수의 초기값이 없다. 값을 생성하지 않는다. |
| `We’ll iterate over our list so we can access each line of text from our file. Then we’ll split each line into two parts. The dividing point is the comma followed by a space on each line:` | 뒤의 반복문 예제를 직접 도입한다. |
| `for l in lines: as_list = l.split(", ") quantities.append(as_list) ingredients.append(as_list)` | 각 목록에 추가할 실제 값/인덱스가 식별되지 않으며, 빠진 구문을 추정해 채우지 않는다. |
| `The for loop lets us read our file line by line. The first value in “as_list” is the quantity of an ingredient. The second value is the name of the ingredient. We then print both of these lists to the console:` | 바로 앞 루프의 두 목록 산출을 직접 설명하며, 해당 코드와 출력이 불완전하다. |
| `Let’s run our code:` / `['2 tbsp, ricotta\\n', '1 tbsp, grated parmesan\\n', '50g, mozzarella\\n', '25g, gorgonzola\\n', '2, thick slices white bread\\n', '1 tbsp, butter\\n'] ['2 tbsp', '1 tbsp', '50g', '25g', '2', '1 tbsp'] ['ricotta\\n', 'grated parmesan\\n', 'mozzarella\\n', 'gorgonzola\\n', 'thick slices white bread\\n', 'butter\\n']` / `Our code prints three lists to the console. The first list is a list of all the lines of text in our file. The second list contains all the quantities from our file. The third list contains all the ingredients.` | 세 목록과 해설은 손상된 루프의 직접 결과다. 첫 `readlines()` 예제의 별도 출력과 혼동하지 않는다. |
| `for l in lines: as_list = l.split(", ") quantities.append(as_list) ingredients.append(as_list.replace("\\n", ""))` | `as_list`의 실제 타입·이름 구성 관계가 완결되지 않아 이 루프를 복구하지 않는다. |
| `In our for loop, we replace the value “\\n” with an empty string. We do this on the as_list value which correlates to the name of each ingredient.` | 바로 앞 손상 루프가 어떤 값을 변환하는지에 직접 의존한다. |
| `Now that we’ve made this change, our program is ready:` / `with open("grilled_cheese.txt", "r") as grilled_cheese: lines = grilled_cheese.readlines() quantities =  ingredients =  for l in lines: as_list = l.split(", ") quantities.append(as_list) ingredients.append(as_list.replace("\\n", "")) print(quantities) print(ingredients)` | 빈 초기화와 손상된 반복을 결합한 프로그램이다. 구조나 누락 값을 만들지 않는다. |
| `Let’s run our code and see what happens:` / `['2 tbsp', '1 tbsp', '50g', '25g', '2', '1 tbsp'] ['ricotta', 'grated parmesan', 'mozzarella', 'gorgonzola', 'thick slices white bread', 'butter']` / `Our code successfully transforms our text file into two lists. One list contains the quantities of ingredients for a recipe. The other list contains the ingredients we’ll use for the recipe.` | 해당 손상 프로그램의 실행 결과와 성공 주장을 함께 보류한다. |

본문에는 `grilled_cheese.txt`의 실제 재료 데이터와 첫 `readlines()` 출력, `readlines()`, `split()`, `replace()`의 독립 설명, 파일 읽기와 쉼표-공백 구분 조건을 남겼다. 초기화 값·목록 인덱스·코드 구조는 새로 만들지 않았다.
