"""고정 BabyLM causal 원함수의 선택 로딩과 관찰용 경계.

모듈 import는 표준 라이브러리만 사용한다. 공식 파일·자료를 읽거나 Torch를
불러오고 모델을 실행하는 것은 명시 호출자의 책임이다. 공식 함수 본문은 수정하지 않는다.
"""
from __future__ import annotations

import ast
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

COMMIT = "6f825c291e2c4c78ad33b1935fd64d45f52642dc"
FILES = {
    "read_files.py": ("742386554D9C7F80E7ED15EF7DFA6D186B29A4ADF6C832C94BFD4254840B1A8F", ("decode_blimp",)),
    "dataset.py": ("133DA1300DDB10D3D7D2B42859D662C25986F6CDCB457721C3DA693E8F00571A", ("process_causal_sentences", "get_causal_collate_fn")),
    "compute_results.py": ("DDCE8DE7185E1C29F13B05A8F76AC2FAB04A386DA86CAE693C7B7F38B198FC83", ("update_subset_to_stats", "rank_and_evaluate", "compute_causal_results")),
    "run.py": ("1E4B11F53DD71A6203ED7936160774BB634220C54EEA605BAE70503B57432668", ("process_results",)),
}
ATOL, RTOL = 1e-5, 1e-4


def value_sha(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest().upper()


def selected_node(tree, name):
    """원 instance method만 top-level 함수로 연결한다. 본문/annotation은 그대로다."""
    if name == "process_causal_sentences":
        owners = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "CompletionRankingDataset"]
        matches = [n for owner in owners for n in owner.body if isinstance(n, ast.FunctionDef) and n.name == name]
    else:
        matches = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(matches) != 1 or matches[0].decorator_list:
        raise ValueError("공식 원함수의 정확한 node/decorator 계약 불일치: " + name)
    node = matches[0]
    if any(isinstance(n, ast.Name) and n.id == "__class__" for n in ast.walk(node)):
        raise ValueError("선택 method의 class closure는 지원하지 않음")
    return node


def load_official(directory, torch, *, device="cpu", progress=None):
    """고정 파일 SHA 확인 뒤 변경 없는 원 node만 공통 globals로 compile한다."""
    from torch.nn.utils.rnn import pad_sequence
    directory = Path(directory)
    namespace = dict(__builtins__=__builtins__, __name__="tinylm_pinned_babylm_causal",
        torch=torch, F=torch.nn.functional, Counter=Counter, defaultdict=defaultdict,
        pad_sequence=pad_sequence, DEVICE=torch.device(device),
        LENGTH_NORMALIZED_TASKS={"global_piqa_parallel", "global_piqa_nonparallel"},
        tqdm=progress if progress is not None else (lambda items: items))
    receipts = {}
    for name, (expected, functions) in FILES.items():
        path = directory / name
        if path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise ValueError("고정 공식 소스 SHA/경로 불일치: " + name)
        raw_bytes = path.read_bytes()
        if hashlib.sha256(raw_bytes).hexdigest().upper() != expected:
            raise ValueError("고정 공식 소스 SHA 불일치: " + name)
        raw = raw_bytes.decode("utf-8")
        tree = ast.parse(raw, filename=str(path))
        nodes = [selected_node(tree, function) for function in functions]
        future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
        module = ast.fix_missing_locations(ast.Module(body=[future, *nodes], type_ignores=[]))
        receipts[name] = dict(sha256=expected, nodes={node.name:dict(
            start_line=node.lineno, end_line=node.end_lineno,
            ast_sha256=hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest().upper()) for node in nodes})
        exec(compile(module, str(path), "exec"), namespace)
    proof = dict(commit=COMMIT, selection="EXACT_UNMODIFIED_AST_NODES_SHARED_GLOBALS", files=receipts,
        official_cli=False, original_package_import=False, source_modified=False,
        excluded_imports=["scipy.stats", "AutoProcessor", "datasets", "aiohttp"],
        caller_no_grad_required=True, default_device=str(torch.get_default_device()),
        default_dtype=str(torch.get_default_dtype()), compute_device=str(namespace["DEVICE"]),
        supplied_globals=["torch", "F", "Counter", "defaultdict", "pad_sequence", "DEVICE", "LENGTH_NORMALIZED_TASKS", "tqdm"],
        progress="ORDER_PRESERVING_IDENTITY_CALLABLE" if progress is None else "CALLER_SUPPLIED_PROGRESS_ONLY")
    return namespace, proof


