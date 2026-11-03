# 1313471 termios 라벨의 제한된 복원 근거

총괄은 지정 original 전문과 [Oracle 공식 termios(3HEAD)](https://docs.oracle.com/cd/E19253-01/816-5173/6mbb8ae2i/index.html)의 설명·표를 실제 읽고 대조했다. 공식 페이지는 SunOS 5.10, 2004-09-10 개정/2010 copyright이며 현재 발췌의 Solaris 11 Express 11/10 판 전체를 확인한 것은 아니다. 아래는 **발췌에 이미 있는 설명과 정확히 대응한 라벨만** 복원한다. 누락된 설명행·다른 판의 추가 정의·플랫폼 일반화는 넣지 않는다.

각 그룹에서 현재 발췌의 실제 설명행 순서와 아래 라벨의 수가 일치해야 한다. 설명 문장은 그대로 보존하고 라벨만 같은 행에 붙인다. 새로운 코드·조건·반환값을 생성하지 않는다. 그룹 경계를 넘어 순서만으로 연결하지 않는다.

| 발췌 그룹 | 확인한 대응 라벨 순서 |
|---|---|
| typedef 아래 세 설명 | cc_t, speed_t, tcflag_t |
| control characters 배열 크기 설명 | NCCS |
| c_iflag 설명 열 개 | BRKINT, ICRNL, IGNBRK, IGNPAR, INLCR, INPCK, IXANY, IXOFF, IXON, PARMRK |
| c_oflag와 하위 delay 설명 27개 | ONLCR, OCRNL, ONOCR, ONLRET, OFILL, NLDLY, NL0, NL1, CRDLY, CR0, CR1, CR2, CR3, TABDLY, TAB0, TAB1, TAB2, TAB3, BSDLY, BS0, BS1, VTDLY, VT0, VT1, FFDLY, FF0, FF1 |
| 실제 baud rate 설명 일곱 개 | B1200, B1800, B2400, B4800, B9600, B19200, B38400 |
| c_cflag 아래 네 설명 | CSTOPB, PARODD, HUPCL, CLOCAL |
| c_lflag 아래 다섯 설명 | ECHOE, ICANON, IEXTEN, NOFLSH, TOSTOP |
| tcsetattr 아래 세 설명 | TCSANOW, TCSADRAIN, TCSAFLUSH |
| tcflush 아래 세 설명 | TCIFLUSH, TCIOFLUSH, TCOFLUSH |
| tcflow 아래 두 설명 | TCIOFF, TCION |

이는 65개 라벨의 제한된 복원이다. 원문에 이미 있는 수치 1 200/1 800 등의 표기는 바꾸지 않는다. 공식 페이지에 있으나 현재 발췌에 없는 IGNCR/ISTRIP/OPOST/다른 baud/CSIZE 행 등을 추가하지 않는다.

원문의 struct 다섯 type/name/comment는 모두 실제 채워져 있다. 이를 field 정보로 보존하되 새 세미콜론·struct wrapper·실행 코드를 생성하지 않는다. c_cc subscript 표는 발췌에 실제 설명행 자체가 없으므로 해당 빈 표 예고만 원형 sidecar로 분리하고 외부 표를 가져오지 않는다. 끝 attributes 빈 예고와 실제 탐색 UI도 분리한다. VMIN/VTIME/VEOF/VEOL의 채워진 관계 및 나머지 원문 문장은 유지한다.

Luna가 새 전체 TXT·원형 sidecar·새 리뷰를 만들고 전문과 full diff를 확인한다. 총괄은 이후 65대응의 정확 개수·라벨·나머지 원문 보존을 검사해야 하며, 이 MD 존재만으로 검사나 캐시 채택을 완료했다고 말하지 않는다.
