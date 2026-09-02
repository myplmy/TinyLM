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
    visits = int(eff.n_prelude + round(eff.n_middle * float(eff.train_repeat))
                 + eff.n_coda)
    kv_ent = visits // max(int(eff.cla_group), 1)
    tok = steps * mb * ac * seq
    print()
    print(f"     학습토큰  {tok / 1e6:,.1f}M  = {steps} x {mb} x {ac} x {seq}")
    print(f"     M         {M:,}  (micro_bs x seq)   방문 {visits}회  "
          f"KV 엔트리 {kv_ent}개")
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
        if not runs:
            continue
        print("\n" + "=" * 96)
        print(f"  {p.name}   학습 호출 {len(runs)}개")
        print("=" * 96)
        for _t, rest in runs:
            n_run += 1
            show(analyse(rest, takes), strict_hits)

    print("\n" + "=" * 96)
    print(f"  학습 호출 {n_run}개를 읽었다.")
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
    if a.bats and n_run == 0:
        print("  🚫지정한 배치에서 학습 호출을 하나도 못 찾았다.")
        return 2
    return 1 if (a.strict and strict_hits) else 0


if __name__ == "__main__":
    sys.exit(main())
