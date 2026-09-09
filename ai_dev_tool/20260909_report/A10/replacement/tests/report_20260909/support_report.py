"""보고서 교체본용 작은 합성 fixture. 실험의 실제 품질 판정에는 사용하지 않는다."""
from types import SimpleNamespace


class CharacterTokenizer:
    def encode(self, text, add_special_tokens=False):
        return SimpleNamespace(ids=[1 + ord(c) % 31 for c in text],
                               offsets=[(i, i + 1) for i in range(len(text))])
    def token_to_id(self, text):
        return 0 if text in ("<bos>", "<eos>") else None
    def get_vocab_size(self):
        return 32


def paired_record(ident, value, *, metric="correct", status="ok", family=None):
    return {"id": ident, metric: value, "status": status, "family": family,
            "item_sha256": "item-" + ident, "dataset_sha256": "dataset",
            "scoring_profile": "test", "gold": 0,
            "model_provenance": {"tokenizer_sha256": "same"}}
