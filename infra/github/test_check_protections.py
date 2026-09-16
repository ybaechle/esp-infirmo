import json
import unittest
from pathlib import Path

from check_protections import Unknown, audit_branch


class ProtectionAuditTest(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((Path(__file__).parent / "rulesets/branch-main.json").read_text())

    def check(self, rules, protected=False, legacy=None):
        def read(path, **kwargs):
            if path == "repos/example/repo/branches/main":
                return {"name": "main", "protected": protected, "commit": {"sha": "a" * 40}}
            if path == "repos/example/repo/rules/branches/main?per_page=100":
                self.assertTrue(kwargs["paginated"])
                if isinstance(rules, Exception):
                    raise rules
                return rules
            if path == "repos/example/repo/branches/main/protection":
                if isinstance(legacy, Exception):
                    raise legacy
                return legacy
            self.fail(f"Unexpected endpoint: {path}")
        return audit_branch("example/repo", "main", self.policy, read)

    def test_actual_branch_rules_and_missing_rules(self):
        self.assertEqual(self.check(self.policy["rules"])["status"], "pass")
        missing = self.check([])
        self.assertEqual(missing["status"], "missing")
        self.assertIn("required check: Quality gate", missing["missing"])
        self.policy["conditions"]["ref_name"]["include"] = ["refs/heads/other"]
        with self.assertRaises(Unknown):
            self.check(self.policy["rules"])

    def test_union_with_legacy_and_strict_gate(self):
        legacy = {"required_pull_request_reviews": {
            "required_approving_review_count": 1, "dismiss_stale_reviews": True},
            "required_conversation_resolution": {"enabled": True},
            "allow_force_pushes": {"enabled": False}, "allow_deletions": {"enabled": False}}
        rules = [rule for rule in self.policy["rules"] if rule["type"] == "required_status_checks"]
        self.assertEqual(self.check(rules, True, legacy)["status"], "pass")
        legacy["required_status_checks"] = {"strict": True, "contexts": ["Quality gate"]}
        self.assertEqual(self.check([], True, legacy)["status"], "pass")
        del legacy["required_status_checks"]
        rules[0]["parameters"]["strict_required_status_checks_policy"] = False
        # The expected file remains strict; only observed rules are weakened.
        self.policy = json.loads((Path(__file__).parent / "rulesets/branch-main.json").read_text())
        self.assertEqual(self.check(rules, True, legacy)["status"], "missing")

    def test_unreadable_is_unknown_not_missing(self):
        self.assertEqual(self.check(Unknown("Forbidden", "403"))["status"], "unknown")
        self.assertEqual(self.check([], True, Unknown("Not Found", "404"))["status"], "unknown")
        self.assertEqual(self.check([], True, Unknown("Branch not protected", "404"))["status"], "missing")


if __name__ == "__main__":
    unittest.main()
