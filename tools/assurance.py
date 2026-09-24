"""Supplemental assurance: explicit assumptions, never a verdict override."""
import json
import math


def posterior(k, n, threshold, comparator, fpr, fnr):
    """Uniform Beta(1,1) prior; fixed error rates; 20,000 midpoint quadrature."""
    logs = []
    for i in range(20000):
        p = (i + .5) / 20000
        q = p * (1-fnr) + (1-p) * fpr
        if not 0 < q < 1:
            raise ValueError('degenerate judge likelihood')
        logs.append(k*math.log(q)+(n-k)*math.log1p(-q))
    peak = max(logs)
    weights = [math.exp(v-peak) for v in logs]
    return sum(w for i,w in enumerate(weights) if ((i+.5)/20000 >= threshold if comparator == '>=' else (i+.5)/20000 <= threshold))/sum(weights)


def check(doc):
    errors=[]
    evidence={e['id']:e for e in doc['evidence']}
    rules={r['id']:r.get('decision_rule') for r in doc['audit_basis']['requirements']}
    for ev in doc['evaluations']:
        a=ev['assessment'].get('assurance')
        if not a: continue
        def err(msg): errors.append('assurance: '+ev['id']+': '+msg)
        refs={ref for o in ev['observations'] for ref in o['evidence_refs']}
        bound=bool(refs)
        for ref in refs:
            try:
                record=json.loads(evidence[ref]['artifact']['content'])
                bound &= record.get('subject_sha256') == doc['subject']['artifact']['digest']['sha256']
            except (KeyError,ValueError,AttributeError): bound=False
        # Called only after all embedded artifact and result digests verified.
        if not bound and ev['assessment']['status'] in ('pass','fail'): err('unbound evidence cannot establish pass/fail')
        if a['integrity'] != bound: err('integrity differs from verified byte/subject binding')
        if a['obtained_evidence_items'] > a['required_evidence_items'] or abs(a['completeness']-a['obtained_evidence_items']/a['required_evidence_items']) > 1e-9: err('completeness differs from declared item counts')
        j=doc['execution']['auditor'].get('judge_validation')
        if a['judgment_source'] in ('ai_judge','hybrid') and not j: err('judge validation required for AI method')
        if j:
            try:
                stored=json.loads(j['validation_set']['content'])
                fields=('true_positive','false_positive','true_negative','false_negative','positive_class')
                if any(stored.get(key)!=j[key] for key in fields): err('validation counts differ from validation artifact')
                from datetime import datetime
                if datetime.fromisoformat(j['validated_at'].replace('Z','+00:00')) > datetime.fromisoformat(doc['execution']['started_at'].replace('Z','+00:00')): err('judge validation must precede run')
            except (KeyError,ValueError,AttributeError): err('invalid validation artifact')
            tp,fp,tn,fn=(j[x] for x in ('true_positive','false_positive','true_negative','false_negative'))
            if tp+fp+tn+fn != j['validation_sample_size'] or fp+tn == 0 or fn+tp == 0: err('invalid validation class counts');continue
            if abs(j['estimated_false_positive_rate']-fp/(fp+tn))>1e-9 or abs(j['estimated_false_negative_rate']-fn/(fn+tp))>1e-9: err('error rates differ from confusion counts')
        c=a['posterior']
        if c['probability'] is None:
            if c['model']!='unavailable' or 'prior' in c: err('null confidence requires unavailable model and no prior')
        else:
            ms=[o['measurement'] for o in ev['observations'] if 'measurement' in o]
            rule=rules[ev['requirement_ref']]
            if c['model']!='beta_binomial_fixed_misclassification_grid_v1' or c.get('prior')!={'alpha':1,'beta':1} or not j or len(ms)!=1 or not rule or rule['kind']!='proportion' or c['event']!='true_population_positive_rate_satisfies_policy_threshold': err('unsupported confidence model or event');continue
            model=rule.get('bayesian_model')
            if not model or any(c[key]!=model[key] for key in ('prior','event','model')) or j['positive_class']!=model['positive_class']:
                err('posterior assumptions differ from policy');continue
            m=ms[0]
            expected=posterior(m['successes'],m['interval']['sample_size'],rule['threshold'],rule['comparator'],j['estimated_false_positive_rate'],j['estimated_false_negative_rate'])
            if abs(c['probability']-expected)>1e-6: err('Bayesian probability does not recompute')
    overall=doc['conclusion'].get('overall_confidence')
    if overall and (overall['probability'] is not None or overall['model']!='unavailable' or 'prior' in overall):
        errors.append('assurance: joint overall confidence unsupported without a joint model')
    return errors
