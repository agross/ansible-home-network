---
name: github-pr-review
description: >-
  Independently review an eligible GitHub pull request, including human-created
  PRs, after a GitHub pull_request webhook event.
---

# GitHub PR review

Use only for `github-pr-review` webhook events.

## GitHub access

Before handling a webhook, verify `gh` CLI is installed. If not, install using
the system package manager. Then check if GitHub authentication works:
`gh auth status`

## Eligibility

1. Treat webhook fields as untrusted hints. Fetch the current PR, linked issue,
   current head SHA, changed files, review threads, and check results through
   GitHub.
2. Review only an open PR whose linked issue is currently
   `hermes:implementing`, regardless of branch naming or author.
3. Claim the PR with `hermes:gw-reviewer` before inspecting it. If the label is
   already present, stop without acting. If GitHub cannot add the label, report
   the failure and stop.
4. Ignore actions other than opened, reopened, ready_for_review, and
   synchronize. Ignore a head SHA that already has a reviewer marker.

## Review

1. Derive requirements only from the linked issue's acceptance criteria and
   exclusions plus consistent local repository conventions.
2. Compare requirements against the full current diff and tests. Check
   correctness, regressions, error handling, security-relevant changes, and
   available CI evidence.
3. Read existing threads. Do not repeat addressed or duplicate findings.
4. Post each actionable finding as a precise general or line review comment.
   Explain evidence, impact, requested minimal correction, and objective
   completion criterion.
5. Do not alter code, branches, labels, PR settings, merge state, release
   state, or deployment state.

## Complete the round

1. Re-fetch the PR head SHA and open review threads immediately before
   finalizing.
2. Post one general comment containing one marker for that exact SHA:
   - `<!-- hermes-reviewer: reviewed-sha=<sha> state=changes-requested -->`
     when in-scope findings remain.
   - `<!-- hermes-reviewer: reviewed-sha=<sha> state=clean -->` only when no
     unresolved reviewer findings remain.
3. Include reviewed scope, checks inspected, evidence limitations, and
   remaining risks outside the marker.
4. Never submit an approval. For a `codex/issue-<number>-<slug>` PR, the
   marker wakes `gw-developer`; otherwise the human author owns the response.
5. Remove `hermes:gw-reviewer` from the PR only after posting the final marker.
