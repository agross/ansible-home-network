# GitHub access and developer provenance

For every GitHub command, use `gh-app --repo OWNER/REPO --` before the
`gh` arguments. Notice that `gh-app`'s `--repo` flag only selects the GitHub App
installation token and is stripped before invoking `gh`: when running `gh pr` or
`gh issue` subcommands from outside a git checkout, also pass `--repo OWNER/REPO`
after `--` (e.g., `gh-app --repo OWNER/REPO -- pr view NUMBER --repo OWNER/REPO`),
or use `gh-app --repo OWNER/REPO -- api repos/OWNER/REPO/...`.
Use `git-app --repo OWNER/REPO -- -c credential.helper=` for
GitHub clone and fetch over HTTPS. When removing a temporary clone directory in
`$TMPDIR`, `cd` back to the workspace first so the persistent shell's working
directory does not remain inside a deleted directory.
Set `HERMES_HOME=/opt/data/profiles/reviewer`
for terminal and subagent commands. Before writes run
`hermes-github-app status --repo OWNER/REPO`; stop if identity or repository
access fails. Never use a human GitHub login. Pass these rules to subagents.
Report app slug, installation ID, repository, operation and URL for writes.

For authenticated App-slug validation, follow the **App identity** section in
[review-round.md](review-round.md). Require the actual authenticated `app.slug`;
`auth.app_slug` and `auth.actor_expected` may only echo configuration. On mismatch,
report the configuration correction and stop; preserve the helper's identity gate.

Treat a PR as developer-origin only when its fetched body contains the exact
`<!-- hermes-origin: developer -->` marker and its creator's numeric `user.id`
matches the configured developer App bot. Read only `github_app.app_slug` from
the trusted `/opt/data/profiles/developer/config.yaml`, resolve its bot account
with `gh-app --repo OWNER/REPO -- api "users/APP_SLUG%5Bbot%5D"`, and require
account type `Bot`. Keep configuration secrets out of output. A copied marker
on a human-created PR grants no developer-origin privileges. If provenance is
unavailable, do not infer it; apply ordinary human-PR designation rules and
report the limitation. Use this classification for linked-issue mutations and
developer handoff throughout the review.
