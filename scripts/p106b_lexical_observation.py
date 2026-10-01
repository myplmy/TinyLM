"""Bounded character observations, never admission/retry/semantic decisions.

within compares this response only; recent adds a bounded prior-answer queue.
No models, normalization of numbers/negation/case, universal quality threshold,
or global corpus index. Later embedding/NLI review is a separate artifact.
"""
from collections import deque
import time


def overlap(a, b, n):
    if min(len(a), len(b)) < n:
        return {"n": n, "status": "SHORT_TEXT", "jaccard": None,
                "contain_a_in_b": None, "contain_b_in_a": None, "common_examples": []}
    sa, sb = {a[i:i+n] for i in range(len(a)-n+1)}, {b[i:i+n] for i in range(len(b)-n+1)}
    common = sa & sb
    return {"n": n, "status": "OBSERVED", "jaccard": len(common)/len(sa | sb),
            "contain_a_in_b": len(common)/len(sa), "contain_b_in_a": len(common)/len(sb),
            "common_examples": sorted(common)[:4]}


class TextObserver:
    def __init__(self, mode="within", window=32, maximum_bytes=262144):
        if mode not in ("within", "recent") or type(window) is not int or not 1 <= window <= 64:
            raise ValueError("bounded within/recent observation required")
        if type(maximum_bytes) is not int or not 1024 <= maximum_bytes <= 1048576:
            raise ValueError("bounded queue memory required")
        self.mode, self.window, self.maximum_bytes = mode, window, maximum_bytes
        self.history, self.bytes = deque(), 0

    def observe(self, request_id, question, answers):
        if len(answers) > 4 or any(len(a) > 6000 for a in answers) or len(question) > 2000:
            raise ValueError("observation input exceeds pinned wire contract")
        began = time.perf_counter()
        pairs, cross = [], []
        def pair(left, right, left_text, right_text):
            return {"left": left, "right": right,
                    "scores": [overlap(left_text, right_text, n) for n in (3, 5)],
                    "right_question": question, "right_answer": right_text,
                    "left_answer": left_text}
        for i, answer in enumerate(answers):
            for j in range(i):
                pairs.append(pair(f"{request_id}:a{j+1}", f"{request_id}:a{i+1}", answers[j], answer))
            if self.mode == "recent":
                for previous in self.history:
                    candidate = pair(previous["id"], f"{request_id}:a{i+1}", previous["answer"], answer)
                    candidate["left_question"] = previous["question"]
                    cross.append(candidate)
        # Top-three is only a bounded display budget, not a defect threshold.
        cross.sort(key=lambda p: p["scores"][1]["jaccard"] or 0, reverse=True)
        pairs.extend(cross[:3])
        if self.mode == "recent":
            for i, answer in enumerate(answers):
                size = len((question + answer).encode("utf-8"))
                if size > self.maximum_bytes:
                    continue
                self.history.append({"id": f"{request_id}:a{i+1}", "question": question,
                                     "answer": answer, "bytes": size})
                self.bytes += size
                while len(self.history) > self.window or self.bytes > self.maximum_bytes:
                    self.bytes -= self.history.popleft()["bytes"]
        return {"mode": self.mode, "pairs": pairs, "pair_count": len(pairs),
                "cross_pairs_examined": len(cross), "queue_rows": len(self.history),
                "queue_text_bytes": self.bytes, "observation_wall_sec": time.perf_counter()-began,
                "effect": "WARNING_ONLY_NO_ADMISSION_RETRY_OR_TRUTH_DECISION",
                "review_status": "CONTEXT_REVIEW_NOT_RUN"}
