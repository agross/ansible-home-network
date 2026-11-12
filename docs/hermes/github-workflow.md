# Intended GitHub workflow

1. A human labels an existing issue `ready-for-agent`. The developer verifies
   the issue and its current designation, implements behavior changes test-first,
   maps acceptance criteria to verification evidence, and opens a pull request
   linked to the issue. The developer verifies that the remote branch and open
   PR match the verified commit and waits for required CI on that final commit
   before marking implementation complete.
2. The reviewer sets `in-review` on the pull request and its identifiable
   original issue, reviews the current head, and submits a GitHub pull request
   review comment containing a result for that head. The developer does not
   set `in-review` when opening the PR.
3. If the review is clean, the reviewer removes `in-review` from the pull
   request and its identifiable original issue, and sets `needs-human` on the
   PR. The developer assigns the PR to the original issue author for human
   follow-up only after verifying required CI still passes for the current head.
4. If the review comment has findings, hand the pull request back to the
   developer. The developer addresses the findings, pushes an updated head,
   and the reviewer reviews it again. Repeat until the result is clean.

The GitHub Apps must be installed on the repository, and their webhooks must
reach the developer and reviewer routes. The developer receives issue-label,
issue-comment, and submitted-review events; the reviewer receives pull request events. Each route
accepts only configured installation IDs.

When an issue still has `ready-for-agent`, a new comment by a human with
repository write or admin access can resume work without removing and readding
the label. The developer re-fetches the issue and comment, checks the comment's
author against the event sender, and verifies the author's current repository
permission before acting. Bot comments and PR conversation comments do not
trigger this issue-comment path. Enable the GitHub App's Issue comment event
subscription for delivery.

## Verification

The configured routes and profile instructions cover issue selection, PR
creation, review submission, findings handoff, and clean handoff. New
pull requests carry a marker identifying the original issue; the developer
fetches its author, assigns that user to the PR, and verifies the assignment.
If the original issue or author cannot be identified or assigned, the PR stays
`needs-human` and the incomplete handoff is reported.

The developer's verification contract is in
[`verification.md`](../../templates/hermes-agent/hermes/templates/app/profiles/developer/skills/development/github-issue-to-pr/references/verification.md).
It applies to initial implementation and feedback repairs. Reports include
observed red/green evidence when applicable, acceptance coverage, published
commit identity, and required-check evidence. Missing or stale checks block
completion; CI clearance remains separate from independent reviewer approval.

Skill deployment preserves existing files with `force: false`. Updating these
repository templates does not replace an existing live `SKILL.md`; reconcile
the existing developer skill with this version when rolling out the change.

Focused Sevro operation evals and fixture checks are documented in
[`evals/developer`](../../evals/developer/README.md). They execute the skill through
an isolated Codex surrogate with fake GitHub App commands and local Git remotes.
They retain all eight authorization, repair, and CI scenarios, but do not verify
live Hermes execution, GitHub authentication, or webhook delivery.

Reviewer findings are handed back by the submitted review event. The reviewer
does not add `ready-for-agent` to developer-origin PRs, avoiding a second
handoff event. Live webhook delivery and agent behavior remain unverified.

Developer origin requires both the body marker and verified PR creation by the
configured developer App bot. A human-created PR with a copied marker still
requires `ready-for-agent` for developer work. Both profiles resolve bot identity
from trusted local profile configuration and GitHub account IDs.

Before changing labels, reactions, or a checkout for PR feedback, the developer
verifies the triggering review's author and classifies the work. Humans with
current repository write/admin access can request concrete scope changes,
subject to stricter repository approval rules. The configured reviewer App can
request in-scope repairs. Unauthorized and informational events leave workflow
state untouched; verified clean reviewer results can initiate human handoff.
An authorized repair clears `needs-human` for both verified developer-origin
and designated PRs before editing, retaining any designation. This permits
review of the updated head even when repair resumes after a prior human handoff.

## Handing an existing PR to the developer

1. Put the requested corrections in a GitHub pull request review or review
   comments, then apply `ready-for-agent` to the PR. The label is the explicit
   developer handoff for a PR without verified developer provenance. If it is
   already present, applying it again does not create a new label event; submit
   a PR review to trigger the feedback route, or remove and reapply the label.
2. The developer re-fetches the PR, confirms the designation remains present,
   reads submitted reviews, issue comments, and open review threads. The
   reviewer owns the `in-review` transition. Concrete requests from verified
   maintainers can define the repair scope, including requests in general
   `COMMENT` review bodies. The developer stops on genuine unresolved ambiguity
   or conflicting instructions.
