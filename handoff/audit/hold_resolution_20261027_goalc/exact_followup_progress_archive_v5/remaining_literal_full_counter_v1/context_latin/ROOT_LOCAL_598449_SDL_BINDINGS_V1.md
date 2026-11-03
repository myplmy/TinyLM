# 598449의 서로 다른 두 함수 주체

총괄이 지정 원문11–15줄과120–136줄의 실제 문맥을 읽었다.131줄과132–133줄을 한 함수로 합치면 안 된다.

131줄은 SDL2_image의 IMG 접두,renderer+파일경로라는 두 인수,texture 생성/nil 실패를 말한다. 같은 절123줄은 IMG_LoadTexture가 이미지를 직접texture로 만든다고 명시한다. [공식 IMG_LoadTexture](https://wiki.libsdl.org/SDL2_image/IMG_LoadTexture)의 대응도 확인했다. 이 기존 이름을131줄의 정확 주체로 복원할 근거가 있다.

132–133줄은 renderer/texture/두rectangle의 네 인수와nil 두개,전체texture→target 크기확장,0/음수 반환을 말한다. 같은 원문14줄의 명시 SDL_RenderCopy 호출과 정확히 대응하며 [공식 SDL_RenderCopy](https://wiki.libsdl.org/SDL2/SDL_RenderCopy)도 그 관계를 확인한다. 이 기존 이름을132–133줄의 주체로 연결할 수 있다.

새body/호출코드를 만들지 않고 실제 두 이름만 각 해당 문장/단락에 구분해 붙인다.200×200→500×500 및 기존 경로·Pascal의PSDL_Rect/nil 표기는 그대로 유지한다. 뒤의 SDL1.2 절을 SDL2로 바꾸거나 다른API/인수/현대 설치절차를 가져오지 않는다. 원문에서 소실된코드/그림 직접예고는 기존 sidecar로 분리한다.

새 전체TXT/원형sidecar와 자기TASK047의다른네행을보존한새리뷰로연결한다. 자체코드/해시/웹/SDL실행권한은추가되지않는다.
