# B partial-context punctuation review 004

- Scope: `B_SOURCE_CONTEXT_G_PARTIAL_CONTEXT_SCOPE_V2.json`, SHA-256 `90897B180B97FB12BD6982DB11F9ACC70523BA4DB1C8D8818FCB296658FDFA66`.
- IDs: `329979, 362103, 365144, 368621, 368631, 37325, 382282, 408192, 433393, 437186`.
- Evidence: fixed reader `hold-b-g-context-v2` only. Existing primary full-read and unchanged-outside-changes claims were reused; source-first-read credit and ROOT/cache admission are zero. Each record reports exact final reconstruction and preserved text outside the delivered changes.
- View notation records parts actually returned. `MORE` means an additional part was available and not needed for the scoped change review. No raw source/body reads, independent hashing, or TXT changes were made.

## Findings

### 329979 — APPROVE_EXISTING_BODY

- Body SHA-256: `6460A9B36BF963C23E27315E94C0E4DB10AE7A123C4DC541D59598FC10922966`.
- Views: changes candidate parts 1–2/2, EOF; flags part 1/1, EOF (`NO_LOCAL_BLOCK_FLAGS`).
- The two changes remove empty publication-field punctuation from the citation and add a final newline. The authors, 2017, full paper title, repository URL, and filled discipline labels remain. Missing publisher/issue/page values were not supplied or represented as real citations; the body remains an understandable citation with its available fields.

### 362103 — APPROVE_EXISTING_BODY

- Body SHA-256: `0E84718831D6364ED63A15BE99D7CF6B52442E835EA78C0D22838579FA78EB9B`.
- Views: changes candidate parts 1–2/2, EOF; flags part 1/1, EOF (`POSSIBLE_UNFINISHED_KOREAN_PROSE_NEEDS_CONTEXT`), showing the populated MBC cast list.
- The title's two empty alternate-title slots are removed. The film year, both MBC/SBS voice-cast headings, every named cast/role, populated slash-separated dual role, URL, and filled categories remain. The prose flag is the list context, not evidence of a title or cast value removed here.

### 365144 — APPROVE_EXISTING_BODY

- Body SHA-256: `30A57F9E0B1D835D8D13DC53D6C312348D5E2403FFB4A8B1E7FAB85451C8CCF3`.
- Views: changes candidate parts 1–2/2, EOF; flags part 1/1, EOF (`NO_LOCAL_BLOCK_FLAGS`).
- Four changes close the populated Korean-title parenthesis, remove an empty song-title parenthetical and an unmatched triple-apostrophe formatting marker, and add a final newline. Release date, credits, track name, DVD title, tie-up labels and `#1`/`#2` references remain. The stray style marker does not wrap a filled value.

### 368621 — APPROVE_EXISTING_BODY

- Body SHA-256: `9C447CC468C1268D425D7136A115B0A7FD3DFDB0915B7A43D29E55A9FC081138`.
- Views: changes candidate parts 1–2/2, EOF; flags part 1/1, EOF (`NO_LOCAL_BLOCK_FLAGS`).
- Nine changes remove empty alternate-name punctuation after populated titles and remove the empty `《》` wrapper from the 1983–1984 entry. That entry still gives its date and Japanese television-animation medium; no missing Korean title is invented. The other year/title/medium pairs and the English interwiki remain.

### 368631 — APPROVE_EXISTING_BODY

- Body SHA-256: `3B58DF104C88417C2C24C2C9C06A4DA410E788A35ED5F3F861A5C2F21A869F66`.
- Views: changes candidate parts 1–2/2, EOF; flags part 1/1, EOF (`NO_LOCAL_BLOCK_FLAGS`).
- Two changes remove empty Korean-title brackets from the entries with populated English titles `Fox's Peter Pan & the Pirates` and `Les Nouvelles Aventures de Peter Pan`; the third adds a final newline. Years, media descriptions, other filled film titles, and the stage entries remain in the same order.

### 37325 — APPROVE_EXISTING_BODY

