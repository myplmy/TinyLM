# 189258 공식 원문에 따른 표 구조 복구 범위

대상 원형: `expanded_train:189258`, SHA-256 `B7C5F06D0E413CF20C69F9B4EDE11B335C567340D7A7A189B1E3C67C38F6C5CD`. 원형35495자는 보존한다.

근거는 [JMIR Nursing 공식 논문](https://nursing.jmir.org/2020/1/e20747/)이다. 기존 네 표의 수치와 원문 대응을 총괄이 확인했다. 새 수치 행을 추가하지 않고 잃은 행/열 명명과 한 글자 구두점만 복구하는 범위다. 의학적 효과 재검증이나 통계 재계산이 아니다.

1. 표1: `<40` 바로 앞의 변수명은 `Age (years)`다. 기존 다른 범주·하위집단·두 군 n=55/56·값의 연결은 유지한다. `7 (13|`는 수치를 바꾸지 않고 `7 (13)|`로 닫을 수 있다. 공식 원문에도 이 닫는 괄호가 빠져 있으므로 단순 서식 교정으로 이력을 남긴다. 원형에 없는 P값/수치 행은 가져오지 않는다.
2. 표2: 네 연속 블록은 순서대로 `Physical function`, `Psychological function`, `Social function`, `Total`이다. 기존 첫 Before의 두 군 값은 각각18.87/21.75,9.26/10.96,14.76/14.68,42.91/47.42이며 이후 각 블록의After/paired-test/changes를 같은 블록에 둔다. 본문에 없는 추가 P-value 행은 가져오지 않는다.
3. 표3: 기존 세 교육수준 행은 `Education level`, 기존Somewhat adequate/Not adequate 행은 `Income adequacy` 아래다. 진단 이후 시간·BMI·이전3개월입원 등 기존 명명행/각주를 유지한다. 공식표에만있는성별/직업/흡연 등새값·행을추가하지않는다. 원형의기존P값/검정각주를다른변수에붙이지않는다.
4. 표4: 네Before/After쌍은표2와같은네영역순서다. 마지막3개열의실제하위명칭은 `Group variable`, `Income`, `Hospitalization`이다. `Partial eta squared`상위표제를함께보존한다. 괄호안팎수치의뜻을새로해석하거나수치/부호/소수점을바꾸지않는다.

표를평탄화하면영역/시점을명시하는열또는그룹행을사용할수있다. 군/변수/시간구조가명확해야하며새표제가새숫자값처럼섞이지않게한다. 기존수치셀은그대로두고일반서식외추가본문수정은최소화한다. 초록·방법·대상/제외조건·3개월등원래한정·한계·참고문헌은보존한다. 이복구가실제앱효과나모델품질PASS를뜻하지않는다.

인용: Davoudi M, Najafi Ghezeljeh T, Vakilian Aghouee F. Effect of a Smartphone-Based App on the Quality of Life of Patients With Heart Failure: Randomized Controlled Trial. JMIR Nursing 2020;3(1):e20747. DOI:10.2196/20747.

©Mahboube Davoudi, Tahereh Najafi Ghezeljeh, Farveh Vakilian Aghouee. Originally published in JMIR Nursing Informatics,02.11.2020. 공식원문은[CC BY4.0](https://creativecommons.org/licenses/by/4.0/)으로제공되며원출판물링크·완전서지·저작권/라이선스정보를함께보존한다. 이귀속과복구이력은sidecar/manifest에연결하고검수메모를학습본문에넣지않는다.

허용출력: 자기page010폴더의새 `expanded_train_189258_task006_v3.txt`, `hold_189258_task006_v3.md`, `review_006_v3.md`. 기존다른4행/원형/후보/초안은유지한다. 기존판독의전문재독은필요없으며새전체본문·전체diff·EOF를확인한뒤총괄의셀보존검산을기다린다.

