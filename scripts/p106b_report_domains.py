"""Separated reporting: operational evidence never substitutes for semantic truth.

No scoring model, word matcher, input reads or side effects. A later local/GPT
review can attach to frozen source identities in a separate review artifact.
"""
def separated_report(report):
    def known_count(key):
        value = report.get(key)
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError("count must be a nonnegative integer or unmeasured null: " + key)
        return value
    return {
        "schema": "P106B_REPORT_DOMAINS_V1",
        "operational": {"status": report.get("status"),
            "exit_code": report.get("exit_code"), "requests": known_count("raw_rows"),
            "response_status_counts": report.get("status_counts"),
            "technical_gate_passed": report.get("technical_gate_passed"),
            "admission_is_semantic_approval": False},
        "corpus": {"canonical_rows": known_count("canonical_rows"),
            "selected_rows": known_count("selected_rows"),
            "conversation_tokens": known_count("student_conversation_tokens"),
            "assistant_targets": known_count("assistant_targets"),
            "raw_sha256": report.get("raw_concat_sha256"),
            "canonical_sha256": report.get("canonical_concat_sha256"),
            "selected_sha256": report.get("selected_concat_sha256"),
            "formal_train_ready": False, "label_status": "PSEUDO_UNVERIFIED"},
        "cost": {"teacher_completion_tokens": known_count("teacher_completion_tokens"),
            "completion_token_scope": "reasoning plus final, not student conversation tokens",
            "request_sum_sec": report.get("request_sum_sec"),
            "whole_wall_sec": report.get("whole_wall_sec"),
            "processed_student_tokens": report.get("processed_conversation_tokens")},
        "posthoc_review": {"status": "NOT_REVIEWED", "reviewed_rows": None,
            "fact_correctness": None, "naturalness": None, "review_artifact": None,
            "review_input_identity": report.get("selected_concat_sha256") or report.get("canonical_concat_sha256"),
            "permitted_reviewers": ["local_model", "GPT", "human"],
            "reviewer_run": "NOT_RUN"},
        "student_effect": {"status": "RECORDED_NOT_GENERAL_QUALITY" if "student_answers" in report else "NOT_RUN",
            "first_answer_assessment": report.get("student_answers"),
            "parent_answer_assessment": report.get("parent_answers"),
            "native_ce_delta": report.get("base_full_val_delta"),
            "operational_safety": report.get("operational_safety"),
            "broad_capability_claim": "NOT_ESTABLISHED"},
        "null_policy": "null means not recorded/evaluated, never zero failures or PASS",
    }
