# expanded_train:199325 원형 보류

선택 본문은 설명과 경고 중 독립적으로 이해되는 구간을 보존했다. 아래는 실제 원문에서 직접 참조 대상이나 문법이 빠져 독립 문장/실행 가능한 예제로 유지하지 않은 원형 조각이다. 빈 명령·기호·코드 구조를 추정해 채우지 않았다.

- "So, you are here because everyone keeps telling you that things like" / "are bad. But no one really says why" — 지시 대상이 없다.
- "But wait, there's more! Speaking of system(\"PAUSE\"), here is WaltP" / "'s simplified, but complete, breakdown of what exactly system() does to accomplish its goal:" — 이름 연결과 소개된 설명 본문이 끊겼다.
- "The last two need a little explanation." — 이어질 설명 예시가 누락되어 직접 참조가 미완이다.
- "Here's a little console program to try out:" 다음의 "#if defined(WIN32) || defined(_WIN32) || defined(__WIN32__) || defined(__TOS_WIN__) || defined(__WINDOWS__)", "#define EDITOR \"notepad\"", "#define EDITOR \"emacs\"", "printf( \"Now I'm going to start your text editor!\\n\" );", "system( EDITOR );", "printf( \"Good-bye!\\n\" );" — 조건/매크로 갈래와 코드 문맥이 소실되어 하나의 완결 프로그램으로 복원할 수 없다.
- Unix/Linux 메모의 에디터 설정·실행 조각 및 "To escape emacs if you don't know how, press Ctrl-X", "then Ctrl-C" — 앞의 손상 프로그램과 직접 묶인 조작 안내다.
- "Before running your program, you'll have to make sure that the PATH includes the current directory. For bash users, type:" 및 이어지는 빈 명령, "Don't worry, this is only temporary. Once you are done with these exercises, type a period and press ENTER to restart bash to the proper defaults." — 실제 셸 명령이 없고, 복구할 수 없는 입력 지시다.
- "So then, go ahead and compile and run it to see it work." / "Now that you've seen it work properly, create yourself a new little program in the same directory:" / "printf( \"Bwah, hah, hah, hah, hah!\\n\" );" / "Compile it and name the executable \"notepad.exe" / "\" if you are on Windows, or \"emacs" / "\" (or whatever your used above) if you are on *nix." / "(Be careful not to clobber your first program's executable.)" / "Now run the first program again. What happened?" — 앞뒤 프로그램·명령 구조와 실행 파일 이름 경계가 손상되어 직접 실행 예제로 선택하지 않았다.
- "Unix/Linux users, now would be a good time to restart your shell." — 위의 보류한 PATH 조작에 직접 연결된다.
- "Remember, this example was contrived -- there are plenty of other ways to get malicious software into the execution path." — 위의 프로그램/실행 예제가 빠져 이 지시 대상도 함께 보류했다.
- "Anything you" / "can do it" — 문장이 잘려 목적어/의미가 완결되지 않았다.
- "if (system( NULL )) then_I_can_safely_use_system();" — 본문이 이를 셸 존재 확인 예시로 소개하지만, 코드의 동작/안전 조건이 불완전하므로 코드 조각을 새로 해석하지 않았다.
