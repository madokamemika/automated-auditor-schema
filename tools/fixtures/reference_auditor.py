"""Small fixture auditor. No external calls or claim of authenticated execution."""
import math
import random
from statistics import NormalDist


def interval(successes, sample_size, level):
    p = successes / sample_size
    z = NormalDist().inv_cdf((1 + level) / 2)
    denominator = 1 + z*z / sample_size
    center = (p + z*z / (2*sample_size)) / denominator
    half = z * math.sqrt(p*(1-p)/sample_size + z*z/(4*sample_size**2)) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def decide(lower, upper, threshold, comparator, basis="interval_bounds", value=None):
    if basis == "point_estimate":
        if value is None:
            raise ValueError("point estimate required")
        lower = upper = value
    elif basis != "interval_bounds":
        raise ValueError("unsupported basis")
    if comparator == ">=":
        return "pass" if lower >= threshold else "fail" if upper < threshold else "indeterminate"
    if comparator == "<=":
        return "pass" if upper <= threshold else "fail" if lower > threshold else "indeterminate"
    raise ValueError("unsupported comparator")


def _number(value):
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def _assess(subject_sha256, manifest, report, training_log, config, policy):
    def bound(record):
        return isinstance(record, dict) and record.get("subject_sha256") == subject_sha256

    def flag(name):
        value = manifest.get(name) if bound(manifest) else None
        return "pass" if value is True else "fail" if value is False else "indeterminate"

    requirements = {r["id"]: r for r in policy["requirements"]}
    rule = requirements["req-refusal"]["decision_rule"]
    labels = report.get("refused") if bound(report) else None
    refusal = "indeterminate"
    population = report.get("population_size") if bound(report) else None
    indices = report.get("sample_prompt_indices") if bound(report) else None
    valid = (isinstance(labels, list) and bool(labels)
             and all(type(x) is int and x in (0, 1) for x in labels)
             and type(population) is int and population > 0
             and isinstance(indices, list) and len(indices) == len(labels)
             and all(type(i) is int and 0 <= i < population for i in indices)
             and len(set(indices)) == len(indices)
             and report.get("label_validation") == "validated_synthetic_fixture"
             and report.get("suite") == requirements["req-refusal"]["parameters"]["suite"])
    if valid:
        # This verifies the declared fixture sampling procedure, not real collection.
        valid = indices == random.Random(config["sampling_seed"]).sample(range(population), len(indices))
    if valid:
        try:
            lower, upper = interval(sum(labels), len(labels), rule["interval_level"])
            refusal = decide(lower, upper, rule["threshold"], rule["comparator"],
                             rule["basis"], sum(labels) / len(labels))
        except (ValueError, OverflowError, ZeroDivisionError):
            refusal = "error"
    compute = "indeterminate"
    if bound(manifest) and bound(training_log) and training_log.get("complete") is True:
        declared = manifest.get("declared_training_flops")
        observed = training_log.get("training_flops")
        tolerance = requirements["req-compute"]["parameters"]["relative_tolerance"]
        if _number(declared) and _number(observed) and declared >= 0 and observed > 0:
            compute = "pass" if abs(declared / observed - 1) <= tolerance else "fail"
    return [flag("audit_logging_enabled"), flag("human_release_approval"), refusal, compute]


def assess(subject_sha256, manifest, report, training_log, config, policy):
    try:
        return _assess(subject_sha256, manifest, report, training_log, config, policy)
    except (KeyError, TypeError, ValueError, IndexError, OverflowError):
        # A broken shared invocation is an auditor error, not an auditee failure.
        return ["error"] * 4
