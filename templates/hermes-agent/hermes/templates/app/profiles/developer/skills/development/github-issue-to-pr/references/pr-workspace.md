# Preserve local work and publish to the PR head

Use only after the parent skill's read-only feedback gate authorizes a repair.
Keep the existing PR and its remote branch name, including for a fork PR.

## Bind the destination before editing

Fetch the PR through the base repository and record its number, open state,
`head.repo.full_name`, `head.ref`, and `head.sha` (or equivalent GraphQL fields).
Keep `BASE_OWNER/BASE_REPO` separate from `HEAD_OWNER/HEAD_REPO` throughout.
Construct the HTTPS Git URL from the fetched head repository's validated owner
and repository names on the same trusted GitHub host. Treat branch names as
quoted data and validate them with `git check-ref-format --branch`.

Run `hermes-github-app status --repo HEAD_OWNER/HEAD_REPO` and inspect the
authenticated head-repository access before editing. Require the developer App
identity and Contents write capability for that destination. A deleted fork,
missing head branch, unavailable installation, or unverified write access blocks
repair publication; report it instead of using the base repository or human
credentials. Branch rules can still reject a later push; report that rejection.

Fetch the actual head branch through
`git-app --repo HEAD_OWNER/HEAD_REPO -- -c credential.helper= fetch HEAD_URL refs/heads/HEAD_BRANCH`
with the validated URL and quoted ref substituted. Require the fetched commit
and a freshly fetched PR head to equal the recorded SHA. If the head moved,
refresh the binding and reconcile feedback before editing.

## Preserve the checkout and local commits

Inspect `git status --short`, the current branch, and local history relative to
the fetched PR head. A clean working tree does not establish that local commits
are published or belong to this task. Reuse a checkout only if it is clean,
belongs to this repair, and its HEAD equals the fetched PR SHA.

Otherwise preserve the existing branch, commits, index, and untracked files and
create a separate worktree at the fetched SHA. Use an unused
`codex/issue-<number>-<slug>` local branch name; use the PR number when no linked
issue exists, and add a unique suffix on collision. Leave existing branch tips
intact. Never reset, stash, delete, or force-move an existing branch to prepare
the repair. If local-only commits appear to be an unfinished attempt at this
same repair, report them and establish whether to resume them before duplicating
the work; do not publish them merely because they exist.

The prepared repair checkout must start at the current PR head with unrelated
local work preserved. Follow the parent's verification contract for all edits.

## Publish only to the bound destination

After local verification, re-fetch the PR metadata and actual head branch.
Require the same open PR, head repository, branch, and starting SHA before
pushing. If another actor advanced the branch, preserve the candidate and
reconcile the new head before publication; do not overwrite it.

Push using an explicit destination URL and refspec, with the App installation
selected for the head repository:

```sh
git-app --repo HEAD_OWNER/HEAD_REPO -- -c credential.helper= push HEAD_URL HEAD:refs/heads/HEAD_BRANCH
```

Substitute the bound HTTPS URL and quote the URL and refspec. This must be a
non-force push to the existing head branch. `origin` is not the destination
unless independently verified to be exactly that head repository; use the
explicit URL above even when it matches. Keep PR queries and labels addressed
to the base repository.

Verify publication with
`git-app --repo HEAD_OWNER/HEAD_REPO -- -c credential.helper= ls-remote HEAD_URL refs/heads/HEAD_BRANCH`
and a fresh PR query through the base repository. Both must equal the locally
verified commit before final-commit CI can clear delivery. Report both repository
identities and both branch names when the local and remote names differ.
