"""Fresh pilot의 명시적 grading metadata만 판정한다. 의미/사고과정의 완전 검증이 아니다."""
from __future__ import annotations
import re
import unicodedata


def normalized(text):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def grade_response(record, response):
    grading = record.get("meta", {}).get("grading")
    if not isinstance(grading, dict):
        return {"status": "unscored", "reason": "missing_grading_metadata", "ranking_eligible": False}
    mode = grading.get("scoring_mode")
    allowed = {"normalized_exact", "required_elements", "choice_and_required_elements",
               "required_elements_and_format", "diagnostic_required_elements"}
    if mode not in allowed:
        return {"status": "unscored", "reason": "unsupported_scoring_mode", "ranking_eligible": False}
    text = normalized(response)
    accepted = [normalized(x) for x in grading.get("accepted_answers", [])]
    required = [normalized(x) for x in grading.get("required_elements", [])]
    forbidden = [normalized(x) for x in grading.get("forbidden_elements", [])]
    if any(not x for x in accepted + required + forbidden):
        raise ValueError("빈 grading element")
    if not accepted and not required:
        return {"status": "unscored", "reason": "no_positive_criterion", "ranking_eligible": False}
    checks = {"nonempty": bool(text), "forbidden_absent": not any(x in text for x in forbidden)}
    if mode == "normalized_exact":
        if not accepted:
            return {"status": "unscored", "reason": "exact_without_answers", "ranking_eligible": False}
        checks["accepted_exact"] = text in accepted
    else:
        checks["required_present"] = all(x in text for x in required)
        if accepted:
            checks["accepted_present"] = any(x in text for x in accepted)
    if mode == "required_elements_and_format":
        constraints = grading.get("format_constraints")
        if not isinstance(constraints, dict) or not constraints:
            return {"status": "unscored", "reason": "missing_format_constraints", "ranking_eligible": False}
        supported = {"sentence_count", "max_sentences", "max_chars", "min_chars", "max_words", "min_words", "prefix"}
        if set(constraints) - supported:
            return {"status": "unscored", "reason": "unsupported_format_constraint",
                    "ranking_eligible": False}
        sentences = len([s for s in re.split(r"[.!?。！？]+", text) if s.strip()])
        for key, value in constraints.items():
            if key == "sentence_count":
                checks[key] = sentences == int(value)
            elif key == "max_sentences":
                checks[key] = sentences <= int(value)
            elif key == "max_chars":
                checks[key] = len(text) <= int(value)
            elif key == "min_chars":
                checks[key] = len(text) >= int(value)
            elif key == "max_words":
                checks[key] = len(text.split()) <= int(value)
            elif key == "min_words":
                checks[key] = len(text.split()) >= int(value)
            elif key == "prefix":
                checks[key] = text.startswith(normalized(value))
    return {"status": "scored", "correct": int(all(checks.values())), "checks": checks,
            "ranking_eligible": bool(grading.get("ranking_eligible", False))
                                and mode != "diagnostic_required_elements",
            "metric_scope": "metadata lexical/format score; not full semantic correctness",
            "scoring_mode": mode}
