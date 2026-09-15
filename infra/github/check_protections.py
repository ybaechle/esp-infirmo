"""Read effective main/develop protection using the existing gh authentication."""

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class Unknown(RuntimeError):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def gh_json(*arguments):
    try:
        result = subprocess.run(
            ["gh", *arguments], cwd=ROOT, capture_output=True, text=True,
            encoding="utf-8", timeout=45,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise Unknown(str(error)) from None
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise Unknown(result.stderr.strip() or "GitHub returned invalid JSON") from None
    if result.returncode:
        error = value if isinstance(value, dict) else {}
        status = re.search(r"HTTP (\d{3})", result.stderr)
        raise Unknown(error.get("message", result.stderr.strip()),
                      str(error.get("status", status[1] if status else "")))
    return value


def api(endpoint, *, paginated=False):
    arguments = ["api", "--method", "GET", "-H", "X-GitHub-Api-Version: 2022-11-28", endpoint]
    if paginated:
        pages = gh_json(*arguments, "--paginate", "--slurp")
        if not isinstance(pages, list) or not all(isinstance(page, list) for page in pages):
            raise Unknown("Unexpected paginated rule response")
        return [rule for page in pages for rule in page]
    return gh_json(*arguments)


def protections(rules, legacy=None):
    legacy = legacy or {}
    reviews = [rule.get("parameters", {}) for rule in rules if rule["type"] == "pull_request"]
    checks = [rule.get("parameters", {}) for rule in rules if rule["type"] == "required_status_checks"]
    old_reviews = legacy.get("required_pull_request_reviews") or {}
    old_checks = legacy.get("required_status_checks") or {}
    contexts = set(old_checks.get("contexts", []))
    contexts.update(item["context"] for item in old_checks.get("checks", []))
    contexts.update(item["context"] for rule in checks for item in rule.get("required_status_checks", []))
    return {
        "pull_request": bool(reviews or old_reviews),
        "approving_reviews": max([old_reviews.get("required_approving_review_count", 0)] + [rule.get("required_approving_review_count", 0) for rule in reviews]),
        "dismiss_stale_reviews": old_reviews.get("dismiss_stale_reviews", False) or any(rule.get("dismiss_stale_reviews_on_push", False) for rule in reviews),
        "resolve_threads": (legacy.get("required_conversation_resolution") or {}).get("enabled", False) or any(rule.get("required_review_thread_resolution", False) for rule in reviews),
        "block_force_push": any(rule["type"] == "non_fast_forward" for rule in rules) or (legacy.get("allow_force_pushes") or {}).get("enabled") is False,
        "block_deletion": any(rule["type"] == "deletion" for rule in rules) or (legacy.get("allow_deletions") or {}).get("enabled") is False,
        "strict_status_checks": old_checks.get("strict", False) or any(rule.get("strict_required_status_checks_policy", False) for rule in checks),
        "required_contexts": sorted(contexts),
    }


def missing_checks(expected, actual):
    missing = []
    for key, wanted in expected.items():
        found = actual[key]
        if isinstance(wanted, list):
            missing.extend(f"required check: {name}" for name in wanted if name not in found)
        elif found < wanted:
            missing.append(f"{key} (required {wanted}, found {found})")
    return missing


def audit_branch(repo, branch, policy, read=api):
    ref = f"refs/heads/{branch}"
    condition = policy.get("conditions", {}).get("ref_name", {})
    if (policy.get("enforcement") != "active" or policy.get("target") != "branch"
            or condition.get("include") != [ref] or condition.get("exclude")):
        raise Unknown(f"Local policy must target active {ref} explicitly")
    expected = protections(policy["rules"])
    if (any(not value for value in expected.values())
            or expected["approving_reviews"] < 1
            or "Quality gate" not in expected["required_contexts"]):
        raise Unknown(f"Local policy for {branch} omits a mandatory protection")
    result = {"branch": branch, "expected": expected, "status": "unknown"}
    try:
        details = read(f"repos/{repo}/branches/{branch}")
        if details.get("name") != branch or not isinstance(details.get("protected"), bool):
            raise Unknown("Unexpected branch metadata")
        result.update(sha=details["commit"]["sha"], protected=details["protected"])
        result["legacy_status_contexts"] = details.get("protection", {}).get("required_status_checks", {}).get("contexts", [])
        rules = read(f"repos/{repo}/rules/branches/{branch}?per_page=100", paginated=True)
        if not isinstance(rules, list):
            raise Unknown("Unexpected effective-rule response")
        result["effective_rules"] = rules
        legacy = None
        result["legacy_read"] = "not needed: effective rules cover requirements"
        if missing_checks(expected, protections(rules)):
            if details["protected"]:
                try:
                    legacy = read(f"repos/{repo}/branches/{branch}/protection")
                    if not isinstance(legacy, dict):
                        raise Unknown("Unexpected legacy protection response")
                    result["legacy_read"] = "read"
                except Unknown as error:
                    if error.status != "404" or str(error) != "Branch not protected":
                        raise
                    result["legacy_read"] = "absent: Branch not protected (404)"
            else:
                result["legacy_read"] = "absent: protected=false"
        result["observed"] = protections(rules, legacy)
        result["missing"] = missing_checks(expected, result["observed"])
        result["status"] = "missing" if result["missing"] else "pass"
    except (Unknown, KeyError, TypeError, ValueError, AttributeError) as error:
        result["error"] = str(error)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write the dated JSON evidence")
    args = parser.parse_args()
    report = {"collected_at": datetime.now(timezone.utc).isoformat(), "branches": [],
              "scope": "Read-only configuration audit; no push, deletion, merge or bypass-actor test."}
    try:
        repo = gh_json("repo", "view", "--json", "nameWithOwner")["nameWithOwner"]
        details = api(f"repos/{repo}")
        if not isinstance(details.get("permissions"), dict):
            raise Unknown("Repository permissions are unreadable")
        report.update(repository=repo, permissions=details.get("permissions"))
        for branch in ("main", "develop"):
            path = ROOT / "infra" / "github" / "rulesets" / f"branch-{branch}.json"
            content = path.read_bytes()
            result = audit_branch(repo, branch, json.loads(content))
            result["policy_sha256"] = hashlib.sha256(content).hexdigest()
            report["branches"].append(result)
        statuses = {result["status"] for result in report["branches"]}
        code = 2 if "unknown" in statuses else 1 if "missing" in statuses else 0
    except (Unknown, OSError, KeyError, TypeError, ValueError, AttributeError) as error:
        report["error"] = str(error)
        code = 2
    report["exit_code"] = code
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{report['collected_at']} {report.get('repository', 'unknown repository')}")
    print(f"Permissions: {json.dumps(report.get('permissions'))}")
    for result in report["branches"]:
        print(f"{result['branch']} {result.get('sha', '?')}: {result['status'].upper()}")
        if result.get("missing"):
            print("  Missing: " + "; ".join(result["missing"]))
        if result.get("error"):
            print("  Unknown: " + result["error"])
    if report.get("error"):
        print("Unknown: " + report["error"])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
