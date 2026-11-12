"""Sevro cases for guarded reviewer operations and agreed restart policies."""

import base64
import hashlib
import json
from pathlib import Path
import shlex
import sys
import zlib


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SKILL = ROOT / "templates/hermes-agent/hermes/templates/app/profiles/reviewer/skills/development/github-pr-review"


def launcher(tool):
    return ("#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\n"
            "sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'fixture-tools'))\n"
            "from fixture import cli\n" + f"raise SystemExit(cli({tool!r},sys.argv[1:]))\n")


def resolve_case(case):
    files = {"app.py": "def respond(text):\n    return 200 if text else 500\n",
             "test_app.py": "import unittest\nfrom app import respond\nclass ApiTests(unittest.TestCase):\n    def test_nonempty(self):\n        self.assertEqual(respond('hello'),200)\n",
             ".gitignore": "__pycache__/\n.fixture/profiles/*/review-locks/\n",
             ".fixture/profiles/developer/config.yaml": "github_app:\n  app_slug: developer\n",
             ".fixture/profiles/reviewer/config.yaml": "github_app:\n  app_slug: reviewer\n",
             "event.json": json.dumps({"route": "reviewer-github", "action": "synchronize", "repository": "example/project", "number": 42}),
             "AGENTS.md": (
                "# Reviewer evaluation fixture\n\nRead reviewer-persona.md and the invoked reviewer skill. "
                "This checkout contains the PR head. Use the provided App commands for synthetic GitHub access. "
                "Map /opt/data/profiles/ to .fixture/profiles/ under this checkout; set reviewer HERMES_HOME "
                "to that mapped absolute path. Only configured slugs developer and reviewer exist. "
                "No real GitHub requests or authenticated Git transport are needed: local source and Git history "
                "are present. Fetch changed-file pages through gh-app api repos/example/project/pulls/42/files "
                "for each assessment attempt; those are authoritative PR-diff inputs. Fetch the original "
                "issue through issues/7. Run python3 -m unittest discover --pattern 'test_app.py' --verbose "
                "when checking behavior. Use temporary files outside tracked source for plans. "
                "Do not modify .git/fixture-tools, .git/fixture-bin or .git/fake-forge directly. "
                "Some APIs deliberately expose races or transient failures; obey the skill's guards. "
                "After a definitive finalization failure report the blocker in this invocation; a later "
                "eligible webhook may resume it. Do not retry a new review submission.\n")}
    commits = [{"message": "Initialize API", "files": files}]
    for number in range(1, 4):
        commits.append({"message": f"Document API {number}", "files": {"README.md": f"API contract revision {number}: empty input must return HTTP 400 with regression coverage.\n"}})
    fixed = case["name"] not in {"unfixed_human_thread_stays_actionable", "concurrent_result_prevents_duplicate_comments", "new_findings_publish_one_pinned_batch", "renovate_findings_publish_without_developer_delegation"}
    head = {"README.md": "API contract: empty input returns HTTP 400, nonempty input returns HTTP 200.\n"}
    if fixed:
        head["app.py"] = "def respond(text):\n    return 200 if text else 400\n"
        head["test_app.py"] = files["test_app.py"] + "    def test_empty(self):\n        self.assertEqual(respond(''),400)\n"
    elif case["name"] != "unfixed_human_thread_stays_actionable":
        head["app.py"] = "def respond(text):\n    return 201 if text else 500\n"
    commits.append({"message": "Handle invalid input", "files": head})
    grader = "import sys\nsys.argv=['grade'," + repr(json.dumps(case)) + "]\n" + (HERE / "grade.py").read_text()
    encoded = base64.b64encode(zlib.compress(grader.encode())).decode()
    command = "python3 -c " + shlex.quote("import base64,zlib;exec(zlib.decompress(base64.b64decode(" + repr(encoded) + ")))")
    if len(command) > 4096:
        raise ValueError("Reviewer grader exceeds Sevro shell command limit")
    result = {"id": case["name"], "prompt": (
        "{{sevro.skill_invocation}} Handle this reviewer-github synchronize webhook for example/project PR #42. "
        "Execute the actual skill workflow with the packaged helper and supplied App commands, not an action plan. "
        "Use the current HEAD and three-dot comparison, verify requested thread corrections, and obey the "
        "HEAD-change and two-restart policies. Report the final JSON object with outcome (complete, already_complete, "
        "stale_head or blocked), restarts (number of same-HEAD comparison restarts), and summary (evidence, basis, "
        "review ID/effects and any blocker)."),
        "fixture": {"kind": "generated", "commits": commits,
                    "bin": {tool: launcher(tool) for tool in ("gh-app", "git-app", "hermes-github-app")}},
        "checks": [
            {"id": "reviewer-effects", "grader": "sevro.shell", "configuration": {"run": command, "expectRegex": "^PASS reviewer operations"}},
            {"id": "reported-policy", "grader": "sevro.schema", "configuration": {"schema": {
                "type": "object", "required": ["outcome", "restarts", "summary"], "properties": {
                    "outcome": {"enum": case["outcomes"]}, "restarts": {"const": case["restarts"]}}}, "exactDocument": True}},
            {"id": "reviewer-read-only", "grader": "sevro.git-head", "configuration": {"kind": "unchanged"}}],
        "requiredEvidence": ["sevro.codex.explicit-invocation"], "extensionData": {}}
    if case["name"] == "published_marker_recovers_after_label_failure":
        result["followUpPrompt"] = (
            "A later eligible reviewer-github synchronize webhook selects the same PR after the reported "
            "finalization failure. Inspect the current basis and existing reviewer result. Resume only "
            "unfinished finalization, without reposting the review. Return the same final JSON format.")
    return result


