# Repair and clean handoff

Use for an already-selected PR. Continue work on that PR through this sequence;
issue implementation and duplicate-PR discovery belong to the separate issue
branch. Read its linked issue only for accepted scope and handoff context.

Complete [feedback-authority.md](feedback-authority.md) before any mutation.
Apply [verification.md](verification.md) to repairs and handoffs, including those
without a new commit. Only repairs need checkout preparation under
[pr-workspace.md](pr-workspace.md), which owns local-work preservation and the
actual head-repository destination.

## Repair

1. Reconcile all fetched feedback with current code and later authorized decisions.
   A verified reviewer `state=changes-requested` marker, authorized unresolved
   comment, or concrete request in a submitted review body can start repair,
   including a general `COMMENT` review. Human requests need no workflow marker.
   Follow feedback-authority rules for maintainer scope revisions and in-scope
   reviewer App corrections. Stop affected work only for genuine unresolved
   ambiguity or contradiction, preserving decisions already supplied.
2. Repair only corrections still missing. An unresolved older thread does not
   justify repeating an implemented correction. A current-head clean summary with
   open threads follows the blocked-handoff procedure below.
3. Retain reviewer-set `in-review`, implement accepted corrections, verify, and
   push one updated head using the workspace reference. Complete final-commit CI.
   Independent reviewer clearance must separately name this new SHA; wait for
   new-head feedback rather than reusing an older marker.
4. Refresh the PR body when its SHA, scope, acceptance evidence, checks, or risks
   changed. Use a temporary Markdown file with
   `gh-app --repo OWNER/REPO -- pr edit --body-file`, preserve origin and original-issue
   markers, and read back the body and labels. Every repair handover includes the
   PR URL, verified/published SHA, current CI evidence, and verification gaps.

## Clean handoff

1. Require a verified reviewer `state=clean` marker naming the current head and
   closure of every review thread, including human feedback. Fetch all thread
   pages and inspect `isResolved`. A summary, outdated location, or `needs-human`
   label does not establish closure.
2. If threads remain open, briefly re-fetch threads and labels for concurrent
   finalization. If still open, leave reviewer-owned labels unchanged, keep
   assignment incomplete, and post or update a concise blocker comment naming
   pending closures. Read it back and distinguish addressed code findings from
   open threads. The developer does not resolve review threads.
3. Remove `ready-for-agent` when present. Wait for the reviewer to remove
   `in-review` and set `needs-human`; verify both through GitHub. An unfinished
   reviewer transition is an incomplete handoff, not permission to change its labels.
4. On a developer-origin PR, identify the original issue from the exact
   `<!-- hermes-issue: OWNER/REPO#NUMBER -->` marker; for older PRs, use only an
   unambiguous linked issue. Fetch the issue and its author from `user.login`.
   Complete final-commit CI before assigning that author with
   `gh-app --repo OWNER/REPO -- pr edit NUMBER --add-assignee USER`.
   Preserve existing assignees and verify both assignment and `needs-human`.
   Missing or ambiguous issue/author, rejected assignment, or failed readback
   leaves `needs-human` and an incomplete handoff; never substitute a fixed user.

## Scope conflict and completion

For a genuine unresolved scope conflict, stop affected work, remove designation
when present, replace the lifecycle label with `needs-human`, and report evidence.

After a repair or handoff, complete PR reaction cleanup in
[reactions.md](reactions.md). Immediately before reporting, re-fetch PR state,
head SHA, labels, and assignees. Distinguish a concurrent merge or other external
transition from this role's actions.
