# 1198332 보류 원문

아래 문구는 누락된 코드/의존성 설정을 직접 예고하거나 미완 선언을 담는다. 원형으로 보존한다. Java API, 예시 클래스명, 파일 경로/변수, 코드 문자열을 추측해 보충하지 않았고 코드를 실행하지 않았다.

PrintWriter 생성·닫기 예제 도입과 그 미기재 동작을 받는 평가:
> Let's create a PrintWriter instance pointing to an existing file, deleting existing content of the file by just closing it, and then make sure the file length is empty:
>
> Also, note that if we don't need the PrintWriter object for further processing, this is the best option.

FileOutputStream 예제 예고:
> Now, let's delete the content of the file using FileOutputStream:

Apache Commons IO 의존성 예고:
> To see how this works, let’s add the Apache Commons IO dependency to our pom.xml:

FileChannel 예제 예고:
> We can also delete the file contents using java.nio.channels.FileChannel:

Guava 의존성 예고와 불완전 선언:
> First, we need to add the Guava dependency in our pom.xml:
>
> byte empty = new byte;

본문에는 실제 PrintWriter assertion과 writer declaration, FileWriter 호출, FileUtils.write 호출, Files.newBufferedWriter 호출, Guava File 객체 생성처럼 원문에 채워진 코드/이름을 남겼다. 빠진 동작이나 예제를 채우지 않았다. Apache Commons IO와 Guava에서는 의존성 지시만 분리하고, 원문의 예제 소개문구는 실제 붙은 코드를 가리킬 수 있도록 “After that”/“After that” 연결어만 제거해 유지했다. Java 문법/API를 외부에서 검증하지 않았다.
