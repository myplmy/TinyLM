"""★실험 배치 **드라이런** — 이 배치를 돌리면 **어떤 조건으로** 돌아가는가. (2026-09-02 신설)

## 왜 만들었나 — 3.6시간을 잃은 사고 하나

`run_P052_stage4` 가 `--cla-group 1` 을 **빠뜨렸다.** 프리셋 `m100R1c` 의 기본값은 **2** 다.
그래서 `mC_cla1_ag4_r20_s3` 라는 이름으로 **cla2 모델이 3.6시간** 학습됐다(결과 039 §11).

기존 그물이 왜 다 통과시켰나:

| 게이트 | 무엇을 보나 | 왜 못 잡았나 |
|---|---|---|
| `check_batch_flags` | 플래그가 **파서에 있는가** | 🚫**없는 플래그**를 잡지 이 배치가 **안 쓴 플래그**는 모른다 |
| `lint_bat` | 배치 **문법** | 문법은 옳았다 |
| `check_run_registry` | 태그 **충돌·중복** | 태그는 안 겹쳤다 |
| `check_tag_arch` | 태그 주장 ↔ **json 실제값** | ✅잡는다 — **다만 런이 끝난 뒤에** |

★**빠진 자리가 하나 있었다: "돌리기 전에, 프리셋 기본값까지 넣은 유효 조건"** 을
아무도 인쇄하지 않았다. 이 도구가 그것을 인쇄한다.

## 무엇을 인쇄하나

각 `run100m.py train` 호출마다:

1. **명령이 준 값 / 프리셋 기본값 / 유효값** — 세 칸.
   명령이 침묵했는데 유효값이 중립이 아니면 `프리셋이 정함` 이라 적고,
   ★그중 **KV·품질 귀속을 조용히 바꾸는 축**(`cla_group`·`attn_group`·`train_repeat`)만
   따로 요약한다. E12 가 정확히 그 요약의 한 줄이다.
2. **파생량** — 학습토큰 · `M` · 방문 수 · `M×방문` 과 `--no-ckpt` 예산 · KV 엔트리 ·
   KV MiB(bf16 @ seq 1024).
3. **태그 주장 대조** — `check_tag_arch` 와 **같은 문법**을 쓴다(함정 18: 한 곳에서만 정의).

## 무엇을 안 하나 (정직하게)

- 🚫**학습을 흉내내지 않는다.** `trainer.py` 의 오버라이드 **다섯 줄**만 반영한다
  (`cla_group` · `mlp_group`(tied 만) · `attn_group`(tied 만) · `train_repeat` · `ckpt`).
  그 다섯 줄이 `trainer.py` 에 그대로 있는지 **매번 확인**하고, 모양이 바뀌면 경고한다.
- 🚫**품질을 예측하지 않는다.** 조건만 인쇄한다.
- 🚫**torch·GPU 를 쓰지 않는다.** `tinylm/config.py` 를 파일에서 직접 로드한다.

사용:

    python scripts/dryrun_batch.py                       # 최상위 run_*.bat 전부
    python scripts/dryrun_batch.py run_P079_stage3.bat   # 하나만
    python scripts/dryrun_batch.py --strict              # 태그 불일치·예산 초과면 exit 1
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_tag_arch import claims                        # noqa: E402  (함정 18)

# ★`check_batch_flags` 와 같은 호출 추출 규약. 바꿀 때는 둘을 함께 본다.
CALL = re.compile(r"^\s*python\s+(?:scripts\\runlog\.py[^\n]*?--\s+python\s+)?"
                  r"([\w\\/.-]+\.py)\s+(.*)$", re.I | re.M)

# `--no-ckpt` 예산. 정본은 `lint_bat.NOCKPT_MAX_MV` 이고 여기서는 **읽기만** 한다.
NOCKPT_MAX_MV = 294_912

# ★판정 호출 검사의 면제: 체크포인트가 **하나도 없는 기계**(새 클론·정리 직후)에서는
#   전부 빨간불이 된다. 영구 적색이면 게이트가 아니다(2026-09-06 §6.3 과 같은 이유).
_CKPT_ANY = any((ROOT / 'runs' / 'ckpt').glob('*.pt'))

# ★인쇄할 축과 **중립값**(= "이 축을 안 건드렸다" 는 값).
#   중립값이 아닌데 명령이 침묵하면 '프리셋이 정함' 이라 적는다.
AXES: list[tuple[str, str, object]] = [
    # (cfg 필드, 명령줄 플래그, 중립값)
    ("mlp_group", "--mlp-group", 1),
    ("cla_group", "--cla-group", 1),
    ("attn_group", "--attn-group", 1),
    ("train_repeat", "--train-repeat", 1.0),
    ("grad_ckpt", "--no-ckpt", True),
    ("sparse34", "--sparse34", False),
    ("mlp_film", "--mlp-film", False),
    ("emb_rank", "--emb-rank", None),
    ("kv_dtype", "--kv-dtype", "fp32"),
]

_PRESETS = None


def presets():
    """`tinylm/config.py` 를 **torch 없이** 파일에서 직접 로드한다(lint_bat 와 같은 수법)."""
    global _PRESETS
    if _PRESETS is None:
        try:
            import importlib.util
            name = "_tinylm_cfg_for_dryrun"
            spec = importlib.util.spec_from_file_location(
                name, ROOT / "tinylm" / "config.py")
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod                # @dataclass 가 이걸 읽는다
            spec.loader.exec_module(mod)
            _PRESETS = mod
        except Exception as e:                                # noqa: BLE001
            print(f"  [!] config.py 로드 실패: {e}")
            _PRESETS = False
    return _PRESETS


# ── cli.py 의 파서에서 "값을 먹는 플래그" 표를 만든다 ────────────────────────
def flag_table():
    """`--flag` -> True(값을 먹는다) / False(store_true).

    🚫여기서 목록을 손으로 적지 않는다 — `cli.py` 가 정본이다(함정 18).
    """
    src = (ROOT / "tinylm" / "cli.py").read_text(encoding="utf-8", errors="replace")
    out = {}
    for m in re.finditer(r'add_argument\(\s*"(--[a-z0-9-]+)"(.*?)\)\s*$',
                         src, re.M | re.S):
        name, rest = m.group(1), m.group(2)[:400]
        out[name] = "store_true" not in rest and "store_false" not in rest
    return out


def parse_cmd(rest: str, takes: dict) -> dict:
    """명령줄 조각에서 실제로 준 값을 뽑는다. 따옴표 안은 데이터라 먼저 지운다."""
    rest = re.sub(r'"[^"]*"', " ", rest)
    toks = rest.split()
    got: dict[str, object] = {}
    i = 0
    while i < len(toks):
        t = toks[i]
        if t.startswith("--"):
            if takes.get(t, True) and i + 1 < len(toks) and not toks[i + 1].startswith("--"):
                got[t] = toks[i + 1]
                i += 2
                continue
            got[t] = True
        i += 1
    return got


def _num(v, cast=float):
    try:
        return cast(v)
    except Exception:                                         # noqa: BLE001
        return None


def trainer_override_shape_ok() -> list[str]:
    """`trainer.py` 가 아직 이 도구가 가정한 다섯 줄대로 오버라이드하는가.

    ★모양이 바뀌면 **이 도구가 조용히 틀린다.** 그래서 매번 확인한다(함정 18).
    """
    src = (ROOT / "tinylm" / "train" / "trainer.py").read_text(
        encoding="utf-8", errors="replace")
    want = [
        ("cla_group", r"if cla_group is not None:"),
        ("mlp_group", r"if mlp_group and arch == \"tied\":"),
        ("attn_group", r"if attn_group is not None and arch == \"tied\":"),
        ("train_repeat", r"if train_repeat is not None:"),
        ("ckpt", r"build_config\(preset, arch, seq, ckpt\)"),
    ]
    return [n for n, pat in want if not re.search(pat, src)]


def analyse(cmd: str, takes: dict) -> dict:
    got = parse_cmd(cmd, takes)
    cfgmod = presets()
    preset = got.get("--preset", "m100")
    arch = got.get("--arch", "tied")
    seq = _num(got.get("--seq", 1024), int) or 1024
    ckpt = "--no-ckpt" not in got

    base = eff = None
    if cfgmod:
        try:
            base = cfgmod.build_config(preset, arch, seq, True)   # 프리셋 기본(ckpt ON)
            eff = cfgmod.build_config(preset, arch, seq, ckpt)
            # ★trainer.py 의 오버라이드 다섯 줄을 그대로 반영한다
            if "--cla-group" in got:
                eff.cla_group = _num(got["--cla-group"], int)
            if "--mlp-group" in got and arch == "tied":
                eff.mlp_group = _num(got["--mlp-group"], int)
            if "--attn-group" in got and arch == "tied":
                eff.attn_group = _num(got["--attn-group"], int)
            if "--train-repeat" in got:
                eff.train_repeat = _num(got["--train-repeat"])
            if "--kv-dtype" in got:
                eff.kv_dtype = got["--kv-dtype"]
            if "--sparse34" in got:
                eff.sparse34 = True
            if "--mlp-film" in got:
                eff.mlp_film = True
            if "--emb-rank" in got:
                eff.emb_rank = _num(got["--emb-rank"], int)
        except Exception as e:                                    # noqa: BLE001
            return {"err": f"build_config 실패: {e}", "got": got, "preset": preset}

    return {"got": got, "preset": preset, "arch": arch, "seq": seq,
            "ckpt": ckpt, "base": base, "eff": eff,
            "tag": got.get("--tag"), "err": None}


# ★★명령이 침묵했을 때 **KV 나 품질 귀속을 조용히 바꾸는** 축.
#   E12 가 정확히 이 목록의 `cla_group` 이었다. 나머지 축은 인쇄만 하고 요약하지 않는다.
SILENT_COSTLY = ("cla_group", "attn_group", "train_repeat")


def show(r: dict, strict_hits: list):
    got, base, eff = r["got"], r["base"], r["eff"]
    tag = r["tag"] or "(태그 없음)"
    print(f"\n  ── {tag}   preset={r['preset']}  arch={r['arch']}  seq={r['seq']}"
          f"  grad_ckpt={r['ckpt']}")
    if r["err"]:
        print(f"     🚫{r['err']}")
        return
    if eff is None:
        print("     [!] config 를 못 읽어 유효값을 못 낸다")
        return

    silent: list[str] = []
    print(f"     {'축':<14}{'명령':>12}{'프리셋기본':>12}{'유효':>12}   비고")
    print("     " + "-" * 74)
    for field, flag, neutral in AXES:
        b = getattr(base, field, None)
        e = getattr(eff, field, None)
        if field == "grad_ckpt":
            b, e = True, r["ckpt"]
        given = got.get(flag, "—")
        if given is True:
            given = "(켬)"
        note = ""
        if field in ("mlp_group",) and r["arch"] == "dense":
            # dense 는 `tie_mlp=False` 라 이 필드를 안 쓴다 — 값이 남아 있을 뿐이다.
            note = "(dense: 미사용)"
        elif flag not in got and e != neutral:
            # ★담담하게 적는다. 타잉 프리셋의 `mlp_group=8` 은 사고가 아니라 설계다 —
            #   전부 ★를 붙이면 경보 피로가 생겨 진짜 한 줄을 가린다.
            note = "프리셋이 정함"
            if field in SILENT_COSTLY:
                silent.append(field)
        print(f"     {field:<14}{str(given):>12}{str(b):>12}{str(e):>12}   {note}")

    # ── 파생량 ────────────────────────────────────────────────────────────
    steps = _num(got.get("--steps", 3000), int) or 0
    mb = _num(got.get("--micro-bs", 8), int) or 0
    ac = _num(got.get("--accum", 8), int) or 0
    seq = r["seq"]
    M = mb * seq
    # ★★2026-09-07 — **`repeat_mode` 를 반영한다.** 종전 식은 `uniform` 전용이라
    #   `block`·`progressive` 에서 방문을 **과대 계산**했다(d14 block 실제 16 인데 24 로 인쇄).
    #   과대라 `--no-ckpt` 예산에는 보수적이지만, **인쇄한 수가 틀린 것**은 함정 4 다 —
    #   그 수를 사람이 *"속도 비용"* 으로 읽는다(방문 19 가 15 tok/s 경계다).
    #   ★`transformer._repeat_schedule` 과 **같은 분기**를 쓴다(함정 18: 한 곳에서만 정의).
    visits = _visits(eff, got)
    kv_ent = visits // max(int(eff.cla_group), 1)
    tok = steps * mb * ac * seq
    _mode = got.get("--repeat-mode", "uniform")
    print()
    print(f"     학습토큰  {tok / 1e6:,.1f}M  = {steps} x {mb} x {ac} x {seq}")
    print(f"     M         {M:,}  (micro_bs x seq)   방문 {visits}회  "
          f"KV 엔트리 {kv_ent}개" + (f"  [repeat_mode={_mode}]" if _mode != "uniform" else ""))
    if float(eff.train_repeat) != 1.0 or _mode != "uniform":
        # ★속도 모형은 결과 014 §16.2 실측(같은 날 네 점, R² 0.9866).
        _ms = 6.786 + 3.1379 * visits
        print(f"     ⚙속도     {_ms:.1f} ms/token = **{1000/_ms:.2f} tok/s** "
              f"(t = 6.79 + 3.138 x 방문, 결과 014 §16.2) -> "
              f"{'바닥 안' if 1000/_ms >= 15 else '⚠️15 tok/s 미달 — **정보다**'}")
        if 1000 / _ms < 15:
            # ★★2026-09-08 사용자 지시 2A — **속도로 실험을 닫지 않는다.**
            #   🚫종전 인쇄는 `🚫15 tok/s 미달` 이라 **판정처럼 읽혔다**. 속도는 지금
            #   필수가 아니고(1순위는 상주와 지능), LUT 커널·`block` 재귀·폭 축이
            #   전부 미측정이라 **오늘의 tok/s 로 축을 닫으면 안 잰 길을 닫는 것**이다.
            print("               🚫**이 줄로 실험을 취소하지 않는다**(사용자 지시 2A, "
                  "기준표 B.23.1) — 속도는 2순위이고 남은 길이 셋 있다")
    # ★KV 는 `dim` 이 아니라 **`kv_dim`(GQA)** 이다. 실측 대조:
    #   mC_initonly_nc 엔트리 10개 -> 7.5 MiB @ bf16 seq1024 (결과 067 §단계0b)
    kvd = getattr(eff, "kv_dim", None)
    kvmb = kv_ent * 2 * kvd * 2 * 1024 / (1024 * 1024) if kvd else 0
    if kvmb:
        print(f"     KV        {kvmb:.1f} MiB @ seq 1024 · bf16 "
              f"(엔트리 {kv_ent} x K/V 2벌 x kv_dim {kvd} x 2B)")
    if silent:
        print()
        print(f"     ★**명령이 침묵한 비용 축**: {', '.join(silent)}")
        print("        이 축들은 KV 엔트리나 품질 귀속을 바꾼다. 프리셋 기본값을")
        print("        **의도한 것이 맞는지** 확인한다 — 결과 039 §11 이 여기서 났다.")
    if not r["ckpt"]:
        mv = M * visits
        ok = mv <= NOCKPT_MAX_MV
        print(f"     --no-ckpt  M x 방문 = {mv:,}  vs 확인된 최대 {NOCKPT_MAX_MV:,}  "
              f"-> {'✅ 예산 안' if ok else '🚫 예산 초과 — OOM 위험'}")
        if not ok:
            strict_hits.append(f"{tag}: M x 방문 {mv:,} > {NOCKPT_MAX_MV:,}")

    # ── 태그 주장 대조 ────────────────────────────────────────────────────
    if r["tag"]:
        cl = claims(r["tag"])
        if cl:
            print()
            for tok_, field, want in cl:
                have = getattr(eff, field, None)
                if field == "grad_ckpt":
                    have = r["ckpt"]
                if field == "kd":
                    have = "--kd" in got
                ok = (have == want)
                print(f"     태그 `{tok_}` 주장 {field}={want}  실제 {have}  "
                      f"{'✅' if ok else '🚫★불일치'}")
                if not ok:
                    strict_hits.append(
                        f"{tag}: 태그가 {field}={want} 를 주장하는데 유효값은 {have}")

    # ── ★★부모·교사 체크포인트가 **읽히는가** (2026-09-07 신설) ──────────────
    #
    #  🚫사고: `--tokens 600M --init-from` 이 `m100s8_ko-en_600M_dense.pt` 를 찾다 즉사했다.
    #  부모 dense 는 300M 로만 학습돼 있다. **4팔이 죽었다**(P062 단계9 3팔 + P005 단계2 4팔째).
    #  ★2026-09-06 에 **판정** 호출에 붙인 그물과 **같은 결함**인데 **학습** 호출에는 안 붙였다.
    #  → 여기서 같은 `_resolve_ckpt_names` 를 쓴다(함정 18: 한 곳에서만 정의).
    #  ⚠️면제 셋: `runs/ckpt/` 가 비면 건너뛴다 · 큐 앞 배치가 만드는 태그는 선결 ·
    #     `--init-from` 도 `--kd` 도 없으면 읽을 것이 없다.
    if _CKPT_ANY:
        _data = got.get("--data", "ko-en")
        _tokstr = _norm_tok(got.get("--tokens", "300M"))
        _ctok = _norm_tok(got.get("--ckpt-tokens")) or _tokstr
        srcs = []
        if got.get("--init-from-tag"):
            srcs.append(("부모초기화", got["--init-from-tag"]))
        elif "--init-from" in got:
            srcs.append(("부모초기화", "dense"))
        if "--kd" in got:
            srcs.append(("KD 교사", got.get("--kd-teacher-tag")
                         or ("dense_best" if "--kd-best" in got else "dense")))
        if srcs:
            print()
            made = trained_tags()
            for what, stag in srcs:
                hit, tried = _resolve_ckpt_names(r["preset"], _data, _ctok, stag)
                if hit:
                    print(f"     {what} 원본  ✅{hit}")
                    continue
                if stag in made:
                    print(f"     {what} 원본  ⏳{stag} — 아직 없다. "
                          f"**{made[stag]} 가 만든다**(선결)")
                    continue
                print(f"     {what} 원본  🚫**해석 실패**. 시도: "
                      + (", ".join(tried) or "(없음)"))
                alt = sorted(p.name for p in (ROOT / "runs" / "ckpt")
                             .glob(f"*_{_data}_*_{stag}.pt"))
                if alt:
                    print("       ★같은 태그가 **다른 토큰 칸**에 있다: "
                          + ", ".join(alt[:3]))
                    print("         -> `--ckpt-tokens <그 칸>` 을 준다. "
                          "`--tokens` 는 데이터 캐시이자 **쓰는** 이름, "
                          "`--ckpt-tokens` 는 **읽는** 이름이다")
                strict_hits.append(
                    f"{tag}: {what} 원본 미해석 {stag} (tokens={_ctok})")




# ─────────────────────────────────────────────────────────────────────────
# ★★판정 호출 드라이런 (2026-09-06 신설) — R23 이 적어 둔 구멍
# ─────────────────────────────────────────────────────────────────────────
#
#  R23 본문: *셋 중 어느 것도 플래그의 **규약**은 못 잡는다. `dryrun_batch` 는
#  **학습** 호출만 읽는데, 죽은 것은 **판정** 호출이었다.*
#
#  2026-09-06 에 정확히 그 자리에서 두 번 죽었다:
#
#      [건너뜀] 체크포인트 없음: m100s8_ko-en_600M_d12_cla2_r20.pt
#
#  `paired_eval --tokens 600M` 의 `600M` 이 **val 캐시 크기**이자 **체크포인트 파일명**이라
#  held-out 규약(pool_tokens <= X)과 파일명 규약이 충돌했다. `P016 Stage4`(0.1h)와
#  `P062 Stage7 [2/2]`(1.2h 학습 뒤의 판정)이 둘 다 exit 2 로 끝나 **판정이 비었다.**
#
#  🚫새 게이트를 만들지 않았다 — **있는 게이트의 범위를 넓혔다**(2026-09-06 §6.2 교훈).
#  ⚠️면제 둘을 함께 넣었다:
#    · `runs/ckpt/` 가 비어 있으면 통째로 건너뛴다(새 클론에서 전부 빨간불이 된다)
#    · `--live-only` 가 이미 `-done` 을 뺀다 — 끝난 배치는 체크포인트가 정리됐을 수 있다


_TRAINED_TAGS = None


def trained_tags():
    # ★면제용: **어떤 배치가 `--tag X` 로 학습하는가.** 큐의 앞 배치가 만들 태그를
    #   뒤 배치가 판정하는 것은 결함이 아니라 **선결**이다(2026-09-06 §6.2: 범위를
    #   넓히면 면제를 함께 넣는다). 🚫'아직 없다' 와 '영영 없다' 를 가른다.
    global _TRAINED_TAGS
    if _TRAINED_TAGS is None:
        out = {}
        pats = list(ROOT.glob('run_*.bat')) + list((ROOT / 'scripts' / 'batch').glob('*.bat'))
        for f in pats:
            try:
                txt = f.read_text(encoding='utf-8', errors='replace')
            except OSError:
                continue
            for m in CALL.finditer(txt):
                if Path(m.group(1).replace(chr(92), '/')).name != 'run100m.py':
                    continue
                for t in re.findall(r'--tag\s+(\S+)', m.group(2)):
                    out.setdefault(t, f.name)
        _TRAINED_TAGS = out
    return _TRAINED_TAGS

def _visits(eff, got):
    """`transformer._repeat_schedule` 과 **같은 분기**로 방문 수를 센다.

    🚫종전 한 줄(`p + round(m*R) + coda`)은 `uniform` 전용이었다 —
    `block` 은 **한 그룹만** 반복하고 `progressive` 는 깊이에 따라 는다.
    ⚠️여기서 다르게 세면 게이트가 **틀린 속도**를 인쇄한다(함정 4·18).
    """
    p = int(eff.n_prelude)
    m = int(eff.n_middle)
    g = max(int(getattr(eff, "mlp_group", 1) or 1), 1)
    coda = int(eff.n_coda)
    R = float(eff.train_repeat)
    mode = str(got.get("--repeat-mode", "uniform") or "uniform")
    reps = int(round(R))
    if R == 1.0:
        return p + m + coda
    if mode == "block":
        b = _num(got.get("--repeat-block", 0), int) or 0
        lo, hi = p + b * g, p + (b + 1) * g
        n = sum(reps if lo <= i < hi else 1 for i in range(p, p + m))
    elif mode == "inplace":
        n = m * reps
    elif mode == "progressive":
        n = sum(max(1, int(round(1 + (reps - 1) * (k / max(m - 1, 1)))))
                for k in range(m))
    else:                                   # uniform
        n = m * reps
    return p + n + coda


def _norm_tok(s):
    """`cli.py` 의 `tokstr` 규약을 **그대로** 따라간다 — `1.2B` 도 `600M` 도 `NNNM` 이 된다.

    🚫여기서 다르게 정규화하면 게이트가 통과시키고 런이 죽는다(함정 18).
    """
    if not s or s is True:
        return None
    s = str(s)
    try:
        n = int(float(s.rstrip("MmBb")) * (1e9 if s[-1] in "Bb" else 1e6))
    except ValueError:
        return s
    return f"{n // 1_000_000}M" if n >= 10 ** 6 else str(n)


def _preset_parent():
    mod = presets()
    return dict(getattr(mod, "PRESET_PARENT", {}) or {}) if mod else {}


def _resolve_ckpt_names(preset, data, tok, tag):
    # `paths.resolve_ckpt` 와 **같은 순서**로 후보를 만든다(함정 18: 한 곳에서만 정의).
    ck = ROOT / "runs" / "ckpt"
    tried = []
    for pr in [preset, _preset_parent().get(preset)]:
        if not pr:
            continue
        cand = ck / f"{pr}_{data}_{tok}_{tag}.pt"
        tried.append(cand.name)
        if cand.exists():
            return cand.name, tried
    hits = sorted(ck.glob(f"*_{data}_{tok}_{tag}.pt"))
    if len(hits) == 1:
        return hits[0].name, tried
    if len(hits) > 1:
        return None, tried + [f"(전역 검색 {len(hits)}건 — 사람이 정한다)"]
    return None, tried


def _judge_val(rest, flag, default=None):
    m = re.search(re.escape(flag) + r"\s+([^\s-][\S]*)", rest)
    return m.group(1) if m else default


def _judge_model_spec(raw, default_preset):
    """판정 도구의 모델 표기 하나를 ``(태그, 프리셋)`` 으로 푼다.

    보통 ``--models`` 는 태그만 받지만 census 는 깊이가 다른 모델을 한
    호출에 섞기 위해 ``태그=프리셋`` 을 받는다. 종전 코드는 등호의
    오른쪽을 무조건 태그로 읽어 여섯 체크포인트를 전부 미해석했다.
    알려진 프리셋 집합을 기준으로 방향을 판별하고, 어느 쪽도 프리셋이
    아니면 종전 규약(오른쪽이 태그)으로 되돌아간다.
    """
    left, sep, right = raw.partition("=")
    if not sep:
        return left.split("#", 1)[0], default_preset
    mod = presets()
    known = set(getattr(mod, "PRESETS", {}) or {}) if mod else set()
    if right in known and left not in known:       # census: tag=preset
        tag, preset = left, right
    elif left in known and right not in known:     # 허용: preset=tag
        tag, preset = right, left
    else:                                           # 종전 동작 보존
        tag, preset = right, default_preset
    return tag.split("#", 1)[0], preset


def judge_calls(text):
    # `--models` 를 받는 비학습 호출. 🚫도구 이름 목록을 손으로 적지 않는다.
    out = []
    for m in CALL.finditer(text):
        script, rest = m.group(1), m.group(2)
        name = Path(script.replace(chr(92), "/")).name
        if name == "run100m.py" or "--models" not in rest:
            continue
        out.append((name, rest))
    return out


def show_judge(name, rest, strict_hits):
    # 이 판정 호출이 **오늘 이 기계에서** 체크포인트를 찾는가.
    body = re.sub(r'"[^"]*"', ' ', rest)
    preset = _judge_val(body, '--preset', 'm100')
    data = _judge_val(body, '--data') or _judge_val(body, '--data-default', 'ko-en')
    tok = _judge_val(body, '--tokens', '300M')
    ctok = _judge_val(body, '--ckpt-tokens') or tok
    mm = re.search(r'--models\s+(.*)$', body)
    specs = []
    if mm:
        for t in mm.group(1).split():
            if t.startswith('-'):
                break
            specs.append(_judge_model_spec(t, preset))
    tags = [tag for tag, _pre in specs]
    spec_presets = [pre for _tag, pre in specs]
    shown_preset = (spec_presets[0] if spec_presets and len(set(spec_presets)) == 1
                    else "★모델별(" + " ".join(spec_presets) + ")"
                    if spec_presets else preset)
    # ★★2026-09-10(2차) — **`common_bpb --tokens` 는 모델별로 여러 값**을 받는다.
    #   🚫`_judge_val` 은 **첫 값 하나만** 읽으므로 두 가족을 섞은 호출에서
    #   뒤쪽 모델을 전부 *"아직 없다"* 로 오판한다(함정 34 — 게이트가 낡은 쪽).
    #   ★모델 수와 토큰 값 수가 같으면 **짝을 지어** 해석한다.
    _tk_all = re.search(r'--tokens\s+((?:[0-9]+[MB]\s*)+)', body)
    per_tok = _tk_all.group(1).split() if _tk_all else []
    if len(per_tok) == len(tags) and len(set(per_tok)) > 1:
        ctoks = per_tok
        print(f'    {name}   preset={shown_preset} data={data} '
              f'tokens=★모델별({" ".join(per_tok)})   모델 {len(tags)}개')
    else:
        ctoks = [ctok] * len(tags)
        extra = (f' ckpt-tokens={ctok}' if ctok != tok else '')
        print(f'    {name}   preset={shown_preset} data={data} tokens={tok}{extra}   모델 {len(tags)}개')
    bad = []
    for (t, tpre), _ct in zip(specs, ctoks):
        hit, tried = _resolve_ckpt_names(tpre, data, _ct, t)
        if hit is None:
            bad.append((t, tpre, _ct, tried))
    if not tags:
        print('      ⚠️`--models` 뒤에서 태그를 못 읽었다 — 사람이 본다')
        return
    if not bad:
        print('      ✅전부 해석된다')
        return
    made = trained_tags()
    hard = [(t, pre, ct, tr) for t, pre, ct, tr in bad if t not in made]
    soon = [(t, pre, ct, tr) for t, pre, ct, tr in bad if t in made]
    for t, _pre, _ct, _tr in soon:
        print(f'      ⏳{t} — 아직 없다. **{made[t]} 가 만든다**(선결). 큐 순서로 보장한다')
    for t, tpre, _ct, tried in hard:
        print(f'      🚫**{t}** — 해석 실패(preset={tpre}). 시도: '
              + (', '.join(tried) or '(없음)'))
        strict_hits.append(f'{name}: 체크포인트 미해석 {t} (preset={tpre}, tokens={_ct})')
    for t, _pre, _ct, _tr in hard:
        alt = sorted(p.name for p in (ROOT / 'runs' / 'ckpt').glob(f'*_{data}_*_{t}.pt'))
        if alt:
            print(f'      ★같은 태그가 **다른 토큰 칸**에 있다: ' + ', '.join(alt[:3]))
            print('        -> `--ckpt-tokens <그 칸>` 을 준다. '
                  '`--tokens` 는 val 캐시, `--ckpt-tokens` 는 파일명이다')


def main() -> int:
    ap = argparse.ArgumentParser(description="배치 드라이런 — 유효 실험 조건 인쇄")
    ap.add_argument("bats", nargs="*", help="비우면 최상위 run_*.bat 전부")
    ap.add_argument("--strict", action="store_true",
                    help="태그 불일치·예산 초과가 있으면 exit 1")
    ap.add_argument("--live-only", action="store_true",
                    help="`-done` 배치를 건너뛴다. ★정적 스위트는 이 모드로 돈다 — "
                         "이미 끝난 배치의 알려진 실패로 스위트가 영구히 빨간불이 되면 "
                         "새 문제를 가린다(경보 피로)")
    a = ap.parse_args()

    print("=" * 96)
    print("  ★배치 드라이런 — 이 배치를 돌리면 **어떤 조건으로** 돌아가는가 "
          "(학습 0 · torch 0)")
    print("=" * 96)

    missing = trainer_override_shape_ok()
    if missing:
        print(f"  ⚠️★**trainer.py 의 오버라이드 모양이 바뀌었다**: {', '.join(missing)}")
        print("     이 도구는 그 다섯 줄을 가정한다 — 유효값이 틀릴 수 있다. 코드를 먼저 본다.")
    else:
        print("  ✅trainer.py 의 오버라이드 다섯 줄 확인 "
              "(cla_group · mlp_group · attn_group · train_repeat · ckpt)")

    files = ([Path(b) for b in a.bats] if a.bats
             else sorted(ROOT.glob("run_*.bat")))
    if a.live_only:
        files = [f for f in files if "-done" not in f.name]
    takes = flag_table()
    strict_hits: list[str] = []
    n_run = 0
    n_judge = 0
    for f in files:
        p = f if f.exists() else ROOT / f.name
        if not p.exists():
            print(f"\n  [!] 없다: {f}")
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        runs = [(t, rest) for t, rest in
                ((m.group(1), m.group(2)) for m in CALL.finditer(text))
                if Path(t.replace("\\", "/")).name == "run100m.py"
                and re.match(r"\s*train\b", rest)]
        judges = judge_calls(text)
        if not runs and not judges:
            continue
        print("\n" + "=" * 96)
        print(f"  {p.name}   학습 호출 {len(runs)}개 · 판정 호출 {len(judges)}개")
        print("=" * 96)
        for _t, rest in runs:
            n_run += 1
            show(analyse(rest, takes), strict_hits)
        if judges and _CKPT_ANY:
            print('  ── 판정 호출 — 체크포인트가 **오늘 이 기계에서** 해석되는가')
            for jname, jrest in judges:
                n_judge += 1
                show_judge(jname, jrest, strict_hits)
        elif judges:
            print('  ── 판정 호출 — 🚫`runs/ckpt/` 가 비어 있어 건너뛴다')

    print("\n" + "=" * 96)
    print(f"  학습 호출 {n_run}개 · 판정 호출 {n_judge}개를 읽었다.")
    if strict_hits:
        print(f"  🚫★지적 {len(strict_hits)}건")
        for h in strict_hits:
            print(f"     · {h}")
    else:
        print("  ✅태그 주장과 유효값이 일치하고 `--no-ckpt` 예산도 안이다.")
    print("  ⚠️★**조건만 본다.** 이 조건이 좋은 실험인지는 사람이 정한다.")
    print("  ⚠️`trainer.py` 오버라이드 다섯 줄만 반영한다 — 학습을 흉내내지 않는다.")
    print("=" * 96)
    # ★계측 0 에 exit 0 은 금지(R19). 배치를 지정했는데 학습 호출이 0이면 실패다.
    if a.bats and n_run == 0 and n_judge == 0:
        print("  🚫지정한 배치에서 학습 호출도 판정 호출도 못 찾았다.")
        return 2
    return 1 if (a.strict and strict_hits) else 0


if __name__ == "__main__":
    sys.exit(main())