class TextProcessor:
    """원 native tokenizer를 한 번 호출하며 ID/offset/특수문자를 재작성하지 않는다."""
    def __init__(self, tokenizer, *, native, vocab):
        self.tokenizer, self.native, self.vocab = tokenizer, native, vocab
        self.calls = 0
        self.max_tokens = 0

    def __call__(self, *, text, return_offsets_mapping):
        if not isinstance(text, str) or not text or return_offsets_mapping is not True:
            raise ValueError("원문의 비어 있지 않은 문자열과 실제 offsets 필요")
        if self.native:
            if getattr(self.tokenizer,"truncation",None) is not None or getattr(self.tokenizer,"padding",None) is not None:
                raise ValueError("원 native tokenizer의 절단/padding 설정을 바꾸지 않고 거부")
            encoded = self.tokenizer.encode(text, add_special_tokens=True)
            if getattr(encoded,"overflowing",None) != []:
                raise ValueError("원 native Encoding의 overflow 부재 증거 필요")
            value = dict(input_ids=list(encoded.ids), attention_mask=list(encoded.attention_mask),
                         offset_mapping=[list(v) for v in encoded.offsets])
        else:
            encoded = self.tokenizer(text=text, return_offsets_mapping=True)
            value = {key: list(encoded[key]) for key in ("input_ids", "attention_mask", "offset_mapping")}
        tokens, attention, offsets = (value[k] for k in ("input_ids", "attention_mask", "offset_mapping"))
        if (len(tokens) < 2 or len(tokens) - 1 > 1024 or len(attention) != len(tokens)
                or len(offsets) != len(tokens) or any(type(i) is not int or not 0 <= i < self.vocab for i in tokens)
                or any(i != 1 for i in attention) or any(len(v) != 2 or any(type(x) is not int for x in v)
                    or not 0 <= v[0] <= v[1] <= len(text) for v in offsets)):
            raise ValueError("공식 causal flat-token/1024/offset 계약 밖; 절단·BOS 추가·행 제외하지 않음")
        self.calls += 1
        self.max_tokens = max(self.max_tokens, len(tokens))
        return value


def processed_pair(official, processor, raw, filename):
    decoded = official["decode_blimp"](raw, Path(filename))
    if (decoded["label"] != 0 or len(decoded["sentences"]) != 2
            or decoded["sentences"] != decoded["completions"]
            or any(not isinstance(v, str) or not v for v in decoded["sentences"])):
        raise ValueError("원 good/bad 두 완전 문장 계약 필요")
    processed = official["process_causal_sentences"](SimpleNamespace(processor=processor), decoded, None)
    for j in range(2):
        prefix = "sentence_" + str(j)
        tokens, attention, mask = (processed[prefix + suffix] for suffix in ("_tokens", "_attn_mask", "_phrase_mask"))
        if (tokens.ndim != 1 or tokens.shape != attention.shape or tokens.shape != mask.shape
                or not bool(mask[1:].sum() > 0) or not bool(((mask == 0) | (mask == 1)).all())):
            raise ValueError("원 phrase mask/shift target이 비거나 shape 불일치")
    metadata = {key: decoded[key] for key in ("field", "UID", "linguistics_term")}
    return (decoded, processed, decoded["label"], metadata, decoded["UID"])


def scalar_oracle(logits, targets, mask):
    """작은 합성 logits의 독립 FP64/Python logit-LSE. 실물 전체용이 아니다."""
    if len(logits) != len(targets) or len(targets) != len(mask):
        raise ValueError("독립 oracle shape 불일치")
    total = 0.0
    for values, target, supervised in zip(logits, targets, mask):
        if any(not math.isfinite(float(v)) for v in values):
            raise ValueError("유한 합성 logits 필요")
        if supervised:
            maximum = max(values)
            total += values[target] - maximum - math.log(math.fsum(math.exp(v - maximum) for v in values))
    return total


