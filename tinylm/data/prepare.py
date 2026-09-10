"""토큰화 + 크기별 재사용 캐시.

캐시 규칙
  - 실데이터: data_cache/{name}_{tokens}/ 에 train.bin·val.bin·meta.json 저장.
    요청 토큰 이상을 담은 같은 이름의 캐시가 이미 있으면 재생성 없이 재사용한다
    (가장 작은 상위 호환 캐시 선택). 그래서 architecture_v6 를 만들어도 재토큰화 불필요.
  - 토크나이저: data_cache/tok-{name}-{vocab}.json 에 이름당 하나만 두고 크기 간 공유.
  - 합성(synthetic): 판정 불가 데이터라 항상 재생성(캐시 안 함).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from .. import paths   # HF_HOME 등 설정을 위해 먼저 import
from ..config import VOCAB

DATA_CACHE = paths.DATA_CACHE

DATASETS = {
    # 이름: [(hf_id, config, split, text_key, 혼합 비율), ...]
    "ko-en": [("wikimedia/wikipedia", "20231101.ko", "train", "text", 0.5),
              ("HuggingFaceFW/fineweb-edu", "sample-10BT", "train", "text", 0.5)],
    # (P012) 큐레이션 대칭 믹스: ko=Korean-webtext-edu(FineWeb-Edu 방식 교육필터, Qwen3-80B 채점 ≥3.0),
    #   en=FineWeb-Edu. ko-en(원시 위키)과 공존하며 같은 토큰에서 데이터효율(bpb) 비교용.
    #   config=None(기본 subset), text_key="text". 비교는 반드시 같은 토크나이저로.
    "ko-edu-en": [("eliceai/korean-webtext-edu", None, "train", "text", 0.5),
                  ("HuggingFaceFW/fineweb-edu", "sample-10BT", "train", "text", 0.5)],
    "ko":    [("wikimedia/wikipedia", "20231101.ko", "train", "text", 1.0)],
    "en":    [("Salesforce/wikitext", "wikitext-103-raw-v1", "train", "text", 1.0)],
}


def tokenizer_path(name, vocab_size=VOCAB):
    return DATA_CACHE / f"tok-{name}-{vocab_size}.json"


class _SyntheticEncoding:
    """`tokenizers.Encoding` 중 우리가 쓰는 것만 흉내낸다 — `.ids` 와 ★`.offsets`.

    ★★2026-09-10(2차) — **`offsets` 를 더했다**(SFT 마스크 선결).
    `tinylm/data/sft.py` 가 **문자 구간 → 토큰 구간** 매핑에 `offsets` 를 쓴다.
    🚫스텁에 그것이 없으면 **합성 모드로 마스크 경로를 못 돌린다** =
    스모크가 그 축을 못 만진다(함정 37: 팔을 넣었다 ≠ 그 팔이 돌 수 있다).
    ⚠️`tokenizers.Encoding.offsets` 와 같이 **원문 문자열의 문자 인덱스** 반열림 구간이다.
    """

    __slots__ = ("ids", "offsets")

    def __init__(self, ids, offsets=None):
        self.ids = list(ids)
        self.offsets = list(offsets) if offsets is not None else [(0, 0)] * len(self.ids)


class SyntheticTokenizer:
    """★★2026-09-08(2차) 신설 — **`--data synthetic` 전용 스텁 토크나이저.**

    ## 왜 있나

    `prepare()` 는 `name == "synthetic"` 일 때 **BPE 를 학습하지 않는다**(위 §캐시 규칙).
    그래서 `data_cache/tok-synthetic-32768.json` 은 **설계상 영원히 없다.**
    그런데 체크포인트를 읽는 도구들은 전부 `Tokenizer.from_file(tokenizer_path(a.data))` 를
    **무조건** 부른다 — 즉 ★**합성 체크포인트를 스모크로 검사하는 것이 구조적으로 불가능했다.**

    🚫2026-09-08 스모크 팔 **[21c]**(LUT 배포 상주)가 정확히 여기서 죽었다:
    `Exception: 지정된 파일을 찾을 수 없습니다. (os error 2)`. 실험 큐 전체가 멈췄다.

    ## 무엇을 보증하나 / 무엇을 안 보증하나

    - ✅**토큰 id 는 합성 학습 데이터와 같은 대역**(`[0, 4096)`)에서 나온다 — `prepare()` 의
      `vocab_eff = min(VOCAB, 4096)` 과 맞춘 것이다. 모델이 한 번도 못 본 id 를 넣지 않는다.
    - ✅**결정적**이다. 같은 프롬프트는 항상 같은 id 열이 된다 → 로짓 동등성 게이트가 유효하다.
    - 🚫**의미가 없다.** 생성된 텍스트를 읽지 마라. 합성 체크포인트의 출력은 원래 의미가 없다.
    - 🚫★**실데이터 이름에는 절대 안 붙는다**(`load_tokenizer` 가 이름으로 가른다).
      실데이터의 토크나이저 파일이 없는 것은 **사고**이고, 사고를 스텁으로 덮으면
      *"측정 0인데 exit 0"*(R19)이 된다.
    """

    def __init__(self, vocab_size=VOCAB, span=4096):
        self.vocab_size = int(vocab_size)
        self.span = min(int(span), int(vocab_size))

    def encode(self, text):
        s = str(text)
        # ★결정적 해시. hash() 는 프로세스마다 달라지므로 쓰지 않는다.
        # ★★2026-09-10(2차) — 문자마다 그 문자의 UTF-8 바이트 수만큼 id 를 내고
        #   **그 id 들의 offsets 를 [i, i+1) 로** 준다(id 는 바이트 단위, 구간은 문자 단위).
        #   🚫id 열은 **바이트 하나 하나가 그대로** 나오던 종전과 **완전히 같다** — 순서가 같다.
        ids, offs, h = [], [], 0
        for i, ch in enumerate(s):
            for byte in ch.encode("utf-8"):
                h = (h * 1315423911 + byte) & 0xFFFFFFFF
                ids.append(h % self.span)
                offs.append((i, i + 1))
        if not ids:
            return _SyntheticEncoding([0], [(0, 0)])
        return _SyntheticEncoding(ids, offs)

    def decode(self, ids):
        return "<synthetic:" + " ".join(str(int(i)) for i in ids) + ">"

    def token_to_id(self, token):
        return None            # `<eos>` 가 없다 → 호출부가 stop_at_eos 를 끈다

    def get_vocab_size(self):
        return self.vocab_size


def load_tokenizer(name, vocab_size=VOCAB):
    """★**데이터 이름 하나로 토크나이저를 얻는 단일 소스**(R14).

    🚫`Tokenizer.from_file(str(tokenizer_path(...)))` 를 도구마다 새로 쓰지 않는다 —
    그렇게 하면 `synthetic` 처리가 도구 수만큼 갈라지고, 실제로 **스모크 팔 하나가
    그 갈라짐에 빠져 죽었다**(2026-09-08).

    - `synthetic` → `SyntheticTokenizer`(설계상 파일이 없다). **인쇄로 알린다.**
    - 그 외 → 실제 파일. 없으면 **`SystemExit(2)`** 로 즉시 죽는다(R19 — 조용한 폴백 금지).
    """
    if name == "synthetic":
        print("[tok] ★합성 데이터에는 토크나이저 파일이 없다 — 스텁을 쓴다"
              " (id 대역 [0,4096), 결정적). 🚫생성 텍스트는 읽지 마라.")
        return SyntheticTokenizer(vocab_size)
    p = tokenizer_path(name, vocab_size)
    if not p.exists():
        print(f"  🚫**토크나이저가 없다: {p}**")
        print(f"     `python run100m.py prepare --data {name} --tokens <N>` 를 먼저 돌린다.")
        raise SystemExit(2)
    from tokenizers import Tokenizer
    return Tokenizer.from_file(str(p))


def _stream(name, exhausted_cb=None):
    """★L4(2026-08-06, 결과 023 §9.3) — **소스 고갈을 조용히 넘기지 않는다.**

    종전에는 `StopIteration` 을 그냥 `continue` 했다. 한국어 위키가 약 300M 토큰에서
    소진되면 그 뒤로는 fineweb 만 나오는데 **아무 신호도 없었다** — `ko-en` 1200M 풀의
    실제 믹스가 **25.0 / 75.0** 이 된 것을 아무도 몰랐고, `prepare()` 의 말미 val 분할과
    만나 **val 셋에 한국어가 0.0%** 가 됐다(결과 006 §5.3).

    `exhausted_cb(i)` 는 소스 i 가 **처음** 고갈된 순간 1회 불린다.
    동작(뽑은 순서·내용)은 **종전과 완전히 같다** — 신호만 추가한다.
    """
    from datasets import load_dataset
    specs = DATASETS[name]
    iters, ratios = [], []
    for hf_id, cfg, split, key, r in specs:
        ds = load_dataset(hf_id, cfg, split=split, streaming=True)
        iters.append((iter(ds), key)); ratios.append(r)
    rng = np.random.default_rng(0)
    p = np.array(ratios) / sum(ratios)
    dead = set()
    while True:
        i = rng.choice(len(iters), p=p)
        it, key = iters[i]
        try:
            t = next(it)[key]
        except StopIteration:
            if i not in dead:
                dead.add(i)
                if exhausted_cb is not None:
                    exhausted_cb(i)
            if len(dead) == len(iters):
                return                      # 전부 고갈 — 무한루프 대신 정상 종료
            continue
        if t and len(t) > 64:
            # ★L1(2026-08-06): 소스 인덱스를 함께 낸다. `rng.choice` 는 **문서**를 고르므로
            #   문서 길이가 소스마다 다르면 **토큰 비율은 설정한 ratio 가 아니다.**
            #   지금까지 "한국어 50%" 라고 적어 온 모든 문서가 미확인이었다
            #   (docs/methods/07_corpus_selection.md §4.3). 이제 실측해서 meta 에 남긴다.
            yield t, i


def build_tokenizer(name, vocab_size=VOCAB):
    from tokenizers import ByteLevelBPETokenizer
    path = tokenizer_path(name, vocab_size)
    if path.exists():
        from tokenizers import Tokenizer
        print(f"[tok] 캐시 사용 {path}")
        return Tokenizer.from_file(str(path))
    print(f"[tok] {vocab_size} BPE 학습 중 (표본 20만 문서)...")
    tok = ByteLevelBPETokenizer()
    src = _stream(name)
    def sample():
        # ★_stream 이 (텍스트, 소스인덱스) 를 낸다(L1, 2026-08-06). 토크나이저는 텍스트만 쓴다.
        for i, (t, _src_i) in enumerate(src):
            if i >= 200_000:
                break
            yield t
    tok.train_from_iterator(sample(), vocab_size=vocab_size, min_frequency=2,
                            special_tokens=["<pad>", "<bos>", "<eos>"])
    DATA_CACHE.mkdir(parents=True, exist_ok=True)
    tok.save(str(path))
    print(f"[tok] 저장 {path}")
    return tok


def _find_reusable(name, n_tokens):
    """같은 name, tokens>=n_tokens 캐시 중 가장 작은 것(상위 호환)을 고른다."""
    best = None
    for d in sorted(DATA_CACHE.glob(f"{name}_*")):
        mp = d / "meta.json"
        if not (mp.exists() and (d / "train.bin").exists()):
            continue
        try:
            m = json.loads(mp.read_text())
        except Exception:
            continue
        if m.get("tokens", 0) >= n_tokens:
            if best is None or m["tokens"] < best["tokens"]:
                m["dir"] = str(d); best = m
    return best


def _ensure_bpt(meta):
    """bytes_per_token 이 없으면 val.bin 을 디코드해 계산·백필(토크나이저 무관 bpb용)."""
    if meta.get("bytes_per_token") or meta.get("data") == "synthetic":
        return meta
    try:
        from tokenizers import Tokenizer
        if meta.get("hf_tokenizer"):
            from ..hf_spec import load_hf_tokenizer
            tok, _ = load_hf_tokenizer(meta["hf_tokenizer"])
        else:
            tok = Tokenizer.from_file(str(tokenizer_path(meta["data"])))
        _td = np.dtype(meta.get("token_dtype", "uint16"))
        d = np.memmap(Path(meta["dir"]) / "val.bin", dtype=_td, mode="r")
        ids = d[:min(len(d), 500_000)].tolist()
        meta["bytes_per_token"] = len(tok.decode(ids).encode("utf-8")) / max(len(ids), 1)
        mp = Path(meta["dir"]) / "meta.json"
        m2 = json.loads(mp.read_text()); m2["bytes_per_token"] = meta["bytes_per_token"]
        mp.write_text(json.dumps(m2, indent=2))
        print(f"[bpb] bytes_per_token={meta['bytes_per_token']:.3f} 백필 완료")
    except Exception as e:
        print(f"[bpb] bytes_per_token 계산 실패(무시): {e}")
    return meta


def spam_signature(text, min_chars=50_000):
    """★P037 단계2 — 결과 018 이 실측한 **SEO 스팸 문서의 서명**. 참이면 버린다.

    `ko-edu-en` val 의 손실 53% 를 차지하던 거대 문서 7개는 길이 문제가 아니었다.
    자격증 덤프 판매 문구 + 무관한 소설 + **단어 중간에 삽입된 제품 키워드** 였고,
    언어모델이 예측할 수 있는 텍스트가 아니다. 손실 8~9.6(전체 6.09)이 난 이유가
    난이도가 아니라 **무작위성**이라는 뜻이다.

    측정된 서명(결과 018 §3.2) — 세 조건이 **함께** 성립할 때만 스팸으로 본다:
      · 대형            : min_chars 이상
      · 줄바꿈 ~0%      : 문서 전체가 한 줄
      · 줄 고유율 100%  : 반복 구조가 아니라 통짜 텍스트
    건강한 대조군(`ko-en`)은 줄바꿈 0.3~2.3% / 줄 고유율 94.8~99.6% 라 걸리지 않는다.

    ★길이 상한이 아니라 **내용 필터**인 이유: 길이로 자르면 스팸이 잘린 채 남는다.
    ★보수적으로 설계했다 — 애매하면 남긴다. 데이터를 지우는 쪽이 되돌리기 어렵다.
    """
    if len(text) < min_chars:
        return False
    lines = text.split("\n")
    nl_frac = (len(lines) - 1) / max(len(text), 1)
    uniq = len(set(lines)) / max(len(lines), 1)
    return nl_frac < 1e-4 and uniq >= 0.999


def prepare(name, n_tokens, val_frac=0.005, exact=False,
            doc_filter=False, doc_min_chars=50_000, hf_tok=None):
    """★P067(2026-08-22) — `hf_tok` 은 **외부 HF 모델 폴더 경로**다.

    주면 우리 BPE 대신 그 모델의 `tokenizer.json` 으로 토큰화하고
    ★**캐시 디렉터리에 `_tok-<이름>` 접미사**를 붙인다.
    🚫**기존 캐시를 덮어쓰지 않는다** — 토큰 id 가 완전히 다르므로 섞이면 재앙이다.
    ⚠️`uint16` 저장이므로 **어휘 65,536 을 넘으면 `uint32` 로 올린다**(아래 `_dt`).
    """
    """exact=True 면 상위호환(_find_reusable)을 쓰지 않고 **정확히 {name}_{n_tokens}** 캐시만 사용한다.
    (있으면 그 캐시, 없으면 정확히 그 크기로 신규 생성.) 토큰스윕처럼 '모든 예산이 같은 풀에서 샘플'해야
    할 때, 더 큰 캐시가 존재해도 특정 크기를 콕 집어 요청하는 용도."""
    n_tokens = int(n_tokens)
    DATA_CACHE.mkdir(parents=True, exist_ok=True)

    if name != "synthetic":
        if exact:
            _sfx = ("_filtered" if doc_filter else "")
            if hf_tok:
                _sfx += "_tok-" + Path(str(hf_tok)).name.replace("models--", "").replace("--", "-")
            d = DATA_CACHE / (f"{name}_{n_tokens}" + _sfx)
            if (d / "meta.json").exists() and (d / "train.bin").exists():
                m = json.loads((d / "meta.json").read_text()); m["dir"] = str(d)
                print(f"[data] 정확 캐시 사용(exact, 상위호환 무시): {n_tokens/1e6:.1f}M ({name}) -> {d}")
                return _ensure_bpt(m)
            print(f"[data] 정확 캐시({name}_{n_tokens}) 없음 → 정확히 그 크기로 신규 생성(상위호환 무시)")
        else:
            reuse = _find_reusable(name, n_tokens)
            if reuse:
                print(f"[data] 캐시 재사용: {reuse['tokens']/1e6:.1f}M 토큰 ({name}) "
                      f"-> {reuse['dir']}")
                return _ensure_bpt(reuse)

    # ★P037 단계2: 필터를 켜면 **다른 디렉터리**에 쓴다. 기존 캐시로 학습한 런들이
    #   자기 로그와 계속 비교 가능해야 하므로 덮어쓰지 않는다(결과 018 §5).
    suffix = "_filtered" if doc_filter else ""
    # ★P067 — 외부 토크나이저면 **완전히 다른 캐시**다. 접미사로 분리한다.
    if hf_tok:
        suffix += "_tok-" + Path(str(hf_tok)).name.replace("models--", "").replace("--", "-")
    cache_dir = DATA_CACHE / f"{name}_{n_tokens}{suffix}"
    cache_dir.mkdir(parents=True, exist_ok=True)

    if name == "synthetic":
        print(f"[data] 합성 토큰 {n_tokens/1e6:.1f}M 생성 (동작 확인용, 캐시 안 함)")
        rng = np.random.default_rng(0)
        vocab_eff = min(VOCAB, 4096)
        phrases = [rng.integers(0, vocab_eff, rng.integers(3, 12)) for _ in range(50_000)]
        out, n = [], 0
        while n < n_tokens:
            ph = phrases[rng.integers(len(phrases))]
            out.append(ph); n += len(ph)
        arr = np.concatenate(out)[:n_tokens].astype(np.uint16)
        _v, _dt = VOCAB, np.uint16
    else:
        if hf_tok:
            # ★P067 — 외부 토크나이저. **우리 BPE 를 학습하지 않는다.**
            from ..hf_spec import load_hf_tokenizer
            tok, _tokdir = load_hf_tokenizer(hf_tok)
            _v = tok.get_vocab_size()
            eos = (tok.token_to_id("<eos>") or tok.token_to_id("<|endoftext|>")
                   or tok.token_to_id("<end_of_turn>") or 1)
            print(f"[tok] ★외부 토크나이저 사용: {_tokdir}  어휘 {_v:,}  eos={eos}")
            print(f"[tok] ⚠️★이 캐시는 **기존 캐시와 직접 비교 불가**다 — 토큰 경계가 다르다"
                  f"(함정 2). 교차비교는 `scripts/common_bpb.py` 로만.")
        else:
            tok = build_tokenizer(name)
            _v = VOCAB
            eos = tok.token_to_id("<eos>") or 2
        # ★★P067 — **`uint16` 은 65,536 까지다.** Qwen3 151,936 · Gemma3 262,144 는 넘는다.
        #   넘는데 uint16 으로 쓰면 **토큰 id 가 조용히 wrap 된다** — 손실이 정상으로 보이고
        #   모델은 쓰레기를 배운다. 이 저장소가 가장 두려워하는 종류의 사고다.
        _dt = np.uint16 if _v <= 65536 else np.uint32
        if _dt is np.uint32:
            print(f"[tok] ★어휘 {_v:,} > 65,536 → 토큰 저장 dtype 을 **uint32** 로 올린다"
                  f"(캐시가 2배가 된다). meta.json 의 'token_dtype' 이 정본이다.")
        buf, total, total_bytes = [], 0, 0
        t0 = time.time()
        n_drop, n_drop_chars = 0, 0
        n_src = len(DATASETS[name])
        src_tok = [0] * n_src            # ★L1: 소스별 실제 토큰 수
        src_doc = [0] * n_src            # ★L1: 소스별 문서 수
        exhausted = {}                   # ★L4: 소스 -> 고갈 시점의 누적 토큰 수

        def _on_exhausted(i):
            exhausted[i] = total
            _hf = DATASETS[name][i][0]
            print(f"[mix] ★경고: 소스 고갈 — {_hf} 가 {total/1e6:.1f}M 토큰 지점에서 소진됐다.")
            print(f"[mix] ★이 지점 이후 **믹스 비율이 바뀐다**(남은 소스가 조용히 채운다). "
                  f"L4 결함, 결과 023 §9.3.")
            print(f"[mix] ★그리고 val 은 **스트림 말미 0.5%** 라 "
                  f"**val 셋의 구성도 함께 바뀐다**(L5, 결과 006 §5.3).")

        for text, src_i in _stream(name, exhausted_cb=_on_exhausted):
            if doc_filter and spam_signature(text, doc_min_chars):
                n_drop += 1
                n_drop_chars += len(text)
                continue
            ids = tok.encode(text).ids
            buf.append(np.array(ids + [eos], dtype=_dt))
            total += len(ids) + 1
            src_tok[src_i] += len(ids) + 1
            src_doc[src_i] += 1
            total_bytes += len(text.encode("utf-8"))
            if total >= n_tokens:
                break
            if total % 5_000_000 < 2000:
                print(f"  {total/1e6:>6.1f}M / {n_tokens/1e6:.0f}M  "
                      f"({total/max(time.time()-t0,1e-9)/1e3:.0f}K tok/s)")
        arr = np.concatenate(buf)[:n_tokens]
        # ★L4 후속: 전 소스가 고갈되면 `_stream()` 이 종료하므로 **요청보다 적은 캐시**가 만들어진다.
        #   `meta["tokens"]` 에는 실제 수가 들어가므로 재사용 판정은 옳지만, **디렉터리 이름이
        #   거짓말을 한다**(`ko_400000000` 인데 300M). 조용히 넘기지 않는다.
        if len(arr) < n_tokens:
            print(f"[data] ★★경고: 요청 {n_tokens/1e6:.1f}M 인데 **{len(arr)/1e6:.1f}M 만** 만들어졌다 "
                  f"— 전 소스 고갈(L4).")
            print(f"[data] ★디렉터리 이름({cache_dir.name})과 실제 토큰 수가 다르다. "
                  f"meta.json 의 'tokens' 가 정본이다.")
        # ★L1 실측 보고 — 설정 비율과 실제 토큰 비율이 다르면 여기서 드러난다.
        print("[mix] 소스별 실제 비율 (설정 비율은 DATASETS 의 ratio)")
        _specs = DATASETS[name]
        for _i, (_hf, _c, _sp, _k, _r) in enumerate(_specs):
            _tp = src_tok[_i] / max(total, 1)
            _dp = src_doc[_i] / max(sum(src_doc), 1)
            _flag = "  <-- 설정과 5%p 이상 차이" if abs(_tp - _r / sum(x[4] for x in _specs)) > 0.05 else ""
            print(f"      {_hf:38} 설정 {_r:.2f} | 문서 {_dp:6.1%} | ★토큰 {_tp:6.1%}"
                  f" ({src_tok[_i]/1e6:.1f}M){_flag}")
        print("      ★문서 비율과 토큰 비율이 다른 이유: rng 가 **문서**를 고르는데 "
              "소스마다 문서 길이가 다르다(L1).")
        if exhausted:
            print("      ★★L4: 아래 소스가 고갈됐다 — **이 캐시의 믹스는 풀 크기의 함수다.**")
            for _i, _at in sorted(exhausted.items()):
                print(f"         {DATASETS[name][_i][0]:38} 고갈 지점 {_at/1e6:.1f}M 토큰")
            print("      ★다른 풀 크기로 만든 캐시와 **비교하지 말 것**(결과 006 §5.4).")
        if doc_filter:
            print(f"[filter] 스팸 서명으로 제외한 문서 {n_drop:,}개 / {n_drop_chars/1e6:.1f}M 자")
            print(f"[filter] 서명 = 길이 {doc_min_chars:,}자 이상 AND 줄바꿈 ~0% AND 줄 고유율 100%")
            print(f"[filter] ★제외율이 몇 퍼센트를 넘으면 무엇이 걸렸는지 먼저 확인할 것"
                  f"(결과 018 §5).")

    n_val = max(1, int(len(arr) * val_frac))
    arr[:-n_val].tofile(cache_dir / "train.bin")
    arr[-n_val:].tofile(cache_dir / "val.bin")
    meta = {"data": name, "tokens": int(len(arr)),
            "vocab": (_v if name != "synthetic" else VOCAB),
            "token_dtype": str(np.dtype(_dt if name != "synthetic" else np.uint16).name),
            "hf_tokenizer": (str(hf_tok) if hf_tok else None),
            "train": int(len(arr) - n_val), "val": int(n_val), "dir": str(cache_dir)}
    if name != "synthetic":
        meta["bytes_per_token"] = total_bytes / max(total, 1)
        # ★2026-08-06(결과 006 §5.5) — `bytes_per_token` 은 **스트림 전체** 평균인데
        #   `bpb = loss / ln2 / bytes_per_token` 의 loss 는 **val 에서만** 잰다. 구성이 다르면
        #   bpb 가 최대 1.9% 틀어지고, 그 크기는 bpb 분해능(0.008)의 3배다. → val 기준도 함께 남긴다.
        #   기존 필드는 **건드리지 않는다**(구 로그·구 문서와의 연속성).
        try:
            from tokenizers import Tokenizer as _Tok
            _t = _Tok.from_file(str(tokenizer_path(name)))
            _v = arr[-n_val:].tolist()
            meta["bytes_per_token_val"] = len(_t.decode(_v).encode("utf-8")) / max(len(_v), 1)
            print(f"[bpb] bytes_per_token  스트림 {meta['bytes_per_token']:.4f} / "
                  f"★val {meta['bytes_per_token_val']:.4f} "
                  f"(차이 {100*(meta['bytes_per_token_val']/meta['bytes_per_token']-1):+.1f}%)")
        except Exception as _e:
            print(f"[bpb] bytes_per_token_val 계산 실패(무시): {_e}")
        meta["doc_filter"] = bool(doc_filter)
        # ★L4: 고갈 기록. 없으면 빈 dict = "이 풀에서는 고갈 없음" 이라는 정보다.
        meta["mix_exhausted"] = {str(k): int(v) for k, v in exhausted.items()}
        # ★L1: 소스별 실측 비율을 meta 에 남긴다 — 이후 어떤 문서도 "50%" 를 추정으로 쓰지 않는다.
        meta["mix_sources"] = [x[0] for x in DATASETS[name]]
        meta["mix_ratio_cfg"] = [x[4] for x in DATASETS[name]]
        meta["mix_tokens"] = src_tok
        meta["mix_docs"] = src_doc
        meta["mix_token_frac"] = [t / max(total, 1) for t in src_tok]
        if doc_filter:
            meta["doc_min_chars"] = int(doc_min_chars)
            meta["docs_dropped"] = int(n_drop)
    (cache_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"[data] train {meta['train']/1e6:.1f}M / val {meta['val']/1e3:.0f}K 토큰 저장 -> {cache_dir}")
    return meta
