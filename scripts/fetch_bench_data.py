#!/usr/bin/env python3
"""★**벤치마크 데이터셋 내려받기 — 학습 0·GPU 0. 네트워크만 쓴다.**

## 왜 별도 도구인가

`eval_bench_suite.py` 는 **네트워크를 쓰지 않는다.** 평가 도중 다운로드가 섞이면
*"느린 것이 모델인가 네트워크인가"* 를 못 가른다. **받는 것과 재는 것을 분리**한다.

## 받는 것 (사용자 지시 2026-08-22 — **예상 결과와 무관하게 전부**)

    MMLU · MMLU-Redux · MuSR · IFEval · GSM8K · HumanEval+ · BFCL v3
    ARC(e/c) · BoolQ · HellaSwag · PIQA · WinoGrande · LAMBADA

⚠️★**HF 게이트가 걸린 것은 실패로 끝난다** — 그것도 결과다. **로그에 남긴다.**
⚠️★**받은 뒤 `--verify` 로 문항 수를 인쇄**한다. 공식 규모와 다르면 **split 을 잘못 잡은 것**이다.

사용법
    python scripts/fetch_bench_data.py --list          # 무엇을 받을지 (네트워크 0)
    python scripts/fetch_bench_data.py --all
    python scripts/fetch_bench_data.py --only hellaswag piqa lambada
    python scripts/fetch_bench_data.py --verify        # 이미 받은 것 점검 (네트워크 0)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ★★★2026-08-22 사고 — **이 한 줄이 없어서 15종이 전부 엉뚱한 곳에 받아졌다.**
#   `tinylm/paths.py` 는 import 부작용으로 HF_HOME·HF_HUB_CACHE·HF_DATASETS_CACHE 를
#   **작업폴더 `HF/` 로 강제**한다. 그런데 이 스크립트는 `sys.path` 만 건드리고
#   **`tinylm` 을 import 하지 않아서** 그 부작용이 한 번도 일어나지 않았다.
#   → `datasets` 가 사용자 환경의 `HF_HOME`(Z:\unsloth_files\cache)로 받았고
#      사용자가 손으로 옮겨야 했다.
#   ⚠️★**함정 37 의 다른 얼굴**이다: *"리다이렉트가 존재한다 != 그 경로가 실행된다."*
#   🚫**사용자 환경변수는 영구 수정하지 않는다** — 이 import 는 **이 프로세스 안에서만** 바꾼다.
import tinylm  # noqa: F401,E402  ★반드시 datasets/huggingface_hub 보다 먼저

OUT = ROOT / "datasets" / "bench"

# (이름, HF id, config, split, 공식 규모, 비고)
# ★규모는 **각 논문/데이터카드의 통용값**이다. ⚠️조회 상태는 `docs/methods/10_benchmarks.md` §6.
SPECS = [
    ("hellaswag",     "Rowan/hellaswag",              None,            "validation", 10042, "4지선다 문장완성"),
    # ⚠️2026-08-22 — `ybisk/piqa` 는 **로더 스크립트(piqa.py)** 라 최신 datasets 가 거절한다.
    #   HF 가 자동 변환해 두는 **parquet 브랜치**를 revision 으로 지정한다.
    ("piqa",          "ybisk/piqa",                   None,            "validation",  1838, "2지선다 물리상식"),
    ("winogrande",    "allenai/winogrande",           "winogrande_xl", "validation",  1267, "2지선다 대명사"),
    ("arc_easy",      "allenai/ai2_arc",              "ARC-Easy",      "test",        2376, "4지선다 과학"),
    ("arc_challenge", "allenai/ai2_arc",              "ARC-Challenge", "test",        1172, "4지선다 과학(난)"),
    # ★★2026-09-05 — arc_easy 를 **세 split 전부**로. 근거: McNemar 필요 n 2,451 vs test 2,376
    #   (결과 074 §11.4). 로컬 데이터카드 실사로 train 2,251 + test 2,376 + validation 570.
    #   ⚠️**별도 이름으로 둔다** — 기존 `arc_easy`(test 만)의 수치를 바꾸면 과거 비교가 깨진다.
    ("arc_easy_full", "allenai/ai2_arc",              "ARC-Easy",      "train+validation+test", 5197,
     "★arc_easy 세 split 전부. 정확도 검정력용"),
    # ★★2026-09-05 — KoBEST(arXiv:2204.04541). 한국어 축이 0 이었다.
    #   🚫**BoolQ·WiC·SentiNeg 는 안 받는다** — 논문 Table 4 에서 KoGPT3-39B zero-shot 이
    #   BoolQ 33.1 · WiC 34.7 로 **우연(50) 아래**다. 39B 가 못 하는 것을 81M 에 물리지 않는다.
    ("kobest_copa",   "skt/kobest_v1",                "copa",          "test",        1000, "★한국어 2지선다 인과"),
    ("kobest_hellaswag", "skt/kobest_v1",             "hellaswag",     "test",         500, "★한국어 4지선다 문장완성"),
    # ★★2026-09-06 — 우리 Stage1 held-out. 🚫**HF 가 아니라 로컬 파일**이다(SPECIAL 로 간다).
    #   v2.7 에서 D6(정답이 둘)이 0 이 되어 처음 채점에 쓸 수 있게 됐다.
    # ★2026-09-10 — 공식 개수를 None 으로. v2.7 300 -> v2.8 4,500 이라 **고정 수가 아니다**
    #   (300 을 박아 두면 판이 바뀔 때마다 ⚠️가 뜨는데 그것은 결함이 아니다).
    ("stage1_heldout", "(local)",                     None,            "(local)",     None, "★한국어 4지선다 관계추론(자체·판마다 개수가 다르다)"),
    # ★★2026-09-10(2차) 신설 — SFT 응답 채점셋(사용자 지시 3). 🚫HF 가 아니라 로컬 canonical.
    ("sft_fresh_eval", "(local)",                     None,            "(local)",      300, "★SFT 응답 규칙채점(자체 canonical)"),
    ("boolq",         "google/boolq",                 None,            "validation",  3270, "예/아니오. ⚠️라벨 불균형"),
    ("lambada",       "EleutherAI/lambada_openai",    "en",            "test",        5153, "★마지막 단어 예측"),
    ("mmlu",          "cais/mmlu",                    "all",           "test",       14042, "4지선다 57과목"),
    ("mmlu_redux",    "edinburgh-dawg/mmlu-redux-2.0", "all",          "test",        5700, "MMLU 오류 재라벨"),
    ("musr",          "TAUR-Lab/MuSR",                None,            "murder_mysteries", 250, "★MC 다. 생성 아님"),
    ("gsm8k",         "openai/gsm8k",                 "main",          "test",        1319, "다단계 산술"),
    ("ifeval",        "google/IFEval",                None,            "train",        541, "지시 따르기"),
    ("humaneval",     "openai/openai_humaneval",      None,            "test",         164, "코드 생성"),
    ("humaneval_plus", "evalplus/humanevalplus",      None,            "test",         164, "HE+ 확장 테스트"),
    ("bfcl_v3",       "gorilla-llm/Berkeley-Function-Calling-Leaderboard", None, "train", None, "함수 호출"),
]


def banner(s, ch="="):
    print("\n" + ch * 96)
    print(f"  {s}")
    print(ch * 96)


def do_list():
    banner("받을 목록 — 네트워크를 쓰지 않는다", "#")
    print(f"  저장 위치: datasets/bench/<이름>.jsonl")
    print(f"{'이름':<16}{'HF id':<52}{'config':<18}{'split':<12}{'공식 규모':>10}  비고")
    print("-" * 130)
    for n, hid, cfg, sp, sz, note in SPECS:
        have = (OUT / f"{n}.jsonl").exists()
        print(f"{('✅' if have else '  ') + n:<17}{hid:<52}{str(cfg or '-'):<18}"
              f"{sp:<12}{(str(sz) if sz else '?'):>10}  {note}")
    print(f"\n  ✅ = 이미 받음. 전부 받으려면 `--all`.")


def do_verify():
    banner("받은 것 점검 — 네트워크를 쓰지 않는다", "#")
    ok = miss = 0
    for n, _h, _c, _s, sz, _note in SPECS:
        p = OUT / f"{n}.jsonl"
        if not p.exists():
            print(f"  🚫 {n:<16} 없음")
            miss += 1
            continue
        cnt = sum(1 for _ in p.open(encoding="utf-8"))
        flag = "✅" if (sz is None or cnt == sz) else "⚠️"
        note = "" if (sz is None or cnt == sz) else f"  ← 공식 {sz} 와 다르다. **split 을 확인**"
        print(f"  {flag} {n:<16} {cnt:>7}행{note}")
        ok += 1
    print(f"\n  받음 {ok} / 없음 {miss}")
    print("  ⚠️★행 수가 공식 규모와 다르면 **split 을 잘못 잡은 것**이고, 그대로 재면 "
          "다른 논문 숫자와 비교할 수 없다.")
    return 1 if miss else 0


# ★2026-08-22 — 표준 `load_dataset` 로 안 되는 3종의 우회 경로. **왜 안 되는지 함께 적는다.**
SPECIAL = {}


def _fetch_piqa(split):
    """`ybisk/piqa` 는 **로더 스크립트**라 datasets 3.x 가 거절한다
    (`RuntimeError: Dataset scripts are no longer supported`).
    ★HF 가 모든 스크립트 데이터셋에 대해 자동 생성해 두는 **`refs/convert/parquet`** 브랜치를 쓴다."""
    from datasets import load_dataset
    return load_dataset("ybisk/piqa", revision="refs/convert/parquet", split=split)


def _fetch_mmlu_redux(split):
    """`edinburgh-dawg/mmlu-redux-2.0` 에는 **`all` config 가 없다** — 과목별로 나뉘어 있다.
    ★57개(실제로는 30개) 과목을 **전부 받아 이어붙인다.** 과목 이름을 `subject` 로 남긴다."""
    from datasets import load_dataset, get_dataset_config_names, concatenate_datasets
    names = get_dataset_config_names("edinburgh-dawg/mmlu-redux-2.0")
    parts = []
    for n in names:
        d = load_dataset("edinburgh-dawg/mmlu-redux-2.0", n, split=split)
        parts.append(d.add_column("subject", [n] * len(d)))
    return concatenate_datasets(parts)


def _fetch_bfcl(split):
    """BFCL 레포는 **표준 데이터 디렉터리 구조가 아니다**
    (`DataFilesNotFoundError: No (supported) data files found`).
    ★`.json`(jsonl 내용) 파일을 **직접 나열해 받는다**. 여러 카테고리가 있으므로
    ⚠️**`simple`·`multiple` 등 AST 채점 가능한 것만** 고른다 — 실행 채점이 필요한
    `exec_*` 는 우리가 어차피 못 돌린다(모델 생성 코드를 실행하지 않는다)."""
    from huggingface_hub import list_repo_files, hf_hub_download
    repo = "gorilla-llm/Berkeley-Function-Calling-Leaderboard"
    files = [f for f in list_repo_files(repo, repo_type="dataset")
             if f.endswith(".json") and "possible_answer" not in f
             and any(k in f for k in ("simple", "multiple", "parallel"))
             and "exec" not in f]
    rows = []
    for f in sorted(files):
        fp = hf_hub_download(repo, f, repo_type="dataset")
        for ln in open(fp, encoding="utf-8"):
            ln = ln.strip()
            if ln:
                try:
                    r = json.loads(ln)
                    r["_src"] = f
                    rows.append(r)
                except json.JSONDecodeError:
                    pass
    if not rows:
        raise RuntimeError(f"{repo} 에서 읽을 수 있는 항목이 0개다 — 파일 목록 {files[:5]}")
    return rows


# ★★A01(2026-09-10) — **held-out 판을 명시해서 고른다.**
#   🚫종전에는 `held-out_v2.*` 를 문자열 정렬해 **마지막 폴더**를 잡았다. 문제 셋:
#     ① v2.8 이 도착한 순간 채점이 **조용히** 바뀌었다(캐시가 있으면 그것조차 안 바뀌었다).
#     ② 문자열 정렬은 **v2.10 에서 v2.9 뒤가 아니라 v2.1 뒤로 간다.**
#     ③ 어느 판으로 쟀는지가 **결과 어디에도 안 남았다.**
#   ★지금은 판마다 캐시가 따로 있고(`stage1_heldout.v2.7.jsonl`) 원본 해시가 meta 에 남는다.
_HELDOUT_VERSION = "latest"          # main() 이 `--heldout-version` 으로 덮어쓴다


def heldout_dirs():
    """디스크의 held-out 폴더를 **판 번호로** 정렬해 돌려준다(문자열 정렬이 아니다)."""
    import sys as _sys
    _sys.path.insert(0, str(ROOT / "scripts"))
    from check_heldout_defects import BASE                       # noqa: PLC0415
    out = {}
    for d in BASE.glob("held-out_v2.*"):
        if d.is_dir():
            out[d.name.split("held-out_v", 1)[1]] = d
    return dict(sorted(out.items(), key=lambda kv: [int(x) for x in kv[0].split(".")]))


def resolve_heldout_version(version):
    """`latest` 를 **실제 판 번호**로 바꾼다. 🚫모르는 판이면 거절한다(추측하지 않는다)."""
    dirs = heldout_dirs()
    if not dirs:
        raise RuntimeError("held-out_v2.* 폴더가 하나도 없다")
    v = str(version).lstrip("v")
    if v == "latest":
        return list(dirs)[-1], dirs[list(dirs)[-1]]
    if v not in dirs:
        raise RuntimeError(f"모르는 held-out 판 `{v}` — 디스크에 있는 것: {', '.join(dirs)}")
    return v, dirs[v]


def heldout_cache_path(version):
    return OUT / f"stage1_heldout.v{version}.jsonl"


def _sha256(path):
    import hashlib
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def heldout_source_file(folder):
    """그 폴더의 **본문 파일** 하나. 🚫둘 이상이면 고르지 않고 거절한다."""
    cands = [q for q in sorted(folder.glob("*benchmark*.json"))
             if "metadata" not in q.name]
    if len(cands) != 1:
        raise RuntimeError(f"{folder.name}: 본문 파일을 하나로 특정할 수 없다 "
                           f"({[q.name for q in cands]})")
    return cands[0]


def _fetch_stage1_heldout(split):
    """★로컬 held-out 을 **지정한 판에서** 읽어 온다. HF 를 안 탄다.

    🚫★**결함이 있는 판은 내보내지 않는다.** `check_heldout_defects` 의 **D1**(오답이 정답과
    같아짐)과 **D6**(정답이 둘)은 **정확한 검사**이고 둘 중 하나라도 0 이 아니면
    그 판으로 채점한 점수는 **뜻이 없다**. 그래서 여기서 막는다 —
    ⚠️게이트를 사람이 따로 돌기를 기대하지 않는다(함정 38: 인쇄와 판정이 갈라진다).

    ★**어느 판을 썼는지 반드시 인쇄한다.** 판이 바뀌면 점수가 바뀌는데 태그에는 안 남는다.
    """
    import sys as _sys
    _sys.path.insert(0, str(ROOT / "scripts"))
    from check_heldout_defects import load, scan, d6_two_answers   # noqa: PLC0415

    ver, folder = resolve_heldout_version(_HELDOUT_VERSION)
    _, recs = load(folder)
    d1 = scan(folder)[0] or []
    d6 = d6_two_answers(recs)
    print(f"  ★정본 판 = {folder.name}  ·  문항 {len(recs)}개  ·  D1 {len(d1)}건 · D6 {len(d6)}건"
          f"  (요청 `{_HELDOUT_VERSION}` -^> v{ver})")
    if d1 or d6:
        raise RuntimeError(
            f"🚫{folder.name} 은 D1 {len(d1)}건 · D6 {len(d6)}건이다 — "
            f"정답이 없거나 둘인 문항이 있는 판으로는 채점하지 않는다. "
            f"`python scripts/check_heldout_defects.py` 로 확인할 것")
    return recs


SFT_EVAL = (ROOT / "datasets" / "TinyDataset" / "SFT" / "eval"
            / "sft_fresh_v1_eval_300.canonical.jsonl")


def _fetch_sft_fresh_eval(split):
    """★SFT 채점셋을 로컬 canonical 에서 읽는다(2026-09-10(2차), 사용자 지시 3).

    🚫**HF 를 안 탄다.** 우리가 요청해서 받은 자료다.
    ★**규약을 들고 오는 필드가 없으면 거절한다** — `meta.grading` 이 채점기의 입력이다
    (없으면 채점기가 **전부 미채점**으로 끝나고 그것은 *"측정 0인데 exit 0"*(R19)이다).
    """
    if not SFT_EVAL.exists():
        raise RuntimeError(f"{SFT_EVAL} 가 없다 — SFT 코퍼스가 도착하지 않았다")
    rows = [json.loads(x) for x in
            SFT_EVAL.read_text(encoding="utf-8").splitlines() if x.strip()]
    if not rows:
        raise RuntimeError(f"{SFT_EVAL.name}: 레코드 0개")
    bad = [i for i, r in enumerate(rows)
           if not ((r.get("meta") or {}).get("grading") or {}).get("scoring_mode")]
    if bad:
        raise RuntimeError(
            f"🚫{SFT_EVAL.name}: `meta.grading.scoring_mode` 가 없는 레코드 {len(bad)}개"
            f"(첫 index {bad[0]}) — 규칙 채점의 입력이 없으면 전부 미채점이 된다")
    import collections
    _c = collections.Counter(r["meta"]["grading"]["scoring_mode"] for r in rows)
    print(f"  ★SFT 채점셋 = {SFT_EVAL.name}  ·  {len(rows)}행  ·  "
          + " · ".join(f"{k} {v}" for k, v in sorted(_c.items())))
    return rows


SPECIAL.update(piqa=_fetch_piqa, mmlu_redux=_fetch_mmlu_redux, bfcl_v3=_fetch_bfcl,
               sft_fresh_eval=_fetch_sft_fresh_eval,
               stage1_heldout=_fetch_stage1_heldout)


def heldout_stamp_path():
    """⚠️**레거시** — 2026-09-10 이전의 판 스탬프. 새 경로는 `.meta.json` 을 쓴다.
    옛 캐시(`stage1_heldout.jsonl`)가 남아 있을 때만 읽는다."""
    return OUT / "stage1_heldout.version"


def heldout_cache_state(version):
    """★판별 캐시가 **최신 원본에서 나왔는가**. 반환 `(stale, 사유)`.

    🚫종전 사고: v2.8(4,500문항)이 도착했는데 `stage1_heldout.jsonl` 은 v2.7 300문항인 채로
    남아 있었고 `fetch` 는 *"이미 있다"* 로 건너뛰었다. → **채점이 계속 v2.7 로 돌았다.**
    ★지금은 캐시가 판마다 따로 있으므로 *"덮어써서 사라지는"* 일 자체가 없고,
    남은 위험은 **같은 판 폴더의 내용이 바뀌는 것**뿐이라 원본 sha256 을 댄다.
    """
    try:
        ver, folder = resolve_heldout_version(version)
    except RuntimeError as e:
        return True, str(e)
    cache = heldout_cache_path(ver)
    meta = cache.with_suffix(".meta.json")
    if not cache.exists() or not meta.exists():
        return True, f"v{ver} 캐시 없음"
    try:
        m = json.loads(meta.read_text(encoding="utf-8"))
    except Exception:                                    # noqa: BLE001
        return True, f"v{ver} meta 를 못 읽었다"
    src = heldout_source_file(folder)
    if m.get("source_sha256") != _sha256(src):
        return True, f"v{ver} 원본이 캐시 생성 이후 바뀌었다"
    return False, f"v{ver} ({m.get('count')}문항)"


def fetch(name, hid, cfg, split):
    OUT.mkdir(parents=True, exist_ok=True)
    # ★★A01 — held-out 은 **판마다 다른 파일**에 쓴다. 그래야 v2.7 과 v2.8 이 공존하고
    #   점진 누적이 된다(사용자 지시 2026-09-10). 🚫한 파일을 덮어쓰면 옛 판이 사라진다.
    if name == "stage1_heldout":
        ver, folder = resolve_heldout_version(_HELDOUT_VERSION)
        p = heldout_cache_path(ver)
    else:
        p = OUT / f"{name}.jsonl"
    if name in SPECIAL:
        ds = SPECIAL[name](split)
    else:
        from datasets import load_dataset
        ds = load_dataset(hid, cfg, split=split) if cfg else load_dataset(hid, split=split)
    with p.open("w", encoding="utf-8") as f:
        for row in ds:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    if name == "stage1_heldout":
        src = heldout_source_file(folder)
        meta = {"schema": "tinylm.heldout-cache.v2", "version": ver,
                "source": str(src.relative_to(ROOT)).replace(chr(92), "/"),
                "source_sha256": _sha256(src), "cache_sha256": _sha256(p),
                "count": len(ds), "written": "fetch_bench_data.py"}
        p.with_suffix(".meta.json").write_bytes(
            json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))
        print(f"  ★판 기록: {p.name}  ·  meta {p.with_suffix('.meta.json').name}  "
              f"·  원본 sha {meta['source_sha256'][:12]}…")
    return p, len(ds)


def main():
    ap = argparse.ArgumentParser(description="벤치마크 데이터 내려받기 (GPU 0)")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="캐시가 있어도 다시 만든다 (★2026-09-10 신설 — 종전엔 방법이 없었다)")
    ap.add_argument("--heldout-version", default="latest",
                    help="★(A01) `stage1_heldout` 의 판. `2.7`·`2.8`·`latest`(기본). "
                         "판마다 캐시가 따로 생기므로 **둘을 함께 누적**할 수 있다")
    a = ap.parse_args()
    global _HELDOUT_VERSION
    _HELDOUT_VERSION = a.heldout_version

    if a.list:
        do_list()
        return 0
    if a.verify:
        return do_verify()
    if not (a.all or a.only):
        do_list()
        print("\n  ⚠️ 아무것도 받지 않았다. `--all` 또는 `--only <이름…>` 을 주세요.")
        return 2

    want = SPECS if a.all else [s for s in SPECS if s[0] in set(a.only)]
    import os
    banner(f"내려받기 {len(want)}종 — ★HF 게이트로 실패하면 **그것도 결과다. 지우지 않는다**", "#")
    # ★★2026-08-22 — **어디로 받는지를 먼저 인쇄한다.** 지난번엔 조용히 사용자 환경의
    #   HF_HOME 으로 갔고 사용자가 손으로 옮겨야 했다. 보이면 다시는 안 그런다.
    print(f"  HF_HOME          = {os.environ.get('HF_HOME')}")
    print(f"  HF_DATASETS_CACHE= {os.environ.get('HF_DATASETS_CACHE')}")
    print(f"  최종 저장 위치     = {OUT}")
    if str(ROOT) not in str(os.environ.get("HF_HOME", "")):
        print("  🚫★**HF_HOME 이 작업폴더 밖을 가리킨다** — `import tinylm` 이 안 먹었다. 중단.")
        return 3
    print()
    good, bad = [], []
    for n, hid, cfg, sp, sz, _note in want:
        if n == "stage1_heldout":
            stale, why = heldout_cache_state(a.heldout_version)
            try:
                _ver, _ = resolve_heldout_version(a.heldout_version)
                have = heldout_cache_path(_ver).exists()
            except RuntimeError:
                have = False
        else:
            stale, why, have = False, "", (OUT / f"{n}.jsonl").exists()
        if have and not a.force and not stale:
            print(f"  [건너뜀] {n} — 이미 있다"
                  + (f"  (판 `{why}`)" if n == "stage1_heldout" else ""))
            good.append((n, "이미 있음"))
            continue
        if stale and have:
            print(f"  ★{n} 캐시가 낡았다 — {why} → **다시 만든다**")
        try:
            p, cnt = fetch(n, hid, cfg, sp)
            flag = "✅" if (sz is None or cnt == sz) else "⚠️"
            print(f"  {flag} {n:<16} {cnt:>7}행 -> {p.name}"
                  + ("" if (sz is None or cnt == sz) else f"  (공식 {sz})"))
            good.append((n, cnt))
        except Exception as e:                                   # noqa: BLE001
            msg = str(e).splitlines()[0][:160]
            print(f"  🚫 {n:<16} 실패: {type(e).__name__}: {msg}")
            bad.append((n, f"{type(e).__name__}: {msg}"))

    banner("요약")
    print(f"  성공 {len(good)} / 실패 {len(bad)}")
    for n, why in bad:
        print(f"    🚫 {n}: {why}")
    if bad:
        print("\n  ⚠️★**실패 사유를 결과문서에 그대로 적는다.** 게이트·라이선스로 못 받은 것은 "
              "*'구현 안 함'* 이 아니라 *'접근 불가'* 다 — 둘은 다르다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
