# Implement a selected issue

Use only for an authorized issue designation, issue comment, or manual issue
request. This sequence finds or creates the issue's implementation PR.

1. Read repository guidance and current working state. List open PRs before
   editing to find overlapping implementations. If an existing PR covers the
   scope, end this issue sequence and apply the read-only gate in
   [feedback-authority.md](feedback-authority.md). Continue eligible work through
   [pr-feedback.md](pr-feedback.md). If it has neither developer provenance nor
   designation, report the overlap on the issue and request designation.
2. Inspect the checkout and local branch history before creating
   `codex/issue-<number>-<slug>`. Preserve dirty checkouts, branches belonging to
   other tasks, and local-only commits; use a separate worktree from the fetched
   default branch when any are present. Reuse an existing task branch only when
   its ownership and scoped contents are established. Read and follow
   [verification.md](verification.md) for acceptance, test-first
   implementation, local verification, and final-commit CI.
3. Commit only the scoped files and push the branch before creating the PR.
   After any commit hook or formatter runs, re-check `git status --short` and
   `git rev-parse HEAD`; a hook can rewrite files or alter the commit content.
   If hooks changed the verified content, repeat the affected verification.
   Confirm the pushed remote branch equals that exact verified SHA before using
   it in the PR body.
4. Immediately before creating the PR, re-fetch the issue and all its comments.
   Reconcile updates under the parent skill's authorization rules and address them in
   the implementation and PR. Run relevant checks and commit and push any
   resulting changes before creating the PR.
5. Write the PR body to a temporary Markdown file and pass it with `gh-app --repo OWNER/REPO -- pr create
   --body-file`. Its body starts with
   exact `<!-- hermes-origin: developer -->` marker and includes the issue marker
   `<!-- hermes-issue: OWNER/REPO#NUMBER -->` for the original issue, plus a
   link to the issue, criterion-by-criterion acceptance evidence, observed
   red/green commands and results where applicable, final local checks,
   verification gaps, risks, and the current head SHA. Report CI as pending
   until the final-commit CI gate has passed.
   Leave the `in-review` transition on the issue and PR to the reviewer.
6. Verify the PR exists and links the issue. Complete final-commit CI in
   [verification.md](verification.md), then complete the issue reaction
   transition in [reactions.md](reactions.md). Delivery is complete only
   when the verified local commit, remote branch, PR head, and passing CI agree.
