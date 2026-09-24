import unittest
import test_verify as base
import verify
from assurance import posterior

class AssuranceTests(unittest.TestCase):
    def setUp(self):
        self.doc=verify.load(verify.ROOT/'output/example-result.json')
        self.a=self.doc['evaluations'][2]['assessment']['assurance']
    def reject(self, phrase):
        self.assertTrue(any(phrase in e for e in verify.verify(base.reseal(self.doc))))
    def test_valid(self): self.assertEqual(verify.verify(self.doc),[])
    def test_probability_tamper(self):
        self.a['posterior']['probability']=.99;self.reject('does not recompute')
    def test_class_denominator(self):
        self.doc['execution']['auditor']['judge_validation']['estimated_false_positive_rate']=.01;self.reject('confusion counts')
    def test_sample_size(self):
        self.doc['execution']['auditor']['judge_validation']['validation_sample_size']=100;self.reject('class counts')
    def test_completeness(self):
        self.a['completeness']=.5;self.reject('completeness')
    def test_integrity(self):
        self.a['integrity']=False;self.reject('integrity differs')
    def test_joint_not_invented(self):
        self.doc['conclusion']['overall_confidence']['probability']=.8;self.reject('joint overall')
    def test_null_requires_reason(self):
        self.a['posterior']['basis']='';self.reject('structure:')
    def test_uniform_no_data(self):
        self.assertAlmostEqual(posterior(0,0,.95,'>=',.02,.03),.05,places=10)
    def test_symmetric_posterior(self):
        self.assertAlmostEqual(posterior(50,100,.5,'>=',0,0),.5,places=10)
    def test_agent_confidence_never_changes_verdict(self):
        before=[e['assessment']['status'] for e in self.doc['evaluations']]
        status=self.doc['conclusion']['status']
        for e in self.doc['evaluations']: e['assessment']['agent_confidence']['value']=.001
        self.doc['conclusion']['agent_confidence']['value']=.999
        self.assertEqual(verify.verify(base.reseal(self.doc)),[])
        self.assertEqual(before,[e['assessment']['status'] for e in self.doc['evaluations']])
        self.assertEqual(status,self.doc['conclusion']['status'])
    def test_validation_precedes_run(self):
        self.doc['execution']['auditor']['judge_validation']['validated_at']='2030-01-01T00:00:00Z';self.reject('precede run')
    def test_validation_evidence_counts(self):
        j=self.doc['execution']['auditor']['judge_validation'];j['true_positive']=96;j['false_negative']=4;j['estimated_false_negative_rate']=.04
        self.reject('validation artifact')
    def test_calibration_requires_evidence(self):
        self.doc['conclusion']['agent_confidence']['calibration']['status']='calibrated';self.reject('structure:')
    def test_policy_owns_hypothesis(self):
        self.doc['audit_basis']['requirements'][2]['decision_rule']['bayesian_model']['positive_class']='non-refusal';self.reject('assumptions differ')
