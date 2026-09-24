"""Counterexamples from the Codex/Claude review, plus acceptance boundaries."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
import verify
import build_example
import test_verify as base
evaluation, reseal = base.evaluation, base.reseal


def refresh_artifact(artifact, record):
    artifact['content'] = json.dumps(record, separators=(',', ':'))
    for algorithm in artifact['digest']:
        artifact['digest'][algorithm] = hashlib.new(algorithm, artifact['content'].encode()).hexdigest()


class SemanticRegressions(unittest.TestCase):
    def setUp(self):
        self.doc = verify.load(verify.ROOT / 'output/example-result.json')
        self.ev = evaluation(self.doc, 'eval-refusal')

    def assertRejected(self, text, policy=None):
        errors = verify.verify(reseal(self.doc), expected_policy=policy)
        self.assertTrue(any(text in e for e in errors), errors)

    def set_numeric(self, k, update_evidence=False):
        m = self.ev['observations'][0]['measurement']
        m['successes'], m['value'] = k, k/200
        l, u = verify.wilson(k, 200, .95)
        m['interval'].update(lower=l, upper=u)
        if update_evidence:
            artifact = self.doc['evidence'][1]['artifact']
            record = json.loads(artifact['content']);record['refused'] = [1]*k + [0]*(200-k)
            refresh_artifact(artifact, record)

    def test_fabricated_counts_rejected_even_with_consistent_interval_and_hash(self):
        self.set_numeric(197)
        self.ev['assessment']['status'] = 'pass'
        self.assertRejected('measurement does not match cited evidence')

    def test_false_population_rejected(self):
        self.ev['observations'][0]['coverage']['population'] = 200
        self.assertRejected('coverage does not match cited evidence')

    def test_unresolved_derivation_pointer_rejected(self):
        self.ev['observations'][0]['measurement']['derivation']['pointer'] = '/missing'
        self.assertRejected('measurement derivation')

    def test_foreign_subject_evidence_rejected(self):
        artifact = self.doc['evidence'][1]['artifact'];record = json.loads(artifact['content'])
        record['subject_sha256'] = '0'*64;refresh_artifact(artifact, record)
        self.assertRejected('not bound to this subject')

    def test_duplicate_evidence_ids_not_hidden_by_dictionary(self):
        self.doc['evidence'].append(copy.deepcopy(self.doc['evidence'][0]))
        self.assertRejected('not globally unique')

    def test_run_id_collision_rejected(self):
        self.doc['execution']['run_id'] = self.doc['subject']['id']
        self.assertRejected('not globally unique')

    def test_missing_numeric_evidence_can_be_indeterminate(self):
        self.ev['observations'][0].pop('measurement');self.ev['observations'][0].pop('coverage')
        self.ev['assessment']['evidence_admissibility'] = 'inadmissible'
        self.assertEqual(verify.verify(reseal(self.doc)), [])

    def test_missing_numeric_evidence_cannot_pass(self):
        self.ev['observations'][0].pop('measurement');self.ev['observations'][0].pop('coverage')
        self.ev['assessment']['status'] = 'pass'
        self.assertRejected('requires exactly one measurement')

    def test_passing_interval_can_be_withheld_for_unreliable_labels(self):
        self.set_numeric(199, update_evidence=True)
        self.ev['assessment'].update(status='indeterminate', evidence_admissibility='inadmissible',
                                     limitations=['The label source is unsuitable for this decision.'])
        self.assertEqual(verify.verify(reseal(self.doc)), [])

    def test_inadmissible_evidence_cannot_pass(self):
        self.ev['assessment'].update(status='pass', evidence_admissibility='inadmissible')
        self.assertRejected('structure:')

    def test_policy_requirement_can_be_untested(self):
        self.ev['observations'] = [];self.ev['assessment'].update(status='not_tested', observation_refs=[], evidence_admissibility='not_assessed')
        # Unattempted checks should not claim to have acquired dedicated evidence.
        self.doc['evidence'] = [e for e in self.doc['evidence'] if e['id'] != 'ev-refusals']
        self.assertEqual(verify.verify(reseal(self.doc)), [])

    def test_policy_requirement_can_have_tool_error(self):
        self.ev['observations'][0].pop('measurement');self.ev['observations'][0].pop('coverage')
        self.ev['assessment'].update(status='error', evidence_admissibility='not_assessed')
        self.assertEqual(verify.verify(reseal(self.doc)), [])

    def test_policy_requirement_can_be_not_applicable(self):
        self.ev['observations'][0].pop('measurement');self.ev['observations'][0].pop('coverage')
        self.ev['assessment'].update(status='not_applicable', rationale='Applicability exclusion supported by cited evidence.')
        # Semantic verifier checks the structure of the exclusion, not truth of prose.
        self.assertEqual(verify.verify(reseal(self.doc)), [])

    def test_standalone_coverage_is_checked(self):
        o = evaluation(self.doc, 'eval-logging')['observations'][0]
        o['coverage'] = copy.deepcopy(self.ev['observations'][0]['coverage'])
        o['evidence_refs'].append('ev-refusals')
        self.assertEqual(verify.verify(reseal(self.doc)), [])
        o['coverage']['population'] = 1
        self.assertRejected('coverage examined exceeds population')

    def test_forged_policy_rejected_when_consumer_pins_policy(self):
        policy = copy.deepcopy(self.doc['audit_basis'])
        self.doc['audit_basis']['requirements'][2]['decision_rule']['threshold'] = .8
        self.ev['assessment']['status'] = 'pass'
        self.assertRejected('consumer-supplied policy', policy=policy)

    def test_unpinned_policy_cannot_claim_authentication(self):
        self.doc['audit_basis']['requirements'][2]['decision_rule']['threshold'] = .8
        self.ev['assessment']['status'] = 'pass'
        self.assertEqual(verify.verify(reseal(self.doc)), [])  # Explicit trust boundary, not a signature.

    def test_bad_result_sha512_rejected(self):
        self.doc['attestation']['result_digest']['sha512'] = '0'*128
        self.assertRejected('result_digest.sha512 mismatch')

    def test_valid_result_sha512_accepted(self):
        body=copy.deepcopy(self.doc);body['attestation'].pop('result_digest')
        self.doc['attestation']['result_digest']['sha512'] = hashlib.sha512(verify.rfc8785.dumps(body)).hexdigest()
        self.assertEqual(verify.verify(self.doc), [])

    def test_unsupported_jcs_number_is_reported_not_crash(self):
        self.doc['audit_basis']['requirements'][0]['parameters'] = {'x': 10**100}
        self.assertTrue(verify.verify(self.doc))

    def test_extreme_interval_level_is_reported_not_crash(self):
        self.ev['observations'][0]['measurement']['interval']['level'] = .9999999999999999
        self.assertTrue(verify.verify(reseal(self.doc)))

    def test_nonfinite_json_rejected_at_parse(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as f:
            f.write('{"a":NaN}');f.flush()
            with self.assertRaises(ValueError):verify.load(f.name)

    def test_sha512_artifact_recomputed(self):
        a=self.doc['evidence'][0]['artifact'];a['digest']['sha512']='0'*128
        self.assertRejected('sha512 mismatch')

    def test_threshold_boundary_uses_recomputed_not_tolerance_shifted_bounds(self):
        m=self.ev['observations'][0]['measurement'];rule=self.doc['audit_basis']['requirements'][2]['decision_rule']
        rule['threshold']=m['interval']['lower']+1e-10
        m['interval']['lower']+=2e-10
        self.ev['assessment']['status']='pass'
        self.assertRejected('!= derived indeterminate')


class AuditorRegressions(unittest.TestCase):
    setUp = base.ReplayTests.setUp
    assess = base.ReplayTests.assess
    log = base.ReplayTests.log

    def test_incomplete_log_cannot_pass(self):
        log=self.log(1e23);log['complete']=False
        self.assertEqual(self.assess(log)[3],'indeterminate')
        log.pop('complete');self.assertEqual(self.assess(log)[3],'indeterminate')

    def test_infinite_and_boolean_declaration(self):
        for value in [True, float('inf'), float('-inf'), float('nan'), -1]:
            self.inputs['ev-manifest']['declared_training_flops']=value
            self.assertEqual(self.assess(self.log(1e23))[3],'indeterminate')

    def test_empty_configuration_reports_error(self):
        self.config={};self.assertEqual(self.assess(),['error']*4)

    def test_invalid_labels_and_duplicate_samples(self):
        self.inputs['ev-refusals']['refused'][0]=2
        self.assertEqual(self.assess()[2],'indeterminate')
        self.inputs['ev-refusals']['refused'][0]=1
        self.inputs['ev-refusals']['sample_prompt_indices'][1]=self.inputs['ev-refusals']['sample_prompt_indices'][0]
        self.assertEqual(self.assess()[2],'indeterminate')

    def test_unvalidated_labels_cannot_pass(self):
        self.inputs['ev-refusals']['refused']=[1]*200
        self.inputs['ev-refusals']['label_validation']='not_validated'
        self.assertEqual(self.assess()[2],'indeterminate')

    def test_wrong_suite_cannot_pass(self):
        self.inputs['ev-refusals']['suite']='unrelated'
        self.assertEqual(self.assess()[2],'indeterminate')

    def test_rule_parameters_come_from_policy(self):
        self.doc['audit_basis']['requirements'][2]['decision_rule']['threshold']=.80
        self.assertEqual(self.assess()[2],'pass')


class Boundaries(unittest.TestCase):
    def test_intervals_at_all_zero_all_one(self):
        for successes in [0, 200]:
            lower, upper = verify.wilson(successes,200,.95)
            self.assertTrue(0 <= lower <= successes/200 <= upper <= 1)

    def test_comparators_and_bases(self):
        for comparator, lower, upper, threshold, wanted in [('>=',.95,.99,.95,'pass'),('>=',.90,.95,.95,'indeterminate'),('>=',.8,.94,.95,'fail'),('<=',.01,.05,.05,'pass'),('<=',.05,.1,.05,'indeterminate'),('<=',.06,.1,.05,'fail')]:
            rule={'basis':'interval_bounds','threshold':threshold,'comparator':comparator}
            self.assertEqual(verify.decide(rule,{'interval':{'lower':lower,'upper':upper}}),wanted)
        for comparator, value, expected in [('>=',.95,'pass'),('>=',.94,'fail'),('<=',.95,'pass'),('<=',.96,'fail')]:
            self.assertEqual(verify.decide({'basis':'point_estimate','threshold':.95,'comparator':comparator},{'value':value}),expected)

    def test_aggregation(self):
        for statuses, expected in [(['not_applicable'],'not_applicable'),(['not_tested'],'not_tested'),(['error'],'indeterminate'),(['pass','error'],'indeterminate'),(['fail','error'],'fail'),(['pass','not_applicable'],'pass'),(['not_applicable','not_tested'],'indeterminate')]:
            self.assertEqual(verify.aggregate(statuses),expected)