class RankAudit:
    """원 rank 호출 전후를 관찰하고 같은 RNG에서 선택/Counter를 독립 검산한다."""
    def __init__(self, official, torch, *, sink=None):
        self.official, self.torch, self.sink = official, torch, sink
        self.original = official["rank_and_evaluate"]
        self.rows, self.ties, self.shortest_correct, self.longest_correct = 0, 0, 0, 0
        self.equal_character_length_pairs = 0
        self.shortest_random_tie_expected_correct = 0.0
        self.longest_random_tie_expected_correct = 0.0
        self.by_uid = defaultdict(lambda: dict(total=0, correct=0))
        self.score_identity = hashlib.sha256()
        self.predictions = None
        self.expected_prediction_hashes = {}

    def __enter__(self):
        self.official["rank_and_evaluate"] = self.call
        return self

    def __exit__(self, *args):
        self.official["rank_and_evaluate"] = self.original

    def call(self, args, stats, probabilities, raw, labels, metadatas, uids, predictions):
        torch = self.torch
        if (getattr(args,"task",None)!="blimp" or getattr(args,"images_path",True) is not None
                or getattr(args,"save_predictions",None) is not True
                or set(probabilities) != {1.0} or len(probabilities[1.0]) != 2
                or not len(raw) == len(labels) == len(metadatas) == len(uids)
                or any(v.device.type != "cpu" or v.ndim != 1 or len(v) != len(raw)
                    or v.dtype != torch.float32 or not bool(torch.isfinite(v).all()) for v in probabilities[1.0])
                or str(torch.get_default_device()) != "cpu"):
            raise ValueError("공식 rank의 유한 CPU FP32 2후보/행 순서 계약 불일치")
        rng_before = torch.get_rng_state().clone()
        before = {key:dict(total=dict(value["total"]), correct=dict(value["correct"])) for key,value in stats[1.0].items()}
        before_lengths = {uid:len(predictions[1.0].get(uid, ())) for uid in dict.fromkeys(uids)}
        all_before_lengths = {uid:len(values) for uid,values in predictions[1.0].items()}
        if self.predictions is not None and self.predictions is not predictions[1.0]:
            raise ValueError("같은 원 prediction 사전만 연속 관찰 가능")
        self.predictions=predictions[1.0]
        self.original(args, stats, probabilities, raw, labels, metadatas, uids, predictions)
        rng_after = torch.get_rng_state().clone()
        torch.set_rng_state(rng_before)
        replay, changes = [], defaultdict(lambda: dict(total=Counter(), correct=Counter()))
        try:
            for index, (sentence, label, metadata, uid) in enumerate(zip(raw, labels, metadatas, uids)):
                scores = [float(values[index]) for values in probabilities[1.0]]
                best = max(scores)
                candidates = [j for j,v in enumerate(scores) if v == best]
                chosen = candidates[int(torch.randint(len(candidates), (1,)))] if len(candidates)>1 else candidates[0]
                if label != 0 or metadata["UID"] != uid or len(sentence["sentences"]) != 2:
                    raise ValueError("공식 BLiMP metadata/후보/label 계약 불일치")
                for key,value in metadata.items():
                    changes[key]["total"][value] += 1
                    changes[key]["correct"][value] += int(chosen == label)
                event = dict(index=self.rows+index, uid=uid, label=label, chosen=chosen,
                    scores=scores, raw_sentences=sentence, exact_tie=len(candidates)>1,
                    score_margin=scores[0]-scores[1], numerical_rule="OFFICIAL_EXACT_TIE_NO_EPSILON")
                replay.append(event)
            if not torch.equal(torch.get_rng_state(), rng_after):
                raise ValueError("공식 tie RNG 독립 재생 불일치")
        finally:
            torch.set_rng_state(rng_after)
        for key, change in changes.items():
            for unit in ("total", "correct"):
                expected = Counter(before[key][unit]) + change[unit]
                if Counter(stats[1.0][key][unit]) != expected:
                    raise ValueError("공식 Counter 독립 재계산 불일치")
        used = Counter()
        occurrences=Counter(uids)
        if (set(predictions[1.0])!=set(all_before_lengths)|set(uids)
                or any(len(values)!=all_before_lengths.get(uid,0)+occurrences[uid] for uid,values in predictions[1.0].items())):
            raise ValueError("공식 prediction의 UID/전체 수량 변경")
        for event in replay:
            uid=event["uid"]; offset=before_lengths[uid]+used[uid]; used[uid]+=1
            observed=predictions[1.0][uid][offset]
            expected=dict(id=f"{uid}_{offset}", pred=event["raw_sentences"]["completions"][event["chosen"]])
            if observed != expected:
                raise ValueError("공식 prediction/원 순서 독립 검산 불일치")
            self.expected_prediction_hashes.setdefault(uid,hashlib.sha256()).update(
                json.dumps(expected,ensure_ascii=False,sort_keys=True,allow_nan=False).encode("utf-8"))
            self.by_uid[uid]["total"]+=1
            self.by_uid[uid]["correct"]+=int(event["chosen"]==event["label"])
            self.ties+=int(event["exact_tie"])
            strings=event["raw_sentences"]["sentences"]
            self.shortest_correct+=int(min(range(2),key=lambda i:len(strings[i]))==event["label"])
            self.longest_correct+=int(max(range(2),key=lambda i:len(strings[i]))==event["label"])
            equal = len(strings[0]) == len(strings[1])
            self.equal_character_length_pairs += int(equal)
            self.shortest_random_tie_expected_correct += .5 if equal else float(len(strings[0])<len(strings[1]))
            self.longest_random_tie_expected_correct += .5 if equal else float(len(strings[0])>len(strings[1]))
            self.score_identity.update(json.dumps(event,ensure_ascii=False,sort_keys=True,allow_nan=False).encode("utf-8"))
            if self.sink:self.sink(event)
        self.rows+=len(replay)

    def summary(self, average):
        if self.predictions is None or set(self.predictions)!=set(self.expected_prediction_hashes):
            raise ValueError("최종 전체 prediction/UID 검산 불일치")
        for uid,expected in self.expected_prediction_hashes.items():
            actual=hashlib.sha256()
            for row in self.predictions[uid]:
                actual.update(json.dumps(row,ensure_ascii=False,sort_keys=True,allow_nan=False).encode("utf-8"))
            if actual.digest()!=expected.digest():raise ValueError("기존 prediction prefix를 포함한 최종 전체 검산 불일치")
        macro=math.fsum(100*v["correct"]/v["total"] for v in self.by_uid.values())/len(self.by_uid)
        if not math.isclose(macro,average,abs_tol=1e-10,rel_tol=1e-12):
            raise ValueError("공식 UID macro의 독립 재계산 불일치")
        correct=sum(v["correct"] for v in self.by_uid.values())
        return dict(rows=self.rows,uids=len(self.by_uid),correct=correct,
            pair_micro_percent=100*correct/self.rows,uid_macro_percent=macro,exact_ties=self.ties,
            by_uid=dict(self.by_uid),shortest_correct=self.shortest_correct,longest_correct=self.longest_correct,
            equal_character_length_pairs=self.equal_character_length_pairs,
            length_tie_policy="FIRST_GOOD_BIAS_IN_RAW_COUNTS; RANDOM_TIE_EXPECTATION_SEPARATE_NOT_OFFICIAL_MODEL_SCORE",
            shortest_random_tie_expected_correct=self.shortest_random_tie_expected_correct,
            longest_random_tie_expected_correct=self.longest_random_tie_expected_correct,
            uniform_expectation_percent=50.,posthoc_always_good_correct=self.rows,
            candidate_order_disclosure="OFFICIAL_GOOD_FIRST; ALWAYS_FIRST=100% IS LABEL_LEAKAGE_NOT_A_MODEL_BASELINE",
            prediction_audit="PER_BATCH_UID_AND_TOTAL_COUNTS_PLUS_FINAL_ALL_PREFIX_AND_SUFFIX_DIGEST",
            scores_sha256=self.score_identity.hexdigest().upper())
