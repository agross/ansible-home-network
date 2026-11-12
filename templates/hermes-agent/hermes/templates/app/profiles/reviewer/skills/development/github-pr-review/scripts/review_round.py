#!/usr/bin/env python3
"""Guard reviewer publication and recover the remaining finalization operations."""

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import quote


MARKER = re.compile(r"^<!-- hermes-reviewer: reviewed-sha=([0-9a-f]{40,64}) state=(clean|changes-requested) -->$", re.M)
BASIS = re.compile(r"^<!-- hermes-review-basis: base-ref=(\S+) merge-base=([0-9a-f]{40,64}) -->$", re.M)
LIFECYCLE = {"implementing", "in-review", "needs-human"}


class Halt(Exception):
    def __init__(self, status, detail):
        self.status, self.detail = status, detail


class Round:
    def __init__(self, repository, number, reviewer_app):
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository) or number < 1:
            raise ValueError("Invalid repository or PR number")
        if not re.fullmatch(r"[\w-]+", reviewer_app):
            raise ValueError("Invalid configured reviewer App slug")
        self.repository, self.number = repository, number
        self.prefix = f"repos/{repository}"
        self.app = reviewer_app
        self.actor = None
        self.changed = False

    def api(self, endpoint, method="GET", payload=None, paginate=False):
        argv = ["gh-app", "--repo", self.repository, "--", "api", "--method", method]
        if paginate:
            argv.append("--paginate")
        with tempfile.TemporaryDirectory(prefix="review-api-") as temporary:
            if payload is not None:
                path = Path(temporary) / "input.json"
                path.write_text(json.dumps(payload))
                argv.extend(["--input", str(path)])
            result = subprocess.run([*argv, endpoint], text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError(f"{method} {endpoint} failed ({result.returncode}): {result.stderr.strip()[:300]}")
        decoder, text, values = json.JSONDecoder(), result.stdout.strip(), []
        while text:
            value, end = decoder.raw_decode(text)
            values.append(value)
            text = text[end:].lstrip()
        if paginate:
            return [item for value in values for item in (value if isinstance(value, list) else [value])]
        return values[0] if values else None

    def identity(self):
        status = subprocess.run(["hermes-github-app", "status", "--repo", self.repository, "--format", "json"], capture_output=True, text=True)
        if status.returncode:
            raise Halt("blocked", "Reviewer App identity or repository access failed")
        authenticated = json.loads(status.stdout).get("app", {}).get("slug")
        if not authenticated:
            raise Halt("blocked", "Authenticated App slug is missing from status app.slug; identity is unverified")
        if authenticated != self.app:
            raise Halt("blocked", f"Configured reviewer App slug {self.app!r} differs from authenticated App slug {authenticated!r}; correct profile configuration before writes")
        self.actor = self.api("users/" + quote(self.app + "[bot]", safe=""))
        if self.actor.get("type") != "Bot":
            raise Halt("blocked", "Configured reviewer identity is not a Bot")

    def snapshot(self):
        pr = self.api(f"{self.prefix}/pulls/{self.number}")
        comparison = self.api(f"{self.prefix}/compare/{pr['base']['sha']}...{pr['head']['sha']}")
        basis = {"head": pr["head"]["sha"], "merge_base": comparison["merge_base_commit"]["sha"],
                 "base_ref": pr["base"]["ref"]}
        return pr, basis

    def guard(self, expected):
        pr, current = self.snapshot()
        if current["head"] != expected["head"]:
            raise Halt("stale_head", "HEAD changed; stop and let the newer webhook own the new revision")
        if current != expected:
            raise Halt("basis_changed", "Comparison changed with the same HEAD; reassess within the shared two-restart limit")
        if pr["state"] != "open" or pr.get("draft", False):
            raise Halt("ineligible", "PR is closed or draft")
        return pr

    def threads(self):
        owner, name = self.repository.split("/")
        query = '''query($owner:String!,$name:String!,$number:Int!,$after:String){
          repository(owner:$owner,name:$name){pullRequest(number:$number){
            reviewThreads(first:100,after:$after){nodes{id isResolved
              comments(first:100){nodes{id body path author{login}} pageInfo{hasNextPage endCursor}}}
              pageInfo{hasNextPage endCursor}}}}}'''
        result, cursor = [], None
        while True:
            data = self.api("graphql", method="POST", payload={"query": query,
                "variables": {"owner": owner, "name": name, "number": self.number, "after": cursor}})
            if data.get("errors"):
                raise Halt("blocked", "Review-thread query returned errors")
            page = data["data"]["repository"]["pullRequest"]["reviewThreads"]
            for node in page["nodes"]:
                connection = node["comments"]
                seen = set()
                while connection["pageInfo"]["hasNextPage"]:
                    after = connection["pageInfo"].get("endCursor")
                    if not after or after in seen:
                        raise Halt("blocked", "Thread-comment pagination is incomplete or repeated")
                    seen.add(after)
                    extra = self.api("graphql", "POST", {"query": '''query($id:ID!,$after:String!){
                        node(id:$id){... on PullRequestReviewThread{comments(first:100,after:$after){
                        nodes{id body path author{login}} pageInfo{hasNextPage endCursor}}}}}''',
                        "variables": {"id": node["id"], "after": after}})
                    if extra.get("errors"):
                        raise Halt("blocked", "Thread-comment query returned errors")
                    connection = extra["data"]["node"]["comments"]
                    node["comments"]["nodes"].extend(connection["nodes"])
                node["comments"]["pageInfo"] = connection["pageInfo"]
            result.extend(page["nodes"])
            if not page["pageInfo"]["hasNextPage"]:
                return result
            cursor = page["pageInfo"]["endCursor"]

    def reviews(self):
        return self.api(f"{self.prefix}/pulls/{self.number}/reviews", paginate=True)

    def existing(self, expected):
        matches = []
        for review in self.reviews():
            if (review.get("user") or {}).get("id") != self.actor["id"]:
                continue
            marker = MARKER.search(review.get("body", ""))
            if not marker or marker[1] != expected["head"]:
                continue
            basis = BASIS.search(review["body"])
            if not basis:
                raise Halt("blocked", "Existing reviewer marker lacks comparison evidence; reconcile it without duplicate publication")
            if {"head": marker[1], "merge_base": basis[2], "base_ref": unquote_ref(basis[1])} == expected:
                matches.append((review, marker[2]))
        if len(matches) > 1:
            raise Halt("blocked", "Multiple reviewer results cover this comparison; reconcile before finalizing")
        return matches[0] if matches else None

    def inspect(self):
        self.identity()
        pr, basis = self.snapshot()
        existing = self.existing(basis)
        return {"status": "inspected", "basis": basis, "pr": pr, "threads": self.threads(),
                "existing": {"review": existing[0], "state": existing[1]} if existing else None}

    def set_labels(self, number, desired, basis):
        self.guard(basis)
        item = self.api(f"{self.prefix}/issues/{number}")
        current = [label["name"] for label in item["labels"]]
        after = sorted((set(current) - LIFECYCLE) | set(desired))
        if set(current) == set(after):
            return
        self.guard(basis)
        error = None
        try:
            self.api(f"{self.prefix}/issues/{number}", "PATCH", {"labels": after})
        except RuntimeError as exc:
            error = exc
        self.guard(basis)
        observed = self.api(f"{self.prefix}/issues/{number}")
        if {label["name"] for label in observed["labels"]} != set(after):
            raise Halt("blocked", str(error or "Label transition did not persist"))
        self.changed = True

    def reaction(self, content, basis):
        self.guard(basis)
        endpoint = f"{self.prefix}/issues/{self.number}/reactions"
        observed = self.api(endpoint, paginate=True)
        ours = [item for item in observed if item["user"]["id"] == self.actor["id"]]
        for item in ours:
            if item["content"] in {"eyes", "+1", "-1"} and item["content"] != content:
                self.guard(basis)
                self.api(endpoint + "/" + str(item["id"]), "DELETE")
                self.changed = True
        if not any(item["content"] == content for item in ours):
            self.guard(basis)
            self.api(endpoint, "POST", {"content": content})
            self.changed = True
        self.guard(basis)
        final = self.api(endpoint, paginate=True)
        if [item["content"] for item in final if item["user"]["id"] == self.actor["id"] and item["content"] in {"eyes", "+1", "-1"}] != [content]:
            raise Halt("blocked", "Reaction transition did not persist")

    def begin(self, plan):
        basis = plan["basis"]
        pr = self.guard(basis)
        existing = self.existing(basis)
        if existing:
            return {"status": "resume", "state": existing[1], "review_id": existing[0]["id"]}
        if any(label["name"] == "needs-human" for label in pr["labels"]):
            raise Halt("ineligible", "Human handoff is already active and has no matching recoverable review")
        self.set_labels(self.number, ["in-review"], basis)
        if plan.get("issue_number"):
            self.set_labels(plan["issue_number"], ["in-review"], basis)
        self.reaction("eyes", basis)
        return {"status": "begun", "basis": basis}

    def apply(self, plan, developer_app):
        basis = plan["basis"]
        pr = self.guard(basis)
        existing = self.existing(basis)
        state = existing[1] if existing else plan["state"]
        if state not in {"clean", "changes-requested"}:
            raise ValueError("Invalid assessment state")
        threads = {thread["id"]: thread for thread in self.threads()}
        resolutions = plan.get("resolved_threads", [])
        if any(not item.get("evidence") or item["id"] not in threads for item in resolutions):
            raise Halt("blocked", "Each thread resolution needs a verified correction and PR-owned thread ID")
        fixed = {item["id"] for item in resolutions}
        if state == "clean" and any(not thread["isResolved"] and key not in fixed for key, thread in threads.items()):
            raise Halt("blocked", "Clean handoff still has unverified open threads")
        for item in resolutions:
            if threads[item["id"]]["isResolved"]:
                continue
            self.guard(basis)
            result = self.api("graphql", "POST", {"query": "mutation($id:ID!){resolveReviewThread(input:{threadId:$id}){thread{id isResolved}}}",
                                                       "variables": {"id": item["id"]}})
            if result.get("errors"):
                raise Halt("blocked", "Thread resolution failed")
            self.guard(basis)
            readback = {thread["id"]: thread for thread in self.threads()}
            if not readback[item["id"]]["isResolved"]:
                raise Halt("blocked", "Thread closure was not verified")
            self.changed = True
        if not existing:
            self.guard(basis)
            draft = {"commit_id": basis["head"], "event": "COMMENT", "comments": plan.get("comments", [])}
            receipt = hashlib.sha256(json.dumps({"basis": basis, "state": state, "body": plan["body"],
                "comments": draft["comments"]}, sort_keys=True).encode()).hexdigest()
            draft["body"] = (f"<!-- hermes-reviewer: reviewed-sha={basis['head']} state={state} -->\n"
                f"<!-- hermes-review-basis: base-ref={quote(basis['base_ref'], safe='')} merge-base={basis['merge_base']} -->\n"
                f"<!-- hermes-review-receipt: key={receipt} -->\n" + plan["body"])
            try:
                self.api(f"{self.prefix}/pulls/{self.number}/reviews", "POST", draft)
            except RuntimeError:
                found = self.existing(basis)
                if not found or f"key={receipt}" not in found[0]["body"]:
                    raise Halt("blocked", "Review publication is unconfirmed; inspect remote state before any retry")
            self.guard(basis)
            existing = self.existing(basis)
            if not existing or f"key={receipt}" not in existing[0]["body"]:
                raise Halt("blocked", "Published review could not be read back")
            self.changed = True
        self.guard(basis)
        if state == "clean" and any(not thread["isResolved"] for thread in self.threads()):
            raise Halt("blocked", "An open thread appeared before clean finalization")
        developer = self.api("users/" + quote(developer_app + "[bot]", safe=""))
        developer_origin = (developer["type"] == "Bot" and pr["user"]["id"] == developer["id"] and
                            "<!-- hermes-origin: developer -->" in pr["body"])
        delegated = any(label["name"] == "ready-for-agent" for label in pr["labels"])
        desired = ["needs-human"] if state == "clean" else ["in-review"]
        if state == "changes-requested" and not (developer_origin or delegated):
            desired.append("needs-human")
        self.set_labels(self.number, desired, basis)
        if state == "clean" and plan.get("issue_number"):
            self.set_labels(plan["issue_number"], [], basis)
        self.reaction("+1" if state == "clean" else "-1", basis)
        self.guard(basis)
        return {"status": "complete" if self.changed else "already_complete", "review_id": existing[0]["id"],
                "state": state, "basis": basis}


def unquote_ref(value):
    from urllib.parse import unquote
    return unquote(value)


@contextmanager
def publication_lock(repository, number):
    home = os.environ.get("HERMES_HOME")
    if not home:
        raise Halt("blocked", "HERMES_HOME must select the reviewer profile")
    directory = Path(home) / "review-locks"
    directory.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(f"{repository}#{number}".encode()).hexdigest()
    with (directory / key).open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Halt("busy", "Another local session is publishing or finalizing this PR; reconcile after it finishes")
        yield


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["inspect", "begin", "apply"])
    parser.add_argument("--repo", required=True)
    parser.add_argument("--number", required=True, type=int)
    parser.add_argument("--reviewer-app", required=True)
    parser.add_argument("--developer-app", default="developer")
    parser.add_argument("--plan", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    client = Round(args.repo, args.number, args.reviewer_app)
    try:
        if args.operation == "inspect":
            result = client.inspect()
        else:
            if args.plan is None:
                parser.error("--plan is required")
            plan = json.loads(args.plan.read_text())
            with publication_lock(args.repo, args.number):
                client.identity()
                result = client.begin(plan) if args.operation == "begin" else client.apply(plan, args.developer_app)
        print(json.dumps(result))
        return 0
    except Halt as error:
        print(json.dumps({"status": error.status, "detail": error.detail}))
        return 0
    except (RuntimeError, ValueError, KeyError, OSError) as error:
        print(json.dumps({"status": "blocked", "detail": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
