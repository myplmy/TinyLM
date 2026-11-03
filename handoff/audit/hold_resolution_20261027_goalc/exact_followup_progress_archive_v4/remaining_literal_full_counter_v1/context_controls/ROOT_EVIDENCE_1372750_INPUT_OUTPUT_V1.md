# 1372750의 소실된 @Input 식별자

총괄이 지정 원문을 전문 읽고 같은 원 발행처·저자 David Aden의 [SitePoint 기사](https://www.sitepoint.com/angular-2-components-inputs-outputs/)를 직접 대조했다. 원문의 앞 설명은 myname=input,myevent=output으로 명시하지만 대체 구문에서 @Input이 사라져 둘 다 @Output으로 읽히는 결손이 있다.

발행처의 대응 문장은 두 decorator를 각각 명시한다. 기존 원문에서 다음 세 위치의 누락된 식별자만 복원한다.

- `Angular also lets us use an` 뒤: @Input과 @Output이 함께 놓이는 병렬 관계.
- `used the` 뒤에서 myname/myevent를 선언하는 문장: @Input과 @Output의 병렬 관계.
- `Whether you use inputs/outputs or` 뒤: @Input/@Output의 쌍.

원문에 이미 있는 이름·순서·일반 설명을 유지한다. 실제 그림의 코드나 누락 클래스를 생성하지 않으며 Angular 최신 API로 고치지 않는다. 발행처 표시는2018-03-23/갱신2024-11-13이므로 원 캐시의 판본 날짜를 확인했다는 뜻은 아니다. 이 대응은 동일 주제·동일 ParentComp/myname/myevent와 인접 문장의 직접 일치에 한정한다. 다른 빠진 문단·샘플 repo·코드 전체를 가져오지 않는다.

이 MD는 추가 허용된 검수 입력이다. controls는 literal cat으로 이 정확 MD를 읽을 수 있다. 실제 입력은 기존 고정 reader를 유지하고 자기 새 전체TXT/원형sidecar와 TASK023의 다섯 행을 보존한 새 리뷰로 연결한다. 자체 코드·통계·웹·다른 입력 열기는 하지 않는다. @Input이 빠진 원형을 sidecar에 남겨 변경 이력을 보존한다.
