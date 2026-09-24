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
        self.a['confidence']['probability']=.99;self.reject('does not recompute')
    def test_class_denominator(self):
        self.a['judge_validation']['estimated_false_positive_rate']=.01;self.reject('confusion counts')
    def test_sample_size(self):
        self.a['judge_validation']['validation_sample_size']=100;self.reject('class counts')
    def test_completeness(self):
        self.a['completeness']=.5;self.reject('completeness')
    def test_integrity(self):
        self.a['integrity']=False;self.reject('integrity differs')
    def test_joint_not_invented(self):
        self.doc['conclusion']['overall_confidence']['probability']=.8;self.reject('joint overall')
    def test_null_requires_reason(self):
        self.a['confidence']['basis']='';self.reject('structure:')
    def test_uniform_no_data(self):
        self.assertAlmostEqual(posterior(0,0,.95,'>=',.02,.03),.05,places=10)
    def test_symmetric_posterior(self):
        self.assertAlmostEqual(posterior(50,100,.5,'>=',0,0),.5,places=10)
