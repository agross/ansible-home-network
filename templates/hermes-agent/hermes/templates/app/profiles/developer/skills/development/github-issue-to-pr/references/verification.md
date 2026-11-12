# Verification for issue delivery and repairs

Use this contract for initial implementation, each feedback repair, and final
handoff. Keep the parent skill's GitHub App wrappers, authorization, lifecycle
labels, reactions, reviewer ownership, and webhook rules throughout.

## Bind acceptance before editing

Record the accepted scope, material acceptance criteria, exclusions, observable
entrypoints, and relevant repository lint, type, build, and test commands. Map
each criterion to an independent expected result and a check or other evidence.
Read repository guidance and CI configuration to identify required checks and
checks needed for the changed scope. Resolve missing product decisions through
the parent skill's issue-selection rules before dependent implementation.

## Develop behavior changes test-first

For new behavior and reproducible bug fixes, work in successive red/green slices:

1. Write one focused regression test through a documented or accepted public
   API, command, UI, event, or file-format boundary. Derive the expected result
   from acceptance or a known-good example, independently of the implementation.
2. Run the focused command before changing product behavior. Require a failure
   caused by the intended missing behavior. Syntax errors, broken fixtures,
   missing dependencies, and unrelated failures do not establish red.
3. Record the literal command and relevant failure. Make the smallest scoped
   product change, then rerun the identical command and record its passing result.
4. Only after green, refactor if useful and rerun affected checks, or begin the
   next behavior slice. Preserve the ordered red/green evidence for the PR.

Tests must exercise the real behavior and assert an observable result; avoid
private implementation details, assertions that repeat the production algorithm,
or mocks replacing the subject under test. A test added after implementation
does not establish test-first red.

For behavior-preserving refactors, establish a passing baseline and rerun it
afterward. For documentation or configuration-only work without executable
behavior, use applicable validators and concrete acceptance inspection; report
TDD as not applicable with the reason. If a behavior change lacks a viable
harness, public boundary, or independent expected result, report the exact gap
and stop affected implementation rather than inventing TDD evidence or building
unrelated test infrastructure.

## Verify the candidate before publication

Run applicable final lint, type, build, and test gates after the last edit.
Inspect the complete diff against repository standards, accepted scope, and
exclusions. Account for every material criterion with observed evidence or an
explicit gap. Preserve commands, results, pre-existing failures, and limitations.
A passing suite or review alone cannot prove an unassessed criterion.

Resolve failed required local gates and missing acceptance evidence before
publication. When blocked, report the missing evidence and smallest next action;
leave unrelated tests and repository checks intact. If acceptance or candidate
content changes, refresh the affected evidence before committing and pushing.
Independent approval remains owned by the existing reviewer workflow; developer
self-inspection does not replace it or authorize reviewer-owned transitions.

## Require CI on the final published commit

After creating the PR or pushing a repair:

1. Record the intended locally verified commit. Re-fetch the PR's URL, state,
   head repository, head branch, and `headRefOid`. Require an open PR whose head
   and actual remote head branch both equal that commit. Use the parent skill's
   authenticated `git-app ... ls-remote` verification against the actual head
   repository, including for a fork. Resolve a mismatch before claiming completion;
   preserve intervening work and publish intended commits without force.
2. Discover the required checks for the current PR base, including applicable
   branch protection and rulesets where accessible, and reconcile them with
   repository guidance and CI configuration. Use
   `gh-app --repo OWNER/REPO -- pr checks NUMBER --repo OWNER/REPO --required`
   to inspect required check results. Query review/comments metadata separately
   from CI metadata so an unavailable optional field cannot hide both.
3. Use
   `gh-app --repo OWNER/REPO -- run list --repo OWNER/REPO --commit HEAD_SHA`
   for Actions evidence and run URLs. A run listing alone does not enumerate
   every required job or external status. Inspect required check runs and commit
   statuses too, binding each result to the current PR head or its verified
   GitHub test-merge commit. For test-merge checks, verify the merge commit was
   generated for this head and the current base. Refresh after either changes.
4. Observe pending work to completion while the session permits, using
   `gh-app --repo OWNER/REPO -- run watch RUN_ID --repo OWNER/REPO --exit-status`
   for Actions runs, then re-query required checks and their commit identities.
   Repair only failures within the authorized scope, following the same local
   verification and publication gates. Each new commit invalidates earlier CI
   clearance. Preserve evidence and report a blocker if observation cannot finish.
5. Require affirmative passing results for every required check, plus any
   additional CI gate required by acceptance or repository guidance. Pending,
   failed, cancelled, skipped, neutral, missing, unavailable, or stale results
   do not establish passing CI. If no required checks exist, or required-check
   discovery is incomplete or denied, report that limitation and the observed
   checks; do not claim the required-CI gate passed.
6. Immediately before completion, re-fetch the PR and remote branch and confirm
   both still name the intended verified SHA, with current required checks passing.
   Update the PR body through a temporary file when its SHA, acceptance evidence,
   or recorded checks changed, preserving the parent skill's markers and reading
   it back. A concurrent head or base change requires refreshed verification;
   a merged or closed PR is an external transition, not this workflow's delivery.

Only a passed gate permits the initial issue's rocket reaction or a completed
repair/human handoff. A blocked or pending gate does not change reviewer-owned
labels or grant authority to merge, deploy, weaken checks, or change repository
settings. Keep CI clearance separate from current-head independent review and
thread resolution required by the parent skill.

Every handover after publication, including a blocker, includes the PR URL,
intended verified SHA, observed remote branch and PR head SHAs, required-check
results with evidence URLs, acceptance gaps, and the smallest remaining action.
Distinguish verified local behavior, published state, CI clearance, and independent
review so partial progress is never reported as completed delivery.
