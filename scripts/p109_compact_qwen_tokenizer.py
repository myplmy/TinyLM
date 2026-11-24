"""Read an exact Qwen ByteLevel BPE vocabulary and merge list through mmap."""

from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import groupby
import json
import mmap
from pathlib import Path
from struct import Struct

from tokenizers import Tokenizer, pre_tokenizers


MAGIC = b"TLQBPE1\0"
HEADER = Struct("<8s5I")
OFFSET = Struct("<I")
MERGE = Struct("<QII")
ALPHABET_COUNT = 256


def pack(source, destination):
    config = json.loads(Path(source).read_bytes())
    model = config["model"]
    if (model["type"] != "BPE" or model.get("dropout") is not None or model.get("unk_token") is not None
            or model.get("continuing_subword_prefix") or model.get("end_of_word_suffix")
            or model.get("fuse_unk") or model.get("byte_fallback") or model.get("ignore_merges")
            or config.get("truncation") is not None or config.get("padding") is not None
            or config["pre_tokenizer"]["type"] != "Sequence"
            or config["pre_tokenizer"]["pretokenizers"][-1]["type"] != "ByteLevel"
            or config["post_processor"]["type"] != "ByteLevel" or config["decoder"]["type"] != "ByteLevel"):
        raise ValueError("unsupported Qwen tokenizer layout")

    vocabulary = model["vocab"]
    ordinary = len(vocabulary)
    added = {item["content"]: item["id"] for item in config["added_tokens"]}
    seed = {piece: vocabulary[piece] for piece in pre_tokenizers.ByteLevel.alphabet()}
    if (set(seed.values()) != set(range(ALPHABET_COUNT)) or vocabulary.keys() & added.keys()
            or set(vocabulary.values()) != set(range(ordinary))
            or set(added.values()) != set(range(ordinary, ordinary + len(added)))):
        raise ValueError("unexpected Qwen token ID layout")

    scaffold = dict(config, model=dict(model, vocab=seed | added, merges=[]))
    preprocessing = json.dumps(scaffold, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ordered = sorted((vocabulary | added).items(), key=lambda pair: pair[1])
    pieces = bytearray()
    offsets = bytearray(OFFSET.pack(0))
    for piece, _ in ordered:
        pieces.extend(piece.encode("utf-8"))
        offsets.extend(OFFSET.pack(len(pieces)))

    rules = []
    for rank, rule in enumerate(model["merges"]):
        left, right = rule.split(" ") if isinstance(rule, str) else rule
        pair = (vocabulary[left] << 32) | vocabulary[right]
        rules.append((pair, rank, vocabulary[left + right]))
    rules.sort()
    if any(a[0] == b[0] for a, b in zip(rules, rules[1:])):
        raise ValueError("duplicate Qwen merge pair")

    with Path(destination).open("xb") as output:
        output.write(HEADER.pack(MAGIC, len(ordered), ordinary, len(rules), len(preprocessing), len(pieces)))
        output.write(offsets)
        for row in rules:
            output.write(MERGE.pack(*row))
        output.write(preprocessing)
        output.write(pieces)


@dataclass
class Encoding:
    ids: list[int]
    offsets: list[tuple[int, int]]
    word_ids: list[int | None]


class CompactQwenTokenizer:
    def __init__(self, path):
        with Path(path).open("rb") as stream:
            self.data = mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            magic, self.size, ordinary, self.rule_count, preprocessor_size, piece_bytes = HEADER.unpack_from(self.data)
            self.rule_start = HEADER.size + (self.size + 1) * OFFSET.size
            preprocessor_start = self.rule_start + self.rule_count * MERGE.size
            self.piece_start = preprocessor_start + preprocessor_size
            if (magic != MAGIC or not ALPHABET_COUNT <= ordinary <= self.size
                    or self.piece_start + piece_bytes != len(self.data)
                    or self._offset(0) != 0 or self._offset(self.size) != piece_bytes):
                raise ValueError("invalid compact Qwen artifact")
            preprocessor = self.data[preprocessor_start:self.piece_start].decode("utf-8")
            self.scaffold = Tokenizer.from_str(preprocessor)
            self.special = {item["id"] for item in json.loads(preprocessor)["added_tokens"] if item["special"]}
        except Exception:
            self.data.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.data.close()

    def _offset(self, token_id):
        return OFFSET.unpack_from(self.data, HEADER.size + token_id * OFFSET.size)[0]

    def id_to_token(self, token_id):
        if 0 <= token_id < self.size:
            start, stop = self._offset(token_id), self._offset(token_id + 1)
            return self.data[self.piece_start + start:self.piece_start + stop].decode("utf-8")
        return None

    def _merge(self, left, right):
        key = (left << 32) | right
        low, high = 0, self.rule_count
        while low < high:
            middle = (low + high) // 2
            pair, rank, merged = MERGE.unpack_from(self.data, self.rule_start + middle * MERGE.size)
            if pair == key:
                return rank, merged
            if pair < key:
                low = middle + 1
            else:
                high = middle
        return None

    def _merge_word(self, ids, offsets):
        count = len(ids)
        if count < 2:
            return ids, offsets
        previous = list(range(-1, count - 1))
        following = list(range(1, count)) + [-1]
        queue = []

        def queue_pair(left, right):
            if left >= 0 and right >= 0:
                merge = self._merge(ids[left], ids[right])
                if merge is not None:
                    rank, token_id = merge
                    heappush(queue, (rank, left, right, ids[left], ids[right], token_id))

        for edge in range(count - 1):
            queue_pair(edge, edge + 1)

        while queue:
            _, left, right, first, second, token_id = heappop(queue)
            if following[left] != right or ids[left] != first or ids[right] != second:
                continue
            ids[left] = token_id
            offsets[left] = (offsets[left][0], offsets[right][1])
            following[left] = after = following[right]
            following[right] = -1
            if after >= 0:
                previous[after] = left
            queue_pair(previous[left], left)
            queue_pair(left, after)

        merged_ids, merged_offsets = [], []
        index = 0
        while index >= 0:
            merged_ids.append(ids[index])
            merged_offsets.append(offsets[index])
            index = following[index]
        return merged_ids, merged_offsets

    def encode(self, text):
        base = self.scaffold.encode(text, add_special_tokens=False)
        result = Encoding([], [], [])
        spans = zip(base.word_ids, base.ids, base.offsets, strict=True)
        for word, group in groupby(spans, key=lambda item: item[0]):
            ids, offsets = [], []
            for _, token_id, position in group:
                ids.append(token_id)
                offsets.append(position)
            merged, positions = self._merge_word(ids, offsets)
            result.ids.extend(merged)
            result.offsets.extend(positions)
            result.word_ids.extend([word] * len(merged))
        return result

    def decode(self, token_ids, *, skip_special_tokens=True):
        pieces = []
        for token_id in token_ids:
            if skip_special_tokens and token_id in self.special:
                continue
            piece = self.id_to_token(token_id)
            if piece is not None:
                pieces.append(piece)
        return self.scaffold.decoder.decode(pieces)
