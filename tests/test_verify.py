"""Negative and replay tests for the reference verifier. Run: python3 -m unittest discover tests"""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import build_example  # noqa: E402
import verify  # noqa: E402

EXAMPLE = verify.ROOT / "output" / "example-result.json"


def reseal(doc):
    """Recompute the result digest so a test isolates one semantic defect."""
    doc["attestation"]["result_digest"]["sha256"] = verify.result_digest(doc)
    return doc


def evaluation(doc, id_):
    return next(e for e in doc["evaluations"] if e["id"] == id_)


class ExampleTests(unittest.TestCase):
    def setUp(self):
        self.doc = verify.load(EXAMPLE)

    def assertRejected(self, doc, fragment):
        errors = verify.verify(doc)
        self.assertTrue(any(fragment in e for e in errors), f"expected {fragment!r} in {errors}")

    def test_example_verifies(self):
        self.assertEqual(verify.verify(self.doc), [])

    def test_example_is_reproducible_from_fixtures(self):
        self.assertEqual(build_example.build(), self.doc)

    def test_tampered_evidence_bytes(self):
        self.doc["evidence"][0]["artifact"]["content"] += " "
        self.assertRejected(reseal(self.doc), "sha256 mismatch")

    def test_tampered_result_without_resealing(self):
        evaluation(self.doc, "eval-approval")["assessment"]["rationale"] = "Edited."
        self.assertRejected(self.doc, "result_digest.sha256 mismatch")

    def test_status_must_follow_decision_rule(self):
        evaluation(self.doc, "eval-refusal")["assessment"]["status"] = "pass"
        self.assertRejected(reseal(self.doc), "!= derived indeterminate")

    def test_conclusion_must_be_derived(self):
        self.doc["conclusion"]["status"] = "indeterminate"
        self.assertRejected(reseal(self.doc), "conclusion.status")

    def test_coverage_complete_must_be_derived(self):
        self.doc["conclusion"]["coverage_complete"] = True
        self.assertRejected(reseal(self.doc), "coverage_complete")

    def test_interval_must_recompute(self):
        evaluation(self.doc, "eval-refusal")["observations"][0]["measurement"]["interval"]["lower"] = 0.95
        self.assertRejected(reseal(self.doc), "interval does not recompute")

    def test_measurement_requires_policy_rule(self):
        del self.doc["audit_basis"]["requirements"][2]["decision_rule"]
        self.assertRejected(reseal(self.doc), "decision_rule")

    def test_measurement_must_follow_policy_level(self):
        self.doc["audit_basis"]["requirements"][2]["decision_rule"]["interval_level"] = 0.9
        self.assertRejected(reseal(self.doc), "does not follow")

    def test_unresolved_evidence_ref(self):
        evaluation(self.doc, "eval-logging")["observations"][0]["evidence_refs"] = ["ev-missing"]
        self.assertRejected(reseal(self.doc), "unresolved evidence ref")

    def test_duplicate_ids(self):
        evaluation(self.doc, "eval-approval")["id"] = "eval-logging"
        self.assertRejected(reseal(self.doc), "not globally unique")

    def test_every_requirement_evaluated_once(self):
        self.doc["evaluations"].pop()
        self.assertRejected(reseal(self.doc), "exactly once")

    def test_timestamps_ordered(self):
        self.doc["execution"]["ended_at"] = "2026-09-24T15:00:00Z"
        self.assertRejected(reseal(self.doc), "started_at <= ended_at <= generated_at")

    def test_schema_rejects_trailing_newline_in_id(self):
        self.doc["subject"]["id"] = "subject-ai-deployment\n"
        self.assertRejected(self.doc, "structure: subject/id")

    def test_schema_rejects_two_measured_observations(self):
        ev = evaluation(self.doc, "eval-refusal")
        second = copy.deepcopy(ev["observations"][0])
        second["id"] = "obs-refusal-2"
        ev["observations"].append(second)
        self.assertRejected(self.doc, "structure: evaluations/2")

    def test_schema_rejects_not_tested_with_observations(self):
        evaluation(self.doc, "eval-logging")["assessment"]["status"] = "not_tested"
        self.assertRejected(self.doc, "structure: evaluations/0")

    def test_schema_rejects_pass_without_observations(self):
        ev = evaluation(self.doc, "eval-compute")
        ev["assessment"]["status"] = "pass"
        ev["observations"], ev["assessment"]["observation_refs"] = [], []
        self.assertRejected(self.doc, "structure: evaluations/3")

    def test_formats_are_asserted(self):
        self.doc["subject"]["artifact"]["uri"] = "not a uri"
        self.doc["metadata"]["generated_at"] = "2026-13-40T00:00:00Z"
        self.assertRejected(self.doc, "is not a 'uri'")
        self.assertRejected(self.doc, "is not a 'date-time'")

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError):
            json.loads('{"a": 1, "a": 2}', object_pairs_hook=verify._reject_duplicate_keys)


class ReplayTests(unittest.TestCase):
    """The embedded reference auditor reproduces the recorded statuses and handles invalid input."""

    def setUp(self):
        self.doc = verify.load(EXAMPLE)
        self.ns = {}
        exec(self.doc["execution"]["auditor"]["implementation"]["content"], self.ns)
        self.inputs = {e["id"]: json.loads(e["artifact"]["content"]) for e in self.doc["evidence"]}
        self.config = json.loads(self.doc["execution"]["auditor"]["configuration"]["content"])
        self.subject = self.doc["subject"]["artifact"]["digest"]["sha256"]

    def assess(self, training_log=None, subject=None):
        return self.ns["assess"](subject or self.subject, self.inputs["ev-manifest"],
                                 self.inputs["ev-refusals"], training_log, self.config)

    def log(self, flops):
        return {"subject_sha256": self.subject, "training_flops": flops}

    def test_replay_matches_recorded_statuses(self):
        self.assertEqual(self.assess(), [e["assessment"]["status"] for e in self.doc["evaluations"]])

    def test_configuration_matches_policy_rule(self):
        rule = self.doc["audit_basis"]["requirements"][2]["decision_rule"]
        self.assertEqual((self.config["refusal_threshold"], self.config["interval_level"]),
                         (rule["threshold"], rule["interval_level"]))

    def test_invalid_training_totals_are_indeterminate(self):
        for flops in (0, -1e23, float("nan"), "1e23", True, None):
            with self.subTest(flops=flops):
                self.assertEqual(self.assess(self.log(flops))[3], "indeterminate")

    def test_compute_pass_and_fail(self):
        self.assertEqual(self.assess(self.log(1.04e23))[3], "pass")
        self.assertEqual(self.assess(self.log(1.2e23))[3], "fail")

    def test_evidence_for_another_subject_is_indeterminate(self):
        self.assertEqual(self.assess(self.log(1e23), subject="0" * 64), ["indeterminate"] * 4)


if __name__ == "__main__":
    unittest.main()
