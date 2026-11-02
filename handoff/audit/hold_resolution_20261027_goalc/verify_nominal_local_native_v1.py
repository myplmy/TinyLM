"""Replay the existing native-source verifier for every narrow alias match."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent


def once(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new, 1)


source = (AUDIT / 'verify_repeat_local_native_v1.py').read_text(encoding='utf-8')
source = once(source, 'from scripts import p106b_hold_resolution_repeat_context_v1 as context',
'''import importlib.util
helper_path = AUDIT / 'typed_nominal_local_alias_v1.py'
helper_spec = importlib.util.spec_from_file_location('nominal_alias', helper_path)
context = importlib.util.module_from_spec(helper_spec)
helper_spec.loader.exec_module(context)''')
source = once(source, '"repeat_local_proof_candidates_v1"', '"nominal_local_alias_candidates_v1"')
source = once(source, '"repeat_local_native_proofs_v1"', '"nominal_local_native_proofs_v1"')
source = once(source, 'len(sources) == 40, "all40 proof sources must be available"',
    'len(sources) == census["counts"]["proof_matches"] == 223, "all223 proof sources must be available"')
source = once(source, '''        clean = result.get("candidate", result["text"])
        proof = context.prove(clean)
        agrees = inv.sha(clean) == targets[key]["candidate_sha256"] and proof == targets[key]["proof"]''',
'''        baseline = result.get("candidate", result["text"])
        proof = context.prove(baseline)
        agrees = inv.sha(baseline) == targets[key]["v26_candidate_sha256"] and proof == targets[key]["proof"]
        clean = proof["candidate"] if proof is not None else baseline''')
source = once(source, 'remaining.discard("MAIN_BODY_REPETITION_REQUIRES_CONTEXT")',
    'remaining.discard("UNRESOLVED_FIELD_OR_TITLE")\n        remaining.update(policy.literal_holes(clean))')
source = once(source, 'ALL40_FRESH_NATIVE_AND_REGENERATION_CHECKED_REVIEW_STILL_REQUIRED',
    'ALL223_FRESH_NATIVE_ALIAS_AND_REGENERATION_CHECKED_REVIEW_STILL_REQUIRED')
source = once(source, 'ROOT / "scripts/p106b_hold_resolution_repeat_context_v1.py", Path(__file__)',
    'helper_path, AUDIT / "verify_repeat_local_native_v1.py", Path(__file__)')
exec(compile(source, str(Path(__file__)), 'exec'))
