"""A completed physical arm must not fail on the existing flat DEV schema."""
import json
import unittest
from scripts import p108b_policy as policy
from scripts import diag_p108b_target_write as driver


class TargetProgressTests(unittest.TestCase):
    def test_existing_empty_dev_summary_is_serializable_without_nested_fields(self):
        record=dict(name='example',fit=dict(exact=3),dev=policy.dev_summary([]),lost_original_protected_ids=['p1'],norm_match='NET_MATCHED')
        result=driver.progress(record)
        self.assertEqual(result['dev_target'],0);self.assertEqual(result['fit'],3);self.assertEqual(result['lost'],1)
        self.assertEqual(json.loads(json.dumps(result)),result)


if __name__=='__main__':unittest.main()
