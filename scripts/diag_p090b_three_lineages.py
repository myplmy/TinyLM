#!/usr/bin/env python3
"""P090B safe three-arm SFT lineage preflight; no model, GPU, or protected data."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--legacy-tokenizer", type=Path,
                    default=Path("data_cache/tok-ko-en-32768.json"))
    ap.add_argument("--chat32-tokenizer", type=Path,
                    default=Path("data_cache/tok-ko-en-32768-chat32.json"))
    ap.add_argument("--legacy-parent", type=Path,
                    default=Path("runs/ckpt/m100s10_ko-en_300M_d14_cla2_norecur_rms4_lr15.pt"))
    ap.add_argument("--best-candidate", type=Path,
                    default=Path("runs/ckpt/m100s12_ko-en_1200M_d16_cla2_norecur_rms4_t1200.pt"))
    args = ap.parse_args()
    if args.check_only:
        print("[CHECK_ONLY] P090B legacy/chat32/best-parent lineage preflight; model/GPU NOT_RUN")
        return 0
    from tokenizers import Tokenizer
    from tinylm.chat.tokens import SLOT_NAMES
    from tinylm.data.prepare import verify_chat_tokenizer

    legacy = ROOT / args.legacy_tokenizer
    chat32 = ROOT / args.chat32_tokenizer
    parent = ROOT / args.legacy_parent
    best = ROOT / args.best_candidate
    if not legacy.is_file() or not parent.is_file():
        print("[STOP] legacy tokenizer/parent absent")
        return 2
    old = Tokenizer.from_file(str(legacy))
    old_ids = {name: old.token_to_id(name) for name in SLOT_NAMES[:2]}
    print(f"[A] legacy_vocab={old.get_vocab_size()} chatml_single_ids={old_ids} parent_present=YES")
    if old.get_vocab_size() != 32768:
        return 2
    if chat32.is_file():
        new = Tokenizer.from_file(str(chat32))
        ids = verify_chat_tokenizer(new, 32768)
        print(f"[B] chat32_tokenizer=READY marker_ids={ids[SLOT_NAMES[0]]},{ids[SLOT_NAMES[1]]}")
        print("[B] matching newly pretrained parent still requires checkpoint/tokenizer hash evidence")
    else:
        print("[B] chat32_tokenizer=NOT_READY; new parent and training are NOT_RUN")
    print(f"[C] best_parent_candidate_present={best.is_file()} selection=NOT_DECIDED")
    print("[C] an English full-val score alone cannot select the best Korean conversational parent")
    print("[PASS] three-arm lineage inventory; supervised corpus/parent matching/quality NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
