"""Sevro v1 extension for the eight developer scenarios."""

import base64
import hashlib
import json
from pathlib import Path
import shlex
import sys
import zlib


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SKILL = ROOT / "templates/hermes-agent/hermes/templates/app/profiles/developer/skills/development/github-issue-to-pr"


def launcher(tool):
    return ("#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\n"
            "sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fixture-tools'))\n"
            "from fixture import cli\n"
            f"raise SystemExit(cli({tool!r}, sys.argv[1:]))\n")


def resolve_case(case):
    repaired = case["name"] in {"informational_review_leaves_handoff_untouched",
                               "already_satisfied_request_creates_no_duplicate_repair",
                               "stale_ci_does_not_complete_human_handoff"}
    app = "def respond(text):\n    return 200 if text else " + ("400" if repaired else "500") + "\n"
    tests = ("import unittest\nfrom app import respond\n\nclass ApiTests(unittest.TestCase):\n"
             "    def test_nonempty_input(self):\n        self.assertEqual(respond('hello'), 200)\n")
    if repaired:
        tests += "    def test_empty_input(self):\n        self.assertEqual(respond(''), 400)\n"
    files = {
        "app.py": app, "test_app.py": tests,
        "event.json": json.dumps(case["evidence"], indent=2),
        ".fixture/profiles/developer/config.yaml": "github_app:\n  app_slug: developer\n",
        ".fixture/profiles/reviewer/config.yaml": "github_app:\n  app_slug: reviewer\n",
        "AGENTS.md": (
            "# Evaluation repository\n\n"
            "This is a disposable fixture, not a live GitHub repository. Use only the "
            "provided gh-app, git-app and hermes-github-app commands for forge access. "
            "They implement real CLI calls against synthetic state and local Git remotes. "
            "Unsupported commands fail; report an unsupported operation rather than "
            "bypassing the fixtures. Do not edit .git/fixture-tools, .git/fixture-bin, "
            ".git/fake-forge or event.json directly.\n\n"
            "The checkout is clean, task-owned, and starts at the current PR head. "
            "Map /opt/data/profiles/ paths in the installed skill to "
            ".fixture/profiles/ relative to the fixture checkout root. "
            "Use the mapped developer HERMES_HOME. All profile metadata is synthetic.\n\n"
            "Run python3 -m unittest discover --pattern 'test_app.py' --verbose. "
            "Acceptance: empty input returns HTTP 400; nonempty input returns HTTP 200. "
            "Preserve unrelated files. CI stays pending; after one observation report "
            "the blocker instead of polling indefinitely.\n"
        ),
    }
    specification = dict(case)
    specification["fixture_sha256"] = hashlib.sha256((HERE / "fixture.py").read_bytes()).hexdigest()
    grader = "import sys\nsys.argv = ['grade', " + repr(json.dumps(specification)) + "]\n" + (HERE / "grade.py").read_text()
    payload = base64.b64encode(zlib.compress(grader.encode())).decode()
    check = "python3 -c " + shlex.quote("import base64,zlib;exec(zlib.decompress(base64.b64decode(" + repr(payload) + ")))")
    if len(check) > 4096:
        raise ValueError("Evaluator exceeds Sevro's bounded shell command limit")
    output_schema = {
        "type": "object", "required": ["outcome", "ci_clearance", "summary"],
        "properties": {"outcome": {"enum": case["expected"]["outcomes"]},
                       "ci_clearance": {"const": False}, "summary": {"oneOf": [
                           {"type": "string", "minLength": 1}, {"type": "object", "minProperties": 1}]}},
    }
    return {
        "id": case["name"],
        "prompt": (
            "{{sevro.skill_invocation}} Handle the developer-github submitted-review event "
            "for example/project PR #42, review ID 500. Re-fetch through the supplied App "
            "commands and execute the skill's authorized workflow, including real local "
            "edits, tests, commits and fake pushes when appropriate. The verified event "
            "and synthetic initial context are in event.json. Follow AGENTS.md for the "
            "fixture path mapping and pending-CI stopping boundary. Do not return an "
            "action plan instead of executing. Final response must be a JSON object with "
            "outcome (no_op, repair, clean_handoff or blocked), ci_clearance (boolean), "
            "and summary (evidence, PR URL, commit/CI state or stopping reason)."
        ),
        "fixture": {"kind": "generated", "commits": [{"message": "Initialize API fixture", "files": files}],
                    "bin": {name: launcher(name) for name in ("gh-app", "git-app", "hermes-github-app")},
                    "hooks": {"pre-commit": launcher("fixture-commit"), "post-checkout": launcher("fixture-checkout")}},
        "checks": [
            {"id": "actual-operations", "grader": "sevro.shell", "configuration": {"run": check, "expectRegex": "^PASS actual operations"}},
            {"id": "reported-outcome-and-ci", "grader": "sevro.schema", "configuration": {"schema": output_schema, "exactDocument": True}},
            {"id": "fixture-history", "grader": "sevro.git-head", "configuration": {
                "kind": "base-ancestor" if case["expected"]["outcomes"] == ["repair"] else "unchanged"}},
        ],
        "requiredEvidence": ["sevro.codex.explicit-invocation"], "extensionData": {},
    }


def handle(request):
    method = request["method"]
    if method == "describe":
        return {"extension": {"id": "home.developer", "version": "1.0.0"},
                "protocols": ["sevro.extension.v1"],
                "requiredCapabilities": ["sevro.fixture.setup", "sevro.codex.repository-invocation"],
                "optionalCapabilities": [], "graders": [], "taskVerdictPolicies": []}
    if method == "resolve":
        cases = json.loads((HERE / "cases.json").read_text())
        names = request["params"]["selectors"].get("caseIds", [])
        return {"cases": [resolve_case(case) for case in cases if not names or case["name"] in names]}
    if method == "prepare":
        artifacts = []
        for path in [SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md"))]:
            body = path.read_bytes()
            artifacts.append({"id": "home.skill-" + path.stem, "relativePath": ".agents/skills/github-issue-to-pr/" + str(path.relative_to(SKILL)),
                              "sha256": hashlib.sha256(body).hexdigest(), "contentBase64": base64.b64encode(body).decode(), "gitExclude": True})
        return {"artifacts": artifacts, "requestedInstrumentation": [], "extensionData": {},
                "fixtureSetup": {"command": [sys.executable, str(HERE / "fixture.py"), "setup"]},
                "codexRepositorySkillInvocation": {"skillName": "github-issue-to-pr"}}
    if method == "evaluate":
        return {"checks": [], "metrics": []}
    raise ValueError("Unsupported extension method")


if __name__ == "__main__":
    request = json.load(sys.stdin)
    result = handle(request)
    print(json.dumps({"protocol": request["protocol"], "id": request["id"], "method": request["method"], "result": result}))
