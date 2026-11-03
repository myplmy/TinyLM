# 836288 원형 보류

선택 본문: `reviewed_836288_task062_v2.txt`.

- `If you know the equation ... it’s simply:`는 뒤의 식이 실제로 없으므로 예고만 분리했다. 수식을 보충하지 않았다.
- `See how the values are confined, while`는 빠진 그래프/시각 자료를 가리키는 포인터다. 다음 줄의 완결 정보 `t extends infinitely.`는 본문에 남겼다.
- `A more descriptive version ...`로 소개되는 RunService 코드 전체는 한 줄로 평탄화되어 `--` 주석이 뒤의 코드까지 삼키므로, 실행 가능한 예제로 재구성하지 않고 원형 보류했다. `I used step in combination with ‘t’ to show how tick() was used in your example.`도 이 미수록 예제에 직접 연결되며 `step`/`t`의 본문 내 선언·사용이 없으므로 함께 보류했다. 질문의 `math.sin(tick())`, `RunService.RenderStepped` 실행시점과 결과 범위 -1에서 1 설명은 보존했다.

## 원문 발췌

```text
2	It makes it synchronous to time, and sine function is limited between -1 and 1 in output. If you know the equation for a sine wave on a graph, it’s simply:
3	See how confined the values are, while
9	RunService.RenderStepped runs prior to each frame being rendered on the client. A more descriptive version of your example would be:
10	local t = 0 local RunService = game:GetService('RunService') RunService.RenderStepped:Connect(function(step) -- Increment t with the time step -- (time between last and current call of this event) t += step -- You can see how 't' evolves over time by 1 per second print(math.sin(t), t) end)
```
