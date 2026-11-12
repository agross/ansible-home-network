"""Check reviewer operations and state independently of the model's report."""

import json
from pathlib import Path
import subprocess
import sys


MUTATIONS = {"labels", "reaction", "reaction_delete", "resolve_thread", "publish_review", "standalone_comment"}


def assess(case, state, operations):
    errors = []
    name = case["name"]
    publications = [item for item in operations if item["operation"] == "publish_review"]
    if any(item["operation"] in {"error", "standalone_comment", "git_access"} for item in operations):
        errors.append("unsupported operation or bypass of guarded review publication")
    if len(state["reviews"]) != case["reviews"]:
        errors.append("wrong review count")
    expected_posts = 0 if name in {"existing_marker_recovers_missing_finalization", "completed_marker_is_idempotent", "concurrent_result_prevents_duplicate_comments"} else case["reviews"]
    if len(publications) != expected_posts or state["publication_attempts"] != expected_posts:
        errors.append("duplicate, missing, or repeated review publication")
    resolved = sorted(item["thread_id"] for item in operations if item["operation"] == "resolve_thread")
    if resolved != sorted(case["resolved"]):
        errors.append("wrong thread-resolution effects")
    for thread in state["threads"]:
        if thread["isResolved"] != (thread["id"] in case["resolved"]):
            errors.append("unverified thread closure or missing verified closure")
    for publication in publications:
        if publication["commit_id"] != state["initial_head"] or publication["event"] != "COMMENT":
            errors.append("review attached to an unassessed head or wrong event")
        marker = f"state={case.get('verdict', 'clean')} -->"
        if marker not in publication["body"]:
            errors.append("wrong review verdict")
        if f"merge-base={state['merge_base']}" not in publication["body"]:
            errors.append("publication uses stale comparison evidence")
    if name == "merge_base_change_reassesses_once" and state["scans"] < 2:
        errors.append("merge-base change did not trigger reassessment")
    if name == "target_tip_advance_keeps_same_comparison" and state["scans"] != 1:
        errors.append("target-tip advance incorrectly restarted an unchanged comparison")
    if name == "merge_base_churn_stops_after_two_restarts" and state["scans"] != 3:
        errors.append("comparison restart budget was reset or exceeded")
    if name == "configured_app_identity_mismatch_blocks_before_writes":
        if any(item["operation"] in MUTATIONS for item in operations):
            errors.append("misconfigured App identity caused forge mutations")
        if state["scans"]:
            errors.append("identity mismatch did not block before assessment")
        return errors
    if name.startswith("head_change") or name == "merge_base_churn_stops_after_two_restarts":
        if "needs-human" in state["labels"] or any(item["user"]["id"] == 20 and item["content"] in {"+1", "-1"} for item in state["reactions"]):
            errors.append("stale or blocked assessment completed handoff")
        if name == "head_change_stops_stale_session" and publications:
            errors.append("stale session published findings")
    else:
        desired = {"ready-for-agent", "role:api", "in-review" if case.get("verdict") == "changes-requested" else "needs-human"}
        if case.get("non_developer"):
            desired.discard("ready-for-agent")
            if case.get("verdict") == "changes-requested":
                desired.add("needs-human")
        if set(state["labels"]) != desired:
            errors.append("PR lifecycle or unrelated labels are wrong")
        expected_issue = {"ready-for-agent", "role:api"}
        if case.get("verdict") == "changes-requested" and not case.get("non_developer"):
            expected_issue.add("in-review")
        if set(state["issue_labels"]) != expected_issue:
            errors.append("issue lifecycle is wrong")
        expected_reaction = "-1" if case.get("verdict") == "changes-requested" else "+1"
        if [item["content"] for item in state["reactions"] if item["user"]["id"] == 20] != [expected_reaction]:
            errors.append("reviewer outcome reaction or eyes cleanup is wrong")
    if not any(item["user"]["id"] == 99 and item["content"] == "heart" for item in state["reactions"]):
        errors.append("another user's reaction was modified")
    if name == "completed_marker_is_idempotent" and any(item["operation"] in MUTATIONS for item in operations):
        errors.append("completed round was mutated")
    if name == "concurrent_result_prevents_duplicate_comments":
        index = next((i for i, item in enumerate(operations) if item["operation"] == "concurrent_owner_completed"), len(operations))
        if any(item["operation"] in MUTATIONS for item in operations[index + 1:]):
            errors.append("concurrent completed round was overwritten")
    if name == "published_marker_recovers_after_label_failure" and not state["failed_label"]:
        errors.append("label failure recovery was not exercised")
    if name == "new_findings_publish_one_pinned_batch":
        text = " ".join(item["body"] + " " + json.dumps(item["comments"]) for item in publications)
        if not all(value in text for value in ("200", "201", "400", "500")):
            errors.append("new batch lacks concrete evidence for the introduced response defects")
    return errors


def main():
    case = json.loads(sys.argv[1])
    common = Path(subprocess.check_output(["git", "rev-parse", "--git-common-dir"], text=True).strip()).resolve()
    root = common / "fake-forge"
    state = json.loads((root / "state.json").read_text())
    operations = [json.loads(line) for line in (root / "operations.jsonl").read_text().splitlines()]
    errors = assess(case, state, operations)
    if subprocess.run(["git", "diff", "--exit-code", "HEAD"], capture_output=True).returncode:
        errors.append("reviewer changed tracked source")
    assert not errors, "; ".join(errors)
    print("PASS reviewer operations, comparison binding, threads and finalization")


if __name__ == "__main__":
    main()
