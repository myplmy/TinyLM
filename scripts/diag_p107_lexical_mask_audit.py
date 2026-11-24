"""Offline audit of P107 selection against explicit source-position labels."""

from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from tokenizers import Tokenizer
import torch

from tinylm.train.adaptive_masking import HardMaskPolicy, PolicyConfig, audit_selection
from tinylm.train.hybrid_mntp import eligible_mntp, mntp_batch, uniform_mntp_selection


ROOT = Path(__file__).resolve().parents[1]
TOKENIZER = ROOT / "data_cache/tok-ko-en-32768-chat32.json"
TAG = "p107_lexical_mask_selection_audit_v1_20261120"
LANGUAGES = ("ko", "en", "mixed", "und")
DOCUMENTS = (
    ("ko", "가격은 5원이고 재고는 １２개입니다. 지난주 입고 수량은 5"),
    ("en", "The packet holds 5 cards; half is written ½. Check shelf 7"),
    ("mixed", "7월 service charge는 5원. 기록의 교체 시각은 １２"),
    ("und", "5 + ١٢ = 17; ½; 5"),
)


def decimal_token_flags(text, offsets):
    """Flag token occurrences whose half-open source span touches a decimal digit."""
    flags = []
    for start, end in offsets:
        if not 0 <= start <= end <= len(text):
            raise ValueError("token offsets must be character ranges in the original text")
        flags.append(any(character.isdecimal() for character in text[start:end]))
    return flags


