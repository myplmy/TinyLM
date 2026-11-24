"""Check omission of only a role-boundary LF token from the direct-KL targets."""

import os
from pathlib import Path
from types import SimpleNamespace

from tokenizers import Tokenizer

from scripts import diag_p106b_direct_kl_response_mask as original


ref = original.ref
TAG = "p106b_direct_kl_leading_newline_v1_20261120"
OUT = original.OUT.with_name(TAG)
ADDITIONAL = {
    "english": [("user", "Return the content of the label."), ("assistant", "\n\nBlue label.")],
    "korean_multiturn": [("user", "첫 표식은?"), ("assistant", "동쪽"),
                         ("user", "다음 표식은?"), ("assistant", "\n\n서쪽.")],
    "newline_only": [("user", "표식은?"), ("assistant", "\n\n")],
}


def mask_without_shared_lf(text, encoding, spans, stop_id):
    masks, crossing = original.entries(encoding, spans)
    skipped = []
    for item in crossing:
        left, right = item["offsets"]
        spans_touched = [span for span in spans if left < span["content"][1] and right > span["content"][0]]
        if item["kind"] != "content" or len(spans_touched) != 1:
            raise ValueError("A shared token touched a stop or multiple assistant turns")
        begin, end = spans_touched[0]["content"]
        if (left != begin - 1 or not begin < right <= end
                or text[left:begin] != "\n" or any(char != "\n" for char in text[begin:right])):
            raise ValueError("Only a shared header LF and leading body LFs can be omitted")
        skipped.append(dict(token_index=item["token_index"], token_id=encoding.ids[item["token_index"]],
                            body_offsets=[begin, right], omitted_lf_count=right - begin))
    taken = set()
    for span, mask in zip(spans, masks, strict=True):
        begin, end = span["content"]
        if not mask["content"] or not text[begin:end].strip() or [r[1] for r in mask["stop"]] != [stop_id]:
            raise ValueError("A non-empty body and the exact one-token assistant stop are required")
        covered = set()
        for position, token in mask["content"]:
            index = position + 1
            left, right = encoding.offsets[index]
            assert token == encoding.ids[index] and begin <= left < right <= end
            covered.update(range(left, right))
        omitted = {i for item in skipped for i in range(*item["body_offsets"])}
        if (set(range(begin, end)) - covered) != (set(range(begin, end)) & omitted) or covered & omitted:
            raise ValueError("The original body must be covered except for the identified leading LFs")
        taken.update(position + 1 for targets in mask.values() for position, _ in targets)
    if taken.intersection(item["token_index"] for item in skipped):
        raise ValueError("A shared role token was still targeted")
    return dict(masks=masks, skipped=skipped)


def observe(tok, messages):
    text, spans = original.render(messages)
    encoding = tok.encode(text, add_special_tokens=False)
    result = dict(text=text, ids=encoding.ids, spans=spans)
    try:
        result.update(mask_without_shared_lf(text, encoding, spans, original.EXPECT_IDS[original.END]))
        result["admitted"] = True
    except ValueError as exc:
        result.update(admitted=False, rejection=str(exc))
    return result


def non_lf_negative(tok):
    text, spans = original.render(original.CASES["nfc"])
    encoding = tok.encode(text, add_special_tokens=False)
    begin = spans[0]["content"][0]
    idx = next(i for i, (left, right) in enumerate(encoding.offsets) if left == begin and right > begin)
    altered = list(encoding.offsets)
    altered[idx] = (begin - 1, altered[idx][1])
    wrong = SimpleNamespace(ids=encoding.ids, offsets=altered)
    try:
        mask_without_shared_lf(text, wrong, spans, original.EXPECT_IDS[original.END])
    except ValueError as exc:
        return str(exc)
    raise AssertionError("A shared token with a non-LF content character was accepted")


def main():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    asset_report = ref.read(ref.OUT / "report.json")
    tokenizer = ref.QWEN_HF / "tokenizer.json"
    assert ref.sha(tokenizer) == asset_report["assets"]["qwen35_hf"]["file_sha256"]
    tok = Tokenizer.from_file(str(tokenizer))
    baseline_path = original.OUT / "report.json"
    baseline = ref.read(baseline_path)["cases"]
    data = {name:observe(tok, messages) for name, messages in (original.CASES | ADDITIONAL).items()}
    for name in original.CASES:
        assert data[name]["ids"] == baseline[name]["token_ids"]
        assert data[name]["masks"] == baseline[name]["if_aligned"]
    recovered = data["newline_boundary"]
    assert recovered["admitted"] and [row["token_id"] for row in recovered["skipped"]] == [1358]
    assert [r["omitted_lf_count"] for r in recovered["skipped"]] == [2]
    assert not data["newline_only"]["admitted"]
    assert all(data[key]["admitted"] for key in data if key != "newline_only")
    distinct_negative = non_lf_negative(tok)
    new = [data[key] for key in ADDITIONAL]
    matches = original.native_matches([x["text"] for x in new], [x["ids"] for x in new], asset_report)
    assert all(all(group["ids_match"]) and group["skipped_tensors"] for group in matches.values())
    OUT.mkdir()
    ref.write(OUT / "report.json", dict(tag=TAG, source_sha256=ref.sha(baseline_path), rows=data, gguf=matches,
              non_lf_negative=distinct_negative, tensor_loads=0, learning_updates=0, production_enabled=False))
    print("P106B_SHARED_LF_MASK", {k:(v["admitted"], len(v.get("skipped", []))) for k,v in data.items()}, flush=True)


if __name__ == "__main__":
    main()