3. The developer checks out the current PR head, applies the corrections, runs
   relevant checks, and pushes to the existing head branch without force-pushing
   or replacing the PR. The GitHub App needs write access to that head branch;
   fork or branch restrictions can prevent the push. The developer preserves
   local-only commits and dirty or unrelated checkouts, preparing a separate
   worktree at the current PR head when needed. It verifies head-repository
   access before editing and pushes to that repository's explicit HTTPS URL;
   a fork repair never falls back to pushing a branch in the base repository.
4. A new head triggers review. A clean reviewer result leads to `needs-human`;
   the developer attempts to assign the original issue author if the original
   issue can be identified. If no linked issue exists or assignment fails, the
   handoff remains incomplete and is reported.

A submitted review produces a `pull_request_review` event; an ordinary PR
conversation comment alone does not match the developer route. Apply the label
after posting such a comment to initiate the handoff. Concrete authorized requests
in submitted general review bodies start repairs; informational or already-fixed
requests do not create duplicate repair commits. Live delivery and execution
remain unverified.

## Reviewer comparison and recovery

The reviewer pins PR HEAD, base ref, and merge base for the three-dot comparison.
An advancing target tip alone does not invalidate review when this basis stays
unchanged. A changed HEAD stops the old session; a newer coalesced webhook owns
the new revision. A changed merge base or base ref with the same HEAD triggers
reassessment in the current session, with at most two restarts. Further changes
block publication and require a fresh stable review.

The reviewer stages findings locally and publishes one COMMENT review through
its packaged `review_round.py` helper, attached to the assessed commit. The
helper guards writes against the pinned comparison, serializes local publication,
and records comparison and receipt markers alongside the existing result marker.
It reconciles ambiguous accepted publication by receipt rather than blindly
resubmitting. A matching review does not prove workflow finalization completed:
a later webhook resumes missing labels and reactions without reposting findings.
Legacy result markers lacking comparison metadata require explicit reconciliation.
Remote API writes are not atomic with branch updates; post-write checks stop
subsequent stale effects if a revision races a write.

A clean result requires verification of every outstanding requested correction.
The reviewer may resolve verified threads by humans or Apps. Unfixed or uncertain
threads remain open and prevent clean handoff. The helper preserves unrelated
labels and other actors' reactions. GitHub App access, route filters, webhook
coalescing, and the existing developer handoff remain in place.

The reviewer skill's [helper contract](../../templates/hermes-agent/hermes/templates/app/profiles/reviewer/skills/development/github-pr-review/references/review-round.md)
and [Sevro evals](../../evals/reviewer/README.md) document the operations and 16
identity, author eligibility, race, thread, publication, and recovery scenarios. Deployment must
reconcile existing reviewer skill files too: `force: false` preserves live files instead
of overwriting them with changed templates.

## GitHub App identity configuration

Profile names and GitHub App slugs are separate. This installation's developer
and reviewer Apps are `agross-developer` and `agross-reviewer`; inventory sets
those exact values in `github_app.app_slug`. App credentials determine the real
GitHub identity. A local slug such as `reviewer` does not change the authenticated
App and can resolve a different, valid GitHub bot account.

The reviewer helper compares trusted configuration with the authenticated
`hermes-github-app status --format json` result's `app.slug` before writes. It
blocks mismatches or missing identity metadata. Configuration-derived
`auth.app_slug` and `auth.actor_expected` are not independent identity evidence.
This prevents successful reactions from being rejected under another bot's ID
and prevents misidentifying developer-created PRs as human PRs.

Rollout must update both profile configurations and reconcile the existing
reviewer skill/helper because skill files are preserved with `force: false`.
After rollout, a fresh eligible webhook can resume a PR left `in-review` with an
eyes reaction; no source change or manual lifecycle reset is needed. Existing
reviews on other PRs must not be replayed or modified as part of that recovery.

The reviewer accepts eligible PRs regardless of author, including Renovate, and
does not require developer provenance, a linked issue, or `ready-for-agent`.
Provenance and designation control developer repair delegation after review.
The identity guard checks the authenticated reviewer App, never whether the PR
was created by that App or by the developer. Findings on undesignated Renovate
PRs are published normally and handed to a human; designation can explicitly
authorize the developer to address them afterward.