def audit_mntp_bias(tokens, documents, selected, probabilities, *,
                    decimals, document_languages, reference_counts, rare_max_count,
                    config, comparison_dtype):
    """Measure expected and drawn selection rates on aligned uncorrupted positions."""
    eligible = eligible_mntp(tokens, documents, vocab_size=config.vocab_size,
                             special_max=config.special_max, mask_id=config.mask_id)
    if (tokens.device.type != "cpu" or decimals.device != tokens.device
            or decimals.dtype != torch.bool or decimals.shape != tokens.shape
            or bool((decimals & (documents < 0)).any())):
        raise ValueError("aligned CPU decimal flags are required, with padding unlabelled")
    if (reference_counts.device != tokens.device or reference_counts.dtype != torch.long
            or reference_counts.shape != (config.vocab_size,) or bool((reference_counts < 0).any())
            or type(rare_max_count) is not int or rare_max_count < 1):
        raise ValueError("one nonnegative clean reference count per token ID and a positive cutoff are required")
    doc_ids, inverse = torch.unique(documents, sorted=True, return_inverse=True)
    language_codes = {language: index for index, language in enumerate(LANGUAGES)}
    codes = []
    for doc_id in doc_ids.tolist():
        if doc_id < 0:
            codes.append(-1)
            continue
        language = document_languages.get(doc_id)
        if language not in language_codes:
            raise ValueError(f"explicit language metadata missing or invalid for document {doc_id}")
        codes.append(language_codes[language])
    language_at = torch.tensor(codes, dtype=torch.long, device="cpu")[inverse]
    frequency_at = reference_counts[tokens]
    groups = {
        "all": torch.ones_like(eligible),
        "decimal": decimals,
        "non_decimal": ~decimals,
        "reference_unseen": frequency_at == 0,
        "reference_rare": (frequency_at > 0) & (frequency_at <= rare_max_count),
        "reference_common": frequency_at > rare_max_count,
    }
    for language, code in language_codes.items():
        group = language_at == code
        groups[language] = group
        groups[f"{language}_decimal"] = group & decimals
        groups[f"{language}_non_decimal"] = group & ~decimals
    return audit_selection(eligible, selected, probabilities, groups, comparison_dtype=comparison_dtype)


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def run_fixture():
    tok = Tokenizer.from_file(str(TOKENIZER))
    vocab_size = tok.get_vocab_size()
    languages = {i: language for i, (language, _) in enumerate(DOCUMENTS)}
    encodings = [tok.encode(text, add_special_tokens=False) for _, text in DOCUMENTS]
    flags = [decimal_token_flags(text, encoded.offsets)
             for (_, text), encoded in zip(DOCUMENTS, encodings, strict=True)]
    instances = {char: [] for char in ("5", "１", "١", "½")}
    for (_, text), encoded, labels in zip(DOCUMENTS, encodings, flags, strict=True):
        for (start, end), label in zip(encoded.offsets, labels, strict=True):
            for char in instances:
                if char in text[start:end]:
                    instances[char].append(label)
    assert all(instances[char] and all(instances[char]) for char in ("5", "１", "١"))
    assert instances["½"] and not any(instances["½"])
    assert decimal_token_flags("1", [(0, 0)]) == [False]

    paths = ((0, 2), (1, 3), (2, 0), (3, 1)) * 8
    width = max(sum(len(encodings[i].ids) for i in path) for path in paths)
    tokens = torch.zeros((len(paths), width), dtype=torch.long)
    documents = torch.full_like(tokens, -1)
    decimals = torch.zeros_like(tokens, dtype=torch.bool)
    for row, path in enumerate(paths):
        offset = 0
        for i in path:
            ids = encodings[i].ids
            span = slice(offset, offset + len(ids))
            tokens[row, span] = torch.tensor(ids)
            documents[row, span] = i
            decimals[row, span] = torch.tensor(flags[i])
            offset += len(ids)

    reference = Counter(t for encoded in encodings for t in encoded.ids)
    frequency = torch.zeros(vocab_size, dtype=torch.long)
    for token, count in reference.items():
        frequency[token] = count
    tokenizer_sha = file_sha(TOKENIZER)
    source_sha = hashlib.sha256(json.dumps(DOCUMENTS, ensure_ascii=False).encode()).hexdigest().upper()
    config = PolicyConfig(vocab_size=vocab_size, mask_rate=.15, ema=.2, refresh_updates=2,
                          unseen_policy="keep", seed=1337, special_max=34, mask_id=13,
                          corpus_sha256=source_sha, run_sha256=file_sha(Path(__file__)))
    eligible = eligible_mntp(tokens, documents, vocab_size=vocab_size)
    starts = (documents[:, 1:] != documents[:, :-1]) & (documents[:, 1:] >= 0)
    assert bool((starts & decimals[:, 1:]).any()) and not bool((starts & eligible[:, 1:]).any())
    assert bool(decimals[:, -1].any()) and not bool(eligible[:, -1].any())
    assert bool((documents == -1).any()) and not bool((eligible & (documents == -1)).any())

    observe = HardMaskPolicy(config)
    for update in range(4):
        observe.begin_update(update, split="train", expected_observations=1)
        selected, _ = observe.select(tokens, documents, adaptive=False)
        batch = mntp_batch(tokens, documents, selected, vocab_size=vocab_size)
        predictions = batch.targets.clamp_min(0).masked_fill(decimals[:, 1:], 0)
        observe.observe(batch, predictions, observation_index=0)
        observe.finish_update(accepted=True)

    reports = {}
    masks = {}
    for mode in ("uniform", "adaptive"):
        policy = HardMaskPolicy(config)
        policy.load_state_dict(observe.state_dict())
        policy.begin_update(4, split="train", expected_observations=1)
        selected, probabilities = policy.select(tokens, documents, adaptive=mode == "adaptive")
        if mode == "uniform":
            rng = torch.Generator(device="cpu").set_state(observe.generator.get_state())
            direct = uniform_mntp_selection(tokens, documents, vocab_size=vocab_size,
                                            probability=config.mask_rate, generator=rng)
            assert torch.equal(selected, direct)
        reports[mode] = audit_mntp_bias(
            tokens, documents, selected, probabilities, decimals=decimals,
            document_languages=languages, reference_counts=frequency, rare_max_count=1,
            config=config, comparison_dtype=policy.draw_dtype,
        )
        masks[mode] = selected

    for mode, report in reports.items():
        target_count = 0
        expected_positions = Counter()
        for row, path in enumerate(paths):
            offset = 0
            for i in path:
                for local, (token, decimal) in enumerate(zip(encodings[i].ids, flags[i], strict=True)):
                    j = offset + local
                    if local and j < width - 1 and token > config.special_max:
                        frequency_name = "reference_rare" if reference[token] == 1 else "reference_common"
                        decimal_name = "decimal" if decimal else "non_decimal"
                        names = ("all", languages[i], decimal_name, frequency_name,
                                 f"{languages[i]}_{decimal_name}")
                        for name in names:
                            expected_positions[name, "eligible"] += 1
                            expected_positions[name, "selected"] += int(masks[mode][row, j])
                        target_count += 1
                offset += len(encodings[i].ids)
        for name, row in report.items():
            assert row["eligible"] == expected_positions[name, "eligible"], name
            assert row["selected"] == expected_positions[name, "selected"], name
        assert math.isclose(report["all"]["expected"], config.mask_rate * target_count, abs_tol=1e-10)
        assert report["reference_unseen"]["realized_rate"] is None
    assert reports["adaptive"]["decimal"]["expected_rate"] > reports["uniform"]["decimal"]["expected_rate"]
    assert not torch.equal(masks["adaptive"], masks["uniform"])

    return {
        "tag": TAG,
        "scope": "AUTHORED_TEXT_TECHNICAL_FIXTURE",
        "fixture_sha256": source_sha,
        "tokenizer_sha256": tokenizer_sha,
        "source_files": {p: file_sha(ROOT / p) for p in (
            "scripts/diag_p107_lexical_mask_audit.py", "tinylm/train/adaptive_masking.py",
            "tinylm/train/hybrid_mntp.py")},
        "documents": len(DOCUMENTS),
        "clean_reference_tokens": sum(reference.values()),
        "clean_reference_types": len(reference),
        "rows": len(paths),
        "full_width": width,
        "probability_budget": config.mask_rate,
        "rare_max_count": 1,
        "simulated_observation_groups": 4,
        "model_loads": 0,
        "optimizer_updates": 0,
        "report": reports,
    }


if __name__ == "__main__":
    torch.set_num_threads(1)
    print(json.dumps(run_fixture(), ensure_ascii=False, allow_nan=False, sort_keys=True))
