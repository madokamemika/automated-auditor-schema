#!/usr/bin/env python3
"""Reference verifier for automated auditor results (schema 0.6.0).

Implements the three-layer validation contract in output/README.md:
structure (JSON Schema with format checking), semantics (cross-object rules
JSON Schema cannot express) and integrity (artifact and result digests).

Usage: python3 tools/verify.py [result.json ...]
Exit status 0 when every file passes, 1 otherwise.
"""
import argparse
import copy
import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from statistics import NormalDist

import assurance
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
        return json.load(f, object_pairs_hook=_reject_duplicate_keys,
                         parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-JSON number: {value}")))


def _time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def pointer_value(value, pointer):
    """Resolve RFC 6901 without executing code or fetching external resources."""
    if not pointer:
        return value
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not token.isascii() or not token.isdecimal() or (len(token) > 1 and token[0] == "0"):
                raise ValueError("invalid array index")
            value = value[int(token)]
        elif isinstance(value, dict):
            value = value[token]
        else:
            raise ValueError("pointer traverses a scalar")
    return value


def derived_record(doc, obs, evidence, derivation):
    ref = derivation["evidence_ref"]
    if ref not in obs["evidence_refs"] or ref not in evidence:
        raise ValueError("derivation must cite evidence referenced by the observation")
    artifact = evidence[ref]["artifact"]
    if artifact["media_type"] != "application/json" or "content" not in artifact:
        raise ValueError("derivation requires embedded application/json evidence")
    record = json.loads(artifact["content"], object_pairs_hook=_reject_duplicate_keys,
                        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-JSON number: {value}")))
    if not isinstance(record, dict) or record.get("subject_sha256") != doc["subject"]["artifact"]["digest"]["sha256"]:
        raise ValueError("derived evidence is not bound to this subject")
    return record


def wilson(successes, n, level):
    p = successes / n
    z = NormalDist().inv_cdf((1 + level) / 2)
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, center - half), min(1.0, center + half)


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

    ids = [doc["metadata"]["result_id"], doc["execution"]["run_id"], doc["subject"]["id"],
           *(r["id"] for r in doc["audit_basis"]["requirements"]),
           *(e["id"] for e in doc["evidence"])]
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
            coverage = obs.get("coverage")
            if coverage and coverage["examined"] > coverage["population"]:
                err(f"{where}: coverage examined exceeds population")
            if coverage:
                try:
                    derivation = coverage["derivation"]
                    record = derived_record(doc, obs, evidence, derivation)
                    indices = pointer_value(record, derivation["indices_pointer"])
                    population = pointer_value(record, derivation["population_pointer"])
                    seed = pointer_value(record, derivation["seed_pointer"])
                    sampling = pointer_value(record, derivation["sampling_pointer"])
                    if (type(population) is not int or population < 1 or type(seed) is not int
                            or not isinstance(indices, list)
                            or any(type(i) is not int or not 0 <= i < population for i in indices)
                            or len(indices) != len(set(indices))
                            or len(indices) != coverage["examined"] or population != coverage["population"]
                            or seed != coverage["seed"] or sampling != coverage["sampling"]):
                        err(f"{where}: coverage does not match cited evidence")
                except (KeyError, IndexError, ValueError, TypeError) as exc:
                    err(f"{where}: coverage derivation: {exc}")
            for ref in obs["evidence_refs"]:
                if ref not in evidence:
                    err(f"{where}/{obs['id']}: unresolved evidence ref {ref}")
                cited_evidence.add(ref)
        measured = [o for o in ev["observations"] if "measurement" in o]
        facts = [o for o in ev["observations"] if "fact" in o]
        rule = requirement.get("decision_rule") if requirement else None
        if measured and (not rule or rule["kind"] != "proportion"):
            err(f"{where}: measurement requires a policy decision_rule")
        if facts and (not rule or rule["kind"] != "field_equals"):
            err(f"{where}: Boolean fact requires a field_equals policy rule")
        decidable = assessment["status"] not in {"not_applicable", "not_tested", "error"} and assessment["evidence_admissibility"] == "admissible"
        if rule and rule["kind"] == "proportion" and decidable and len(measured) != 1:
            err(f"{where}: an admissible quantitative decision_rule requires exactly one measurement")
        if rule and rule["kind"] == "field_equals" and decidable and len(facts) != 1:
            err(f"{where}: an admissible Boolean decision_rule requires exactly one fact")
        for obs in facts:
            fact = obs["fact"]
            try:
                record = derived_record(doc, obs, evidence, fact["derivation"])
                value = pointer_value(record, fact["derivation"]["pointer"])
                if type(value) is not bool or value is not fact["value"]:
                    err(f"{where}: Boolean fact does not match cited evidence")
                if rule and rule["kind"] == "field_equals":
                    if fact["derivation"]["pointer"] != rule["source"]["pointer"]:
                        err(f"{where}: fact pointer differs from policy source")
                    if decidable:
                        for key, expected in rule["source"]["record_matches"].items():
                            if key not in record or rfc8785.dumps(record[key]) != rfc8785.dumps(expected):
                                err(f"{where}: evidence record does not match policy source field {key}")
                        derived = "pass" if value is rule["equals"] else "fail"
                        if assessment["status"] != derived:
                            err(f"{where}: Boolean status {assessment['status']} != derived {derived}")
            except (KeyError, IndexError, ValueError, TypeError) as exc:
                err(f"{where}: Boolean derivation: {exc}")
        for obs in measured:
            m, iv = obs["measurement"], obs["measurement"]["interval"]
            try:
                record = derived_record(doc, obs, evidence, m["derivation"])
                if rule and m["derivation"]["pointer"] != rule["source"]["pointer"]:
                    err(f"{where}: measurement pointer differs from policy source")
                if rule and decidable:
                    for key, expected in rule["source"]["record_matches"].items():
                        if key not in record or rfc8785.dumps(record[key]) != rfc8785.dumps(expected):
                            err(f"{where}: evidence record does not match policy source field {key}")
                labels = pointer_value(record, m["derivation"]["pointer"])
                if (not isinstance(labels, list) or not labels
                        or any(type(x) is not int or x not in (0, 1) for x in labels)
                        or sum(labels) != m["successes"] or len(labels) != iv["sample_size"]):
                    err(f"{where}: measurement does not match cited evidence outcomes")
            except (KeyError, IndexError, ValueError, TypeError) as exc:
                err(f"{where}: measurement derivation: {exc}")
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
            if rule and rule["kind"] == "proportion":
                if iv["level"] != rule["interval_level"] or iv["method"] != rule["interval_method"]:
                    err(f"{where}: measurement interval does not follow the requirement's decision_rule")
                elif decidable:
                    recomputed = {"value": m["successes"] / iv["sample_size"],
                                  "interval": {"lower": lower, "upper": upper}}
                    derived = decide(rule, recomputed)
                    if assessment["status"] != derived:
                        err(f"{where}: status {assessment['status']} != derived {derived}")
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
    body = copy.deepcopy(doc)
    expected_digests = body["attestation"].pop("result_digest")
    canonical = rfc8785.dumps(body)
    for algorithm, expected in expected_digests.items():
        if hashlib.new(algorithm, canonical).hexdigest() != expected:
            errors.append(f"integrity: attestation.result_digest.{algorithm} mismatch")
    return errors


def verify(doc, schema=None, expected_policy=None):
    """Check structural/recorded-decision consistency and digests, not evidence truth or authenticity."""
    schema = schema or load(SCHEMA_PATH)
    errors = check_structure(doc, schema)
    if errors:
        return errors  # semantic checks assume a structurally valid document
    try:
        # Reject values outside the JCS domain before arithmetic or timestamp parsing.
        rfc8785.dumps(doc)
        if expected_policy is not None and rfc8785.dumps(doc["audit_basis"]) != rfc8785.dumps(expected_policy):
            return ["policy: audit_basis differs from the consumer-supplied policy"]
        integrity_errors = check_integrity(doc)
        return integrity_errors if integrity_errors else check_semantics(doc) + assurance.check(doc)
    except (ValueError, OverflowError, TypeError, UnicodeError) as exc:
        return [f"verification: unsupported value: {exc}"]


def main(argv):
    parser = argparse.ArgumentParser(description="Check record consistency and integrity, not authenticity or evidence truth.")
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--policy", type=Path, help="Independently selected expected audit_basis JSON; never take this from the submitted result.")
    args = parser.parse_args(argv)
    expected_policy = load(args.policy) if args.policy else None
    schema = load(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    print("Scope: record consistency and integrity; " + ("consumer policy pinned." if expected_policy is not None else "policy not independently pinned."))
    failed = False
    for path in args.paths or [ROOT / "output" / "example-result.json"]:
        try:
            doc = load(path)
            errors = verify(doc, schema, expected_policy)
        except ValueError as exc:
            errors = [f"parse: {exc}"]
        failed |= bool(errors)
        print(f"{'FAIL' if errors else 'OK  '} {path}")
        for e in errors:
            print(f"     {e}")
        if not errors:
            for note in withheld_decisions(doc):
                print(f"     {note}")
    return 1 if failed else 0


def withheld_decisions(doc):
    """Expose numerical/Boolean decisions withheld by an assessor; never override them."""
    requirements = {r["id"]: r for r in doc["audit_basis"]["requirements"]}
    notes = []
    for ev in doc["evaluations"]:
        a = ev["assessment"]
        if a["status"] not in {"indeterminate", "error", "not_applicable"}:
            continue
        rule = requirements[ev["requirement_ref"]].get("decision_rule")
        if not rule:
            continue
        for obs in ev["observations"]:
            derived = None
            if rule["kind"] == "proportion" and "measurement" in obs:
                m = obs["measurement"]
                lower, upper = wilson(m["successes"], m["interval"]["sample_size"], m["interval"]["level"])
                derived = decide(rule, {"value": m["successes"] / m["interval"]["sample_size"],
                                        "interval": {"lower": lower, "upper": upper}})
            elif rule["kind"] == "field_equals" and "fact" in obs:
                derived = "pass" if obs["fact"]["value"] is rule["equals"] else "fail"
            if derived in {"pass", "fail"}:
                notes.append(f"withheld: {ev['id']}: {derived}; recorded {a['status']} ({a['evidence_admissibility']})")
    return notes


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
