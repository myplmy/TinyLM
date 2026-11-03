# 669804 원형 보류: 평탄화된 C# 예제와 직접 지시 문구

## 판독 범위
지정 original/candidate와 TASK_053의 여섯 연속 패킷, 전체 diff END/EOF를 대조했다. 아래 코드는 원문에 있는 평탄화된 문자열 그대로다.

## 학습 본문에서 분리한 원형

```text
For example, the following C# code shows how to read from a redirected stream and wait for the child process to exit.
// Start the child process. Process p = new Process(); // Redirect the output stream of the child process. p.StartInfo.UseShellExecute = false; p.StartInfo.RedirectStandardOutput = true; p.StartInfo.FileName = "Write500Lines.exe"; p.Start(); // Do not wait for the child process to exit before // reading to the end of its redirected stream. // p.WaitForExit(); // Read the output stream first and then wait. string output = p.StandardOutput.ReadToEnd(); p.WaitForExit();
The code example avoids a deadlock condition by calling p.StandardOutput.ReadToEnd before p.WaitForExit.
```

```text
There is a similar issue when you read all text from both the standard output and standard error streams. For example, the following C# code performs a read operation on both streams.
// Do not perform a synchronous read to the end of both // redirected streams. // string output = p.StandardOutput.ReadToEnd(); // string error = p.StandardError.ReadToEnd(); // p.WaitForExit(); // Use asynchronous read operations on at least one of the streams. p.BeginOutputReadLine(); string error = p.StandardError.ReadToEnd(); p.WaitForExit();
The code example avoids the deadlock condition by performing asynchronous read operations on the StandardOutput stream.
```

주석과 실행문이 같은 평탄화 행에 붙어 있어 원래의 코드 행·주석 범위를 확인할 수 없다. 이 두 예제와 그 예제를 직접 지시하거나 요약하는 문구를 본문에서 분리했다. 새 줄바꿈이나 코드 구문은 복원하지 않았다.

## 본문에 보존한 독립 설명
두 스트림을 동기식으로 읽을 때 생기는 대기 의존성에 대한 완결 설명, 호출 이름이 명시된 deadlock 조건, 비동기 읽기/별도 스레드에 대한 일반 설명, 그리고 주석 없이 문장/세미콜론 경계가 보이는 `Process compiler` 코드는 그대로 보존했다. 코드 실행이나 컴파일 검증은 하지 않았다.
