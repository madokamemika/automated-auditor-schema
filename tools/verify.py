#!/usr/bin/env python3
"""Reference verifier for automated auditor results (schema 0.4.0).

Implements the three-layer validation contract in output/README.md:
structure (JSON Schema with format checking), semantics (cross-object rules
JSON Schema cannot express) and integrity (artifact and result digests).

Usage: python3 tools/verify.py [result.json ...]
Exit status 0 when every file passes, 1 otherwise.
"""
import copy
import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from statistics import NormalDist

import rfc8785
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "output" / "auditor-result.schema.json"
UNRESOLVED = {"indeterminate", "error", "not_tested"}
TOLERANCE = 1e-9


def _reject_duplicate_keys(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError(f"duplicate object keys: {sorted(k for k in set(keys) if keys.count(k) > 1)}")
    return dict(pairs)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f, object_pairs_hook=_reject_duplicate_keys)


def _time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def wilson(successes, n, level):
    p = successes / n
    z = NormalDist().inv_cdf((1 + level) / 2)
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return center - half, center + half


def decide(rule, measurement):
    if rule["basis"] == "point_estimate":
        lower = upper = measurement["value"]
    else:
        lower, upper = measurement["interval"]["lower"], measurement["interval"]["upper"]
    t = rule["threshold"]
    if rule["comparator"] == ">=":
        return "pass" if lower >= t else "fail" if upper < t else "indeterminate"
    return "pass" if upper <= t else "fail" if lower > t else "indeterminate"


def aggregate(statuses):
    if "fail" in statuses:
        return "fail"
    if all(s == "not_tested" for s in statuses):
        return "not_tested"
    if any(s in UNRESOLVED for s in statuses):
        return "indeterminate"
    if all(s == "not_applicable" for s in statuses):
        return "not_applicable"
    return "pass"


