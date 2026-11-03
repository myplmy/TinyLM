# 142479 원형 코드/포인터 보류

원문과 candidate는 지정 동일성 계획으로 동일성이 연결됐다. Listing 9.4–9.9의 Visual Basic 예제는 여러 선언·실행문·주석이 한 줄로 붙어 있고, 중첩 제어 흐름/문장 경계를 알 수 없으므로 코드 단위로 원형 보류했다. 들여쓰기나 줄바꿈을 복구하지 않았다. 명명된 Print/Cls/Tab/CurrentX/CurrentY/TextWidth/TextHeight/Font 설명, twips 환산, 채워진 조건과 prose에 직접 쓰인 결과는 본문에 남겼다. Figure 번호/Listing 번호와 빈 시각자료 포인터는 제거했으며, 그림 캡션에 실린 독립 정보는 일반 문장으로 보존했다.

## 원형 Listing 제목·코드 단락
Listing 9.4: Command1_Click Event in Print
Private Sub Command1_Click() Dim i As Integer Picture1.Cls For i = 1 To 100 Picture1.Print “abcdefg”; Next i End Sub
Listing 9.5: Command2_Click Event in Print
Private Sub Command2_Click() Dim i As Integer Picture1.Cls For i = 1 To 100 Picture1.Print “abcdefg” Next i End Sub
Listing 9.6: Command3_Click Event in Print
Private Sub Command3_Click() Picture1.Cls Picture1.Print “abc”, “def”, “ghi”, “jkl”, “mno”, “pqr”, _ “stu”, “vwx” Picture1.Print “abcdef”, “ghijkl”, “mnopqr”, “stuvwx” Picture1.Print “abcdefghijkl”, “mnopqrstuvwx” Picture1.Print “abcdefghijklmnopqrstuvwxyz”, _ “abcdefghijklmnopqrstuvwxyz” End Sub
Listing 9.7: Command4_Click Event in Print
Private Sub Command4_Click() Dim t As String Picture1.Cls t = FormatNumber(Picture1.CurrentX, 0) & “,” & _ FormatNumber(Picture1.CurrentY, 0) Picture1.Print t Picture1.CurrentX = 0 Picture1.CurrentY = 2880 t = FormatNumber(Picture1.CurrentX, 0) & “,” & _ FormatNumber(Picture1.CurrentY, 0) Picture1.Print t Picture1.CurrentX = 2880 Picture1.CurrentY = 0 t = FormatNumber(Picture1.CurrentX, 0) & “,” & _ FormatNumber(Picture1.CurrentY, 0) Picture1.Print t Picture1.CurrentX = 2880 Picture1.CurrentY = 2880 t = FormatNumber(Picture1.CurrentX, 0) & “,” & _ FormatNumber(Picture1.CurrentY, 0) Picture1.Print t End Sub
Listing 9.8: Command5_Click Event in Print
Private Sub Command5_Click() Dim t As String t = “Hello” Picture1.Cls Picture1.CurrentX = 1440 Picture1.CurrentY = 1440 Picture1.Print t Picture1.CurrentX = 1440 - Picture1.TextWidth(t) Picture1.CurrentY = 1440 Picture1.Print t Picture1.CurrentX = 1440 Picture1.CurrentY = 1440 - Picture1.TextHeight(t) Picture1.Print t Picture1.CurrentX = 1440 - Picture1.TextWidth(t) Picture1.CurrentY = 1440 - Picture1.TextHeight(t) Picture1.Print t End Sub
Listing 9.9: Command6_Click Event in Print
Private Sub Command6_Click() Dim t As String t = “Hello” Picture1.Cls Picture1.CurrentX = 1440 Picture1.CurrentY = 1440 Picture1.Print t Picture1.Font.Bold = True Picture1.CurrentX = 1440 - Picture1.TextWidth(t) Picture1.CurrentY = 1440 Picture1.Print t Picture1.Font.Italic = True Picture1.CurrentX = 1440 Picture1.CurrentY = 1440 - Picture1.TextHeight(t) Picture1.Print t Picture1.Font.Size = 18 Picture1.CurrentX = 1440 - Picture1.TextWidth(t) Picture1.CurrentY = 1440 - Picture1.TextHeight(t) Picture1.Print t Picture1.Font.Size = 8 Picture1.Font.Bold = False Picture1.Font.Italic = False End Sub

## 원형 코드/그림 포인터 문맥
The Print method works much as you would expect. Each time you call the Print method, the output will begin at the start of the next line, except if the previous Print method ended with a comma or semicolon. In that case, the print would be continued on the same line. Listing 9.4 contains an example of code that allows printing beyond the right edge, and Figure 9.3 shows the results.
Figure 9.3: Any printed output beyond the right edge of the control is lost.
One limitation of this approach is that, eventually, you will reach the end of the object. If you continue to print to the object, the text will fall off the end of the paper or screen and not be visible. Likewise, if you continue to print on the same line, it will also fall off the edge and be lost. Neither of these conditions will generate an error or a warning. Listing 9.5 contains an example of code that allows printing beyond the bottom edge, and Figure 9.4 shows the results.
Figure 9.4: Any printed output beyond the bottom edge of the page is lost
Just like in the original BASIC, if you separate values by commas, each value will start at the beginning of the next print zone. Print zones are aligned based on absolute measurements, not characters. This makes it easier to create columns, as long as your data is not wider than a print zone. If it’s wider, you need to be careful to ensure that you are starting the data in the proper print zone. The code shown in Listing 9.6 creates columns with commas. Figure 9.5 shows its output.
Figure 9.5: When you use commas, columns will line up as long as they are close to the same size.
The code in Listing 9.7 shows how to move around a PictureBox control using the CurrentX and CurrentY properties. I save the values of CurrentX and CurrentY into the string t before I execute the Print method so that these values remain unaffected by the printing process. Figure 9.6 shows the output.
Figure 9.6: You can use the CurrentX and CurrentY properties to control the position of a PictureBox control.
The code in Listing 9.8 shows how to display the same string of text in four different quadrants surrounding the center point of the cursor. Figure 9.7 shows the results.
Figure 9.7: You can use the TextHeight and TextWidth methods to control the position of text.
Doing this in Visual Basic is fairly easy. All you need to do is change the Font object associated with the object you are using. In Listing 9.9, you can see that I copied the same code from the code shown in the previous section and inserted some changes to Picture1’s Font property.
As you can see in Figure 9.8, most of these changes did not materially change how the information is aligned. However, in the upper-left corner, where I changed the font size to 18, you can see that the text is pulled slightly away from the other three text blocks. This is because the padding areas above, below, and to the right of the text are greater in an 18-point font than in the standard 8-point font.
Figure 9.8: You can change font characteristics to emphasize text.
코드와 직접 이어진 Listing 제목/실행 블록은 학습 본문에서 뺐다. Figure 표식/이미지 포인터를 제거해도 뜻이 독립적인 Figure 9.3–9.8 캡션의 사실·조건은 v1 본문에 문장으로 남겼다. Listing 9.7의 code pointer/Figure pointer는 제거했지만, 원문 저자 서술 `I save ...`는 완결된 관계 설명이라 보존했다.
