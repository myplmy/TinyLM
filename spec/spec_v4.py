import math
MB = lambda n, bits: n * bits / 8 / 1024**2
BPW = 1.95   # 공개 수치에서 역산한 실제 배포 밀도 (1.71 이상치 + GGUF 오버헤드)

D, FFN, KV, L, V = 2048, 6144, 1024, 28, 151936   # Qwen3-1.7B shape

print("="*80)
print("A. 측정된 excess가 '레이어 한 장 더 저장'보다 이득인가")
print("   손익분기 r* = 1.71·o·i / (16·(o+i)).  비용 = r/r*.  효율 = excess/비용")
print("="*80)
# (이름, out, in, ALS excess at r=16/32/64/128)
rows = [("q_proj", 2048, 2048, [14, 20, 27, 33]),
        ("k_proj", 1024, 2048, [14, 20, 27, 32]),
        ("v_proj", 1024, 2048, [ 7, 12, 18, 25]),
        ("o_proj", 2048, 2048, [ 6, 10, 15, 21]),
        ("gate_proj", 6144, 2048, [ 5,  7, 11, 17]),
        ("up_proj",   6144, 2048, [ 3,  5,  8, 13]),
        ("down_proj", 2048, 6144, [ 4,  6, 10, 15])]
print(f"  {'행렬':<12}{'r*':>6}" + "".join(f"{f'r={r}':>18}" for r in (16,32,64,128)))
print("  " + "-"*76)
for nm, o, i, ex in rows:
    rstar = 1.71*o*i/(16*(o+i))
    cells = []
    for r, e in zip((16,32,64,128), ex):
        cost = r/rstar*100
        cells.append(f"{e}%/{cost:.0f}%={e/cost:.2f}")
    print(f"  {nm:<12}{rstar:>6.0f}" + "".join(f"{c:>18}" for c in cells))
print()
print("  효율이 1.0 미만 = 같은 메모리로 레이어를 그냥 하나 더 두는 게 낫다.")
print("  전 항목이 1.0 미만. 최고치가 q_proj r=16의 0.95(간신히 본전).")
print("  파라미터의 75%를 차지하는 MLP는 0.3~0.5로 명백한 손해.")

