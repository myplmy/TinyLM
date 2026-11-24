"""Compare actual P109 and chat32 vocabularies and text segmentation."""

from collections import Counter
import os
from pathlib import Path

from tokenizers import Tokenizer

from scripts import diag_p106b_dvlm_real_prefix_head as previous
from scripts.p106b_dvlm_head import native_vocabulary

TAG = "p106b_p109_chat32_ordinary_remap_v1_20261119"
OUT = previous.OUT.with_name(TAG)


def keys(tokenizer, vocab, text):
    ids = tokenizer.encode(text, add_special_tokens=False).ids
    return ids, tuple(vocab[token] for token in ids)


def show(ids, tokenizer):
    return dict(ids=ids, decoded=tokenizer.decode(ids, skip_special_tokens=False))


def main():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    left, right = previous.STUDENT, previous.CHAT32
    source = previous.OUT / "profile.json"
    pinned = previous.read(source)
    assert all(previous.SHA(p) == pinned["pins"][str(p.relative_to(previous.ROOT))] for p in (left, right))
    a, b = (previous.read(p) for p in (left, right))
    native, chat = (native_vocabulary(raw) for raw in (a, b))
    tok, chat_tok = (Tokenizer.from_file(str(path)) for path in (left, right))
    inverse = {piece:index for index,piece in chat.items()}
    assert len(inverse) == len(chat)
    shared = {index:inverse[piece] for index,piece in native.items() if piece in inverse}
    config_keys = ("normalizer","pre_tokenizer","post_processor","decoder")
    merges = [{tuple(rule) if isinstance(rule, list) else tuple(rule.split(" ")): i
               for i,rule in enumerate(raw["model"]["merges"])} for raw in (a,b)]
    common = set(merges[0]) & set(merges[1])
    counts = Counter()
    differences = []
    for doc in pinned["docs"]:
        first, first_pieces = keys(tok,native,doc["text"])
        second, second_pieces = keys(chat_tok,chat,doc["text"])
        assert tok.decode(first,skip_special_tokens=False) == chat_tok.decode(second,skip_special_tokens=False) == doc["text"]
        counts["documents"] += 1
        counts["same_ids"] += int(first == second)
        counts["same_pieces"] += int(first_pieces == second_pieces)
        if first_pieces != second_pieces:
            differences.append(dict(id=doc["id"], native=first, chat32=second))
    native_only = []
    for index, (kind, value, _) in native.items():
        if index in shared or kind != "ORDINARY_BYTES":
            continue
        try:
            text = value.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            native_only.append(dict(id=index, encoding="INCOMPLETE_UTF8"))
            continue
        l, lp = keys(tok,native,text)
        r, rp = keys(chat_tok,chat,text)
        native_only.append(dict(id=index,text=text, native=show(l,tok), chat32=show(r,chat_tok),
                                occurs_as_native_single=l == [index], same_piece_sequence=lp==rp))
    specials = {}
    for marker in ("<|im_start|>", "<|im_end|>", "<|tool_call|>"):
        t=f"문자열 {marker} 끝"
        l, lp = keys(tok,native,t)
        r, rp = keys(chat_tok,chat,t)
        assert not any(kind=="ADDED_LITERAL" for kind,_,_ in lp)
        assert any(kind=="ADDED_LITERAL" for kind,_,_ in rp)
        specials[marker] = dict(native=show(l,tok),chat32=show(r,chat_tok))
    OUT.mkdir(exist_ok=False)
    previous.write(OUT/"report.json",dict(tag=TAG, source=previous.SHA(Path(__file__)),
          profile_sha256=previous.SHA(source), tokenizer_sha256={p.name:previous.SHA(p) for p in (left,right)},
          rows=[len(native),len(chat)], shared_native_pieces=len(shared), same_ids=sum(k==v for k,v in shared.items()),
          id_shift_counts=dict(Counter(v-k for k,v in shared.items())),
          config_equal={k:a.get(k)==b.get(k) for k in config_keys},
          merges=[len(m) for m in merges], shared_merges=len(common),
          shared_merge_order_equal=[rule for rule in merges[0] if rule in common]==[rule for rule in merges[1] if rule in common],
          real_documents=dict(counts), real_differences=differences, native_only=native_only, special_probes=specials,
          model_execution=0))
    print("P109_CHAT32_ALIGNMENT",dict(counts),len(shared),len(native_only),len(common),flush=True)


if __name__ == "__main__":
    main()
