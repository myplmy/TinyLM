"""Keep stage arithmetic; require guard4 and remove an unmeasured cause ranking."""
from pathlib import Path
import hashlib
import sys

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
from active_guard_v4_preflight_v1 import activate, assert_no_protected_opens
activate()
frozen = AUDIT/'record_hold_stages_v2.py'
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == '585041E4FF53AB2C1857E76E8863B9E4378B22C89086DE733D4F480088430E4A'


def transform_current(code):
    replacements = [
        ("'GUARDED_SOURCE_METADATA_CONTRACT_V3'", "'GUARDED_SOURCE_METADATA_CONTRACT_V4'"),
        ('7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306',
         '59CA9419990CD1D6968EA9B1E7EF4416D418C8C460EDD8074E98DA9BF5FCEF7D'),
        ("    direct_cause='Root delayed exact selection, full roster and cache integration while completed reviews and individual unresolved cases accumulated.',",
         "    direct_cause='Most remaining positions have no first review. Review throughput, admission/cache waiting, and recorded rework are distinct observed constraints; no timing-causal ranking is established.',"),
        ("'An observed cache5 full CPU build and independent consumer together cost about 48.94 minutes.'",
         "'The latest verified full build and consumer duration is recorded separately; recent interrupted or rejected attempts are not cache success.'"),
        ('receipt = dict(status=',
         "previous_stage = read(ROOT/c['previous_stage_report'], c['previous_stage_report_sha256'])\nnow = datetime.now(timezone.utc)\ninterval_seconds = (now-datetime.fromisoformat(previous_stage['recorded_at'])).total_seconds()\nfirst_review_delta = len(fresh)-previous_stage['fresh_first_review_unique']\nposition_delta = fresh_positions-previous_stage['fresh_first_review_positions']\nreceipt = dict(status="),
        ('recorded_at=datetime.now(timezone.utc).isoformat()', 'recorded_at=now.isoformat()'),
        ('    raw_original_or_candidate_TXT_opens=0, goal_complete=False, training_authorized=False,',
         "    active_guard_sha256='59CA9419990CD1D6968EA9B1E7EF4416D418C8C460EDD8074E98DA9BF5FCEF7D',\n    official_stage_partition=dict(first_unreviewed=unread_positions,first_reviewed_not_ROOT_admitted=fresh_positions-root_positions,ROOT_admitted_cache_pending=c['official_hold_positions']-selection['expected_roster_HOLD_positions'],prior_reviewed_HOLD=38),\n    comparison_with_previous=dict(previous_recorded_at=previous_stage['recorded_at'],elapsed_seconds=interval_seconds,new_first_review_unique=first_review_delta,new_first_review_positions=position_delta,new_counter_saved=counter['records']-previous_stage['counter_saved'],observed_first_review_unique_per_hour=first_review_delta*3600/interval_seconds,rate_is_not_an_ETA=True),\n    recent_cache_limits=c.get('recent_cache_limits',[]),\n    raw_original_or_candidate_TXT_opens=0, goal_complete=False, training_authorized=False,"),
        ('for path in [frozen, Path(__file__), RECORDER_V1_PATH]:',
         "for path in [frozen, Path(__file__), RECORDER_V1_PATH, AUDIT/'record_hold_stages_v2.py', AUDIT/'active_guard_v4_preflight_v1.py']:"),
        ("out = AUDIT/c['output_basename']",
         "from active_guard_v4_preflight_v1 import assert_no_protected_opens\nassert_no_protected_opens()\nassert sum(receipt['official_stage_partition'].values()) == c['official_hold_positions']\nout = AUDIT/c['output_basename']")]
    for before, after in replacements:
        assert code.count(before) == 1, before
        code = code.replace(before, after)
    return code


code = raw.decode('utf-8')
before = "exec(compile(code,str(frozen),'exec'),"
assert code.count(before) == 1
code = code.replace(before, "code = TRANSFORM_CURRENT(code)\n" + before)
exec(compile(code, str(frozen), 'exec'), dict(__name__='guard4_stages_v3_actual_run',
    __file__=str(Path(__file__)), TRANSFORM_CURRENT=transform_current))
assert_no_protected_opens()