def spec(name, n_pre, n_mid, n_coda, mlp_g, attn_g, emb_params, kda_ratio=0):
    attn_l = D*D + 2*(KV*D) + D*D
    mlp_l  = 3*D*FFN
    pc = (n_pre+n_coda)*(attn_l+mlp_l)
    mid_attn = (n_mid//attn_g)*attn_l
    mid_mlp  = (n_mid//mlp_g)*mlp_l
    total = pc + mid_attn + mid_mlp + emb_params
    mem = MB(total, BPW)
    # 토큰당 FLOPs: 타잉과 무관하게 물리 실행 층수만큼
    flops = 2*(n_pre+n_mid+n_coda)*(attn_l+mlp_l)/1e9
    # KV: KDA 레이어는 고정 상태, MLA/softmax 레이어만 캐시
    full_layers = (n_pre+n_mid+n_coda) * (0.25 if kda_ratio else 1.0)
    kv_kb = full_layers*2*KV*2/1024
    return dict(name=name, total=total, mem=mem, flops=flops, kv=kv_kb)

print()
print("="*80)
print("B. 새 구조 스펙  (prelude/coda 독립 + 어텐션 층별 + MLP만 타잉)")
print("="*80)
emb_full = V*D
emb_fact = 64000*512 + 512*D          # 한/영 64k vocab + factorized E=512
print(f"  전층 독립 28층 + 전체 임베딩 = 기준선")
base = spec("baseline", 0, 28, 0, 1, 1, emb_full)
print(f"  {'구성':<46}{'파라미터':>10}{'메모리':>10}{'감축':>8}{'GFLOP':>8}")
print("  " + "-"*82)
print(f"  {'[기준] 28층 전부 독립 + 전체 임베딩':<46}{base['total']/1e6:>9.0f}M{base['mem']:>8.0f}MB{'1.00x':>8}{base['flops']:>8.2f}")
cfgs = [
    ("2+24+2, MLP g=4, 어텐션 독립, 전체 임베딩", 2,24,2,4,1, emb_full),
    ("2+24+2, MLP g=4, 어텐션 독립, 임베딩 축약", 2,24,2,4,1, emb_fact),
    ("2+24+2, MLP g=6, 어텐션 독립, 임베딩 축약", 2,24,2,6,1, emb_fact),
    ("2+24+2, MLP g=6, 어텐션 g=2, 임베딩 축약", 2,24,2,6,2, emb_fact),
    ("2+24+2, MLP g=8, 어텐션 g=2, 임베딩 축약", 2,24,2,8,2, emb_fact),
]
for nm,a,b,c,mg,ag,e in cfgs:
    s = spec(nm,a,b,c,mg,ag,e)
    print(f"  {nm:<46}{s['total']/1e6:>9.0f}M{s['mem']:>8.0f}MB{base['mem']/s['mem']:>7.2f}x{s['flops']:>8.2f}")
print()
print(f"  참고: Bonsai 1.7B ternary = 471 MB,  Qwen3-1.7B FP16 ≈ 3900 MB")

print()
print("="*80)
print("C. 임베딩 세 방안")
print("="*80)
opts = [("현재 (151,936 x 2048, 삼진)",        V*D,                    "-"),
        ("(a) vocab 64k로 축소",               64000*D,                "한국어 토큰 증가 위험"),
        ("(b) factorized E=512 (vocab 유지)",  V*512 + 512*D,          "로짓 랭크 512로 제한"),
        ("(c) 1-bit 임베딩 (vocab 유지)",      V*D,                    "비트만 1.0"),
        ("(a)+(b) 64k + E=512",                64000*512 + 512*D,      "토크나이저 재학습 필요")]
print(f"  {'방안':<38}{'파라미터':>10}{'메모리':>10}{'절감':>8}   비고")
print("  " + "-"*88)
for nm, p, note in opts:
    bits = 1.0 if "1-bit" in nm else BPW
    m = MB(p, bits)
    print(f"  {nm:<38}{p/1e6:>9.1f}M{m:>8.1f}MB{MB(V*D,BPW)/m:>7.1f}x   {note}")

print()
print("="*80)
print("D. KV 캐시 (28층, GQA kv_dim=1024)")
print("="*80)
print(f"  {'구성':<44}{'KB/토큰':>10}{'32K 컨텍스트':>14}")
print("  " + "-"*70)
for nm, f in [("층별 독립 KV (현재)", 1.0),
              ("+ CLA2 (인접 2층 K/V 공유)", 0.5),
              ("+ CLA4", 0.25),
              ("+ KDA 3:1 하이브리드 (1/4만 full)", 0.25),
              ("KDA 3:1 + CLA2", 0.125),
              ("KDA 3:1 + CLA2 + 4bit KV", 0.03125)]:
    kb = L*2*KV*2/1024*f
    print(f"  {nm:<44}{kb:>9.1f}KB{kb*32768/1024**2:>12.2f}GB")

print()
print("="*80)
print("E. CPU vs RTX 4070 Ti  (MLP g=4 + 임베딩 축약 구성)")
print("="*80)
s = spec("x",2,24,2,4,1,emb_fact)
dram_untied = MB(base['total'], BPW)
# 타이드 MLP는 그룹당 1회만 DRAM에서 읽고 나머지 3회는 캐시 히트
mlp_group_mb = MB(3*D*FFN, BPW)
attn_mb      = MB(D*D+2*KV*D+D*D, BPW)
dram = 6*mlp_group_mb + 24*attn_mb + 4*(mlp_group_mb+attn_mb) + MB(emb_fact,BPW)
print(f"  블록당 타이드 MLP 크기          {mlp_group_mb:.1f} MB   (4회 연속 재사용 → L3 상주 가능)")
print(f"  층당 어텐션 크기                {attn_mb:.1f} MB   (재사용 없음 → 스트리밍)")
print(f"  토큰당 DRAM 트래픽              {dram:.0f} MB")
print()
print(f"  {'':<24}{'대역폭':>12}{'대역폭 시간':>12}{'연산':>12}{'연산 시간':>12}{'병목':>8}")
print("  " + "-"*84)
for nm, bw, ops in [("CPU (50GB/s, 100GOPS)", 50e9, 100e9),
                    ("RTX4070Ti (504GB/s, 80TOPS int8)", 504e9, 80e12)]:
    t_bw = dram*1024**2/bw*1000
    t_op = s['flops']*1e9/ops*1000
    print(f"  {nm:<34}{bw/1e9:>7.0f}GB/s{t_bw:>10.2f}ms{ops/1e12:>9.1f}TOPS{t_op:>10.2f}ms"
          f"{('연산' if t_op>t_bw else '대역폭'):>8}")
print()
print(f"  L3 전체 상주에 필요한 총 가중치 < 24MB → 약 {24*1024**2*8/BPW/1e6:.0f}M 파라미터")
print(f"  현재 구성은 {s['total']/1e6:.0f}M → L3 전체 상주는 {s['total']/1e6/(24*1024**2*8/BPW/1e6):.0f}배 초과")
