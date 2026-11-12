# GitHub access and lifecycle labels

For every GitHub command, use `gh-app --repo OWNER/REPO --` before the
`gh` arguments. Use `git-app --repo OWNER/REPO --` for GitHub clone, fetch,
ls-remote, and push over HTTPS; never use SSH or bare authenticated Git.
Pass `-c credential.helper=` immediately after the wrapper's `--` for each
GitHub Git operation so stored human credentials cannot override askpass.
Set `HERMES_HOME=/opt/data/profiles/developer` for terminal and subagent
commands. Before writes run `hermes-github-app status --repo OWNER/REPO`;
stop if identity or repository access fails. Never use a human GitHub login.
Set the repository-local Git author name to `APP_SLUG[bot]` and email to the
bot's GitHub noreply address before committing, using its numeric user ID.
Pass the same rules to subagents. Report app slug, installation ID, repository,
operation and URL for writes.

Pass `--repo OWNER/REPO` to repository-scoped `gh` subcommands as well as
selecting the wrapper repository, especially before checkout. For example,
use `gh-app --repo OWNER/REPO -- issue comment NUMBER --repo OWNER/REPO --body-file FILE`.
The wrapper selects App credentials; the subcommand still needs an explicit
repository when no local Git checkout is available. Read back the created
comment through its returned API identity before reporting it as posted.

## Lifecycle labels

A work item has at most one lifecycle label: `implementing`,
`in-review`, or `needs-human`. `ready-for-agent` is the
designation label and may coexist with a lifecycle label. When changing state, remove
other lifecycle labels first. When setting labels through
`PATCH repos/OWNER/REPO/issues/NUMBER`, fetch the current labels first and send
the full desired set: preserve every non-Hermes label, retain authorized role
labels, and include exactly one lifecycle label. The endpoint replaces the
entire label set, so sending only lifecycle labels silently removes unrelated
classification. Send `labels` as a JSON array: write `{"labels":[...]}` to a
temporary JSON file and use `gh-app --repo OWNER/REPO -- api --input FILE`, or use repeated
`--field 'labels[]=NAME'` fields when every desired label is already known. Never
pass serialized JSON through `--raw-field labels=...`, because GitHub receives
a string rather than an array and rejects the request. Read back the item after
the mutation. Before an API write, verify that the temporary payload was written
successfully and contains the intended data. If the write fails, stop: an older
payload at the same path could apply stale labels or content. Use a new
task-specific path or rebuild and verify the payload before retrying.

