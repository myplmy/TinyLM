# expanded_train:49092 원형 보류 / NEEDS_ROOT 근거 — 인용 경계 정정판

## 입력·판독 범위

TASK_020에 지정된 원문 패킷 0001–0025는 이전 review_020 판독에서 순서대로 읽어 원문 논리 END와 0025의 실제 패킷 끝을 확인했다. candidate 중간 패킷 0026–0049는 지정된 동일성 계획상 생략 대상이며, 최종 패킷 0050의 candidate END·full_diff END와 실제 EOF도 이미 확인했다. 이 정정판을 쓰기 위해 원문 패킷 0011–0015와 0019–0021을 다시 연속으로 대조했다. 아래 인용은 해당 입력에서 실제로 이어지는 문장을 경계대로 옮긴 것이다.

## 판정

외계생명체에 관한 본문 사이에 무관한 백과사전 정의·링크 문구·틀 조각이 끼어들어 원래 문맥을 안정적으로 나눌 수 없다. 본문에서 몇 문장만 골라 새 문맥으로 조립하지 않고 전체를 학습 후보에서 분리해 원형 보류한다. 개별 비채택 판정은 총괄에 연결할 NEEDS_ROOT로 남긴다. 이것은 원문 전체가 사실 오류라는 판단이 아니다.

## 연속 원문 근거

### 고대 그리스/Thales 문장 사이의 백과사전 혼입

```text
The first important Western thinkers to argue systematically for a universe full of other planets and, therefore, possible extraterrestrial life were the ancient Greek writer Thales and his student Anaximander in the 7th and 6th centuries B. Greek (el ελληνική γλώσσα or simply el ελληνικά — "Hellenic" is an Indo-European language, spoken today by 15-22 million people mainly Thales of Miletus According to Bertrand Russell, "Philosophy begins with Thales Anaximander ( Ancient Greek:) (c 610 BC–c 546 BC was a Pre-Socratic Greek philosopher who lived in Miletus C. The atomists of Greece took up the idea, arguing that an infinite universe ought to have an infinity of populated worlds.
```

이 삽입에는 Greek/Thales/Anaximander의 별도 백과 문구가 원래 주장 사이에 섞여 있다. 입력 패킷 0011의 물리적 끝 `infin`과 0012의 시작 `ite`를 원문 절단으로 보지 않는다. 이어 읽으면 `infinite`라는 온전한 단어다.

### Islam/Qur’an 문맥의 disambiguation·항목 정의 삽입

```text
Within Islam, the statement of the Qur'an "All praise belongs to God, Lord of all the worlds" indicates multiple universal bodies and maybe even multiple universes that may indicate extraterrestrial and even extradimensional life. For other meanings including people named 'Islam' see Islam (disambiguation. The Qur’an ( القرآن, literally "the recitation" also sometimes transliterated as Qur’ān, Koran, Alcoran God is the principal or sole Deity in Religions and other belief systems that worship one deity. Surat Al-Jinn also mentioned a statement from a Jinn regarding the current status and ability of his group in the heavens. Surat Al-Jinn (سورة الجن ( The Jinn or The Sprites) is the 72nd Sura of the Qur'an with 28 Ayat. GEnie (General Electric Network for Information Exchange was an online service
```

`For other meanings ...` 안내, Qur’an/Surat Al-Jinn 항목 정의, GEnie 설명이 외계 생명에 관한 글의 문장 사이에 삽입되어 있다. 패킷 0013 말미 `curren`과 0014 첫 `t`는 물리 분할일 뿐이며 실제 원문은 `current status`로 이어진다. `GEnie ... online service`는 입력에 나타난 불완전한 삽입 문자열만 보존한다.

### Rare Earth 문맥의 EARTH 그룹·백과사전 정의 삽입

```text
In it, they discussed the Rare Earth hypothesis, in which they claim that Earth-like life is rare in the universe, while microbial life is common in the universe. In Planetary astronomy and Astrobiology, the Rare Earth hypothesis argues that the emergence of complex Multicellular life ( Metazoa EARTH was a short-lived Japanese vocal trio which released 6 singles and 1 album between 2000 and 2001 The Universe is defined as everything that Physically Exists: the entirety of Space and Time, all forms of Matter, Energy The Bacteria ( singular: bacterium) are a large group of unicellular Microorganisms Typically a few Micrometres in length bacteria have
```

EARTH 일본 보컬 트리오 문구 및 우주·세균 정의가 Rare Earth 설명 중간에 섞여 있다. 패킷 0019의 마지막 `car`와 0020의 첫 `rying`은 실제 원문에서 `carrying`으로 온전히 연결되므로 이 패킷 분할을 손상 근거로 쓰지 않는다.

### 태양계 문장 뒤의 틀 조각

```text
Scientists are directly searching for evidence of unicellular life within the solar system, carrying out studies on the surface of Mars and examining meteors that have fallen to Earth. The Solar System consists of the Sun and those celestial objects bound to it by Gravity. A mission is also proposed to Europa, one of Jupiter's moons with a possible liquid water layer under its surface, which might contain life. TemplateInfobox Planet.--> Europa (jʊˈroʊpə; or as
```

완결된 `carrying out ... Earth` 문장은 패킷 0019–0020을 이어 읽으면 온전하다. 그 뒤의 태양계 정의와 `TemplateInfobox Planet.--> Europa ... or as` 조각이 문맥에 끼어 있다. `or as` 뒤에 원문에서 제공되지 않은 값을 보충하지 않는다.

## 처리 경계

위 인용은 혼입·절단이 실제 원문 안에 있는지 보여주는 대표 연속 구간이다. 이전 v1에서 `infin`/`curren` 및 `car`/`rying`을 원문 자체의 단어 절단인 것처럼 제시한 설명은 정정한다. 그 세 조각은 패킷 물리 경계에서 나뉘었지만 각각 `infinite`, `current`, `carrying`으로 실제 이어진다. 이 정정은 다른 실제 혼입의 원형 근거와 전체 보류 판정을 바꾸지 않는다. 새 학습 TXT는 만들지 않았고, 비인용 부분의 문장을 재구성하지 않았다.