def artifacts(node, path=""):
    """Yield (json_path, artifact) for every artifact object in the document."""
    if isinstance(node, dict):
        if {"uri", "media_type", "digest"} <= node.keys():
            yield path, node
        for key, value in node.items():
            yield from artifacts(value, f"{path}/{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from artifacts(value, f"{path}/{i}")


def result_digest(doc):
    body = copy.deepcopy(doc)
    del body["attestation"]["result_digest"]
    return hashlib.sha256(rfc8785.dumps(body)).hexdigest()


def check_structure(doc, schema):
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    return [f"structure: {'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
            for e in sorted(validator.iter_errors(doc), key=lambda e: list(map(str, e.absolute_path)))]


def check_semantics(doc):
    errors = []
    err = errors.append
    requirements = {r["id"]: r for r in doc["audit_basis"]["requirements"]}
    evidence = {e["id"]: e for e in doc["evidence"]}

    ids = [doc["subject"]["id"], *requirements, *evidence]
    for ev in doc["evaluations"]:
        ids += [ev["id"], *(o["id"] for o in ev["observations"])]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates or len(requirements) != len(doc["audit_basis"]["requirements"]):
        err(f"semantics: IDs are not globally unique: {duplicates}")

    covered = [ev["requirement_ref"] for ev in doc["evaluations"]]
    if sorted(covered) != sorted(requirements):
        err(f"semantics: evaluations must cover each requirement exactly once (got {covered})")

    cited_evidence = set()
    for ev in doc["evaluations"]:
        where = f"semantics: {ev['id']}"
        requirement = requirements.get(ev["requirement_ref"])
        observations = {o["id"]: o for o in ev["observations"]}
        assessment = ev["assessment"]
        refs = assessment["observation_refs"]
        if set(refs) != set(observations):
            err(f"{where}: assessment must cite exactly the evaluation's own observations")
        for obs in ev["observations"]:
            for ref in obs["evidence_refs"]:
                if ref not in evidence:
                    err(f"{where}/{obs['id']}: unresolved evidence ref {ref}")
                cited_evidence.add(ref)
        measured = [o for o in ev["observations"] if "measurement" in o]
        rule = requirement.get("decision_rule") if requirement else None
        if bool(rule) != bool(measured):
            err(f"{where}: a measured observation is required exactly when the requirement has a decision_rule")
        for obs in measured:
            m, iv = obs["measurement"], obs["measurement"]["interval"]
            if m["successes"] > iv["sample_size"]:
                err(f"{where}: successes exceed sample_size")
                continue
            if abs(m["value"] - m["successes"] / iv["sample_size"]) > TOLERANCE:
                err(f"{where}: value != successes / sample_size")
            lower, upper = wilson(m["successes"], iv["sample_size"], iv["level"])
            if abs(lower - iv["lower"]) > TOLERANCE or abs(upper - iv["upper"]) > TOLERANCE:
                err(f"{where}: interval does not recompute (expected [{lower}, {upper}])")
            if not iv["lower"] <= m["value"] <= iv["upper"]:
                err(f"{where}: value outside interval")
            coverage = obs.get("coverage")
            if coverage and not (coverage["examined"] == iv["sample_size"] <= coverage["population"]):
                err(f"{where}: coverage must satisfy examined == sample_size <= population")
            if rule:
                if iv["level"] != rule["interval_level"] or iv["method"] != rule["interval_method"]:
                    err(f"{where}: measurement interval does not follow the requirement's decision_rule")
                elif assessment["status"] != decide(rule, m):
                    err(f"{where}: status {assessment['status']} != derived {decide(rule, m)}")
        if requirement is None:
            err(f"{where}: unresolved requirement_ref {ev['requirement_ref']}")

    uncited = sorted(set(evidence) - cited_evidence)
    if uncited:
        err(f"semantics: evidence not cited by any observation: {uncited}")

    statuses = [ev["assessment"]["status"] for ev in doc["evaluations"]]
    conclusion = doc["conclusion"]
    if conclusion["status"] != aggregate(statuses):
        err(f"semantics: conclusion.status {conclusion['status']} != derived {aggregate(statuses)}")
    if conclusion["coverage_complete"] != (not UNRESOLVED & set(statuses)):
        err("semantics: coverage_complete does not match evaluation statuses")

    run = doc["execution"]
    generated = _time(doc["metadata"]["generated_at"])
    if not _time(run["started_at"]) <= _time(run["ended_at"]) <= generated:
        err("semantics: require started_at <= ended_at <= generated_at")
    for e in doc["evidence"]:
        if _time(e["acquired_at"]) > generated:
            err(f"semantics: {e['id']} acquired after generated_at")
    return errors


def check_integrity(doc):
    errors = []
    for path, artifact in artifacts(doc):
        if "content" not in artifact:
            errors.append(f"integrity: {path}: bytes not embedded; digest unverified")
            continue
        data = artifact["content"].encode("utf-8")
        for algorithm, expected in artifact["digest"].items():
            if hashlib.new(algorithm, data).hexdigest() != expected:
                errors.append(f"integrity: {path}: {algorithm} mismatch")
    if result_digest(doc) != doc["attestation"]["result_digest"]["sha256"]:
        errors.append("integrity: attestation.result_digest.sha256 mismatch")
    return errors


def verify(doc, schema=None):
    """Return a list of error strings; empty means the result verified."""
    schema = schema or load(SCHEMA_PATH)
    errors = check_structure(doc, schema)
    if errors:
        return errors  # semantic checks assume a structurally valid document
    return check_semantics(doc) + check_integrity(doc)


def main(paths):
    schema = load(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    failed = False
    for path in paths or [ROOT / "output" / "example-result.json"]:
        try:
            errors = verify(load(path), schema)
        except ValueError as exc:
            errors = [f"parse: {exc}"]
        failed |= bool(errors)
        print(f"{'FAIL' if errors else 'OK  '} {path}")
        for e in errors:
            print(f"     {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