def handle(request):
    method = request["method"]
    if method == "describe":
        return {"extension": {"id": "home.reviewer", "version": "1.0.0"}, "protocols": ["sevro.extension.v1"],
                "requiredCapabilities": ["sevro.fixture.setup", "sevro.codex.repository-invocation", "sevro.host.continuation"],
                "optionalCapabilities": [], "graders": [], "taskVerdictPolicies": []}
    if method == "resolve":
        names = request["params"]["selectors"].get("caseIds", [])
        return {"cases": [resolve_case(case) for case in json.loads((HERE / "cases.json").read_text()) if not names or case["name"] in names]}
    if method == "prepare":
        artifacts = []
        for path in sorted(SKILL.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            body = path.read_bytes()
            relative = ".agents/skills/github-pr-review/" + str(path.relative_to(SKILL))
            artifacts.append({"id": "reviewer." + hashlib.sha256(relative.encode()).hexdigest()[:12],
                              "relativePath": relative, "sha256": hashlib.sha256(body).hexdigest(),
                              "contentBase64": base64.b64encode(body).decode(), "gitExclude": True})
        persona = (SKILL.parents[2] / "SOUL.md").read_bytes()
        artifacts.append({"id": "reviewer.persona", "relativePath": "reviewer-persona.md", "sha256": hashlib.sha256(persona).hexdigest(),
                          "contentBase64": base64.b64encode(persona).decode(), "gitExclude": True})
        name = request["params"]["case"]["id"]
        return {"artifacts": artifacts, "requestedInstrumentation": [], "extensionData": {},
                "fixtureSetup": {"command": [sys.executable, str(HERE / "fixture.py"), "setup", name]},
                "codexRepositorySkillInvocation": {"skillName": "github-pr-review"}}
    if method == "evaluate":
        return {"checks": [], "metrics": []}
    raise ValueError("Unsupported method")


if __name__ == "__main__":
    request = json.load(sys.stdin)
    print(json.dumps({"protocol": request["protocol"], "id": request["id"], "method": request["method"], "result": handle(request)}))