- Body SHA-256: `BF495991DB61A4E8271F6024EAB25BCD06D70B5849C36F7B358EC97119CF8C63`.
- Views: changes candidate parts 1–2/2, EOF; flags part 1/1, EOF (`NATIVE_UNRESOLVED_FIELD_NOT_LOCALLY_PROVEN`), covering the introductory element text.
- The empty alias delimiter after `뢴트게늄(←` is removed while the `←` symbols in the name and `Rg(←)` remain. In the discovery explanation, a missing closing parenthesis is inserted and the extra close-plus-colon `):` is removed, yielding a closed parenthetical followed by a period. Atomic numbers, mass, dates, attribution and classifications remain. The unresolved-field flag is unrelated to these punctuation changes; no chemistry claim is being reassessed.

### 382282 — APPROVE_EXISTING_BODY

- Body SHA-256: `54ADCDDA18EB3BC0486672C683C69E7DC69F81E578B447FA0EEA6F4819DED6EC`.
- Views: changes candidate part 1/12, both exact change records delivered, MORE; body part 11/11, EOF, where both edits occur; flags part 1/11, MORE (`NATIVE_UNRESOLVED_FIELD_NOT_LOCALLY_PROVEN`, whole-body scope).
- The two changes remove an unmatched closing `]` after `Scheme` and an extra `]` after the final ellipsis. The intentional placeholder `[ whatever ]`, prose ellipses, and buggy Scheme example code remain. The unrelated whole-body unresolved-field flag was not used to justify either punctuation edit; no code was executed or repaired.

### 408192 — APPROVE_EXISTING_BODY

- Body SHA-256: `1FD96C40277A50768377EA82D1FE6E2A6691EC06A10A02E304AC73B74FA5AF50`.
- Views: changes candidate parts 1–2/2, EOF; flags part 1/1, EOF (`NO_LOCAL_BLOCK_FLAGS`).
- Ten changes remove seven empty CD right-hand fields and the empty `()`/delimiter on three instrumental rows. The list preserves track order and the `Instrumental` labels. The filled `Milky Way (Club Remix) - (Club Remix)` and `Atlanis Princess Just Fiction Mix2003 - Just Fiction Mix2003` entries remain with their separators; both VCD `- （MV）` annotations also remain. The remaining blank right-side slots were not treated as durations or version names.

### 433393 — APPROVE_EXISTING_BODY

- Body SHA-256: `27DB55CC7F3421647F6B35085196A1D09A2C1D54AA0BA0AAF7FB3B3EAC9355E4`.
- Views: changes candidate parts 1–3/5, all eleven change records delivered in part 3, MORE (next part 4); body part 8/8, EOF; flags part 1/1, EOF (`POSSIBLE_UNFINISHED_KOREAN_PROSE_NEEDS_CONTEXT`), showing all five filled subcategory rows.
- Changes remove blank alternate-name fields, one empty term slot, blank lines, an isolated `}`, and add a final newline. The article's filled Chinese and English terms, five subcategory labels and their displayed values, dates, doctrinal prose, footnotes, and filled category list remain. The `참고 문헌` heading is blank in the body; no populated reference was deleted. The flag context's five rows still include their non-empty values (`견고소단` and the following classifications), so the incomplete-prose flag does not indicate a change-induced list omission.

### 437186 — APPROVE_EXISTING_BODY

- Body SHA-256: `EF50CDCCD98743E1858F1F61B05B60231FDA9148EFC29F2053F405AA61724C96`.
- Views: changes candidate part 1/5, all three change records delivered, MORE; body part 5/5, EOF; flags part 1/1, EOF (`NO_LOCAL_BLOCK_FLAGS`).
- The changes remove an extra period and an empty `()` after the URL, then add a final newline. The final suggested reference retains author `Le, C.N.`, article title, Asian-Nation source name and URL. No year was added. The article, copyright, related-article list and comment rules remain through EOF.

## Narrow machine-checkable follow-up

- A field-aware cleanup check can remove delimiters only when the targeted field is zero-length, while comparing all non-empty neighboring values and their ordering before/after. 408192 is the counterexample to blanket separator removal: Remix/Mix and `MV` values still require their field delimiters.
- For references, validate that only empty slots or extra punctuation are deleted; preserve all populated author, title, year, source and URL fields. An empty `참고 문헌` heading is distinct from removing a real bibliography entry, as confirmed for 433393.
- For code and science text, check bracket pairing over the local syntax context and protect operators, placeholders, ranges and ellipses. The preserved `←`, `+`, `[ whatever ]`, and Scheme examples in this batch show why global character stripping is unsafe.

Batch 4 of 5 is complete. No TXT changes were made; no code, helper, test, Git, model, or GPU actions were taken.
