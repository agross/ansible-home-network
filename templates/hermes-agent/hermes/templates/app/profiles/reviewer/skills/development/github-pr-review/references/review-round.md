# Guarded reviewer operations

Resolve `scripts/review_round.py` relative to the loaded skill. Use the mapped
reviewer `HERMES_HOME` and trusted configured App slugs; the script uses only
`gh-app` and `hermes-github-app` for forge access. The parent skill owns evidence,
thread correction judgments, restart accounting, and allowed webhook entry.

## App identity

App credentials choose the authenticated identity. The local `app_slug` setting
only tells the helper which bot to resolve; it cannot rename the GitHub App.
The helper requests `hermes-github-app status --repo OWNER/REPO --format json`
and requires its authenticated `app.slug` to match the supplied trusted reviewer
slug. Missing or mismatched metadata blocks before label/reaction writes. Correct
the profile configuration and reload it before resuming; do not bypass this check.
For this installation, profile `reviewer` uses App `agross-reviewer`, and profile
`developer` uses App `agross-developer`. Other installations must use their own
App slugs. Bot numeric IDs remain the authority for author/reaction ownership.

## Inspect and begin

```sh
python3 "<skill-root>/scripts/review_round.py" inspect --repo OWNER/REPO --number NUMBER --reviewer-app REVIEWER_SLUG
```

Inspection returns the current PR, pinned comparison basis, every thread and
comment page, and any authenticated matching reviewer result. Incomplete or
repeated pagination is a blocker, never evidence for a clean result.

Write a temporary JSON plan. Initially it needs `basis` copied from inspection
and `issue_number` when the original issue has been verified. Then call:

```sh
python3 "<skill-root>/scripts/review_round.py" begin --repo OWNER/REPO --number NUMBER --reviewer-app REVIEWER_SLUG --plan PLAN_FILE
```

Follow `stale_head`, `basis_changed`, `ineligible`, `busy`, or `blocked` as stopping
statuses under the parent skill's policy. `resume` selects existing-result recovery;
it does not authorize another assessment publication. A normal `begun` starts
assessment against the returned unchanged basis.

## Apply the verified plan

The completed plan has this shape. Replace the example hashes, issue, paths,
and evidence with the actual inspection and assessment; use empty comment and
resolution arrays when none are needed.

```json
{
  "basis": {"head": "<assessed SHA>", "merge_base": "<merge-base SHA>", "base_ref": "main"},
  "issue_number": 7,
  "state": "clean",
  "body": "Reviewed scope, standards and acceptance evidence, checks, limitations and risks.",
  "comments": [],
  "resolved_threads": [
    {"id": "<PR-owned thread ID>", "evidence": "Requested correction verified in pinned code and focused check."}
  ]
}
```

For new inline findings, put GitHub review-comment objects (`path`, `line`,
`side`, `body`) in `comments`. Existing actionable threads remain open instead
of receiving duplicate findings. General findings may go in the review body.
For a PR without developer provenance or designation (including Renovate), append: `You can address this
feedback yourself. To delegate it, apply ready-for-agent to this PR.`

```sh
python3 "<skill-root>/scripts/review_round.py" apply --repo OWNER/REPO --number NUMBER --reviewer-app REVIEWER_SLUG --developer-app DEVELOPER_SLUG --plan PLAN_FILE
```

The script generates the existing workflow marker unchanged:

- `<!-- hermes-reviewer: reviewed-sha=<sha> state=changes-requested -->`
- `<!-- hermes-reviewer: reviewed-sha=<sha> state=clean -->`

It adds `hermes-review-basis` metadata and an exact draft receipt to distinguish
the assessed comparison and reconcile uncertain submission. The body is sent
through a temporary JSON file, preserving Markdown and avoiding shell expansion.
The PR-wide nonblocking `flock` lives under the reviewer's profile home and spans
one helper operation. A crash releases the OS lock; the file is retained to
avoid splitting locks across different inodes. This serializes sessions sharing
that home on this host, not reviewers on unrelated hosts.

A current marker without comparison metadata is a reconciliation blocker rather
than evidence for republishing. A matching result resumes its original verdict
and finalization. `complete` or `already_complete` means all readbacks succeeded.
Other statuses report partial effects without authorizing rollback, repeated
publication, stale cleanup, or changes outside reviewer authority. Remote HEAD
changes cannot be made atomic with GitHub API writes; pre/post guards detect
drift and stop dependent effects rather than claiming a completed new-head review.
